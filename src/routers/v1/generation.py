"""De novo molecular generation & lead optimization API endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import List, Optional

from rdkit import Chem

from src.generation import rnn_generator, optimizer, scorer
from src.dependencies import (
    _require_auth,
    _check_quota,
    record_usage,
    _rl,
    _client_ip,
)

router = APIRouter(tags=["generation"])


# ------------------------------------------------------------------
# Request models
# ------------------------------------------------------------------

class GenerateIn(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={"example": {"seed_smiles": ["CCO", "c1ccccc1"], "n": 100}}
    )
    seed_smiles: List[str] = Field(..., min_length=1, max_length=1000)
    n: int = Field(100, ge=1, le=1000)

    @field_validator("seed_smiles")
    @classmethod
    def validate_smiles(cls, v: List[str]) -> List[str]:
        invalid = [s for s in v if Chem.MolFromSmiles(s) is None]
        if invalid:
            raise ValueError(f"Invalid SMILES: {invalid[:5]}")
        return v


class OptimizeIn(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "smiles": "c1ccccc1",
                "target_property": "logP",
                "target_value": 2.5,
            }
        }
    )
    smiles: str = Field(..., min_length=1, max_length=500)
    target_property: str = Field("logP", pattern="^(logP|MW|TPSA|QED)$")
    target_value: float
    max_steps: int = Field(50, ge=1, le=200)

    @field_validator("smiles")
    @classmethod
    def validate_smiles(cls, v: str) -> str:
        if Chem.MolFromSmiles(v) is None:
            raise ValueError(f"Invalid SMILES: {v}")
        return v


class LeadOptimizeIn(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "smiles": "c1ccccc1",
                "objectives": {
                    "logP": [2.5, 1.0],
                    "MW": [400, 50],
                    "QED": [0.8, 0.2],
                },
                "max_steps": 100,
            }
        }
    )
    smiles: str = Field(..., min_length=1, max_length=500)
    objectives: dict[str, tuple[float, float]] = Field(
        ..., description="Property: (target, tolerance)"
    )
    max_steps: int = Field(100, ge=1, le=200)

    @field_validator("smiles")
    @classmethod
    def validate_smiles(cls, v: str) -> str:
        if Chem.MolFromSmiles(v) is None:
            raise ValueError(f"Invalid SMILES: {v}")
        return v

    @field_validator("objectives")
    @classmethod
    def validate_objectives(cls, v: dict[str, tuple[float, float]]) -> dict[str, tuple[float, float]]:
        for prop, tup in v.items():
            if len(tup) != 2:
                raise ValueError(f"Objective '{prop}' must be a tuple of (target, tolerance)")
            if tup[1] <= 0:
                raise ValueError(f"Tolerance for '{prop}' must be > 0")
        return v


class ScoreIn(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "smiles": "c1ccccc1CCO",
                "objectives": {"logP": 2.5, "MW": 400, "QED": 0.8},
            }
        }
    )
    smiles: str = Field(..., min_length=1, max_length=500)
    objectives: Optional[dict[str, float]] = Field(
        None, description="Property: target_value (uses default tolerances)"
    )
    weights: Optional[dict[str, float]] = Field(None, description="Optional per-objective weights")

    @field_validator("smiles")
    @classmethod
    def validate_smiles(cls, v: str) -> str:
        if Chem.MolFromSmiles(v) is None:
            raise ValueError(f"Invalid SMILES: {v}")
        return v


# ------------------------------------------------------------------
# Endpoints
# ------------------------------------------------------------------

@router.post("/generate")
def generate_molecules(
    in_: GenerateIn,
    request: Request,
    x_api_key: str = Header(..., alias="x-api-key"),
):
    """Generate novel SMILES using a character-level Markov model trained on seed molecules."""
    _rl(_client_ip(request), 30, 60.0)
    _require_auth(x_api_key)
    _check_quota(x_api_key, in_.n * 5)
    results = rnn_generator.sample_smiles(in_.seed_smiles, n=in_.n)
    record_usage(x_api_key, "/generate", len(results) * 5)
    return {
        "generated": results,
        "count": len(results),
        "seed_count": len(in_.seed_smiles),
    }


@router.post("/optimize")
def optimize_molecule_endpoint(
    in_: OptimizeIn,
    request: Request,
    x_api_key: str = Header(..., alias="x-api-key"),
):
    """Optimize a single molecule toward a target property (logP, MW, TPSA, or QED)."""
    _rl(_client_ip(request), 30, 60.0)
    _require_auth(x_api_key)
    _check_quota(x_api_key, 10)
    result = optimizer.optimize_molecule(
        in_.smiles,
        in_.target_property,
        in_.target_value,
        max_steps=in_.max_steps,
    )
    record_usage(x_api_key, "/optimize", 10)
    return result


@router.post("/optimize/lead")
def optimize_lead_endpoint(
    in_: LeadOptimizeIn,
    request: Request,
    x_api_key: str = Header(..., alias="x-api-key"),
):
    """Multi-objective lead optimization (e.g., balance logP, MW, and QED simultaneously)."""
    _rl(_client_ip(request), 30, 60.0)
    _require_auth(x_api_key)
    _check_quota(x_api_key, 10)
    result = optimizer.optimize_lead(
        in_.smiles,
        in_.objectives,
        max_steps=in_.max_steps,
    )
    record_usage(x_api_key, "/optimize/lead", 10)
    return result


@router.post("/score")
def score_molecule_endpoint(
    in_: ScoreIn,
    request: Request,
    x_api_key: str = Header(..., alias="x-api-key"),
):
    """Score a molecule against one or more ADMET / drug-likeness objectives."""
    _rl(_client_ip(request), 60, 60.0)
    _require_auth(x_api_key)
    _check_quota(x_api_key, 2)

    mol = Chem.MolFromSmiles(in_.smiles)
    if mol is None:
        raise HTTPException(status_code=400, detail="Invalid SMILES")

    # Build objective map
    if in_.objectives is None:
        # Default: score all common objectives with sensible targets
        objective_map = {
            "logP": scorer.logp_objective(2.5, 1.5),
            "MW": scorer.mw_objective(400, 100),
            "QED": scorer.qed_objective(),
            "TPSA": scorer.tpsa_objective(90, 30),
            "synth": scorer.synthesizability_objective(),
            "lipinski": scorer.lipinski_objective(),
        }
    else:
        objective_map = {}
        for prop, target in in_.objectives.items():
            if prop == "logP":
                objective_map[prop] = scorer.logp_objective(target, 1.0)
            elif prop == "MW":
                objective_map[prop] = scorer.mw_objective(target, 50.0)
            elif prop == "QED":
                objective_map[prop] = scorer.qed_objective()
            elif prop == "TPSA":
                objective_map[prop] = scorer.tpsa_objective(target, 20.0)
            elif prop == "synth":
                objective_map[prop] = scorer.synthesizability_objective()
            elif prop == "lipinski":
                objective_map[prop] = scorer.lipinski_objective()
            else:
                raise HTTPException(status_code=400, detail=f"Unknown objective: {prop}")

    result = scorer.multi_objective_score(mol, objective_map, weights=in_.weights)
    result["smiles"] = in_.smiles
    record_usage(x_api_key, "/score", 2)
    return result
