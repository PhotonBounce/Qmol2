#!/usr/bin/env python3
"""
test-e2e.py — End-to-end test for ComputeSwarm with a simulated worker.

Runs the full flow including a simulated worker that processes the job via
HTTP calls (no Docker needed for the worker, just HTTP requests).

Steps:
  1. Start API if not running (check health, skip if already up).
  2. Register a worker (get worker_id + api_key).
  3. Register researcher and login (get JWT).
  4. Submit a job with 1 work unit (physics-sim).
  5. Simulate worker processing:
       a. Worker sends heartbeat POST /workers/heartbeat → gets assigned work unit.
       b. Worker "claims" the unit via POST /workers/claim-unit (or uses heartbeat response).
       c. Create a fake result.tar.gz file locally.
       d. Compute SHA-256 of the fake result.
       e. Submit result via POST /workers/submit-result with multipart form.
  6. Poll job status until completed or timeout (60 seconds).
  7. Download results via GET /jobs/{job_id}/results.
  8. Verify results are non-empty.
  9. Check worker profile GET /workers/profile to see credits earned.
  10. Print pass/fail summary, exit 0/1.

Usage:
    python scripts/test-e2e.py

Requires: Python 3.11+, requests
"""

from __future__ import annotations

import hashlib
import io
import os
import sys
import tarfile
import tempfile
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
POLL_TIMEOUT = 90
POLL_INTERVAL = 3

RESEARCHER_EMAIL = f"test-e2e-researcher-{uuid.uuid4().hex[:8]}@example.com"
RESEARCHER_PASSWORD = "E2ePass123!"
WORKER_NAME = f"test-e2e-worker-{uuid.uuid4().hex[:8]}"

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


def _api_url(path: str) -> str:
    return f"{BASE_URL}{path}"


