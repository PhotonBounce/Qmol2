from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import List, Annotated

from src import mcs, keys as keysdb
from src.dependencies import check_quota, record_usage

router = APIRouter(tags=["mcs"])


class MCSIn(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "smiles": ["CCO", "c1ccccc1"],
                "complete_rings_only": False,
                "ring_matches_ring_only": False,
                "timeout": 10,
            }
        }
    )
    smiles: List[str] = Field(..., min_length=2, max_length=1000)
    complete_rings_only: bool = False
    ring_matches_ring_only: bool = False
    timeout: int = Field(10, ge=1, le=60)

    @field_validator("smiles")
    @classmethod
    def validate_smiles(cls, v: List[str]) -> List[str]:
        from rdkit import Chem
        invalid = [s for s in v if Chem.MolFromSmiles(s) is None]
        if invalid:
            raise ValueError(f"Invalid SMILES: {invalid[:5]}")
        return v


@router.post("/mcs")
def mcs_endpoint(
    body: MCSIn,
    x_api_key: Annotated[str | None, Header()] = None,
):
    """Maximum Common Substructure."""
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing x-api-key header")
    info = keysdb.lookup(x_api_key)
    if not info or not info.active:
        raise HTTPException(status_code=401, detail="Invalid or inactive API key")
    from src.dependencies import _rl
    _rl(f"mcs:{x_api_key}", limit=20, window=60.0)
    n = len(body.smiles)
    used, quota = check_quota(x_api_key, n)
    try:
        res = mcs.find(
            body.smiles,
            complete_rings_only=body.complete_rings_only,
            ring_matches_ring_only=body.ring_matches_ring_only,
            timeout=body.timeout,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    record_usage(x_api_key, "/mcs", n)
    return {**res.to_dict(), "quota_charged": n}
