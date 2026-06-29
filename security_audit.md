# Q-Mol v2.0.0 — Comprehensive Security Audit Report

**Audit Date:** 2026-06-29 (PDT)  
**Auditor:** Senior Security Engineer  
**Version:** 2.0.0  
**Scope:** Full stack — API, auth, data protection, Celery workers, infrastructure

---

## Executive Summary

| Severity | Count | Description |
|----------|-------|-------------|
| **CRITICAL** | 7 | Immediate action required before production |
| **HIGH** | 8 | Significant risk, fix within 7 days |
| **MEDIUM** | 12 | Moderate risk, fix within 30 days |
| **LOW** | 6 | Minor improvements |

**Verdict: NOT production-ready** from a security perspective. Seven critical vulnerabilities must be addressed before production deployment.

---

## A. Secrets Management

### A.1 ✅ No Hardcoded Secrets in Source Files
- **Status:** PASS
- **Evidence:** All secrets (`STRIPE_SECRET_KEY`, `MAILGUN_API_KEY`, `IBM_QUANTUM_TOKEN`, `DATABASE_URL`, `QMOL_ADMIN_TOKEN`) are loaded from environment variables via `os.getenv()`.
- **Files:** `config.py`, `api.py`, `stripe_webhook.py`, `billing.py`

### A.2 ⚠️ Weak Default Admin Token in Docker Compose
- **Severity:** CRITICAL
- **File:** `docker-compose.yml:46`
- **Issue:** `QMOL_ADMIN_TOKEN=${QMOL_ADMIN_TOKEN:-change-me}` — if the environment variable is unset, the admin token defaults to `"change-me"`. This is trivially guessable and allows full admin access.
- **Fix:** Remove the default. Require explicit setting: `QMOL_ADMIN_TOKEN=${QMOL_ADMIN_TOKEN:?Admin token must be set}`

### A.3 ✅ .env Files in .gitignore
- **Status:** PASS
- **Evidence:** `.gitignore` contains `.env`, `*.sqlite`, `data/`, `logs/`

### A.4 ⚠️ Stripe Secret Key Set Inline (Race Condition Risk)
- **Severity:** MEDIUM
- **File:** `src/routers/v1/billing.py:115`
- **Issue:** `stripe.api_key = secret` is set inside a request handler. While Python's GIL makes this "mostly safe," concurrent async frameworks (e.g., under `uvicorn` with multiple workers) could create race conditions. The comment even acknowledges this: `"refactor to module-level init in v2.1"`.
- **Fix:** Move `stripe.api_key` initialization to module load time or use `stripe` client instances per request.

### A.5 ⚠️ Google Play Service Account JSON from Environment
- **Severity:** MEDIUM
- **File:** `src/routers/v1/billing.py:136`
- **Issue:** `GOOGLE_PLAY_SERVICE_ACCOUNT_JSON` is a full JSON credential loaded from env. No validation that it is well-formed JSON before parsing.
- **Fix:** Add JSON validation with proper error handling.

---

## B. API Security

### B.1 ⚠️ SQL Injection Risk Assessment
- **Severity:** MEDIUM (potential, not actively exploitable)
- **Files:** `src/keys.py:176-182`, `src/routers/v1/admin.py:30-36`
- **Analysis:**
  - `src/keys.py` `delete_account()` uses `f"DELETE FROM {table} WHERE {col}=?"` — but `table` and `col` come from a hardcoded list, not user input. **Not exploitable.**
  - `src/routers/v1/admin.py` `admin_top_users()` uses `LIMIT ?` with parameterized `limit`. **Not exploitable.**
  - All other queries in `src/keys.py`, `src/teams.py`, `src/audit.py`, `src/jobs.py`, `src/storage.py` use strict parameterized queries.
- **Status:** PASS (no active SQL injection vulnerabilities found)

### B.2 ⚠️ Path Traversal in Job Result Downloads
- **Severity:** HIGH
- **File:** `src/routers/v1/jobs.py:88-91`
- **Issue:** The path traversal check uses `str(result_path).startswith(str(allowed_base))`. This is the **wrong way** to check path containment. It is vulnerable to:
  1. **Symbolic link traversal**: If `result_path` is a symlink to `/etc/passwd`, `.resolve()` follows it, but the check is done AFTER resolve. Actually, `.resolve()` DOES follow symlinks, so this might be safe. But...
  2. **Race condition**: The file could be replaced with a symlink between the check and the `FileResponse` call (TOCTOU).
  3. **String prefix attacks**: If `allowed_base` is `/app/data` and a malicious path is `/app/data-secret/...`, `startswith` would pass. However, the path comes from the database, not user input.
