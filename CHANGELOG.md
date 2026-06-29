# Changelog

All notable changes to Q-Mol will be documented in this file.

## [2.0.0] - 2024-06-29

### Added
- PostgreSQL + Redis backend with SQLite fallback
- Celery distributed job queue with SSE streaming
- API v2 with 31 domain routers and Pydantic v2
- ML ADMET predictions (logS, hERG — validated models)
- Drug-target interaction screening (EGFR, AChE, BACE1)
- De novo molecular generation and lead optimization
- Natural language query parsing
- Synthesis scoring (SAscore, purchasability, route complexity)
- Molecule collections with team sharing
- 3D format export (PDB, MOL2, CIF, FDA report)
- pKa prediction
- Matched molecular pair analysis
- Pharmacophore modeling
- Enhanced webhook system with HMAC signing
- React dashboard (interactive SPA)
- Flutter mobile app (iOS/Android)
- Kubernetes Helm chart with monitoring
- GraphQL API (removed in 2.0.1)
- Quantum VQE tier (removed in 2.0.1)

### Security
- API keys now hashed with bcrypt
- Rate limiting on all endpoints
- CORS restricted to allowed origins
- HSTS and security headers
- Path traversal protection
- SSRF protection for webhooks
- Non-root Docker containers
- Stripe webhook signature verification

### Changed
- SQLite-only → PostgreSQL + Redis
- Single-threaded worker → Celery distributed tasks
- Pydantic v1 → Pydantic v2
- No versioning → /v1/ API versioning
- Static HTML → React dashboard
- Heuristic predictions → ML models (validated)

### Removed
- GraphQL endpoint (underutilized)
- Quantum VQE tier (not production-ready)
- Unvalidated DTI targets (7 of 10 removed)
- Dev token backdoor
- Examples/ directory
