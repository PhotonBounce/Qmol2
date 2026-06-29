from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field, ConfigDict
from typing import Annotated

from src import webhooks_out, keys as keysdb

router = APIRouter(tags=["webhooks"])


class WebhookSubIn(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "url": "https://example.com/webhook",
                "secret": "shhh",
            }
        }
    )
    url: str = Field(..., min_length=5)
    secret: str | None = None


@router.post("/webhooks/subscribe")
def webhook_subscribe(
    body: WebhookSubIn,
    x_api_key: Annotated[str | None, Header(default=None)] = None,
):
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing x-api-key header")
    if not keysdb.lookup(x_api_key):
        raise HTTPException(status_code=401, detail="Invalid API key")
    sub = webhooks_out.subscribe(x_api_key, body.url, body.secret)
    return {"url": sub.url, "has_secret": bool(sub.secret)}


@router.delete("/webhooks/subscribe")
def webhook_unsubscribe(
    x_api_key: Annotated[str | None, Header(default=None)] = None,
):
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing x-api-key header")
    webhooks_out.unsubscribe(x_api_key)
    return {"unsubscribed": True}
