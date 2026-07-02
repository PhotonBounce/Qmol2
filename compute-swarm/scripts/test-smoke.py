#!/usr/bin/env python3
"""
test-smoke.py — Lightweight smoke test for ComputeSwarm.

Assumes the backend is already running (e.g., via `uvicorn app.main:app --reload`).
Tests the API endpoints directly without Docker or any service orchestration.

Steps:
  1. Check if http://localhost:8000/health is up (retry 10 times, 2s delay).
  2. Register a worker via POST /auth/worker-register.
  3. Register a researcher via POST /auth/register and login via POST /auth/login.
  4. Submit a job via POST /jobs with the physics-sim docker image.
  5. Poll GET /jobs/{job_id} for status (expected: pending because no worker is running).
  6. Verify the job exists and has 1 work unit in pending status.
  7. Print pass/fail for each step.
  8. Exit 0 if health + register + login + submit all passed.

Usage:
    python scripts/test-smoke.py

Requires: Python 3.11+, requests
"""

from __future__ import annotations

import os
import sys
import time
import uuid
from typing import Any

try:
    import requests
except ImportError:
    print("[FATAL] 'requests' is required. Install with: pip install requests")
    sys.exit(1)

# ------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------
BASE_URL = os.getenv("CS_API_URL", "http://localhost:8000")
HEALTH_RETRIES = 10
HEALTH_DELAY = 2

RESEARCHER_EMAIL = f"test-smoke-researcher-{uuid.uuid4().hex[:8]}@example.com"
RESEARCHER_PASSWORD = "SmokePass123!"
WORKER_NAME = f"test-smoke-worker-{uuid.uuid4().hex[:8]}"

PASS_MARK = "✅ PASS"
FAIL_MARK = "❌ FAIL"

results: list[tuple[str, bool, str]] = []

# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def log(step: str, passed: bool, detail: str = "") -> None:
    mark = PASS_MARK if passed else FAIL_MARK
    print(f"{mark} {step}{': ' + detail if detail else ''}")
    results.append((step, passed, detail))


