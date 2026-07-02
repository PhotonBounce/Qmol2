"""FastAPI router for natural language chemistry queries."""
from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Annotated

from src.nlp import parse_query, execute_query
from src.dependencies import (
    _require_auth,
    _check_quota,
    record_usage,
    _rl,
    _client_ip,
)

router = APIRouter(tags=["nlp"])


# ------------------------------------------------------------------
# Request models
# ------------------------------------------------------------------

class NlpQueryIn(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "query": "find molecules like aspirin with good BBB penetration",
            }
        }
    )
    query: str = Field(..., min_length=1, max_length=5000)


# ------------------------------------------------------------------
# Endpoints
# ------------------------------------------------------------------

@router.post("/nlp/query")
def nlp_query_endpoint(
    body: NlpQueryIn,
    request: Request,
    x_api_key: str = Header(..., alias="x-api-key"),
):
    """Parse a natural language query into a structured API call specification.

    Charges 1x per call.
    """
    _rl(_client_ip(request), 60, 60.0)
    _require_auth(x_api_key)
    _check_quota(x_api_key, 1)
    parsed = parse_query(body.query)
    record_usage(x_api_key, "/nlp/query", 1)
    return {"parsed": parsed, "quota_charged": 1}


@router.post("/nlp/execute")
def nlp_execute_endpoint(
    body: NlpQueryIn,
    request: Request,
    x_api_key: str = Header(..., alias="x-api-key"),
):
    """Parse a natural language query and execute it.

    Charge depends on the resolved endpoint:
    - similarity: 100x
    - generate: 5x per requested molecule
    - predict: 3x per molecule
    - optimize: 10x
    - compute: 1x per molecule
    """
    _rl(_client_ip(request), 30, 60.0)
    _require_auth(x_api_key)

    # Parse first to determine charge
    parsed = parse_query(body.query)
    endpoint = parsed.get("endpoint", "compute")
    params = parsed.get("params", {})

    # Dynamic charge based on endpoint and molecule count
    if endpoint == "similarity":
        charge = 100
    elif endpoint == "generate":
        charge = params.get("n", 10) * 5
    elif endpoint == "predict":
        charge = len(params.get("smiles", ["c1ccccc1"])) * 3
    elif endpoint == "optimize":
        charge = 10
    elif endpoint == "compute":
        charge = len(params.get("smiles", ["c1ccccc1"]))
    else:
        charge = 1

    _check_quota(x_api_key, charge)

    try:
        result = execute_query(body.query)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    record_usage(x_api_key, "/nlp/execute", charge)
    return {**result, "quota_charged": charge}


@router.get("/nlp/molecules")
def list_known_molecules(
    request: Request,
    x_api_key: str = Header(..., alias="x-api-key"),
):
    """List all known molecule names that can be referenced in natural language queries."""
    _rl(_client_ip(request), 120, 60.0)
    _require_auth(x_api_key)
    from src.nlp.parser import MOLECULE_NAMES
    return {
        "molecules": [
            {"name": name, "smiles": smiles}
            for name, smiles in MOLECULE_NAMES.items()
        ],
        "count": len(MOLECULE_NAMES),
    }
