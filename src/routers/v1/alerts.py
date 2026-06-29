from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import List, Annotated

from src import alerts, keys as keysdb
from src.dependencies import check_quota, record_usage

router = APIRouter(tags=["alerts"])


class AlertsIn(BaseModel):
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


@router.get("/alerts/catalogs")
def alert_catalogs():
    """Public: list structural-alert catalogs."""
    return {"catalogs": list(alerts.CATALOG_NAMES)}


@router.post("/alerts")
def alerts_endpoint(
    body: AlertsIn,
    x_api_key: Annotated[str | None, Header()] = None,
):
    """Structural-alert screen (PAINS, BRENK, NIH, ZINC)."""
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing x-api-key header")
    info = keysdb.lookup(x_api_key)
    if not info or not info.active:
        raise HTTPException(status_code=401, detail="Invalid or inactive API key")
    from src.dependencies import _rl
    _rl(f"alerts:{x_api_key}", limit=60, window=60.0)
    n = len(body.smiles)
    used, quota = check_quota(x_api_key, n)
    try:
        results = alerts.screen_batch(body.smiles)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    record_usage(x_api_key, "/alerts", n)
    return {"results": results, "quota_charged": n}
