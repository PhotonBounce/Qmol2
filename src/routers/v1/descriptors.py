from fastapi import APIRouter, Header, HTTPException, Depends
from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import List, Annotated

from src import descriptors, keys as keysdb
from src.dependencies import check_quota, record_usage, require_api_key

router = APIRouter(tags=["descriptors"])


class DescriptorsIn(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "smiles": ["CCO", "c1ccccc1"],
                "names": ["MolWt", "MolLogP"],
            }
        }
    )
    smiles: List[str] = Field(..., min_length=1, max_length=5000)
    names: List[str] | None = Field(default=None, max_length=300)

    @field_validator("smiles")
    @classmethod
    def validate_smiles(cls, v: List[str]) -> List[str]:
        from rdkit import Chem
        invalid = [s for s in v if Chem.MolFromSmiles(s) is None]
        if invalid:
            raise ValueError(f"Invalid SMILES: {invalid[:5]}")
        return v


@router.get("/descriptors/names")
def descriptor_names():
    """Public: list every available RDKit 2D descriptor name (no auth)."""
    return {"n": len(descriptors.ALL_NAMES), "names": list(descriptors.ALL_NAMES)}


@router.post("/descriptors")
def descriptors_endpoint(
    body: DescriptorsIn,
    x_api_key: Annotated[str | None, Header(default=None)] = None,
):
    """Full RDKit 2D descriptor panel (~200 features) per molecule."""
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing x-api-key header")
    from src import ratelimit
    from src.dependencies import _rl
    _rl(f"desc:{x_api_key}", limit=60, window=60.0)
    info = keysdb.lookup(x_api_key)
    if not info or not info.active:
        raise HTTPException(status_code=401, detail="Invalid or inactive API key")
    charge = 2 * len(body.smiles)
    used, quota = check_quota(x_api_key, charge)
    try:
        results = descriptors.compute_batch(body.smiles, names=body.names)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    record_usage(x_api_key, "/descriptors", charge)
    return {"n": len(body.smiles), "results": results, "quota_charged": charge}
