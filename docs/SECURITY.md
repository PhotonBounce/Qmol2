# Security Policy

## Reporting Vulnerabilities

If you discover a security vulnerability in Q-Mol, please report it responsibly:

- **Email:** security@qmol.app
- **Do NOT** open a public GitHub issue for security bugs.
- **Do NOT** disclose the vulnerability publicly until we have had a chance to fix it.

## Response Timeline

| Severity | Acknowledgment | Initial Assessment | Fix Deployment |
|----------|---------------|-------------------|--------------|
| Critical | 24 hours | 72 hours | 7 days |
| High | 24 hours | 72 hours | 30 days |
| Medium | 48 hours | 7 days | 90 days |

## Security Measures

Q-Mol implements the following security controls:

### Authentication & Authorization
- All paid API endpoints require a valid `x-api-key` header.
- API keys are stored hashed with bcrypt (not in plaintext).
- Admin endpoints require a separate `x-admin-token` header.
- Rate limiting prevents brute-force attacks on all endpoints.

### Data Protection
- All API traffic uses TLS 1.3 in production.
- Database connections use SSL/TLS with certificate verification.
- PII (email addresses) is pseudonymized in audit logs.
- GDPR "right to be forgotten" is supported via the account deletion endpoint.

### Input Validation
- All SMILES strings are validated via RDKit before processing.
- Pydantic models enforce strict type and length validation on all inputs.
- SQL queries use parameterized statements to prevent injection.
- File upload paths are validated to prevent directory traversal.

### Infrastructure
- Docker containers run as a non-root user (`qmol`).
- Redis uses authentication (`requirepass`) and TLS.
- PostgreSQL uses strong passwords and SSL/TLS connections.
- Regular dependency scanning with Safety, Bandit, and Trivy.
- Automated Dependabot alerts for vulnerable dependencies.

### Network Security
- CORS is restricted to known origins (`https://qmol.app` and subdomains).
- Webhook URLs are validated against SSRF blocklists (no private IPs, localhost, or metadata endpoints).
- `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, and HSTS headers are enforced.
- The `X-Forwarded-For` header is only trusted from known load balancers.

## Secure Deployment Checklist

Before deploying Q-Mol to production, verify:

- [ ] `QMOL_ADMIN_TOKEN` is set to a strong random string (≥32 chars).
- [ ] `DATABASE_URL` includes `sslmode=require`.
- [ ] `REDIS_URL` uses `rediss://` with a strong password.
- [ ] `ALLOWED_HOSTS` is set to your domain(s).
- [ ] Stripe keys (`STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`) are production keys, not test keys.
- [ ] `FLOWER_PASSWORD` is set for Celery monitoring.
- [ ] Docker image is built with `.dockerignore` excluding `.env` and secrets.
- [ ] Container runs as non-root user.
- [ ] Health checks (`/health`, `/ready`) are monitored by your orchestrator.
- [ ] Log shipping to SIEM is configured.
- [ ] Backup encryption is enabled.

## Security Audit History

| Date | Auditor | Scope | Report |
|------|---------|-------|--------|
| 2026-06-29 | Internal Security Team | Full stack | `security_audit.md` |

## License

This security policy is provided under the same license as the Q-Mol project.
