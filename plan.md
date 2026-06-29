# Stage 3: FastAPI API Modernization — Plan

## Objective
Refactor ~1,800-line `api.py` into a versioned, modular router structure with Pydantic v2, middleware improvements, and SDK generation pipeline.

## Stage Breakdown

### Stage 1 — Foundations (independent)
- Create `src/routers/` directory structure
- Create `src/schemas.py` — shared Pydantic v2 schemas (ErrorResponse, PaginatedResponse, HealthResponse, ReadyResponse)
- Create `src/middleware.py` — RequestID, GZip, TrustedHost, Timing middlewares
- Create `src/routers/__init__.py` (empty)
- Create `src/routers/v1/__init__.py` (imports all sub-routers)
- Create `src/dependencies.py` — centralized auth helpers extracted from api.py

### Stage 2 — Router Files (independent of each other, depend on Stage 1)
- `compute.py` — POST /v1/compute, POST /v1/compute/premium
- `descriptors.py` — POST /v1/descriptors, GET /v1/descriptors/names
- `similarity.py` — POST /v1/similarity, POST /v1/similarity/matrix
- `screen.py` — POST /v1/screen
- `predict.py` — POST /v1/predict
- `fingerprints.py` — POST /v1/fingerprints, GET /v1/fingerprints/kinds
- `cluster.py` — POST /v1/cluster
- `jobs.py` — POST /v1/jobs, GET /v1/jobs/{id}, GET /v1/jobs/{id}/stream, DELETE /v1/jobs/{id}, GET /v1/jobs/{id}/result
- `convert.py` — POST /v1/convert
- `tautomers.py` — POST /v1/tautomers
- `conformers.py` — POST /v1/conformers
- `standardize.py` — POST /v1/standardize
- `formula.py` — POST /v1/formula
- `reactions.py` — POST /v1/reactions, GET /v1/reactions/templates
- `scaffolds.py` — POST /v1/scaffolds
- `retro.py` — POST /v1/retro
- `substructure.py` — POST /v1/substructure
- `diversity.py` — POST /v1/diversity
- `mcs.py` — POST /v1/mcs
- `charges.py` — POST /v1/charges
- `alerts.py` — GET /v1/alerts/catalogs, POST /v1/alerts
- `stereoisomers.py` — POST /v1/stereoisomers
- `shape3d.py` — POST /v1/shape3d
- `dedup.py` — POST /v1/dedup
- `admin.py` — All /admin/* endpoints
- `billing.py` — POST /v1/signup, GET /v1/plans, POST /v1/billing/checkout, POST /v1/billing/play/verify, POST /v1/coupon/check, etc.
- `teams.py` — POST /v1/teams, POST /v1/teams/members, DELETE /v1/teams/members, GET /v1/teams/{id}
- `uploads.py` — POST /v1/upload/compute
- `webhooks.py` — POST /v1/webhooks/subscribe, DELETE /v1/webhooks/subscribe
- `health.py` — GET /v1/health, GET /v1/ready, GET /v1/metrics
- `misc.py` — GET /, GET /openapi-static.json, GET /status, GET /badge/uptime, GET /dashboard, GET /app, GET /reference, GET /privacy, GET /terms, GET /account/export, DELETE /account, GET /usage, GET /usage/history, GET /audit, GET /audit.csv, GET /invoice, GET /invoice.csv, GET /referral, POST /auth/rotate, POST /auth/magic-link, GET /auth/redeem, POST /key/rotate, GET /key/scopes, PUT /key/scopes, DELETE /key/scopes, GET /react/templates, POST /export/parquet, POST /download/sdf

### Stage 3 — Core Refactor (depends on Stage 2)
- Refactor `api.py` to ~200-300 lines with app factory, middleware registration, v1_router inclusion, backward-compatible redirects
- Update `scripts/dump_openapi.py` to reference new app structure
- Update `requirements.txt` if needed (add `structlog` for middleware logging)

### Stage 4 — Config & DevEx (depends on Stage 3)
- Update `config.py` with new env vars (ALLOWED_HOSTS, etc.)
- Update `.env.example` with new env vars
- Create `.github/workflows/sdk-publish.yml`
- Create `sdks/README.md`

### Stage 5 — Test Updates (depends on Stage 3)
- Update all test files to use `/v1/` paths where applicable
- Keep backward-compatible paths tested as well

## Quality Gates
- [ ] api.py < 400 lines
- [ ] All endpoints reachable at both `/v1/` and root paths
- [ ] All Pydantic models use v2 syntax with SMILES validators
- [ ] OpenAPI spec validates without warnings
- [ ] Tests pass

## Backward Compatibility
- Root paths (`/compute`, `/jobs`, etc.) redirect to `/v1/` equivalents via 307 redirects
- All existing request/response shapes preserved exactly
- No breaking changes to auth, quotas, or business logic
