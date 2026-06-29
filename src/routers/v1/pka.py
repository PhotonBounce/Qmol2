from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Annotated

from src.pka import predictor
from src import keys as keysdb
from src.dependencies import check_quota, record_usage

router = APIRouter(tags=["pka"])


class PkaIn(BaseModel):
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


@router.post("/predict/pka")
def predict_pka_endpoint(
    body: PkaIn,
    x_api_key: Annotated[str | None, Header(default=None)] = None,
):
    """Predict pKa values for ionizable groups in a molecule. Charges 2x."""
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing x-api-key header")
    info = keysdb.lookup(x_api_key)
    if not info or not info.active:
        raise HTTPException(status_code=401, detail="Invalid or inactive API key")
    from src.dependencies import _rl
    _rl(f"predict:{x_api_key}", limit=60, window=60.0)
    charge = 2
    used, quota = check_quota(x_api_key, charge)
    result = predictor.predict_pka(body.smiles)
    record_usage(x_api_key, "/predict/pka", charge)
    return {"result": result, "quota_charged": charge}
