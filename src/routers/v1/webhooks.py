from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field, ConfigDict
from typing import Annotated, Any

from src.webhooks import service as webhook_service
from src import keys as keysdb

router = APIRouter(tags=["webhooks"])


class WebhookCreateIn(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "url": "https://example.com/webhook",
                "events": "job.complete,quota.warning",
                "secret": "shhh",
            }
        }
    )
    url: str = Field(..., min_length=5)
    events: str = Field(..., min_length=1)
    secret: str | None = None


class WebhookRotateIn(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={"example": {"webhook_id": "uuid"}}
    )
    webhook_id: str


@router.post("/webhooks")
def create_webhook(
    body: WebhookCreateIn,
    x_api_key: Annotated[str | None, Header(default=None)] = None,
):
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing x-api-key header")
    if not keysdb.lookup(x_api_key):
        raise HTTPException(status_code=401, detail="Invalid API key")
    wh = webhook_service.create_webhook(x_api_key, body.url, body.events, body.secret)
    return {"webhook": wh.to_dict()}


@router.get("/webhooks")
def list_webhooks(
    x_api_key: Annotated[str | None, Header(default=None)] = None,
):
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing x-api-key header")
    if not keysdb.lookup(x_api_key):
        raise HTTPException(status_code=401, detail="Invalid API key")
    webhooks = webhook_service.list_webhooks(x_api_key)
    return {"webhooks": [w.to_dict() for w in webhooks]}


@router.delete("/webhooks/{webhook_id}")
def delete_webhook(
    webhook_id: str,
    x_api_key: Annotated[str | None, Header(default=None)] = None,
):
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing x-api-key header")
    wh = webhook_service.get_webhook(webhook_id)
    if not wh or wh.api_key != x_api_key:
        raise HTTPException(status_code=404, detail="Webhook not found")
    webhook_service.delete_webhook(webhook_id)
    return {"deleted": True}


@router.get("/webhooks/{webhook_id}/logs")
def get_webhook_logs(
    webhook_id: str,
    limit: int = 100,
    x_api_key: Annotated[str | None, Header(default=None)] = None,
):
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing x-api-key header")
    wh = webhook_service.get_webhook(webhook_id)
    if not wh or wh.api_key != x_api_key:
        raise HTTPException(status_code=404, detail="Webhook not found")
    logs = webhook_service.get_logs(webhook_id, limit=limit)
    return {"logs": [l.to_dict() for l in logs]}


@router.post("/webhooks/{webhook_id}/test")
def test_webhook(
    webhook_id: str,
    x_api_key: Annotated[str | None, Header(default=None)] = None,
):
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing x-api-key header")
    wh = webhook_service.get_webhook(webhook_id)
    if not wh or wh.api_key != x_api_key:
        raise HTTPException(status_code=404, detail="Webhook not found")
    payload = webhook_service.test_payload()
    success = webhook_service.deliver(webhook_id, "webhook.test", payload)
    return {"delivered": success}


@router.post("/webhooks/{webhook_id}/rotate")
def rotate_webhook_secret(
    webhook_id: str,
    x_api_key: Annotated[str | None, Header(default=None)] = None,
):
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing x-api-key header")
    wh = webhook_service.get_webhook(webhook_id)
    if not wh or wh.api_key != x_api_key:
        raise HTTPException(status_code=404, detail="Webhook not found")
    new_secret = webhook_service.rotate_secret(webhook_id)
    if new_secret is None:
        raise HTTPException(status_code=500, detail="Failed to rotate secret")
    return {"new_secret": new_secret}
