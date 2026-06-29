"""Shared Pydantic v2 schemas used across all API routers."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Generic, List, TypeVar

from pydantic import BaseModel, Field, ConfigDict, field_validator

T = TypeVar("T")


class ErrorResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "detail": "Invalid SMILES: [bad]",
                "request_id": "550e8400-e29b-41d4-a716-446655440000",
                "timestamp": "2024-06-29T12:00:00Z",
            }
        }
    )
    detail: str
    request_id: str = ""
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class PaginatedResponse(BaseModel, Generic[T]):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "items": [{"smiles": "CCO"}],
                "total": 1,
                "page": 1,
                "page_size": 20,
            }
        }
    )
    items: List[T] = Field(..., description="List of result items")
    total: int = Field(..., ge=0, description="Total items across all pages")
    page: int = Field(..., ge=1, description="Current page number")
    page_size: int = Field(..., ge=1, le=1000, description="Items per page")


class HealthResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "ok",
                "version": "2.0.0",
                "db": "connected",
                "redis": "connected",
                "timestamp": "2024-06-29T12:00:00Z",
            }
        }
    )
    status: str = "ok"
    version: str = "2.0.0"
    db: str = "connected"
    redis: str = "connected"
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ReadyResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "ready": True,
                "checks": {
                    "postgres": True,
                    "redis": True,
                },
            }
        }
    )
    ready: bool = True
    checks: dict[str, bool] = Field(default_factory=dict)


class QuotaOut(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "used_this_month": 1500,
                "monthly_quota": 10000,
                "tier": "research",
            }
        }
    )
    used_this_month: int
    monthly_quota: int
    tier: str