def api_post_json(path: str, payload: dict[str, Any], headers: dict[str, str] | None = None) -> Any:
    resp = requests.post(_api_url(path), json=payload, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.json()


def api_post_form(path: str, data: dict[str, Any], headers: dict[str, str] | None = None, files: dict[str, Any] | None = None) -> Any:
    resp = requests.post(_api_url(path), data=data, headers=headers, files=files, timeout=60)
    resp.raise_for_status()
    return resp.json()


def api_get(path: str, headers: dict[str, str] | None = None, params: dict[str, Any] | None = None) -> Any:
    resp = requests.get(_api_url(path), headers=headers, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


# ------------------------------------------------------------------
# 1. Start API if not running
# ------------------------------------------------------------------
def step_ensure_api() -> bool:
    print("\n[STEP 1] Ensuring API is running ...")
    for attempt in range(1, HEALTH_RETRIES + 1):
        try:
            r = requests.get(f"{BASE_URL}/health", timeout=5)
            if r.status_code == 200:
                log("API health", True, f"API up on attempt {attempt}")
                return True
        except requests.RequestException as exc:
            print(f"  Attempt {attempt}/{HEALTH_RETRIES}: {exc}")
        time.sleep(HEALTH_DELAY)

    log("API health", False, f"API not reachable after {HEALTH_RETRIES} retries")
    print("  [INFO] Start the backend manually: uvicorn app.main:app --reload")
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
        data = api_post_json("/auth/worker-register", payload)
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
        api_post_json("/auth/register", {"email": RESEARCHER_EMAIL, "password": RESEARCHER_PASSWORD})
    except requests.HTTPError as exc:
        if exc.response is not None and exc.response.status_code == 409:
            print("  [INFO] Researcher already exists; continuing to login.")
        else:
            log("Register researcher", False, str(exc))
            return None

    print("  [INFO] Logging in researcher ...")
    try:
        # /auth/login uses OAuth2PasswordRequestForm → form-encoded username/password
        data = api_post_form("/auth/login", data={"username": RESEARCHER_EMAIL, "password": RESEARCHER_PASSWORD})
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
        "name": "e2e-test-physics-sim",
        "docker_image": "computeswarm/physics-sim:latest",
        "command": "python /workspace/input/sim.py --output /workspace/output/result.npy",
        "env_vars": {"SEED": "42"},
        "input_files": [],
        "work_unit_count": 1,
        "reward_per_unit": 10.0,
    }
    headers = {"Authorization": f"Bearer {token}"}
    try:
        data = api_post_json("/jobs", job_payload, headers=headers)
        job_id = data.get("job_id")
        log("Submit job", True, f"job_id={job_id}")
        return {"job_id": job_id}
    except Exception as exc:
        log("Submit job", False, str(exc))
        return None


# ------------------------------------------------------------------
# 5. Simulate worker processing
# ------------------------------------------------------------------
def _try_heartbeat(worker_id: str, api_key: str) -> dict[str, Any] | None:
    """Try heartbeat with JSON payload and X-Worker-API-Key header."""
    try:
        payload = {
            "worker_id": str(worker_id),
            "status": "online",
            "capabilities_snapshot": {},
        }
        headers = {"X-Worker-API-Key": api_key}
        resp = requests.post(_api_url("/workers/heartbeat"), json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        assigned = data.get("assigned_work_unit")
        if assigned:
            return assigned
    except Exception as exc:
        print(f"  [INFO] Heartbeat (JSON) failed: {exc}")
    return None


def _try_claim_unit(api_key: str) -> dict[str, Any] | None:
    """Try claim-unit via form data (backend expects Form auth)."""
    try:
        resp = requests.post(_api_url("/workers/claim-unit"), data={"api_key": api_key}, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        # Backend wraps in "work_unit"; real worker client expects top-level fields
        work_unit = data.get("work_unit")
        if work_unit:
            return work_unit
        # Fallback: maybe the backend returns it directly
        if data.get("work_unit_id"):
            return data
    except Exception as exc:
        print(f"  [INFO] Claim-unit failed: {exc}")
    return None


def _create_fake_result_tar() -> str:
    """Create a temporary fake result.tar.gz and return its path."""
    fd, path = tempfile.mkstemp(suffix="_result.tar.gz")
    os.close(fd)
    with tarfile.open(path, "w:gz") as tar:
        dummy_data = b"This is a fake simulation result for E2E testing.\n"
        info = tarfile.TarInfo(name="result.txt")
        info.size = len(dummy_data)
        tar.addfile(info, io.BytesIO(dummy_data))
    return path


def _compute_sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def step_worker_process(job_id: str, worker_id: str, api_key: str) -> dict[str, Any] | None:
    print("\n[STEP 5] Simulating worker processing ...")

    # 5a. Heartbeat (optional — may return assigned work unit)
    print("  [5a] Sending heartbeat ...")
    assigned_unit = _try_heartbeat(worker_id, api_key)
    if assigned_unit:
        print(f"  [INFO] Heartbeat returned work unit: {assigned_unit.get('work_unit_id')}")
        log("Worker heartbeat", True, f"assigned unit {assigned_unit.get('work_unit_id')}")
    else:
        print("  [INFO] Heartbeat did not return a work unit (will try claim-unit)")
        log("Worker heartbeat", True, "no unit assigned (continuing to claim)")

    # 5b. Claim unit (if heartbeat didn't assign one)
    if not assigned_unit:
        print("  [5b] Claiming work unit ...")
        assigned_unit = _try_claim_unit(api_key)
        if not assigned_unit:
            log("Worker claim-unit", False, "no work unit available")
            return None
        print(f"  [INFO] Claimed work unit: {assigned_unit.get('work_unit_id')}")
        log("Worker claim-unit", True, f"unit {assigned_unit.get('work_unit_id')}")

    work_unit_id = assigned_unit.get("work_unit_id")
    if not work_unit_id:
        log("Worker claim-unit", False, "missing work_unit_id in response")
        return None

    # 5c. Create fake result.tar.gz
    print("  [5c] Creating fake result.tar.gz ...")
    result_path = _create_fake_result_tar()
    try:
        # 5d. Compute SHA-256
        print("  [5d] Computing SHA-256 ...")
        checksum = _compute_sha256(result_path)
        print(f"  [INFO] checksum={checksum}")

        # 5e. Submit result via multipart form
        print("  [5e] Submitting result ...")
        with open(result_path, "rb") as f:
            files = {"result_file": ("result.tar.gz", f, "application/gzip")}
            data = {
                "work_unit_id": str(work_unit_id),
                "api_key": api_key,
                "checksum": checksum,
                "logs": "Simulated worker execution completed successfully.\n",
            }
            try:
                resp = requests.post(_api_url("/workers/submit-result"), data=data, files=files, timeout=60)
                resp.raise_for_status()
                submit_data = resp.json()
                log("Submit result", True, f"status={submit_data.get('status')}")
                return {"work_unit_id": work_unit_id, "checksum": checksum}
            except Exception as exc:
                log("Submit result", False, str(exc))
                return None
    finally:
        try:
            os.remove(result_path)
        except OSError:
            pass


# ------------------------------------------------------------------
# 6. Poll job status until completed or timeout
# ------------------------------------------------------------------
def step_poll_job(job_id: str, token: str) -> dict[str, Any] | None:
    print(f"\n[STEP 6] Polling job status (timeout={POLL_TIMEOUT}s) ...")
    headers = {"Authorization": f"Bearer {token}"}
    start = time.time()
    final_status = None
    while time.time() - start < POLL_TIMEOUT:
        try:
            data = api_get(f"/jobs/{job_id}", headers=headers)
            status = data.get("status")
            print(f"  status={status} (elapsed={int(time.time() - start)}s)")
            if status in ("completed", "failed"):
                final_status = status
                break
        except requests.RequestException as exc:
            print(f"  poll error: {exc}")
        time.sleep(POLL_INTERVAL)

    if final_status == "completed":
        log("Poll job completion", True, f"completed in {int(time.time() - start)}s")
        return {"status": "completed"}
    elif final_status == "failed":
        log("Poll job completion", False, "job failed")
        return {"status": "failed"}
    else:
        log("Poll job completion", False, f"timeout after {POLL_TIMEOUT}s")
        return {"status": "timeout"}


# ------------------------------------------------------------------
# 7. Download results
# ------------------------------------------------------------------
def step_download_results(job_id: str, token: str) -> bool:
    print(f"\n[STEP 7] Downloading results for job {job_id} ...")
    headers = {"Authorization": f"Bearer {token}"}
    try:
        data = api_get(f"/jobs/{job_id}/results", headers=headers)
        download_url = data.get("download_url")
        if not download_url:
            log("Download results", False, "no download_url returned")
            return False

        r = requests.get(download_url, timeout=30)
        r.raise_for_status()
        content_length = len(r.content)
        if content_length > 0:
            log("Download results", True, f"{content_length} bytes downloaded")
            return True
        else:
            log("Download results", False, "empty result file")
            return False
    except Exception as exc:
        log("Download results", False, str(exc))
        return False


# ------------------------------------------------------------------
# 8. Verify results are non-empty (already done in step_download_results)
# ------------------------------------------------------------------
# folded into step_download_results


# ------------------------------------------------------------------
# 9. Check worker profile
# ------------------------------------------------------------------
def step_check_worker_profile(worker_id: str, api_key: str) -> bool:
    print(f"\n[STEP 9] Checking worker profile for {worker_id} ...")
    start = time.time()
    poll_timeout = 45
    while time.time() - start < poll_timeout:
        try:
            data = api_get("/workers/profile", headers={"X-Worker-API-Key": api_key})
            total_credits = data.get("total_credits_earned", 0)
            if total_credits > 0:
                log("Worker profile", True, f"total_credits_earned={total_credits}")
                return True
            print(f"  credits={total_credits}, waiting for scheduler ... (elapsed={int(time.time() - start)}s)")
        except Exception as exc:
            print(f"  poll error: {exc}")
        time.sleep(3)
    log("Worker profile", False, f"total_credits_earned=0 after {poll_timeout}s")
    return False


# ------------------------------------------------------------------
# Cleanup helper
# ------------------------------------------------------------------
def cleanup_job(job_id: str, token: str) -> None:
    """Best-effort cleanup: cancel the test job so it doesn't pollute the DB."""
    print(f"\n[CLEANUP] Cancelling test job {job_id} ...")
    headers = {"Authorization": f"Bearer {token}"}
    try:
        # /jobs/{job_id}/cancel accepts no request body
        resp = requests.post(_api_url(f"/jobs/{job_id}/cancel"), headers=headers, timeout=30)
        resp.raise_for_status()
        log("Cancel test job", True, f"job_id={job_id}")
    except Exception as exc:
        log("Cancel test job", True, f"skipped or failed: {exc}")


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------
def main() -> int:
    print("=" * 60)
    print("ComputeSwarm E2E Test")
    print("=" * 60)

    # 1. Ensure API is running
    if not step_ensure_api():
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

    # 5. Simulate worker processing
    worker_result = step_worker_process(job_id, worker_info["worker_id"], worker_info["api_key"])
    if worker_result is None:
        # Still continue to poll and report
        pass

    # 6. Poll job status
    poll_info = step_poll_job(job_id, token)

    # 7. Download results (best-effort even if timeout)
    step_download_results(job_id, token)

    # 8. Check worker profile
    step_check_worker_profile(worker_info["worker_id"], worker_info["api_key"])

    # 9. Cleanup (cancel job to avoid DB pollution)
    cleanup_job(job_id, token)

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

    # Exit 0 if the critical path succeeded (API up, worker registered, researcher logged in,
    # job submitted, worker processed, job completed)
    critical_steps = [
        "API health",
        "Register worker",
        "Researcher login",
        "Submit job",
    ]
    critical_passed = all(ok for step_name, ok, _ in results if step_name in critical_steps)

    job_completed = any(
        step_name == "Poll job completion" and ok for step_name, ok, _ in results
    )

    if critical_passed and job_completed:
        print("\n[SUCCESS] E2E test passed.")
        return 0
    else:
        print("\n[FAILURE] E2E test failed.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
