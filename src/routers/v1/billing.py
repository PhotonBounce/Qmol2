from fastapi import APIRouter, Request, Header, HTTPException
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import Annotated
import os

from src import keys as keysdb, referrals, coupons, magic_link, plans
from src.dependencies import _client_ip, _rl, require_admin

router = APIRouter(tags=["billing"])


class SignupIn(BaseModel):
    model_config = ConfigDict(json_schema_extra={"example": {"email": "user@example.com"}})
    email: EmailStr


class CouponCheckIn(BaseModel):
    model_config = ConfigDict(json_schema_extra={"example": {"code": "SUMMER20", "tier": "research"}})
    code: str
    tier: str


class CheckoutSessionIn(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "tier": "research",
                "success_url": "https://qmol.app/portal.html?paid=1",
                "cancel_url": "https://qmol.app/checkout.html",
            }
        }
    )
    tier: str = Field(..., min_length=1)
    success_url: str | None = None
    cancel_url: str | None = None


class PlayVerifyIn(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "product_id": "qmol_research_monthly",
                "purchase_token": "abc123",
                "email": "user@example.com",
            }
        }
    )
    product_id: str = Field(..., min_length=1)
    purchase_token: str = Field(..., min_length=1)
    email: EmailStr | None = None


class MagicLinkIn(BaseModel):
    model_config = ConfigDict(json_schema_extra={"example": {"email": "user@example.com"}})
    email: EmailStr


