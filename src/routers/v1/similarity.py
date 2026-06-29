from fastapi import APIRouter, Header, HTTPException, Depends
from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import List, Annotated

from src import similarity, keys as keysdb, storage, ratelimit
from src.dependencies import check_quota, record_usage, require_api_key
import config

router = APIRouter(tags=["similarity"])


class SimilarityIn(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "smiles": "CCO",
                "top_k": 20,
                "min_similarity": 0.3,
            }
        }
    )
    smiles: str = Field(..., min_length=1)
    top_k: int = Field(20, ge=1, le=200)
    min_similarity: float = Field(0.3, ge=0.0, le=1.0)

    @field_validator("smiles")
    @classmethod
    def validate_smiles(cls, v: str) -> str:
        from rdkit import Chem
        if Chem.MolFromSmiles(v) is None:
            raise ValueError(f"Invalid SMILES: {v}")
        return v


class SimMatrixIn(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {"smiles": ["CCO", "c1ccccc1", "CCC"]}
        }
    )
    smiles: List[str] = Field(..., min_length=2, max_length=500)

    @field_validator("smiles")
    @classmethod
    def validate_smiles(cls, v: List[str]) -> List[str]:
        from rdkit import Chem
        invalid = [s for s in v if Chem.MolFromSmiles(s) is None]
        if invalid:
            raise ValueError(f"Invalid SMILES: {invalid[:5]}")
        return v


@router.post("/similarity")
def similarity_search(
    body: SimilarityIn,
    x_api_key: Annotated[str | None, Header(default=None)] = None,
):
    """Tanimoto search over the public dataset. Paid-only."""
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing x-api-key header")
    from src.dependencies import _rl
    _rl(f"sim:{x_api_key}", limit=60, window=60.0)
    info = keysdb.lookup(x_api_key)
    if not info or not info.active:
        raise HTTPException(status_code=401, detail="Invalid or inactive API key")
    CHARGE = 100
    used = keysdb.month_usage(x_api_key)
    if used + CHARGE > info.monthly_quota:
        raise HTTPException(
            status_code=402,
            detail=f"Quota would be exceeded ({used}/{info.monthly_quota})",
        )
    conn = storage.connect(config.DB_PATH)
    try:
        hits = similarity.search(conn, body.smiles, top_k=body.top_k,
                                 min_similarity=body.min_similarity)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        conn.close()
    keysdb.record(x_api_key, "/similarity", CHARGE)
    return {
        "query": body.smiles,
        "hits": [h.to_dict() for h in hits],
        "quota_charged": CHARGE,
    }


@router.post("/similarity/matrix")
def similarity_matrix(
    body: SimMatrixIn,
    x_api_key: Annotated[str | None, Header(default=None)] = None,
):
    """Pairwise ECFP4 Tanimoto matrix."""
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing x-api-key header")
    info = keysdb.lookup(x_api_key)
    if not info or not info.active:
        raise HTTPException(status_code=401, detail="Invalid or inactive API key")
    from src.dependencies import _rl
    _rl(f"simmatrix:{x_api_key}", limit=20, window=60.0)
    n = len(body.smiles)
    from src import teams, simmatrix
    used, quota = teams.effective_quota(x_api_key)
    if used + n > quota:
        raise HTTPException(status_code=402,
                            detail=f"Quota would be exceeded ({used}/{quota})")
    try:
        res = simmatrix.compute(body.smiles)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    keysdb.record(x_api_key, "/similarity/matrix", n)
    return {**res.to_dict(), "quota_charged": n}
