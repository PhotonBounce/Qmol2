from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import List, Annotated

from src import screen, keys as keysdb
from src.dependencies import check_quota, record_usage

router = APIRouter(tags=["screen"])


class ScreenIn(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {"smiles": ["CCO", "c1ccccc1"]}
        }
    )
    smiles: List[str] = Field(..., min_length=1, max_length=10000)

    @field_validator("smiles")
    @classmethod
    def validate_smiles(cls, v: List[str]) -> List[str]:
        from rdkit import Chem
        invalid = [s for s in v if Chem.MolFromSmiles(s) is None]
        if invalid:
            raise ValueError(f"Invalid SMILES: {invalid[:5]}")
        return v


@router.post("/screen")
def screen_endpoint(
    body: ScreenIn,
    x_api_key: Annotated[str | None, Header(default=None)] = None,
):
    """Drug-likeness screening. Charges 5 SMILES/molecule."""
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing x-api-key header")
    from src.dependencies import _rl
    _rl(f"screen:{x_api_key}", limit=60, window=60.0)
    info = keysdb.lookup(x_api_key)
    if not info or not info.active:
        raise HTTPException(status_code=401, detail="Invalid or inactive API key")
    charge = 5 * len(body.smiles)
    used, quota = check_quota(x_api_key, charge)
    report = screen.screen_batch(body.smiles)
    record_usage(x_api_key, "/screen", charge)
    return {**report, "quota_charged": charge}
