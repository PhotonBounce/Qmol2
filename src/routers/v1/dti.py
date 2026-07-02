"""FastAPI router for Drug-Target Interaction (DTI) prediction."""
from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import List, Annotated

from src.dti import predict_binding_affinity, predict_multi_target_activity, list_targets, get_target_info
from src.dti.targets import TARGETS, VALIDATED_TARGETS, validate_target
from src.dependencies import _require_auth, _check_quota, record_usage, _rl, _client_ip

router = APIRouter(tags=["dti"])


class PredictIn(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {"smiles": "CCO", "target_id": "HER2"}
        }
    )
    smiles: str = Field(..., min_length=1)
    target_id: str = Field(..., min_length=1)

    @field_validator("smiles")
    @classmethod
    def validate_smiles(cls, v: str) -> str:
        from rdkit import Chem
        if Chem.MolFromSmiles(v) is None:
            raise ValueError(f"Invalid SMILES: {v!r}")
        return v


class MultiPredictIn(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {"smiles": "CCO", "target_ids": ["HER2", "EGFR"]}
        }
    )
    smiles: str = Field(..., min_length=1)
    target_ids: List[str] | None = Field(default=None)

    @field_validator("smiles")
    @classmethod
    def validate_smiles(cls, v: str) -> str:
        from rdkit import Chem
        if Chem.MolFromSmiles(v) is None:
            raise ValueError(f"Invalid SMILES: {v!r}")
        return v


class ScreenIn(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {"smiles": ["CCO", "c1ccccc1"], "target_id": "HER2"}
        }
    )
    smiles: List[str] = Field(..., min_length=1, max_length=5000)
    target_id: str = Field(..., min_length=1)

    @field_validator("smiles")
    @classmethod
    def validate_smiles(cls, v: List[str]) -> List[str]:
        from rdkit import Chem
        invalid = [s for s in v if Chem.MolFromSmiles(s) is None]
        if invalid:
            raise ValueError(f"Invalid SMILES: {invalid[:5]}")
        return v


@router.get("/dti/targets")
def list_targets_endpoint(
    request: Request,
    x_api_key: Annotated[str | None, Header()] = None,
):
    """List all available protein targets."""
    _rl(_client_ip(request), 120, 60.0)
    _require_auth(x_api_key)
    return {"targets": list_targets()}


@router.get("/dti/targets/{target_id}")
def get_target_info_endpoint(
    target_id: str,
    request: Request,
    x_api_key: Annotated[str | None, Header()] = None,
):
    """Get detailed information about a specific target."""
    _rl(_client_ip(request), 120, 60.0)
    _require_auth(x_api_key)
    info = get_target_info(target_id)
    if not info:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown target: {target_id!r}. Validated targets: {sorted(VALIDATED_TARGETS)}",
        )
    return {"target_id": target_id, **info}


@router.post("/dti/predict")
def predict_endpoint(
    body: PredictIn,
    request: Request,
    x_api_key: Annotated[str | None, Header()] = None,
):
    """Predict binding affinity (pKi) for a single molecule against one target. Charges 5 credits."""
    _rl(_client_ip(request), 60, 60.0)
    _require_auth(x_api_key)
    charge = 5
    used, quota = _check_quota(x_api_key, charge)
    if not validate_target(body.target_id):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid target_id: {body.target_id!r}. Validated targets: {sorted(VALIDATED_TARGETS)}"
        )
    try:
        result = predict_binding_affinity(body.smiles, body.target_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    record_usage(x_api_key, "/dti/predict", charge)
    return {"result": result, "quota_charged": charge}


@router.post("/dti/predict/multi")
def predict_multi_endpoint(
    body: MultiPredictIn,
    request: Request,
    x_api_key: Annotated[str | None, Header()] = None,
):
    """Predict activity across multiple targets for a single molecule. Charges 10 credits."""
    _rl(_client_ip(request), 60, 60.0)
    _require_auth(x_api_key)
    charge = 10
    used, quota = _check_quota(x_api_key, charge)
    if body.target_ids:
        invalid = [t for t in body.target_ids if not validate_target(t)]
        if invalid:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid target_ids: {invalid}. Validated targets: {sorted(VALIDATED_TARGETS)}"
            )
    try:
        result = predict_multi_target_activity(body.smiles, body.target_ids)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    record_usage(x_api_key, "/dti/predict/multi", charge)
    return {"result": result, "quota_charged": charge}


@router.post("/dti/screen")
def screen_endpoint(
    body: ScreenIn,
    request: Request,
    x_api_key: Annotated[str | None, Header()] = None,
):
    """Screen a library of molecules against a single target. Charges 3 credits per molecule."""
    _rl(_client_ip(request), 30, 60.0)
    _require_auth(x_api_key)
    charge = 3 * len(body.smiles)
    used, quota = _check_quota(x_api_key, charge)
    if not validate_target(body.target_id):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid target_id: {body.target_id!r}. Validated targets: {sorted(VALIDATED_TARGETS)}"
        )
    results = []
    for smi in body.smiles:
        try:
            results.append(predict_binding_affinity(smi, body.target_id))
        except ValueError as e:
            results.append({"smiles": smi, "error": str(e)})
    record_usage(x_api_key, "/dti/screen", charge)
    return {
        "target_id": body.target_id,
        "results": results,
        "quota_charged": charge,
    }
