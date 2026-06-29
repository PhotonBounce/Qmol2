from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import List, Annotated

from src import fingerprints, keys as keysdb
from src.dependencies import check_quota, record_usage

router = APIRouter(tags=["fingerprints"])


class FingerprintIn(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "smiles": ["CCO"],
                "kind": "morgan",
                "n_bits": 2048,
                "radius": 2,
                "output": "bits",
            }
        }
    )
    smiles: List[str] = Field(..., min_length=1, max_length=50000)
    kind: str = Field("morgan", min_length=1)
    n_bits: int = Field(2048, ge=64, le=8192)
    radius: int = Field(2, ge=1, le=6)
    output: str = Field("bits", min_length=1)

    @field_validator("smiles")
    @classmethod
    def validate_smiles(cls, v: List[str]) -> List[str]:
        from rdkit import Chem
        invalid = [s for s in v if Chem.MolFromSmiles(s) is None]
        if invalid:
            raise ValueError(f"Invalid SMILES: {invalid[:5]}")
        return v


@router.get("/fingerprints/kinds")
def fingerprint_kinds():
    """Public: list supported fingerprint kinds + defaults."""
    return {
        "kinds": list(fingerprints.KINDS),
        "outputs": list(fingerprints.OUTPUTS),
        "defaults": {"kind": "morgan", "n_bits": 2048, "radius": 2, "output": "bits"},
        "notes": {
            "morgan": "ECFP-style circular; radius 2 == ECFP4",
            "maccs": "fixed 167-bit structural keys; n_bits/radius ignored",
        },
    }


@router.post("/fingerprints")
def fingerprints_endpoint(
    body: FingerprintIn,
    x_api_key: Annotated[str | None, Header()] = None,
):
    """Molecular fingerprints. Charges 1 SMILES/molecule."""
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing x-api-key header")
    info = keysdb.lookup(x_api_key)
    if not info or not info.active:
        raise HTTPException(status_code=401, detail="Invalid or inactive API key")
    from src.dependencies import _rl
    _rl(f"fp:{x_api_key}", limit=60, window=60.0)
    n = len(body.smiles)
    used, quota = check_quota(x_api_key, n)
    try:
        results = fingerprints.compute_batch(
            body.smiles, kind=body.kind, n_bits=body.n_bits,
            radius=body.radius, output=body.output,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    record_usage(x_api_key, "/fingerprints", n)
    return {"kind": body.kind.lower(), "n": n, "results": results, "quota_charged": n}