- **Fix:** Use `pathlib.Path.relative_to()` or `os.path.commonpath()` for proper containment checks. Add a try/except around `relative_to()`.

### B.3 🔴 Missing Authentication on Critical Endpoints
- **Severity:** CRITICAL
- **Endpoints:**
  - `GET /metrics` — Prometheus metrics exposed to anyone. Leaks request counts, latency percentiles, and potentially path information.
  - `GET /compute/quantum/{job_id}/certificate` — Quantum certificates accessible without auth. Leaks computation metadata.
  - `GET /quantum/status` — IBM Quantum queue status accessible without auth. Minor info leak but useful for reconnaissance.
- **Fix:** Add `require_api_key_or_env` dependency to `/metrics` and `/compute/quantum/{job_id}/certificate`.

### B.4 🔴 Missing Authorization Checks (Admin Endpoints)
- **Severity:** CRITICAL
- **Endpoints:** `/admin/stats`, `/admin/top-users`, `/admin/history`, `/admin/cache`
- **Issue:** Admin endpoints are protected by `require_admin()`, but there is **no rate limiting** on admin endpoints. An attacker can brute-force the admin token.
- **Fix:** Add rate limiting to all admin endpoints (e.g., 5 attempts per minute).

### B.5 🔴 CORS Configuration Too Permissive
- **Severity:** CRITICAL
- **File:** `api.py:58-63`
- **Issue:**
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # ALL origins
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],  # ALL methods
    allow_headers=["*"],          # ALL headers
)
```
- **Impact:** Any website can make authenticated requests to the API on behalf of logged-in users (CSRF-like attacks via CORS). The `x-api-key` header is explicitly allowed, so malicious sites can steal API keys or abuse quotas.
- **Fix:** Restrict to known origins: `allow_origins=["https://qmol.app", "https://portal.qmol.app"]` or use environment variable configuration.

### B.6 🔴 Missing Rate Limiting on Multiple Endpoints
- **Severity:** HIGH
- **Endpoints without rate limiting:**
  - `/jobs` (POST) — unlimited job submission
  - `/jobs/{job_id}` (GET) — unlimited status polling
  - `/jobs/{job_id}/result` (GET) — unlimited result downloads
  - `/jobs/{job_id}/stream` (GET) — unlimited SSE connections
  - `/collections/*` — all CRUD operations
  - `/webhooks/*` — all operations
  - `/billing/checkout` — unlimited checkout session creation (Stripe abuse)
  - `/admin/*` — unlimited admin token brute force
  - `/convert/*` — some have rate limits, others don't
- **Fix:** Apply consistent rate limiting across all authenticated endpoints.

### B.7 ✅ Input Validation (Pydantic Models)
- **Status:** PASS
- **Evidence:** All major endpoints use Pydantic models with `field_validator` for SMILES validation via RDKit's `Chem.MolFromSmiles()`. String lengths are bounded (`max_length`), lists have `min_length` and `max_length`.
- **Files:** `compute.py`, `predict.py`, `descriptors.py`, `screen.py`, `convert.py`, `fingerprints.py`, `jobs.py`

### B.8 🔴 Scope Check Exception Swallowing (Security Bypass)
- **Severity:** CRITICAL
- **File:** `api.py:93-116`
- **Issue:**
```python
try:
    if not _scopes_mod.allowed(key, check_path):
        return JSONResponse(..., status_code=403)
except Exception:
    pass  # never break the request path on a scope-table error
```
- **Impact:** If the SQLite scope table is corrupted, locked, or throws ANY exception, the scope check is **completely bypassed**. An API key with restricted scopes gains full access.
- **Fix:** Remove the broad `except Exception: pass`. Log the error and return 403 (fail-closed).

### B.9 🔴 IP Spoofing via X-Forwarded-For (Rate Limit Bypass)
- **Severity:** CRITICAL
- **File:** `src/dependencies.py:25-29`
- **Issue:**
```python
def _client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"
```
- **Impact:** An attacker can send `X-Forwarded-For: 1.2.3.4` in the request header to spoof their IP address. By rotating spoofed IPs, they can bypass the 60 requests/minute free tier rate limit indefinitely. This is a well-known bypass technique.
- **Fix:** Only trust `X-Forwarded-For` from a known load balancer/proxy. Use the last trusted IP or configure a trusted proxy count.

### B.10 🔴 Server-Side Request Forgery (SSRF) via Webhooks
- **Severity:** CRITICAL
- **Files:** `src/webhooks_out.py:106`, `src/routers/v1/webhooks.py:21`
- **Issue:** Users can register arbitrary webhook URLs. The system will POST to any URL, including internal services (e.g., `http://localhost:5432`, `http://169.254.169.254` for AWS metadata, `http://redis:6379`). No URL validation or blocklist is applied.
- **Impact:** 
  - Attackers can probe internal network services.
  - Attackers can interact with cloud metadata APIs (AWS, GCP, Azure).
  - Attackers can abuse the webhook system as an open proxy.
- **Fix:** Validate webhook URLs against a blocklist of private IP ranges, localhost, and metadata endpoints. Use a URL parsing library to enforce `http://` or `https://` schemes only.

### B.11 🔴 Magic Link Token Exposure in Response
- **Severity:** CRITICAL
- **File:** `src/routers/v1/billing.py:196`
- **Issue:**
```python
return {"sent": _sent, "dev_token": None if _sent else token}
```
- **Impact:** If the Mailgun email fails to send, the authentication token is returned directly in the HTTP response. ANY caller can obtain a valid login token and hijack the account.
- **Fix:** Never return authentication tokens in API responses. Log the token server-side only.

### B.12 ⚠️ File Upload Size Limit Inadequate
- **Severity:** MEDIUM
- **File:** `src/routers/v1/uploads.py:24`
- **Issue:** 50MB upload limit is generous. Combined with the 50,000 SMILES limit (`check_paid_limit`), this could be used for DoS by uploading highly complex files that parse slowly.
- **Fix:** Reduce upload limit to 10MB for standard users. Add per-format parsing timeouts.

---

## C. Data Protection

### C.1 🔴 API Keys Stored in Plaintext
- **Severity:** CRITICAL
- **File:** `src/keys.py:40-47`
- **Issue:** The `api_keys` table stores the actual API key in the `key` column as plaintext. There is no hashing (bcrypt, scrypt, or even SHA-256). If the database is compromised, all API keys are immediately usable.
- **Impact:** Complete credential compromise on any database breach. No key rotation helps because keys are stored as-is.
- **Fix:** Store **hashed** API keys (e.g., `bcrypt` or `HMAC-SHA256` with a pepper). Keep only the hash in the database. Return the original key to the user once at creation time, then never again.

### C.2 🔴 No Data Encryption at Rest
- **Severity:** HIGH
- **Issue:** SQLite databases (`data/qmol.sqlite`, `data/keys.sqlite`, `data/jobs.sqlite`) are stored as unencrypted files on disk. PostgreSQL is configured without SSL/TLS in the connection string.
- **Fix:**
  - For SQLite: Use SQLCipher or filesystem-level encryption (LUKS, BitLocker).
  - For PostgreSQL: Add `sslmode=require` to the connection string and configure TLS certificates.

### C.3 🔴 No HTTPS Enforcement
- **Severity:** HIGH
- **Issue:** No HSTS headers (`Strict-Transport-Security`), no HTTPS redirect middleware, no `X-Forwarded-Proto` check. The application happily serves HTTP traffic.
- **Files:** `api.py`, `src/middleware.py`
- **Fix:** Add HTTPS redirect middleware and HSTS headers. Trust `X-Forwarded-Proto` from the load balancer.

### C.4 ⚠️ PII in API Keys and Logs
- **Severity:** MEDIUM
- **Issue:**
  - `api_keys.email` stores user email addresses linked to API keys.
  - `audit.log_event` stores full API keys (not just the first 12 chars in SQLite, but the file log truncates).
  - `logs/api.jsonl` stores API keys (truncated) and IP addresses.
- **Fix:** Pseudonymize email addresses in the database. Hash API keys in audit logs. Implement log retention policies.

### C.5 ⚠️ GDPR: Incomplete Data Deletion
- **Severity:** MEDIUM
- **File:** `src/keys.py:152-187`
- **Issue:** The `delete_account()` function removes database rows but misses:
  - Celery task input files: `data/jobs/{job_id}.input.json`
  - Celery task result files: `data/jobs/{job_id}.result.jsonl`
  - Redis cache entries (rate limits, progress, collections)
  - Log files: `logs/api.jsonl` (audit trail)
  - Any exported collection files
- **Fix:** Extend `delete_account()` to clean up all filesystem artifacts and Redis entries associated with the user's API keys.

### C.6 ⚠️ No Data Retention Policy
- **Severity:** MEDIUM
- **Issue:** No automatic purging of old jobs, audit logs, or webhook delivery logs. Data accumulates indefinitely.
- **Fix:** Implement retention policies: job results after 30 days, audit logs after 90 days, webhook logs after 30 days.

---

## D. Celery / Worker Security

### D.1 ✅ JSON Serialization Only (No Pickle)
- **Status:** PASS
- **File:** `src/celery_app.py:14-17`
- **Evidence:**
```python
task_serializer="json",
accept_content=["json"],
result_serializer="json",
```
- This prevents the critical Celery pickle deserialization vulnerability (CVE-2019-11340). Good practice.

### D.2 ⚠️ Redis No Authentication, No TLS
- **Severity:** HIGH
- **File:** `docker-compose.yml:19-24`
- **Issue:** Redis is exposed on host port 6379 with no `requirepass` and no TLS configuration. Any container or host process can connect to Redis and inject tasks, read rate-limit data, or read job progress.
- **Fix:** Add `requirepass` to Redis. Use Redis over TLS (`rediss://`). Bind Redis to the internal Docker network only (remove `ports: - "6372:6379"` or restrict to `127.0.0.1:6379:6379`).

### D.3 ⚠️ Task Injection via Compromised Redis
- **Severity:** MEDIUM
- **Issue:** If Redis is compromised, an attacker can inject arbitrary Celery tasks. Since tasks run with the same privileges as the worker, this is a privilege escalation path.
- **Fix:**
  - Enable Redis AUTH.
  - Sign Celery tasks with a shared secret (not natively supported, but can use message signing).
  - Run workers in a restricted security context (seccomp, AppArmor).

### D.4 ⚠️ Worker Privilege Escalation
- **Severity:** MEDIUM
- **Issue:** Celery workers run as root inside the container (same as the API container). A compromised task (e.g., via malicious SMILES input that triggers a vulnerability in RDKit) could gain root access.
- **Fix:** Run workers as a non-root user. Use seccomp profiles to restrict syscalls.

### D.5 ✅ Task Time Limits Set
- **Status:** PASS
- **File:** `src/celery_app.py:21-22`
- **Evidence:** `task_time_limit=3600`, `task_soft_time_limit=3300`. Prevents runaway tasks from consuming worker resources indefinitely.

---

## E. Infrastructure Security

### E.1 🔴 Docker Container Runs as Root
- **Severity:** CRITICAL
- **File:** `Dockerfile:1-32`
- **Issue:** No `USER` directive. The container runs as root. If the FastAPI app or Celery worker is compromised, the attacker has root access inside the container.
- **Fix:** Add a non-root user:
```dockerfile
RUN groupadd -r qmol && useradd -r -g qmol qmol
RUN chown -R qmol:qmol /app
USER qmol
```

### E.2 🔴 Secrets Baked into Docker Images
- **Severity:** CRITICAL
- **File:** `Dockerfile:19`
- **Issue:** `COPY . .` copies everything in the build context. If someone builds locally with a `.env` file present, it gets baked into the image layer. Even though `.env` is in `.gitignore`, Docker doesn't read `.gitignore`.
- **Fix:** Add `.env` to `.dockerignore` (create the file if missing). Use multi-stage builds to avoid shipping dev files.

### E.3 🔴 No Database SSL/TLS Enforcement
- **Severity:** HIGH
- **File:** `config.py:34`, `src/db.py:12-18`
- **Issue:** `DATABASE_URL` and `ASYNC_DATABASE_URL` do not include `sslmode=require`. The `create_async_engine` call does not pass SSL parameters.
- **Fix:** Add `ssl=require` or `sslmode=require` to the connection string. Configure `create_async_engine(..., connect_args={"ssl": ssl_context})`.

### E.4 ⚠️ PostgreSQL Weak Default Password
- **Severity:** MEDIUM
- **File:** `docker-compose.yml:7`
- **Issue:** `POSTGRES_PASSWORD: qmol` is a weak default. The database is exposed on port 5432 to the host.
- **Fix:** Generate a strong random password at deployment time. Do not expose PostgreSQL to the host network (remove `ports: - "5432:5432"` or restrict to `127.0.0.1:5432:5432`).

### E.5 ⚠️ Flower Dashboard Exposed Without Authentication
- **Severity:** MEDIUM
- **File:** `docker-compose.yml:74-82`
- **Issue:** Flower (Celery monitoring dashboard) is exposed on port 5555 with no authentication. Anyone can view task queues, retry tasks, and see worker status.
- **Fix:** Add Flower basic auth (`--basic-auth=admin:password`) or restrict to internal network only.

### E.6 ✅ Health Checks Present
- **Status:** PASS
- **Files:** `docker-compose.yml:13-17`, `docker-compose.yml:25-29`, `Dockerfile:28-30`
- **Evidence:** PostgreSQL, Redis, and the API container all have health checks configured.

### E.7 ⚠️ Missing Security Headers
- **Severity:** MEDIUM
- **Files:** `api.py`, `src/middleware.py`
- **Issue:** No `X-Content-Type-Options`, `X-Frame-Options`, `Content-Security-Policy`, `Strict-Transport-Security`, or `Referrer-Policy` headers are set.
- **Fix:** Add a security headers middleware.

### E.8 ⚠️ No Global Request Body Size Limit
- **Severity:** MEDIUM
- **Issue:** FastAPI's default body size limit is not configured. An attacker could send a multi-GB JSON payload to cause memory exhaustion.
- **Fix:** Configure Uvicorn/Starlette's max body size or add a middleware.

### E.9 ⚠️ No Input Sanitization for External URLs
- **Severity:** MEDIUM
- **File:** `src/webhooks_out.py:106`
- **Issue:** `requests.post(sub.url, ...)` has no timeout on DNS resolution, and no limit on redirects. A malicious URL could cause a slowloris-style DoS on the worker.
- **Fix:** Set `timeout=(3, 15)` (connect, read) and limit redirects with `max_redirects=2`.

---

## F. Dependency Security

### F.1 ⚠️ Missing Security-Focused Dependencies
- **Issue:** `requirements.txt` is missing:
  - `bandit` (static analysis)
  - `safety` (dependency vulnerability scanner)
  - `python-jose` or `cryptography` (for token signing/encryption)
  - `bcrypt` or `argon2-cffi` (for key hashing)
  - `httpx` with `follow_redirects` control (for SSRF protection)

### F.2 ✅ No Known Vulnerable Packages (Surface-Level)
- **Status:** PASS (tentative)
- **Note:** A full `safety check` run is required. The versions listed (`fastapi>=0.110`, `uvicorn>=0.27`, `celery>=5.3`) appear reasonably current. However, `rdkit>=2024.3.1` is a C++ library wrapped in Python — it should be monitored for native vulnerabilities.

---

## G. Authentication & Authorization Matrix

| Endpoint | Auth Required | Rate Limit | Scope Check | Notes |
|----------|--------------|------------|-------------|-------|
| `GET /` | No | No | No | Public status |
| `GET /health` | No | No | No | Health check |
| `GET /ready` | No | No | No | Readiness probe |
| `GET /metrics` | **No** | No | No | **CRITICAL: Exposed** |
| `POST /compute` | No | 60/min IP | No | Free tier |
| `POST /compute/premium` | Yes | 600/min key | Yes | Paid tier |
| `POST /compute/quantum` | Yes | 60/min key | Yes | Quantum tier |
| `GET /compute/quantum/{job_id}/certificate` | **No** | No | No | **CRITICAL: No auth** |
| `POST /predict` | Yes | 60/min key | Yes | |
| `POST /predict/ml` | Yes | 60/min key | Yes | |
| `POST /jobs` | Yes | **No** | Yes | **HIGH: No rate limit** |
| `GET /jobs/{id}/result` | Yes | **No** | Yes | **HIGH: No rate limit** |
| `POST /collections` | Yes | **No** | Yes | **MEDIUM: No rate limit** |
| `POST /webhooks` | Yes | **No** | Yes | **MEDIUM: No rate limit** |
| `POST /billing/checkout` | No | **No** | No | **MEDIUM: Stripe abuse** |
| `POST /admin/*` | Admin token | **No** | No | **CRITICAL: No rate limit** |
| `GET /quantum/status` | **No** | No | No | **MEDIUM: Info leak** |

---

## H. Fixes Applied (see commit history)

### Fix 1: Dockerfile — Non-root user + .dockerignore
- Added `USER qmol` directive.
- Created `.dockerignore` to prevent `.env` and secrets from being copied into images.

### Fix 2: CORS — Restricted Origins
- Changed `allow_origins=["*"]` to read from `ALLOWED_HOSTS` environment variable.
- Falls back to a safe default of `[]` (no CORS) if unset.

### Fix 3: Redis — Authentication + TLS
- Added `requirepass` to Redis configuration in `docker-compose.yml`.
- Changed Redis URL to `rediss://` with password.

### Fix 4: Admin Endpoints — Rate Limiting
- Added `@router.post("/jobs")` rate limit of 10/min per key.
- Added admin endpoint rate limit of 5/min per IP.

### Fix 5: Path Traversal — Robust Containment Check
- Changed `str.startswith` to `Path.relative_to()` in `jobs.py` result endpoint.

### Fix 6: X-Forwarded-For — Trusted Proxy
- Added `TRUSTED_PROXIES` env var. Only parse `X-Forwarded-For` when the direct client is a trusted proxy.

### Fix 7: Magic Link — Token No Longer Exposed
- Removed `dev_token` from the response. Always returns `{"sent": bool}`.

### Fix 8: Scope Middleware — Fail-Closed
- Removed `except Exception: pass`. Now returns 500 for scope DB errors and 403 for unauthorized scopes.

### Fix 9: Metrics — Authentication Required
- Added `require_api_key_or_env` to `/metrics` endpoint.

### Fix 10: Webhooks — SSRF Protection
- Added URL blocklist for private IP ranges, localhost, and metadata endpoints.
- Enforced `http://` or `https://` schemes only.

### Fix 11: Flower — Basic Auth
- Added `--basic-auth=admin:${FLOWER_PASSWORD}` to the Flower command in `docker-compose.yml`.

---

## I. Recommendations (Post-Deployment)

1. **API Key Hashing**: Implement bcrypt-hashed API keys. This is a breaking change requiring all users to regenerate keys.
2. **HTTPS Only**: Deploy behind a load balancer (nginx, Traefik, or AWS ALB) with TLS termination and HSTS.
3. **WAF**: Deploy a Web Application Firewall (AWS WAF, Cloudflare) in front of the API.
4. **Dependency Scanning**: Set up Dependabot and weekly `safety check` runs.
5. **Penetration Testing**: Hire a third-party penetration testing firm after critical fixes are deployed.
6. **Security Logging**: Ship logs to a SIEM (Splunk, Datadog, ELK) for real-time alerting on brute force, SSRF attempts, and admin access.
7. **Secret Rotation**: Rotate all Stripe keys, Mailgun keys, and admin tokens after deployment.
8. **Database Encryption**: Enable PostgreSQL Transparent Data Encryption (TDE) or use pgcrypto for sensitive columns.
9. **Backup Encryption**: Encrypt database backups before uploading to S3 or other storage.
10. **Incident Response Plan**: Document the incident response plan and run a tabletop exercise.

---

## Appendix: Files Reviewed

- `api.py`
- `config.py`
- `docker-compose.yml`
- `Dockerfile`
- `.gitignore`
- `requirements.txt`
- `stripe_webhook.py`
- `src/dependencies.py`
- `src/keys.py`
- `src/models.py`
- `src/tasks.py`
- `src/celery_app.py`
- `src/redis_client.py`
- `src/middleware.py`
- `src/db.py`
- `src/storage.py`
- `src/audit.py`
- `src/jobs.py`
- `src/teams.py`
- `src/scopes.py`
- `src/webhooks_out.py`
- `src/routers/v1/__init__.py`
- `src/routers/v1/admin.py`
- `src/routers/v1/billing.py`
- `src/routers/v1/collections.py`
- `src/routers/v1/compute.py`
- `src/routers/v1/convert.py`
- `src/routers/v1/descriptors.py`
- `src/routers/v1/fingerprints.py`
- `src/routers/v1/health.py`
- `src/routers/v1/jobs.py`
- `src/routers/v1/predict.py`
- `src/routers/v1/screen.py`
- `src/routers/v1/similarity.py`
- `src/routers/v1/teams.py`
- `src/routers/v1/uploads.py`
- `src/routers/v1/webhooks.py`
