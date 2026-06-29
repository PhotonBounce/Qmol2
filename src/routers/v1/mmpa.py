from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import List, Annotated

from src.mmpa import analyzer
from src import keys as keysdb
from src.dependencies import check_quota, record_usage

router = APIRouter(tags=["mmpa"])


class MmpaIn(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={"example": {"smiles": ["CCO", "CCCO", "CCCCO"]}}
    )
    smiles: List[str] = Field(..., min_length=2, max_length=1000)

    @field_validator("smiles")
    @classmethod
    def validate_smiles(cls, v: List[str]) -> List[str]:
        from rdkit import Chem
        invalid = [s for s in v if Chem.MolFromSmiles(s) is None]
        if invalid:
            raise ValueError(f"Invalid SMILES: {invalid[:5]}")
        return v


@router.post("/mmpa/analyze")
def mmpa_analyze_endpoint(
    body: MmpaIn,
    x_api_key: Annotated[str | None, Header(default=None)] = None,
):
    """Matched Molecular Pair Analysis. Charges 5x per molecule."""
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing x-api-key header")
    info = keysdb.lookup(x_api_key)
    if not info or not info.active:
        raise HTTPException(status_code=401, detail="Invalid or inactive API key")
    from src.dependencies import _rl
    _rl(f"mmpa:{x_api_key}", limit=30, window=60.0)
    charge = 5 * len(body.smiles)
    used, quota = check_quota(x_api_key, charge)
    try:
        pairs = analyzer.analyze_mmp(body.smiles)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    record_usage(x_api_key, "/mmpa/analyze", charge)
    return {"pairs": pairs, "n_pairs": len(pairs), "quota_charged": charge}
