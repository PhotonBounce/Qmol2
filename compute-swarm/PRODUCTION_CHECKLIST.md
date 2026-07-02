# ComputeSwarm — Production Deployment Checklist

Use this checklist before taking ComputeSwarm live. Do not skip items.

## Pre-Deployment

- [ ] **Change all default passwords**
  - [ ] PostgreSQL `DB_PASSWORD` (not `changeme`)
  - [ ] MinIO `MINIO_ROOT_PASSWORD` (not `minioadmin`)
  - [ ] Any sample / seeded user passwords removed

- [ ] **Generate strong `SECRET_KEY`**
  - Run `python scripts/generate-secrets.py` or `openssl rand -base64 64`
  - Minimum 64 characters, random, never committed to git

- [ ] **Configure Stripe live keys**
  - [ ] `STRIPE_SECRET_KEY` starts with `sk_live_`
  - [ ] `STRIPE_WEBHOOK_SECRET` is set and the webhook endpoint is registered in Stripe Dashboard
  - [ ] Test keys are NOT used in production

- [ ] **Set up DNS A records**
  - [ ] `api.yourdomain.com` → VPS public IP
  - [ ] `app.yourdomain.com` → VPS public IP
  - [ ] `www.yourdomain.com` (optional) → VPS public IP

- [ ] **Verify firewall rules**
  - [ ] Ports 80 (HTTP) and 443 (HTTPS) are open
  - [ ] Port 22 (SSH) is restricted to your IP if possible
  - [ ] All other ports (e.g., 5432, 6379, 9000, 9001) are closed to the public

- [ ] **Provision VPS resources**
  - [ ] At least 2 vCPU, 4 GB RAM, 40 GB SSD for small production
  - [ ] Docker Engine + Docker Compose plugin installed
  - [ ] Automatic security updates enabled (`unattended-upgrades` on Ubuntu)

## Deployment

- [ ] **Copy and customize `.env.prod`**
  - [ ] `API_DOMAIN` and `APP_DOMAIN` match DNS records
  - [ ] `LETSENCRYPT_EMAIL` is a real, monitored address
  - [ ] All database and MinIO credentials are strong and unique

- [ ] **Run `scripts/deploy.sh`**
  - [ ] No errors during image build
  - [ ] Database migrations run successfully (`alembic upgrade head`)
  - [ ] All services show `Up` in `docker compose ps`

- [ ] **Verify SSL certificates**
  - [ ] `https://api.yourdomain.com/health` returns valid certificate
  - [ ] `https://app.yourdomain.com` returns valid certificate
  - [ ] HTTP → HTTPS redirect works (curl -I http://api.yourdomain.com)

- [ ] **Create first admin user**
  - [ ] Run `python backend/scripts/create_admin.py` inside the API container
  - [ ] Log in to the dashboard and verify admin access

## Post-Deployment

- [ ] **Enable automated backups**
  - [ ] `scripts/backup-db.sh` runs successfully when executed manually
  - [ ] Cron job installed: `0 3 * * * /opt/computeswarm/scripts/backup-db.sh`
  - [ ] Backup retention policy is configured (default 7 days)
  - [ ] At least one backup has been restored to a test environment to verify integrity

- [ ] **Set up monitoring alerts**
  - [ ] UptimeRobot / Pingdom / StatusCake monitoring `https://api.yourdomain.com/health`
  - [ ] Alert channel (email / Slack / PagerDuty) configured
  - [ ] Prometheus scraping `/metrics` (optional but recommended)
  - [ ] Dashboard (`app.yourdomain.com`) also monitored

- [ ] **Configure rate limiting**
  - [ ] Traefik `api-ratelimit` middleware is active (`100 req/min` per IP)
  - [ ] Load-tested or verified with a simple script

- [ ] **Review CORS origins**
  - [ ] `main.py` CORS `allow_origins` is set to exact domains, not `["*"]`
  - [ ] `https://app.yourdomain.com` is explicitly allowed
  - [ ] Localhost origins are removed in production

- [ ] **Disable debug mode**
  - [ ] `APP_ENV=production` in `.env`
  - [ ] FastAPI `debug` is not enabled (no auto-reload in container)
  - [ ] SQLAlchemy `echo=False` (no query logging in production)

- [ ] **Set up log rotation**
  - [ ] Docker logging driver is `json-file` with `max-size: 100m` and `max-file: 3`
  - [ ] Log aggregation (Loki / Fluentd / CloudWatch) planned or enabled
  - [ ] Container disk usage monitored to prevent log bloat

- [ ] **Test disaster recovery**
  - [ ] Simulate database restore from backup on a clean VPS
  - [ ] Document recovery time objective (RTO) and recovery point objective (RPO)
  - [ ] Verify MinIO object data is not lost on container recreation
  - [ ] Have a runbook for:
    - [ ] Database corruption / restore
    - [ ] SSL certificate expiry
    - [ ] VPS migration (new IP, DNS cutover)
    - [ ] Worker node failure / replacement

## Security & Compliance

- [ ] **Run a security audit**
  - [ ] `docker scout` or Trivy scan on all images
  - [ ] No secrets in image layers (`docker history` / `dive` check)
  - [ ] Non-root user running the API container (`appuser`)

- [ ] **Review dependency freshness**
  - [ ] `pip list --outdated` checked for backend packages
  - [ ] `npm audit` checked for dashboard packages

- [ ] **Stripe webhook security**
  - [ ] Webhook endpoint verifies `STRIPE_WEBHOOK_SECRET`
  - [ ] Idempotency keys handled for duplicate events

## Sign-off

- [ ] All items above are checked and verified
- [ ] A second engineer has reviewed the deployment
- [ ] Go-live date and time documented
- [ ] Rollback plan documented and tested

---

> **Tip:** Store this checklist in your project wiki and update it after each major release or infrastructure change.
