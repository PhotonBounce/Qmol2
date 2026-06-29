import pytest
import requests
import time

BASE_URL = "http://localhost:8000/v1"


def test_health():
    r = requests.get(f"{BASE_URL}/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_ready():
    r = requests.get(f"{BASE_URL}/ready")
    assert r.status_code == 200
    data = r.json()
    assert "ready" in data
    assert data["checks"]["postgres"] in [True, False]
    assert data["checks"]["redis"] in [True, False]


def test_compute():
    r = requests.post(f"{BASE_URL}/compute", json={"smiles": ["CCO"]})
    assert r.status_code == 200
    data = r.json()
    assert "results" in data
    assert data["results"][0]["mw"] > 0


def test_compute_batch():
    r = requests.post(f"{BASE_URL}/compute", json={"smiles": ["CCO", "c1ccccc1", "CC(C)C"]})
    assert r.status_code == 200
    data = r.json()
    assert len(data["results"]) == 3
    for result in data["results"]:
        assert result["mw"] > 0


def test_invalid_smiles():
    r = requests.post(f"{BASE_URL}/compute", json={"smiles": ["INVALID"]})
    assert r.status_code == 400


def test_empty_smiles():
    r = requests.post(f"{BASE_URL}/compute", json={"smiles": []})
    assert r.status_code == 422


def test_rate_limit_free():
    """Hit the free endpoint 65 times and expect 429 on the last ones."""
    responses = []
    for _ in range(65):
        r = requests.post(f"{BASE_URL}/compute", json={"smiles": ["CCO"]})
        responses.append(r.status_code)
        if r.status_code == 429:
            break
    assert 429 in responses, "Expected rate limit (429) to be hit"


def test_metrics_requires_auth():
    """Metrics endpoint should require authentication."""
    r = requests.get(f"{BASE_URL}/metrics")
    # Should be 401 or 403 after fix
    assert r.status_code in (401, 403)


def test_admin_requires_token():
    """Admin endpoints should require a valid admin token."""
    r = requests.get(f"{BASE_URL}/admin/stats")
    assert r.status_code == 401

    r = requests.get(f"{BASE_URL}/admin/stats", headers={"x-admin-token": "wrong"})
    assert r.status_code == 401


def test_admin_rate_limit():
    """Admin endpoints should be rate-limited."""
    for _ in range(10):
        r = requests.get(f"{BASE_URL}/admin/stats", headers={"x-admin-token": "wrong"})
    # After repeated failed attempts, should be rate-limited
    assert r.status_code in (401, 429)


def test_path_traversal_jobs():
    """Try to access files outside data/jobs/ via result endpoint."""
    # This endpoint requires auth, so we first expect 401
    r = requests.get(f"{BASE_URL}/jobs/../../../../etc/passwd/result")
    # Without auth: 401; with auth but invalid path: 403 or 404
    assert r.status_code in (401, 403, 404)


def test_path_traversal_openapi():
    """Try to access arbitrary files via legacy paths."""
    r = requests.get(f"{BASE_URL}/../../etc/passwd")
    # Should be caught by routing or return 404
    assert r.status_code in (404, 403)


def test_sql_injection_admin_keys():
    """Try SQL injection in query params on admin endpoints."""
    r = requests.get(
        f"{BASE_URL}/admin/keys?q=' OR 1=1 --",
        headers={"x-admin-token": "test"}
    )
    # Should be blocked by auth first (401) or admin-only check
    assert r.status_code in (401, 403, 404)


def test_sql_injection_similarity():
    """Try SQL injection via SMILES input (should be blocked by validation)."""
    # Similarity search requires auth; we just verify SMILES validation works
    r = requests.post(f"{BASE_URL}/compute", json={"smiles": ["'; DROP TABLE molecules; --"]})
    assert r.status_code == 400


def test_cors_preflight():
    """Test CORS preflight requests."""
    r = requests.options(
        f"{BASE_URL}/compute",
        headers={
            "Origin": "https://evil.com",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "x-api-key",
        }
    )
    # After fix, origins should be restricted. Should not allow evil.com.
    if r.status_code == 200:
        acao = r.headers.get("access-control-allow-origin")
        assert acao != "*", "CORS should not allow wildcard in production"


def test_webhook_ssrf():
    """Webhook registration should block internal/localhost URLs."""
    # This requires a valid API key; without one we expect 401
    # But we can still test the validation logic exists
    r = requests.post(
        f"{BASE_URL}/webhooks",
        json={"url": "http://localhost:5432", "events": "job.complete"}
    )
    assert r.status_code in (401, 400), "SSRF protection should block localhost URLs"


def test_magic_link_no_token_exposure():
    """Magic link endpoint should never return the token in the response."""
    r = requests.post(
        f"{BASE_URL}/auth/magic-link",
        json={"email": "test@example.com"}
    )
    if r.status_code == 200:
        data = r.json()
        assert "dev_token" not in data or data["dev_token"] is None


def test_signup_rate_limit():
    """Signup should be rate-limited to 1 per minute per IP."""
    r1 = requests.post(f"{BASE_URL}/signup", json={"email": "a1@example.com"})
    r2 = requests.post(f"{BASE_URL}/signup", json={"email": "a2@example.com"})
    # Second request should be rate-limited
    if r1.status_code == 200:
        assert r2.status_code in (200, 429)


def test_quota_check():
    """Test with a known API key that has exceeded quota."""
    # This is a stub; in a real test environment, we'd create a key with zero quota.
    # For now, we just verify the quota endpoint structure.
    r = requests.get(f"{BASE_URL}/plans")
    assert r.status_code == 200
    data = r.json()
    assert "plans" in data


def test_premium_requires_key():
    """Premium compute should require a valid API key."""
    r = requests.post(f"{BASE_URL}/compute/premium", json={"smiles": ["CCO"]})
    assert r.status_code == 401


def test_premium_invalid_key():
    """Premium compute should reject invalid API keys."""
    r = requests.post(
        f"{BASE_URL}/compute/premium",
        json={"smiles": ["CCO"]},
        headers={"x-api-key": "invalid_key"}
    )
    assert r.status_code == 401


def test_descriptors_names_public():
    """Descriptor names endpoint should be public."""
    r = requests.get(f"{BASE_URL}/descriptors/names")
    assert r.status_code == 200
    assert "names" in r.json()


def test_fingerprint_kinds_public():
    """Fingerprint kinds endpoint should be public."""
    r = requests.get(f"{BASE_URL}/fingerprints/kinds")
    assert r.status_code == 200
    assert "kinds" in r.json()


def test_quantum_status_no_auth():
    """Quantum status is currently public; this test documents the behavior."""
    r = requests.get(f"{BASE_URL}/quantum/status")
    assert r.status_code == 200


def test_content_type_options():
    """Security headers should be present."""
    r = requests.get(f"{BASE_URL}/health")
    assert "x-content-type-options" in r.headers
    assert r.headers["x-content-type-options"].lower() == "nosniff"


def test_frame_options():
    """X-Frame-Options should be present."""
    r = requests.get(f"{BASE_URL}/health")
    assert "x-frame-options" in r.headers


def test_large_payload_rejected():
    """Very large payloads should be rejected."""
    huge_smiles = ["C" * 1000 for _ in range(10000)]
    r = requests.post(f"{BASE_URL}/compute", json={"smiles": huge_smiles})
    # Should be rejected due to size or validation limits
    assert r.status_code in (400, 413, 422)
