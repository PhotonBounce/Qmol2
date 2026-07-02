"""Harvest router — dataset management and monetization endpoints.

These endpoints are for admin/owner use only. They allow:
- Viewing harvest statistics
- Creating curated datasets from the harvested molecules
- Exporting datasets for sale
- Tracking market intelligence
"""
from __future__ import annotations
from typing import Annotated, Any
from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel, Field, ConfigDict

from src import harvest
from src.dependencies import require_admin, _rl, _client_ip

router = APIRouter(tags=["harvest"], prefix="/harvest")


class DatasetCreateIn(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "High-QED Drug Candidates",
                "description": "Molecules with QED >= 0.7, Lipinski pass, no PAINS",
                "filter_sql": "qed >= 0.7 AND lipinski_pass = 1 AND pains_hit = 0",
                "max_molecules": 5000,
            }
        }
    )
    name: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1, max_length=2000)
    filter_sql: str = Field(..., min_length=1, max_length=500)
    max_molecules: int = Field(10_000, ge=1, le=100_000)


@router.get("/stats")
def harvest_stats(
    request: Request,
    x_admin_token: str | None = Header(default=None),
):
    """Return harvest database statistics. Admin only."""
    _rl(_client_ip(request), 60, 60.0)
    require_admin(x_admin_token)
    return harvest.stats()


@router.post("/datasets")
def create_dataset(
    body: DatasetCreateIn,
    request: Request,
    x_admin_token: str | None = Header(default=None),
):
    """Create a curated dataset from harvested molecules. Admin only."""
    _rl(_client_ip(request), 30, 60.0)
    require_admin(x_admin_token)
    return harvest.create_dataset(
        name=body.name,
        description=body.description,
        filter_sql=body.filter_sql,
        max_molecules=body.max_molecules,
    )


@router.get("/datasets/{dataset_id}/csv")
def export_dataset_csv(
    dataset_id: int,
    request: Request,
    x_admin_token: str | None = Header(default=None),
):
    """Export a dataset as CSV. Admin only."""
    _rl(_client_ip(request), 30, 60.0)
    require_admin(x_admin_token)
    from fastapi.responses import PlainTextResponse
    csv_data = harvest.export_dataset_csv(dataset_id)
    return PlainTextResponse(
        csv_data,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="qmol_dataset_{dataset_id}.csv"'
        },
    )
