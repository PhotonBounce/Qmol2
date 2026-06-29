from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Annotated

from src import conformers, keys as keysdb
from src.dependencies import check_quota, record_usage

router = APIRouter(tags=["conformers"])


class ConformerIn(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "smiles": "CCO",
                "n_conformers": 10,
            }
        }
    )
    smiles: str = Field(..., min_length=1)
    n_conformers: int = Field(10, ge=1, le=50)

    @field_validator("smiles")
    @classmethod
    def validate_smiles(cls, v: str) -> str:
        from rdkit import Chem
        if Chem.MolFromSmiles(v) is None:
            raise ValueError(f"Invalid SMILES: {v}")
        return v


@router.post("/conformers")
def conformers_endpoint(
    body: ConformerIn,
    x_api_key: Annotated[str | None, Header(default=None)] = None,
):
    """Generate ETKDG v3 + MMFF94s-optimized 3D conformer. Charges 10/call."""
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing x-api-key header")
    from src.dependencies import _rl
    _rl(f"conf:{x_api_key}", limit=30, window=60.0)
    info = keysdb.lookup(x_api_key)
    if not info or not info.active:
        raise HTTPException(status_code=401, detail="Invalid or inactive API key")
    CHARGE = 10
    used = keysdb.month_usage(x_api_key)
    if used + CHARGE > info.monthly_quota:
        raise HTTPException(status_code=402,
                            detail=f"Quota would be exceeded ({used}/{info.monthly_quota})")
    try:
        conf = conformers.generate(body.smiles, n_conformers=body.n_conformers)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    record_usage(x_api_key, "/conformers", CHARGE)
    return {**conf.to_dict(), "quota_charged": CHARGE}
