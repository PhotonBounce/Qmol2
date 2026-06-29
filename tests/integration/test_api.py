import pytest
import os
import time
from unittest.mock import patch
from fastapi.testclient import TestClient
from api import app
from src import keys, ratelimit, jobs as jobs_module

client = TestClient(app)

TEST_EMAIL = "test@qmol.app"
TEST_KEY = None

def _fake_submit(api_key, smiles, endpoint="/jobs", charge=None):
    """Fake job submit that avoids Celery."""
    import uuid, json
    job_id = f"job_{uuid.uuid4().hex[:16]}"
    # Store in local SQLite for testing
    from src.jobs import _connect, DEFAULT_DB
    conn = _connect(DEFAULT_DB)
    conn.execute(
        "INSERT INTO jobs (id, api_key, endpoint, status, n_smiles, charge) VALUES (?, ?, ?, ?, ?, ?)",
        (job_id, api_key, endpoint, "queued", len(smiles), charge or len(smiles)),
    )
    conn.commit()
    conn.close()
    return job_id


def _cleanup_test_email(email: str):
    """Remove all keys and usage for a test email."""
    conn = keys._connect()
    rows = conn.execute("SELECT key FROM api_keys WHERE email = ?", (email,)).fetchall()
    for row in rows:
        k = row[0]
        conn.execute("DELETE FROM usage WHERE key = ?", (k,))
    conn.execute("DELETE FROM api_keys WHERE email = ?", (email,))
    conn.commit()
    conn.close()


@pytest.fixture(scope="module", autouse=True)
def setup_test_key():
    """Create a test API key before running tests."""
    global TEST_KEY
    _cleanup_test_email(TEST_EMAIL)

    info = keys.provision(email=TEST_EMAIL, tier="research")
    TEST_KEY = info.key

    # Monkeypatch jobs.submit to avoid Celery
    jobs_module.submit = _fake_submit

    yield

    # Cleanup
    _cleanup_test_email(TEST_EMAIL)
    # Also reset rate limit buckets
    ratelimit.reset()


@pytest.fixture(autouse=True)
def reset_rate_limits():
    """Reset all rate limit buckets before each test."""
    ratelimit.reset()
    yield


