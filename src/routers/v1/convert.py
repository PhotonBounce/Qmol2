from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import List, Annotated

from src import convert, keys as keysdb
from src.dependencies import check_quota, record_usage

router = APIRouter(tags=["convert"])


class ConvertIn(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "smiles": ["CCO"],
                "input_format": "smiles",
                "with_molblock": False,
            }
        }
    )
    smiles: List[str] = Field(..., min_length=1, max_length=10000)
    input_format: str = Field("smiles", min_length=1)
    with_molblock: bool = False

    @field_validator("smiles")
    @classmethod
    def validate_smiles(cls, v: List[str]) -> List[str]:
        from rdkit import Chem
        invalid = [s for s in v if Chem.MolFromSmiles(s) is None]
        if invalid:
            raise ValueError(f"Invalid SMILES: {invalid[:5]}")
        return v


@router.post("/convert")
def convert_endpoint(
    body: ConvertIn,
    x_api_key: Annotated[str | None, Header(default=None)] = None,
):
    """Convert to canonical SMILES + InChI + InChIKey (+ optional MolBlock)."""
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing x-api-key header")
    info = keysdb.lookup(x_api_key)
    if not info or not info.active:
        raise HTTPException(status_code=401, detail="Invalid or inactive API key")
    from src.dependencies import _rl
    _rl(f"convert:{x_api_key}", limit=120, window=60.0)
    n = len(body.smiles)
    used, quota = check_quota(x_api_key, n)
    try:
        results = convert.convert_batch(
            body.smiles, input_format=body.input_format,
            with_molblock=body.with_molblock,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    record_usage(x_api_key, "/convert", n)
    return {"results": results, "quota_charged": n}
