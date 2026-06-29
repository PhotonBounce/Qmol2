from fastapi import APIRouter, Request, Header, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import List, Annotated

from src import compute, storage, result_cache, ratelimit
from src.dependencies import (
    _client_ip, _rl, check_free_limit, check_paid_limit, check_quota,
    record_usage, require_api_key_or_env, API_KEYS, FREE_LIMIT, PAID_LIMIT
)
import config

router = APIRouter(tags=["compute"])


class ComputeIn(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={"example": {"smiles": ["CCO", "c1ccccc1"]}}
    )
    smiles: List[str] = Field(..., min_length=1, max_length=50000)

    @field_validator("smiles")
    @classmethod
    def validate_smiles(cls, v: List[str]) -> List[str]:
        from rdkit import Chem
        invalid = [s for s in v if Chem.MolFromSmiles(s) is None]
        if invalid:
            raise ValueError(f"Invalid SMILES: {invalid[:5]}")
        return v


def _run_compute(smiles_list: list[str]) -> list[dict]:
    out = []
    for i, smi in enumerate(smiles_list):
        d = result_cache.memoize(
            "compute", smi,
            lambda i=i, smi=smi: compute.compute_molecule(
                cid=-(i + 1), smiles=smi
            ).to_dict(),
        )
        out.append(d)
    return out


@router.post("/compute")
def compute_free(body: ComputeIn, request: Request):
    ip = _client_ip(request)
    if ip == "unknown":
        ua = request.headers.get("user-agent", "anon")[:32]
        ip = f"unknown:{ua}"
    _rl(f"free:{ip}", limit=60, window=60.0)
    check_free_limit(len(body.smiles))
    return {"results": _run_compute(body.smiles)}


@router.post("/compute/premium")
def compute_paid(
    body: ComputeIn,
    x_api_key: Annotated[str | None, Header()] = None,
):
    x_api_key = require_api_key_or_env(x_api_key)
    _rl(f"paid:{x_api_key}", limit=600, window=60.0)
    if x_api_key in API_KEYS:
        check_paid_limit(len(body.smiles))
        return {"results": _run_compute(body.smiles)}
    from src import keys as keysdb
    info = keysdb.lookup(x_api_key)
    used = keysdb.month_usage(x_api_key)
    if used + len(body.smiles) > info.monthly_quota:
        raise HTTPException(
            status_code=402,
            detail=f"Monthly quota exceeded ({used}/{info.monthly_quota}). Upgrade tier at /checkout.",
        )
    check_paid_limit(len(body.smiles))
    results = _run_compute(body.smiles)
    record_usage(x_api_key, "/compute/premium", len(body.smiles))
    return {
        "results": results,
        "quota": {
            "used_this_month": used + len(body.smiles),
            "monthly_quota": info.monthly_quota,
            "tier": info.tier,
        },
    }


