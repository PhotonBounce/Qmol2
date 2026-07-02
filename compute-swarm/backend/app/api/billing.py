from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.config import settings
from app.db.database import get_db
from app.models import Transaction, User

router = APIRouter(prefix="/billing", tags=["billing"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class CheckoutRequest(BaseModel):
    credits: int = Field(ge=1, le=100000)


class CheckoutResponse(BaseModel):
    session_url: str
    session_id: str


class BalanceResponse(BaseModel):
    credits_balance: float


class WithdrawRequest(BaseModel):
    amount: float = Field(ge=0.0)
    method: str = "stripe"


class WithdrawResponse(BaseModel):
    status: str
    message: str


class TransactionResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    worker_id: uuid.UUID | None
    amount: float
    type: str
    description: str
    created_at: datetime

    class Config:
        from_attributes = True


class PaginatedTransactionsResponse(BaseModel):
    total: int
    skip: int
    limit: int
    items: list[TransactionResponse]


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout_session(
    payload: CheckoutRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CheckoutResponse:
    if not settings.stripe_secret_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe is not configured",
        )
    try:
        import stripe
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe library is not installed",
        )
    stripe.api_key = settings.stripe_secret_key

    # Create a Stripe Checkout session (stub pricing: $1 per credit)
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[
                {
                    "price_data": {
                        "currency": "usd",
                        "product_data": {"name": "ComputeSwarm Credits"},
                        "unit_amount": 100,  # $1.00 per credit in cents
                    },
                    "quantity": payload.credits,
                }
            ],
            mode="payment",
            success_url="https://computeswarm.local/billing/success?session_id={CHECKOUT_SESSION_ID}",
            cancel_url="https://computeswarm.local/billing/cancel",
            customer_email=current_user.email,
        )
        return CheckoutResponse(session_url=session.url, session_id=session.id)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Stripe checkout failed: {exc}",
        ) from exc


@router.get("/balance", response_model=BalanceResponse)
async def get_balance(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BalanceResponse:
    return BalanceResponse(credits_balance=current_user.credits_balance)


@router.post("/withdraw", response_model=WithdrawResponse)
async def request_withdrawal(
    payload: WithdrawRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WithdrawResponse:
    # Stub: payouts are not implemented in MVP
    return WithdrawResponse(
        status="not_implemented",
        message="Payout requests are not implemented in the MVP.",
    )


@router.get("/transactions", response_model=PaginatedTransactionsResponse)
async def list_transactions(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PaginatedTransactionsResponse:
    count_stmt = select(func.count(Transaction.id)).where(Transaction.user_id == current_user.id)
    count_result = await db.execute(count_stmt)
    total = count_result.scalar_one()

    stmt = (
        select(Transaction)
        .where(Transaction.user_id == current_user.id)
        .order_by(Transaction.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(stmt)
    items = result.scalars().all()

    return PaginatedTransactionsResponse(total=total, skip=skip, limit=limit, items=items)
