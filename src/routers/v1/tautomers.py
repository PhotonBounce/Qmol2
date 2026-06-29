from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import List, Annotated

from src import tautomers, keys as keysdb
from src.dependencies import check_quota, record_usage

router = APIRouter(tags=["tautomers"])


class TautomerIn(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "smiles": ["CCO"],
                "max_tautomers": 100,
            }
        }
    )
    smiles: List[str] = Field(..., min_length=1, max_length=1000)
    max_tautomers: int = Field(100, ge=1, le=1000)

    @field_validator("smiles")
    @classmethod
    def validate_smiles(cls, v: List[str]) -> List[str]:
        from rdkit import Chem
        invalid = [s for s in v if Chem.MolFromSmiles(s) is None]
        if invalid:
            raise ValueError(f"Invalid SMILES: {invalid[:5]}")
        return v


@router.post("/tautomers")
def tautomers_endpoint(
    body: TautomerIn,
    x_api_key: Annotated[str | None, Header(default=None)] = None,
):
    """Enumerate plausible tautomers. Charges 2 SMILES/molecule."""
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing x-api-key header")
    info = keysdb.lookup(x_api_key)
    if not info or not info.active:
        raise HTTPException(status_code=401, detail="Invalid or inactive API key")
    from src.dependencies import _rl
    _rl(f"taut:{x_api_key}", limit=30, window=60.0)
    charge = 2 * len(body.smiles)
    used, quota = check_quota(x_api_key, charge)
    try:
        results = tautomers.enumerate_batch(body.smiles, max_tautomers=body.max_tautomers)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    record_usage(x_api_key, "/tautomers", charge)
    return {"results": results, "quota_charged": charge}
