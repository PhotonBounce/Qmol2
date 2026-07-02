# Changelog

All notable changes to this project will be documented in this file.

## [0.1.0-MVP] — 2024-07-01

### Added
- Job submission and management (containerized compute jobs)
- Worker daemon with Docker execution and auto-registration
- Result validation and auto-validation for MVP
- Credit system (balance, spending, worker payouts)
- Billing stubs with Stripe placeholder integration
- Admin dashboard with stats, worker management, job overview, and user list
- Seed data script for local development (`backend/scripts/seed.py`)
- Email notification stubs (console logging, ready for SMTP)
- Help & FAQ page for researchers and workers
- Loading skeletons and toast notifications across the dashboard
- Responsive navbar with mobile collapse and footer with version info
- CI/CD GitHub Actions stubs (`ci.yml`, `deploy.yml`)
- Dockerignore files for backend, dashboard, and worker

### Known Issues
- No full redundancy validation (only auto-validate in MVP)
- No Stripe live integration (credits seeded manually)
- No WebSocket real-time updates (polling only)
- Worker GPU scheduling not yet implemented
- Email system is stubbed (logs to console, SMTP config TODO)

