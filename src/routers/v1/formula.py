from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import List, Annotated

from src import formula, keys as keysdb
from src.dependencies import check_quota, record_usage

router = APIRouter(tags=["formula"])


class FormulaIn(BaseModel):
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


@router.post("/formula")
def formula_endpoint(
    body: FormulaIn,
    x_api_key: Annotated[str | None, Header()] = None,
):
    """Molecular formula, exact mass, elemental composition, RDBE."""
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing x-api-key header")
    info = keysdb.lookup(x_api_key)
    if not info or not info.active:
        raise HTTPException(status_code=401, detail="Invalid or inactive API key")
    from src.dependencies import _rl
    _rl(f"formula:{x_api_key}", limit=120, window=60.0)
    n = len(body.smiles)
    used, quota = check_quota(x_api_key, n)
    try:
        results = formula.compute_batch(body.smiles)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    record_usage(x_api_key, "/formula", n)
    return {"results": results, "quota_charged": n}
