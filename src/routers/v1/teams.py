from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field, ConfigDict

from src import teams, keys as keysdb
from src.dependencies import require_admin

router = APIRouter(tags=["teams"])


class TeamCreateIn(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Acme Research",
                "tier": "commercial",
                "monthly_quota": 100000,
                "owner_email": "admin@acme.com",
            }
        }
    )
    name: str = Field(..., min_length=1, max_length=120)
    tier: str = Field(..., min_length=1)
    monthly_quota: int = Field(..., ge=1)
    owner_email: str | None = None


class TeamMemberIn(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {"team_id": "team_xxx", "api_key": "qmol_xxx"}
        }
    )
    team_id: str
    api_key: str


@router.post("/teams")
def team_create(
    body: TeamCreateIn,
    x_admin_token: str | None = Header(default=None),
):
    require_admin(x_admin_token)
    t = teams.create(body.name, body.tier, body.monthly_quota, body.owner_email)
    return t.to_dict()


@router.post("/teams/members")
def team_add_member(
    body: TeamMemberIn,
    x_admin_token: str | None = Header(default=None),
):
    require_admin(x_admin_token)
    if teams.get(body.team_id) is None:
        raise HTTPException(status_code=404, detail="Team not found")
    if keysdb.lookup(body.api_key) is None:
        raise HTTPException(status_code=404, detail="API key not found")
    teams.add_member(body.team_id, body.api_key)
    return {"added": True}


@router.delete("/teams/members")
def team_remove_member(
    body: TeamMemberIn,
    x_admin_token: str | None = Header(default=None),
):
    require_admin(x_admin_token)
    teams.remove_member(body.team_id, body.api_key)
    return {"removed": True}


@router.get("/teams/{team_id}")
def team_get(
    team_id: str,
    x_admin_token: str | None = Header(default=None),
):
    require_admin(x_admin_token)
    t = teams.get(team_id)
    if not t:
        raise HTTPException(status_code=404, detail="Team not found")
    used = teams.month_usage(team_id)
    return {**t.to_dict(), "used_this_month": used, "members": teams.members(team_id)}