class TestHealth:
    def test_health(self):
        r = client.get("/v1/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert "version" in data

    def test_ready(self):
        r = client.get("/v1/ready")
        assert r.status_code == 200
        data = r.json()
        assert "ready" in data
        assert "checks" in data


class TestCompute:
    def test_compute_single(self):
        r = client.post("/v1/compute", json={"smiles": ["CCO"]})
        assert r.status_code == 200
        data = r.json()
        assert "results" in data
        assert len(data["results"]) == 1
        assert data["results"][0]["mw"] > 0

    def test_compute_batch(self):
        r = client.post("/v1/compute", json={"smiles": ["CCO", "c1ccccc1", "CC(C)C"]})
        assert r.status_code == 200
        assert len(r.json()["results"]) == 3

    def test_compute_invalid_smiles(self):
        r = client.post("/v1/compute", json={"smiles": ["INVALID"]})
        # Pydantic validation returns 422 for invalid SMILES
        assert r.status_code == 422

    def test_compute_unauthorized_premium(self):
        r = client.post("/v1/compute/premium", headers={"x-api-key": "invalid_key"}, json={"smiles": ["CCO"]})
        assert r.status_code == 401

    def test_compute_premium_valid_key(self):
        r = client.post("/v1/compute/premium", headers={"x-api-key": TEST_KEY}, json={"smiles": ["CCO"]})
        assert r.status_code == 200
        data = r.json()
        assert "results" in data
        assert "quota" in data

    def test_compute_quota_exceeded(self):
        # Create a key with very low quota (1)
        limited_email = "limited@qmol.app"
        _cleanup_test_email(limited_email)
        limited_key = keys.provision(email=limited_email, tier="research")
        # Override quota to 1
        conn = keys._connect()
        conn.execute("UPDATE api_keys SET monthly_quota = 1 WHERE key = ?", (limited_key.key,))
        conn.commit()
        conn.close()
        # Use up the quota
        r = client.post("/v1/compute/premium", headers={"x-api-key": limited_key.key}, json={"smiles": ["CCO"]})
        assert r.status_code == 200
        # Next request should fail with 402
        r = client.post("/v1/compute/premium", headers={"x-api-key": limited_key.key}, json={"smiles": ["c1ccccc1"]})
        assert r.status_code == 402
        _cleanup_test_email(limited_email)


class TestPredict:
    def test_predict(self):
        r = client.post("/v1/predict", headers={"x-api-key": TEST_KEY}, json={"smiles": ["CCO"]})
        assert r.status_code == 200
        data = r.json()
        assert "results" in data
        assert len(data["results"]) == 1

    def test_predict_ml(self):
        r = client.post("/v1/predict/ml", headers={"x-api-key": TEST_KEY}, json={"smiles": ["CCO"]})
        # May return 503 if ML models not available, or 200 if available
        assert r.status_code in [200, 503]

    def test_predict_unauthorized(self):
        r = client.post("/v1/predict", json={"smiles": ["CCO"]})
        assert r.status_code == 401


class TestJobs:
    def test_create_job(self):
        r = client.post("/v1/jobs", headers={"x-api-key": TEST_KEY}, json={"smiles": ["CCO", "c1ccccc1"]})
        assert r.status_code == 200
        data = r.json()
        assert "job_id" in data
        assert data["status"] == "queued"

    def test_get_job(self):
        # Create a job first
        r = client.post("/v1/jobs", headers={"x-api-key": TEST_KEY}, json={"smiles": ["CCO"]})
        job_id = r.json()["job_id"]
        # Get job status
        r = client.get(f"/v1/jobs/{job_id}", headers={"x-api-key": TEST_KEY})
        assert r.status_code == 200
        data = r.json()
        assert "status" in data

    def test_job_not_found(self):
        r = client.get("/v1/jobs/nonexistent_job", headers={"x-api-key": TEST_KEY})
        assert r.status_code == 404


class TestBilling:
    def test_signup(self):
        email = "test_signup@qmol.app"
        _cleanup_test_email(email)
        r = client.post("/v1/signup", json={"email": email})
        assert r.status_code == 200
        data = r.json()
        assert "api_key" in data
        assert "tier" in data
        _cleanup_test_email(email)

    def test_plans(self):
        r = client.get("/v1/plans")
        assert r.status_code == 200
        data = r.json()
        assert "plans" in data
        assert len(data["plans"]) >= 3

    def test_usage(self):
        r = client.get("/v1/usage", headers={"x-api-key": TEST_KEY})
        assert r.status_code == 200
        data = r.json()
        assert "used_this_month" in data
        assert "monthly_quota" in data


class TestRateLimiting:
    def test_free_rate_limit(self):
        # Hit the free endpoint multiple times without key
        last_status = 200
        for i in range(65):
            r = client.post("/v1/compute", json={"smiles": ["CCO"]})
            last_status = r.status_code
            if r.status_code == 429:
                break
        # After 60 requests, should get 429
        assert last_status == 429


class TestPathTraversal:
    def test_job_result_path_traversal(self):
        # Try path traversal on job result endpoint
        r = client.get("/v1/jobs/../../../etc/passwd/result", headers={"x-api-key": TEST_KEY})
        # The route parser will treat this as job_id = "../../../etc/passwd" and look it up
        # Should fail with 404 (job not found) because the path doesn't resolve to a real job
        assert r.status_code in [404, 403]


class TestAdmin:
    def test_admin_requires_auth(self):
        r = client.get("/v1/admin/stats")
        assert r.status_code in [401, 403]

    def test_admin_with_wrong_token(self):
        r = client.get("/v1/admin/stats", headers={"x-admin-token": "wrong_token"})
        assert r.status_code in [401, 403]

    def test_admin_with_env_token(self):
        # This requires QMOL_ADMIN_TOKEN to be set in environment
        admin_token = os.getenv("QMOL_ADMIN_TOKEN")
        if not admin_token:
            pytest.skip("QMOL_ADMIN_TOKEN not set")
        r = client.get("/v1/admin/stats", headers={"x-admin-token": admin_token})
        assert r.status_code == 200


class TestMetrics:
    def test_metrics_requires_auth(self):
        r = client.get("/v1/metrics")
        # Missing required header returns 422 in FastAPI/Pydantic v2
        assert r.status_code in [401, 403, 422]

    def test_metrics_with_valid_key(self):
        r = client.get("/v1/metrics", headers={"x-api-key": TEST_KEY})
        assert r.status_code == 200


class TestDescriptors:
    def test_descriptors_names_public(self):
        r = client.get("/v1/descriptors/names")
        assert r.status_code == 200
        data = r.json()
        assert "names" in data

    def test_descriptors_requires_auth(self):
        r = client.post("/v1/descriptors", json={"smiles": ["CCO"]})
        assert r.status_code == 401

    def test_descriptors_with_auth(self):
        r = client.post("/v1/descriptors", headers={"x-api-key": TEST_KEY}, json={"smiles": ["CCO"]})
        assert r.status_code == 200
        data = r.json()
        assert "results" in data


class TestFingerprints:
    def test_fingerprint_kinds_public(self):
        r = client.get("/v1/fingerprints/kinds")
        assert r.status_code == 200
        data = r.json()
        assert "kinds" in data

    def test_fingerprints_requires_auth(self):
        r = client.post("/v1/fingerprints", json={"smiles": ["CCO"]})
        assert r.status_code == 401

    def test_fingerprints_with_auth(self):
        r = client.post("/v1/fingerprints", headers={"x-api-key": TEST_KEY}, json={"smiles": ["CCO"]})
        assert r.status_code == 200
        data = r.json()
        assert "results" in data


class TestSecurityHeaders:
    def test_content_type_options(self):
        r = client.get("/v1/health")
        assert "x-content-type-options" in r.headers
        assert r.headers["x-content-type-options"].lower() == "nosniff"

    def test_frame_options(self):
        r = client.get("/v1/health")
        assert "x-frame-options" in r.headers


class TestCors:
    def test_cors_preflight(self):
        r = client.options(
            "/v1/compute",
            headers={
                "Origin": "https://evil.com",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "x-api-key",
            }
        )
        # CORS middleware is configured but may not allow evil.com
        # If it returns 200, check that wildcard is not used
        if r.status_code == 200:
            acao = r.headers.get("access-control-allow-origin")
            if acao is not None:
                assert acao != "*", "CORS should not allow wildcard in production"


class TestLargePayload:
    def test_large_payload_rejected(self):
        # 501 items exceeds the free tier limit of 500
        huge_smiles = ["C" * 50 for _ in range(501)]
        r = client.post("/v1/compute", json={"smiles": huge_smiles})
        # Should be rejected due to validation limits (free tier 500)
        assert r.status_code in (400, 413, 422)


class TestWebhooks:
    def test_webhook_requires_auth(self):
        r = client.post("/v1/webhooks", json={"url": "http://localhost:5432", "events": "job.complete"})
        assert r.status_code == 401

    def test_webhook_ssrf_no_auth(self):
        # Without auth we expect 401; the actual SSRF validation happens after auth
        r = client.post("/v1/webhooks", json={"url": "http://localhost:5432", "events": "job.complete"})
        assert r.status_code in [401, 400]
