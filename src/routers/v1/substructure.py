from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import List, Annotated

from src import substructure, keys as keysdb
from src.dependencies import check_quota, record_usage

router = APIRouter(tags=["substructure"])


class SubstructureIn(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "smarts": "[#6]-[#7]",
                "smiles": ["CCO", "c1ccccc1"],
                "max_hits": 10000,
            }
        }
    )
    smarts: str = Field(..., min_length=1)
    smiles: List[str] = Field(..., min_length=1, max_length=100000)
    max_hits: int = Field(10000, ge=1, le=100000)

    @field_validator("smiles")
    @classmethod
    def validate_smiles(cls, v: List[str]) -> List[str]:
        from rdkit import Chem
        invalid = [s for s in v if Chem.MolFromSmiles(s) is None]
        if invalid:
            raise ValueError(f"Invalid SMILES: {invalid[:5]}")
        return v


@router.post("/substructure")
def substructure_endpoint(
    body: SubstructureIn,
    x_api_key: Annotated[str | None, Header(default=None)] = None,
):
    """Find molecules matching a SMARTS pattern."""
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing x-api-key header")
    info = keysdb.lookup(x_api_key)
    if not info or not info.active:
        raise HTTPException(status_code=401, detail="Invalid or inactive API key")
    from src.dependencies import _rl
    _rl(f"sub:{x_api_key}", limit=30, window=60.0)
    n = len(body.smiles)
    used, quota = check_quota(x_api_key, n)
    try:
        hits = substructure.filter_smarts(body.smarts, body.smiles, max_hits=body.max_hits)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    record_usage(x_api_key, "/substructure", n)
    return {
        "n_input": n,
        "n_hits": len(hits),
        "hits": [{"smiles": h.smiles, "match_atoms": h.match_atoms} for h in hits],
        "quota_charged": n,
    }
