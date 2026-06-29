from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Annotated

from src.pharmacophore import modeler
from src import keys as keysdb
from src.dependencies import check_quota, record_usage

router = APIRouter(tags=["pharmacophore"])


class PharmacophoreIn(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={"example": {"smiles": "CCO"}}
    )
    smiles: str = Field(..., min_length=1)

    @field_validator("smiles")
    @classmethod
    def validate_smiles(cls, v: str) -> str:
        from rdkit import Chem
        if Chem.MolFromSmiles(v) is None:
            raise ValueError(f"Invalid SMILES: {v!r}")
        return v


@router.post("/pharmacophore")
def pharmacophore_endpoint(
    body: PharmacophoreIn,
    x_api_key: Annotated[str | None, Header()] = None,
):
    """Generate 2D pharmacophore fingerprint and feature list."""
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing x-api-key header")
    info = keysdb.lookup(x_api_key)
    if not info or not info.active:
        raise HTTPException(status_code=401, detail="Invalid or inactive API key")
    from src.dependencies import _rl
    _rl(f"pharmacophore:{x_api_key}", limit=120, window=60.0)
    used, quota = check_quota(x_api_key, 1)
    result = modeler.generate_pharmacophore(body.smiles)
    record_usage(x_api_key, "/pharmacophore", 1)
    return {"result": result, "quota_charged": 1}


@router.post("/pharmacophore/3d")
def pharmacophore_3d_endpoint(
    body: PharmacophoreIn,
    x_api_key: Annotated[str | None, Header()] = None,
):
    """Generate 3D pharmacophore features with coordinates."""
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing x-api-key header")
    info = keysdb.lookup(x_api_key)
    if not info or not info.active:
        raise HTTPException(status_code=401, detail="Invalid or inactive API key")
    from src.dependencies import _rl
    _rl(f"pharmacophore:{x_api_key}", limit=120, window=60.0)
    used, quota = check_quota(x_api_key, 1)
    result = modeler.smiles_to_pharmacophore_3d(body.smiles)
    record_usage(x_api_key, "/pharmacophore/3d", 1)
    return {"result": result, "quota_charged": 1}
