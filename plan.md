# Q-Mol Missing Features Build Plan

## Stage 1 — Core Models & Requirements
- [ ] Update `src/models.py` — Add Collection, CollectionItem, Webhook, WebhookLog tables
- [ ] Update `requirements.txt` — Add strawberry-graphql dependencies

## Stage 2 — Service Modules (no inter-deps)
- [ ] `src/collections/service.py` — Collections CRUD (SQLite + PostgreSQL)
- [ ] `src/export/formats.py` — 3D conversions, FDA report, InChI, CDX
- [ ] `src/pka/predictor.py` — pKa prediction with SMARTS patterns
- [ ] `src/mmpa/analyzer.py` — Matched Molecular Pair Analysis
- [ ] `src/pharmacophore/modeler.py` — Pharmacophore modeling
- [ ] `src/webhooks/service.py` — Enhanced webhook system with events, logs, rotation
- [ ] `src/graphql/schema.py` — Strawberry GraphQL schema

## Stage 3 — Routers (depend on Stage 2)
- [ ] `src/routers/v1/collections.py` — Collections REST API
- [ ] `src/routers/v1/convert.py` — Update with new export formats
- [ ] `src/routers/v1/pka.py` — pKa prediction endpoint
- [ ] `src/routers/v1/mmpa.py` — MMP analysis endpoint
- [ ] `src/routers/v1/pharmacophore.py` — Pharmacophore endpoint
- [ ] `src/routers/v1/webhooks.py` — Replace with enhanced webhook router

## Stage 4 — Integration (depend on Stage 3)
- [ ] `src/routers/v1/__init__.py` — Add all new routers
- [ ] `api.py` — Mount GraphQL endpoint

## Stage 5 — Verification
- [ ] Python syntax check on all new files
- [ ] Import check on all modules
