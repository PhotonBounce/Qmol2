"""Pricing / plan catalog.

Single source of truth consumed by:
  - checkout.html  (shows what you're buying)
  - /plans         (API; used by landing/portal)
  - invoice.py     (tier -> unit price for metered overage)
"""
from __future__ import annotations

# All prices in USD.
PLANS = [
    {
        "id": "free",
        "name": "Free",
        "price_usd": 0,
        "price_monthly": 0,
        "price_yearly": 0,
        "cadence": "forever",
        "monthly_quota": 500,
        "features": [
            "500 SMILES / month",
            "/compute, /similarity",
            "No credit card",
        ],
        "stripe_price_id": None,
    },
    {
        "id": "trial",
        "name": "Trial",
        "price_usd": 0,
        "price_monthly": 0,
        "price_yearly": 0,
        "cadence": "7-day",
        "monthly_quota": 10_000,
        "duration_days": 7,
        "features": [
            "10k SMILES / 7 days",
            "All endpoints (descriptors, substructure, diversity, SDF, Parquet)",
            "No credit card required",
        ],
        "stripe_price_id": None,
    },
    {
        "id": "research",
        "name": "Research",
        "price_usd": 20,
        "price_monthly": 20,
        "price_yearly": 180,  # $60 savings
        "cadence": "month",
        "monthly_quota": 10_000,
        "features": [
            "10k SMILES / month",
            "All endpoints (descriptors, substructure, diversity, SDF, Parquet)",
            "Audit log + CSV exports",
            "Email support",
        ],
        "stripe_price_id": "price_research_monthly",
    },
    {
        "id": "commercial",
        "name": "Commercial",
        "price_usd": 50,
        "price_monthly": 50,
        "price_yearly": 450,  # $150 savings
        "cadence": "month",
        "monthly_quota": 50_000,
        "features": [
            "50k SMILES / month",
            "Commercial redistribution rights",
            "Teams + shared quota pool",
            "Outbound webhooks",
            "Priority email support",
        ],
        "stripe_price_id": "price_commercial_monthly",
    },
    {
        "id": "enterprise",
        "name": "Enterprise",
        "price_usd": None,
        "price_monthly": None,
        "price_yearly": None,
        "cadence": "year",
        "monthly_quota": None,  # Custom
        "features": [
            "Unlimited SMILES / month",
            "SLA + dedicated support",
            "SSO (SAML/OIDC)",
            "Custom model training",
            "On-premise deployment option",
            "Audit logs",
            "Volume pricing",
        ],
        "stripe_price_id": None,
        "contact_url": "https://qmol.app/enterprise",
    },
]


def by_id(plan_id: str) -> dict | None:
    for p in PLANS:
        if p["id"] == plan_id:
            return p
    return None
