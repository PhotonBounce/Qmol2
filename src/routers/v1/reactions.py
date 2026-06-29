from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import List, Annotated

from src import reactions, keys as keysdb
from src.dependencies import check_quota, record_usage

router = APIRouter(tags=["reactions"])


class ReactionIn(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "template": "amide",
                "reagents": [["CCO"], ["N"]],
                "max_products": 10000,
                "unique": True,
            }
        }
    )
    template: str = Field(..., min_length=1)
    reagents: List[List[str]] = Field(..., min_length=1)
    max_products: int = Field(10000, ge=1, le=100000)
    unique: bool = True


@router.post("/reactions")
def react_endpoint(
    body: ReactionIn,
    x_api_key: Annotated[str | None, Header()] = None,
):
    """Enumerate a combinatorial library from SMARTS template + reagents."""
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing x-api-key header")
    from src.dependencies import _rl
    _rl(f"react:{x_api_key}", limit=30, window=60.0)
    info = keysdb.lookup(x_api_key)
    if not info or not info.active:
        raise HTTPException(status_code=401, detail="Invalid or inactive API key")
    try:
        result = reactions.enumerate_library(
            body.template, body.reagents,
            max_products=body.max_products, unique=body.unique,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    used = keysdb.month_usage(x_api_key)
    if used + result.n_products > info.monthly_quota:
        raise HTTPException(status_code=402,
                            detail=f"Quota would be exceeded ({used}/{info.monthly_quota})")
    record_usage(x_api_key, "/reactions", result.n_products)
    return {**result.to_dict(), "quota_charged": result.n_products}


@router.get("/reactions/templates")
def react_templates():
    """Public: list built-in reaction templates."""
    return {"templates": {k: v for k, v in reactions.TEMPLATES.items()}}