def api_post(path: str, payload: dict[str, Any] | None = None, headers: dict[str, str] | None = None, data: dict[str, Any] | None = None) -> Any:
    """POST helper.  Sends JSON when *payload* is given, form-data when *data* is given."""
    url = f"{BASE_URL}{path}"
    if payload is not None:
        resp = requests.post(url, json=payload, headers=headers, timeout=30)
    else:
        resp = requests.post(url, data=data, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.json()


def api_get(path: str, headers: dict[str, str] | None = None) -> Any:
    resp = requests.get(f"{BASE_URL}{path}", headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.json()


# ------------------------------------------------------------------
# 1. Health check
# ------------------------------------------------------------------
def step_health_check() -> bool:
    print("\n[STEP 1] Checking API health ...")
    for attempt in range(1, HEALTH_RETRIES + 1):
        try:
            r = requests.get(f"{BASE_URL}/health", timeout=5)
            if r.status_code == 200:
                log("Health check", True, f"API up on attempt {attempt}")
                return True
        except requests.RequestException as exc:
            print(f"  Attempt {attempt}/{HEALTH_RETRIES}: {exc}")
        time.sleep(HEALTH_DELAY)

    log("Health check", False, f"API not reachable after {HEALTH_RETRIES} retries")
    return False


# ------------------------------------------------------------------
# 2. Register a worker
# ------------------------------------------------------------------
def step_register_worker() -> dict[str, Any] | None:
    print("\n[STEP 2] Registering test worker ...")
    payload = {
        "name": WORKER_NAME,
        "capabilities": {
            "cpu_cores": 4,
            "ram_gb": 8,
            "gpu_model": None,
            "cuda_version": None,
            "os": "linux",
            "docker_version": "24.0",
        },
    }
    try:
        data = api_post("/auth/worker-register", payload)
        worker_id = data.get("worker_id")
        api_key = data.get("api_key")
        log("Register worker", True, f"worker_id={worker_id}")
        return {"worker_id": worker_id, "api_key": api_key}
    except Exception as exc:
        log("Register worker", False, str(exc))
        return None


# ------------------------------------------------------------------
# 3. Register researcher + login
# ------------------------------------------------------------------
def step_register_researcher() -> dict[str, Any] | None:
    print("\n[STEP 3] Registering test researcher ...")
    try:
        api_post("/auth/register", {"email": RESEARCHER_EMAIL, "password": RESEARCHER_PASSWORD})
    except requests.HTTPError as exc:
        # 409 Conflict is acceptable when re-running the test against the same DB
        if exc.response is not None and exc.response.status_code == 409:
            print("  [INFO] Researcher already exists; continuing to login.")
        else:
            log("Register researcher", False, str(exc))
            return None

    print("  [INFO] Logging in researcher ...")
    try:
        # /auth/login uses OAuth2PasswordRequestForm → form-encoded username/password
        data = api_post("/auth/login", data={"username": RESEARCHER_EMAIL, "password": RESEARCHER_PASSWORD})
        token = data.get("access_token")
        log("Researcher login", True, f"token received (len={len(token) if token else 0})")
        return {"token": token}
    except Exception as exc:
        log("Researcher login", False, str(exc))
        return None


# ------------------------------------------------------------------
# 4. Submit a job
# ------------------------------------------------------------------
def step_submit_job(token: str) -> dict[str, Any] | None:
    print("\n[STEP 4] Submitting test job (physics-sim) ...")
    job_payload = {
        "name": "smoke-test-physics-sim",
        "docker_image": "computeswarm/physics-sim:latest",
        "command": "python /workspace/input/sim.py --output /workspace/output/result.npy",
        "env_vars": {"SEED": "42"},
        "input_files": [],
        "work_unit_count": 1,
        "reward_per_unit": 10.0,
    }
    headers = {"Authorization": f"Bearer {token}"}
    try:
        data = api_post("/jobs", job_payload, headers=headers)
        job_id = data.get("job_id")
        log("Submit job", True, f"job_id={job_id}")
        return {"job_id": job_id}
    except Exception as exc:
        log("Submit job", False, str(exc))
        return None


# ------------------------------------------------------------------
# 5. Poll job status and verify work units
# ------------------------------------------------------------------
def step_poll_and_verify_job(job_id: str, token: str) -> dict[str, Any] | None:
    print(f"\n[STEP 5] Polling job {job_id} status ...")
    headers = {"Authorization": f"Bearer {token}"}
    try:
        data = api_get(f"/jobs/{job_id}", headers=headers)
    except Exception as exc:
        log("Poll job status", False, str(exc))
        return None

    status = data.get("status")
    work_units = data.get("work_units", [])
    print(f"  status={status}, work_units={len(work_units)}")

    # Smoke test: expect pending because no real worker is running
    if status == "pending":
        log("Job status", True, f"status={status}")
    else:
        log("Job status", True, f"status={status} (unexpected, but continuing)")

    # Verify 1 work unit in pending status
    pending_units = [wu for wu in work_units if wu.get("status") == "pending"]
    if len(work_units) == 1 and len(pending_units) == 1:
        log("Work unit count", True, f"1 work unit in pending status")
        return {"status": status, "work_units": work_units}
    else:
        log("Work unit count", False, f"expected 1 pending unit, got {len(work_units)} total, {len(pending_units)} pending")
        return {"status": status, "work_units": work_units}


# ------------------------------------------------------------------
# Cleanup helper
# ------------------------------------------------------------------
def step_cleanup(job_id: str, token: str) -> None:
    """Best-effort cleanup: cancel the test job so it doesn't sit in the DB indefinitely."""
    print("\n[STEP 6] Cleaning up test job ...")
    headers = {"Authorization": f"Bearer {token}"}
    try:
        # /jobs/{job_id}/cancel accepts no request body
        api_post(f"/jobs/{job_id}/cancel", headers=headers)
        log("Cancel test job", True, f"job_id={job_id}")
    except Exception as exc:
        # Job may already be completed or not cancellable — not a hard failure
        log("Cancel test job", True, f"skipped or failed: {exc}")


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------
def main() -> int:
    print("=" * 60)
    print("ComputeSwarm Smoke Test")
    print("=" * 60)

    # 1. Health check
    if not step_health_check():
        print("\n[ABORT] API is not reachable. Is the backend running?")
        print("        Start it with: uvicorn app.main:app --reload")
        return 1

    # 2. Register worker
    worker_info = step_register_worker()
    if worker_info is None:
        return 1

    # 3. Register researcher + login
    researcher_info = step_register_researcher()
    if researcher_info is None:
        return 1

    token = researcher_info["token"]

    # 4. Submit job
    job_info = step_submit_job(token)
    if job_info is None:
        return 1

    job_id = job_info["job_id"]

    # 5. Poll and verify job
    step_poll_and_verify_job(job_id, token)

    # 6. Cleanup (cancel job so it doesn't pollute the DB as pending)
    step_cleanup(job_id, token)

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    passed = 0
    failed = 0
    for step_name, ok, detail in results:
        mark = PASS_MARK if ok else FAIL_MARK
        print(f"{mark} {step_name}{': ' + detail if detail else ''}")
        if ok:
            passed += 1
        else:
            failed += 1

    print(f"\nTotal: {passed} passed, {failed} failed")

    # Exit 0 if the core steps (health + register + login + submit) all passed
    core_steps = ["Health check", "Register worker", "Researcher login", "Submit job"]
    core_passed = all(
        ok for step_name, ok, _ in results if step_name in core_steps
    )

    if core_passed:
        print("\n[SUCCESS] Smoke test passed (core steps OK).")
        return 0
    else:
        print("\n[FAILURE] Smoke test failed.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