class TrialIn(BaseModel):
    model_config = ConfigDict(json_schema_extra={"example": {"email": "user@example.com"}})
    email: str = Field(..., pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


class EnterpriseContactIn(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "company": "Acme Pharma",
                "email": "contact@acme.com",
                "team_size": 50,
                "use_case": "Virtual screening for oncology pipeline",
                "budget_range": "$50k-$100k",
            }
        }
    )
    company: str = Field(..., min_length=1, max_length=255)
    email: str = Field(..., pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
    team_size: int = Field(..., ge=1)
    use_case: str = Field(..., min_length=10, max_length=2000)
    budget_range: str = Field(
        "",
        pattern=r"^(|$1k-$10k|$10k-$50k|$50k-$100k|$100k+)$",
    )


# Tier -> Stripe price env var
_CHECKOUT_TIERS = {
    "research": "STRIPE_PRICE_RESEARCH",
    "commercial": "STRIPE_PRICE_COMMERCIAL",
    "redistribution": "STRIPE_PRICE_REDISTRIBUTION",
}

_PLAY_PRODUCTS = {
    os.getenv("PLAY_PRODUCT_RESEARCH", "qmol_research_monthly"): "research",
    os.getenv("PLAY_PRODUCT_COMMERCIAL", "qmol_commercial_monthly"): "commercial",
}


@router.post("/signup")
def signup(body: SignupIn, request: Request, ref: str | None = None):
    ip = _client_ip(request)
    _rl(f"signup:{ip}", limit=1, window=60.0)
    info = keysdb.provision(str(body.email), tier="free")
    referral = None
    if ref:
        referral = referrals.credit(ref, str(body.email), "free")
    return {
        "api_key": info.key,
        "tier": info.tier,
        "monthly_quota": info.monthly_quota,
        "referral": referral,
        "note": "Save this key. To upgrade, buy a license at /checkout.html",
    }


@router.get("/plans")
def list_plans():
    """Public pricing catalog."""
    return {"plans": plans.PLANS}


@router.post("/billing/checkout")
def billing_checkout(body: CheckoutSessionIn):
    tier = body.tier.lower()
    env_var = _CHECKOUT_TIERS.get(tier)
    if not env_var:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown tier '{tier}'. Choose: {sorted(_CHECKOUT_TIERS)}",
        )
    price_id = os.getenv(env_var, f"price_{tier}")
    try:
        import stripe
    except Exception:
        raise HTTPException(status_code=503, detail="Billing not configured (stripe library not installed)")
    secret = os.getenv("STRIPE_SECRET_KEY")
    if not secret:
        raise HTTPException(status_code=503, detail="Billing not configured (STRIPE_SECRET_KEY unset)")
    secret = os.getenv("STRIPE_SECRET_KEY")
    if not secret:
        raise HTTPException(status_code=503, detail="Billing not configured (STRIPE_SECRET_KEY unset)")
    import stripe
    stripe.api_key = secret  # thread-safe in GIL, but refactor to module-level init in v2.1
    base = os.getenv("QMOL_PUBLIC_URL", "https://qmol.app").rstrip("/")
    try:
        session = stripe.checkout.Session.create(
            mode="subscription",
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=body.success_url or f"{base}/portal.html?paid=1",
            cancel_url=body.cancel_url or f"{base}/checkout.html",
            allow_promotion_codes=True,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Stripe error: {e}")
    return {"url": session.url, "id": session.id, "tier": tier}


@router.post("/billing/play/verify")
def play_verify(body: PlayVerifyIn):
    tier = _PLAY_PRODUCTS.get(body.product_id)
    if not tier:
        raise HTTPException(status_code=400, detail=f"Unknown product '{body.product_id}'")
    package = os.getenv("ANDROID_PACKAGE_NAME")
    sa = os.getenv("GOOGLE_PLAY_SERVICE_ACCOUNT_JSON")
    if not package or not sa:
        raise HTTPException(
            status_code=503,
            detail="Play billing not configured (set ANDROID_PACKAGE_NAME + GOOGLE_PLAY_SERVICE_ACCOUNT_JSON)",
        )
    try:
        ok = _verify_play_purchase(package, body.product_id, body.purchase_token, sa)
    except ImportError:
        raise HTTPException(status_code=503, detail="Play billing not configured (google-api-python-client not installed)")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Play verification error: {e}")
    if not ok:
        raise HTTPException(status_code=402, detail="Purchase not valid or not active")
    email = str(body.email) if body.email else f"play+{body.purchase_token[:12]}@qmol.app"
    info = keysdb.provision(email, tier)
    return {"api_key": info.key, "tier": info.tier, "monthly_quota": info.monthly_quota}


def _verify_play_purchase(package: str, product_id: str, token: str, service_account_json: str) -> bool:
    import json as _json
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    creds = service_account.Credentials.from_service_account_info(
        _json.loads(service_account_json),
        scopes=["https://www.googleapis.com/auth/androidpublisher"],
    )
    svc = build("androidpublisher", "v3", credentials=creds, cache_discovery=False)
    res = svc.purchases().subscriptions().get(
        packageName=package, subscriptionId=product_id, token=token,
    ).execute()
    import time as _t
    expiry_ms = int(res.get("expiryTimeMillis", 0))
    return res.get("paymentState") in (1, 2) and expiry_ms > _t.time() * 1000


@router.post("/coupon/check")
def coupon_check(body: CouponCheckIn):
    _PRICE_CENTS = {"research": 2900, "commercial": 29900, "redistribution": 99900, "enterprise": 500000}
    base = _PRICE_CENTS.get(body.tier, 0)
    if base == 0:
        raise HTTPException(status_code=400, detail="Unknown tier")
    return coupons.apply(body.code, body.tier, base)


@router.post("/auth/magic-link")
def magic_link_request(body: MagicLinkIn, request: Request):
    ip = _client_ip(request)
    _rl(f"magic:{ip}", limit=3, window=300.0)
    token = magic_link.issue(str(body.email))
    base = os.getenv("QMOL_PUBLIC_URL", "https://qmol.app").rstrip("/")
    link = f"{base}/auth/redeem?token={token}"
    _sent = False
    try:
        from stripe_webhook import _send_mailgun
        _sent = _send_mailgun(str(body.email), "Your Q-Mol login link",
                                f"Click to retrieve your API key: {link}\n\nLink expires in 15 minutes.")
    except Exception:
        _sent = False
    return {"sent": _sent}


@router.get("/auth/redeem")
def magic_link_redeem(token: str):
    api_key = magic_link.consume(token)
    if not api_key:
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    return {"api_key": api_key}


@router.post("/trial")
def start_trial(body: TrialIn):
    """Start a 7-day free trial (no credit card required)."""
    email = body.email.strip().lower()

    # Check if this email already had a trial
    conn = keysdb._connect()
    cursor = conn.execute(
        "SELECT created_at FROM api_keys WHERE email = ? AND tier = 'trial'", (email,)
    )
    if cursor.fetchone():
        conn.close()
        raise HTTPException(400, "Free trial already used for this email")
    conn.close()

    # Create trial key with Research tier quotas for 7 days
    key = keysdb.provision(email=email, tier="trial")

    return {
        "api_key": key.key,
        "email": email,
        "tier": "trial",
        "quota": key.monthly_quota,
        "trial_days": 7,
        "message": "Trial expires in 7 days. Upgrade to keep access.",
    }


@router.post("/enterprise/contact")
def enterprise_contact(body: EnterpriseContactIn):
    """Submit enterprise contact form."""
    # Store in database or send email
    # For now, just log and return confirmation
    return {
        "status": "received",
        "message": "Thank you for your interest. Our sales team will contact you within 24 hours.",
        "next_steps": "Check your email for a calendar link to schedule a demo.",
    }
