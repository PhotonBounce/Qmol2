from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Annotated

from src import retro, keys as keysdb
from src.dependencies import check_quota, record_usage

router = APIRouter(tags=["retro"])


class RetroIn(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "smiles": "CCO",
                "max_results": 20,
            }
        }
    )
    smiles: str = Field(..., min_length=1)
    max_results: int = Field(20, ge=1, le=100)

    @field_validator("smiles")
    @classmethod
    def validate_smiles(cls, v: str) -> str:
        from rdkit import Chem
        if Chem.MolFromSmiles(v) is None:
            raise ValueError(f"Invalid SMILES: {v}")
        return v


@router.post("/retro")
def retro_endpoint(
    body: RetroIn,
    x_api_key: Annotated[str | None, Header()] = None,
):
    """Return plausible 1-step disconnections."""
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing x-api-key header")
    info = keysdb.lookup(x_api_key)
    if not info or not info.active:
        raise HTTPException(status_code=401, detail="Invalid or inactive API key")
    from src.dependencies import _rl
    _rl(f"retro:{x_api_key}", limit=30, window=60.0)
    used, quota = check_quota(x_api_key, 1)
    try:
        steps = retro.one_step(body.smiles, max_results=body.max_results)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    record_usage(x_api_key, "/retro", 1)
    return {"smiles": body.smiles, "n": len(steps),
            "steps": [s.to_dict() for s in steps], "quota_charged": 1}
