from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import List, Annotated

from src import diversity, keys as keysdb
from src.dependencies import check_quota, record_usage

router = APIRouter(tags=["diversity"])


class DiversityIn(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "smiles": ["CCO", "c1ccccc1", "CCC"],
                "k": 20,
                "seed": 42,
            }
        }
    )
    smiles: List[str] = Field(..., min_length=2, max_length=50000)
    k: int = Field(20, ge=1, le=10000)
    seed: int = 42

    @field_validator("smiles")
    @classmethod
    def validate_smiles(cls, v: List[str]) -> List[str]:
        from rdkit import Chem
        invalid = [s for s in v if Chem.MolFromSmiles(s) is None]
        if invalid:
            raise ValueError(f"Invalid SMILES: {invalid[:5]}")
        return v


@router.post("/diversity")
def diversity_endpoint(
    body: DiversityIn,
    x_api_key: Annotated[str | None, Header()] = None,
):
    """MaxMin Tanimoto-diversity pick."""
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing x-api-key header")
    info = keysdb.lookup(x_api_key)
    if not info or not info.active:
        raise HTTPException(status_code=401, detail="Invalid or inactive API key")
    from src.dependencies import _rl
    _rl(f"div:{x_api_key}", limit=20, window=60.0)
    n = len(body.smiles)
    used, quota = check_quota(x_api_key, n)
    try:
        res = diversity.pick(body.smiles, k=body.k, seed=body.seed)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    record_usage(x_api_key, "/diversity", n)
    return {**res.to_dict(), "quota_charged": n}
