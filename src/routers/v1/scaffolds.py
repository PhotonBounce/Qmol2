from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import List, Annotated

from src import scaffolds, keys as keysdb
from src.dependencies import check_quota, record_usage

router = APIRouter(tags=["scaffolds"])


class ScaffoldIn(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "smiles": ["CCO", "c1ccccc1"],
                "top_k": 20,
            }
        }
    )
    smiles: List[str] = Field(..., min_length=1, max_length=50000)
    top_k: int = Field(20, ge=1, le=1000)

    @field_validator("smiles")
    @classmethod
    def validate_smiles(cls, v: List[str]) -> List[str]:
        from rdkit import Chem
        invalid = [s for s in v if Chem.MolFromSmiles(s) is None]
        if invalid:
            raise ValueError(f"Invalid SMILES: {invalid[:5]}")
        return v


@router.post("/scaffolds")
def scaffolds_endpoint(
    body: ScaffoldIn,
    x_api_key: Annotated[str | None, Header(default=None)] = None,
):
    """Bemis-Murcko scaffold clustering."""
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing x-api-key header")
    from src.dependencies import _rl
    _rl(f"scaf:{x_api_key}", limit=30, window=60.0)
    info = keysdb.lookup(x_api_key)
    if not info or not info.active:
        raise HTTPException(status_code=401, detail="Invalid or inactive API key")
    n = len(body.smiles)
    used, quota = check_quota(x_api_key, n)
    rows = scaffolds.analyze(body.smiles, top_k=body.top_k)
    record_usage(x_api_key, "/scaffolds", n)
    return {
        "n_unique_scaffolds": len(rows),
        "scaffolds": [r.to_dict() for r in rows],
        "quota_charged": n,
    }
