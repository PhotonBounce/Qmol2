from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import List, Annotated

from src import shape3d, keys as keysdb
from src.dependencies import check_quota, record_usage

router = APIRouter(tags=["shape3d"])


class Shape3DIn(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {"smiles": ["CCO"]}
        }
    )
    smiles: List[str] = Field(..., min_length=1, max_length=500)

    @field_validator("smiles")
    @classmethod
    def validate_smiles(cls, v: List[str]) -> List[str]:
        from rdkit import Chem
        invalid = [s for s in v if Chem.MolFromSmiles(s) is None]
        if invalid:
            raise ValueError(f"Invalid SMILES: {invalid[:5]}")
        return v


@router.post("/shape3d")
def shape3d_endpoint(
    body: Shape3DIn,
    x_api_key: Annotated[str | None, Header()] = None,
):
    """3D shape descriptors from generated conformer."""
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing x-api-key header")
    info = keysdb.lookup(x_api_key)
    if not info or not info.active:
        raise HTTPException(status_code=401, detail="Invalid or inactive API key")
    from src.dependencies import _rl
    _rl(f"shape3d:{x_api_key}", limit=20, window=60.0)
    charge = 5 * len(body.smiles)
    used, quota = check_quota(x_api_key, charge)
    try:
        results = shape3d.compute_batch(body.smiles)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    record_usage(x_api_key, "/shape3d", charge)
    return {"results": results, "quota_charged": charge}
