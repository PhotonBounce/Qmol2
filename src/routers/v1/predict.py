from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import List, Annotated, Any

from src import predict, keys as keysdb
from src.dependencies import check_quota, record_usage
from src.ml import predictor as ml_predictor, model_cards

router = APIRouter(tags=["predict"])


class PredictIn(BaseModel):
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


class SinglePredictIn(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {"smiles": "CCO"}
        }
    )
    smiles: str = Field(..., min_length=1)

    @field_validator("smiles")
    @classmethod
    def validate_smiles(cls, v: str) -> str:
        from rdkit import Chem
        if Chem.MolFromSmiles(v) is None:
            raise ValueError(f"Invalid SMILES: {v!r}")
        return v


class PropertyPredictionOut(BaseModel):
    value: Any
    confidence: float
    in_domain: bool
    unit: str
    model_version: str
    source: str = "onnx"
    expected_r2: float | None = None
    warning: str | None = None


class MlPanelResult(BaseModel):
    aqueous_logs: PropertyPredictionOut
    bbb_probability: PropertyPredictionOut
    herg_risk: PropertyPredictionOut
    gi_absorption: PropertyPredictionOut
    sa_score_lite: PropertyPredictionOut


class ModelCardOut(BaseModel):
    model_id: str
    name: str
    description: str
    unit: str
    expected_r2: float | None = None
    expected_auroc: float | None = None
    expected_balanced_accuracy: float | None = None
    expected_accuracy: float | None = None
    training_set_size: int
    source: str
    model_type: str
    model_version: str
    input_dim: int
    feature_mode: str
    class_labels: List[str] | None = None
    citation: str | None = None


def _authenticate(x_api_key: str | None) -> None:
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing x-api-key header")
    from src.dependencies import _rl
    _rl(f"predict:{x_api_key}", limit=60, window=60.0)
    info = keysdb.lookup(x_api_key)
    if not info or not info.active:
        raise HTTPException(status_code=401, detail="Invalid or inactive API key")


@router.post("/predict")
def predict_endpoint(
    body: PredictIn,
    x_api_key: Annotated[str | None, Header(default=None)] = None,
):
    """Legacy ADMET predictions: logS, BBB, hERG, GI, SA-score (heuristic)."""
    _authenticate(x_api_key)
    charge = 3 * len(body.smiles)
    used, quota = check_quota(x_api_key, charge)
    try:
        results = predict.predict_batch(body.smiles)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    record_usage(x_api_key, "/predict", charge)
    return {"results": results, "quota_charged": charge}


@router.post("/predict/ml")
def predict_ml_endpoint(
    body: PredictIn,
    x_api_key: Annotated[str | None, Header(default=None)] = None,
):
    """Full ML prediction panel (5 properties). Charges 5x per molecule."""
    _authenticate(x_api_key)
    charge = 5 * len(body.smiles)
    used, quota = check_quota(x_api_key, charge)
    try:
        results = predict.predict_batch_ml(body.smiles)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    record_usage(x_api_key, "/predict/ml", charge)
    return {"results": results, "quota_charged": charge}


@router.post("/predict/{property}")
def predict_single_property_endpoint(
    property: str,
    body: SinglePredictIn,
    x_api_key: Annotated[str | None, Header(default=None)] = None,
):
    """Single property prediction (charges 2x per molecule)."""
    _authenticate(x_api_key)
    charge = 2
    used, quota = check_quota(x_api_key, charge)
    if property not in model_cards.MODEL_CARDS:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown model_id: {property!r}. Available: {list(model_cards.MODEL_CARDS.keys())}",
        )
    try:
        ml = ml_predictor.get_predictor()
        result = ml.predict_single(body.smiles, model_id=property)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    record_usage(x_api_key, f"/predict/{property}", charge)
    return {"result": result, "quota_charged": charge}


@router.get("/models")
def list_models_endpoint(
    x_api_key: Annotated[str | None, Header(default=None)] = None,
):
    """List all available prediction models with accuracy metrics."""
    _authenticate(x_api_key)
    return {"models": model_cards.list_models()}


@router.get("/models/{model_id}")
def get_model_card_endpoint(
    model_id: str,
    x_api_key: Annotated[str | None, Header(default=None)] = None,
):
    """Get detailed model card for a specific model_id."""
    _authenticate(x_api_key)
    info = model_cards.get_model_info(model_id)
    if not info:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown model_id: {model_id!r}. Available: {list(model_cards.MODEL_CARDS.keys())}",
        )
    return {"model_id": model_id, **info}
