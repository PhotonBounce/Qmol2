"""FastAPI router for synthesis-aware molecular scoring."""
from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Annotated

from src.synthesis import (
    score_synthesizability,
    score_purchasability,
    score_synthesis_route,
)
from src.dependencies import (
    _require_auth,
    _check_quota,
    record_usage,
    _rl,
    _client_ip,
)

router = APIRouter(tags=["synthesis"])


# ------------------------------------------------------------------
# Request models
# ------------------------------------------------------------------

class SynthesisScoreIn(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "smiles": "CC(=O)Oc1ccccc1C(=O)O",
            }
        }
    )
    smiles: str = Field(..., min_length=1, max_length=500)

    @field_validator("smiles")
    @classmethod
    def validate_smiles(cls, v: str) -> str:
        from rdkit import Chem
        if Chem.MolFromSmiles(v) is None:
            raise ValueError(f"Invalid SMILES: {v}")
        return v


# ------------------------------------------------------------------
# Endpoints
# ------------------------------------------------------------------

@router.post("/synthesis/score")
def synthesis_full_score(
    body: SynthesisScoreIn,
    request: Request,
    x_api_key: str = Header(..., alias="x-api-key"),
):
    """Full synthesis score: SAscore + purchasability + route complexity.

    Charges 3x per molecule.
    """
    _rl(_client_ip(request), 60, 60.0)
    _require_auth(x_api_key)
    _check_quota(x_api_key, 3)
    result = {
        "synthesizability": score_synthesizability(body.smiles),
        "purchasability": score_purchasability(body.smiles),
        "route": score_synthesis_route(body.smiles),
        "smiles": body.smiles,
    }
    record_usage(x_api_key, "/synthesis/score", 3)
    return {**result, "quota_charged": 3}


@router.post("/synthesis/sa")
def synthesis_sa_score(
    body: SynthesisScoreIn,
    request: Request,
    x_api_key: str = Header(..., alias="x-api-key"),
):
    """Synthetic accessibility score only. Charges 1x."""
    _rl(_client_ip(request), 60, 60.0)
    _require_auth(x_api_key)
    _check_quota(x_api_key, 1)
    result = score_synthesizability(body.smiles)
    record_usage(x_api_key, "/synthesis/sa", 1)
    return {"result": result, "smiles": body.smiles, "quota_charged": 1}


@router.post("/synthesis/purchase")
def synthesis_purchase_score(
    body: SynthesisScoreIn,
    request: Request,
    x_api_key: str = Header(..., alias="x-api-key"),
):
    """Purchasability score only. Charges 1x."""
    _rl(_client_ip(request), 60, 60.0)
    _require_auth(x_api_key)
    _check_quota(x_api_key, 1)
    result = score_purchasability(body.smiles)
    record_usage(x_api_key, "/synthesis/purchase", 1)
    return {"result": result, "smiles": body.smiles, "quota_charged": 1}


@router.post("/synthesis/route")
def synthesis_route_score(
    body: SynthesisScoreIn,
    request: Request,
    x_api_key: str = Header(..., alias="x-api-key"),
):
    """Retrosynthetic route complexity only. Charges 1x."""
    _rl(_client_ip(request), 60, 60.0)
    _require_auth(x_api_key)
    _check_quota(x_api_key, 1)
    result = score_synthesis_route(body.smiles)
    record_usage(x_api_key, "/synthesis/route", 1)
    return {"result": result, "smiles": body.smiles, "quota_charged": 1}
