from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import List, Annotated

from src import stereoisomers, keys as keysdb
from src.dependencies import check_quota, record_usage

router = APIRouter(tags=["stereoisomers"])


class StereoIn(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "smiles": ["CCO"],
                "max_isomers": 64,
                "only_unassigned": True,
            }
        }
    )
    smiles: List[str] = Field(..., min_length=1, max_length=1000)
    max_isomers: int = Field(64, ge=1, le=1024)
    only_unassigned: bool = True

    @field_validator("smiles")
    @classmethod
    def validate_smiles(cls, v: List[str]) -> List[str]:
        from rdkit import Chem
        invalid = [s for s in v if Chem.MolFromSmiles(s) is None]
        if invalid:
            raise ValueError(f"Invalid SMILES: {invalid[:5]}")
        return v


@router.post("/stereoisomers")
def stereoisomers_endpoint(
    body: StereoIn,
    x_api_key: Annotated[str | None, Header()] = None,
):
    """Enumerate distinct stereoisomers."""
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing x-api-key header")
    info = keysdb.lookup(x_api_key)
    if not info or not info.active:
        raise HTTPException(status_code=401, detail="Invalid or inactive API key")
    from src.dependencies import _rl
    _rl(f"stereo:{x_api_key}", limit=30, window=60.0)
    charge = 2 * len(body.smiles)
    used, quota = check_quota(x_api_key, charge)
    try:
        results = stereoisomers.enumerate_batch(
            body.smiles, max_isomers=body.max_isomers,
            only_unassigned=body.only_unassigned,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    record_usage(x_api_key, "/stereoisomers", charge)
    return {"results": results, "quota_charged": charge}
