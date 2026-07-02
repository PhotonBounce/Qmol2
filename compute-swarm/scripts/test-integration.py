#!/usr/bin/env python3
"""
test-integration.py — End-to-end integration test for ComputeSwarm.

Steps:
  1. Start all services via docker-compose.
  2. Register a test worker.
  3. Register a test researcher and authenticate (JWT).
  4. Submit a test job (physics-sim example).
  5. Simulate worker processing (heartbeat, claim, submit result).
  6. Poll job status until completed or timeout (120s).
  7. Download results and validate they exist.
  8. Check worker credits were earned.
  9. Print pass/fail for each step and exit 0/1.

Usage:
    python scripts/test-integration.py

Requires: Python 3.11+, requests, docker-compose
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import sys
import tarfile
import tempfile
import time
import uuid
from pathlib import Path
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
ORCHESTRATOR_URL = BASE_URL
TIMEOUT_SEC = int(os.getenv("CS_TEST_TIMEOUT", "120"))
POLL_INTERVAL = 3

RESEARCHER_EMAIL = f"test-researcher-{uuid.uuid4().hex[:8]}@example.com"
RESEARCHER_PASSWORD = "TestPass123!"
WORKER_NAME = f"test-worker-{uuid.uuid4().hex[:8]}"

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


def docker_compose(args: list[str]) -> int:
    """Run docker-compose or docker compose."""
    import subprocess

    cmd = ["docker-compose"] if _has_docker_compose_v1() else ["docker", "compose"]
    cmd += args
    print(f"[CMD] {' '.join(cmd)}")
    return subprocess.call(cmd, cwd=str(Path(__file__).parent.parent))


def _has_docker_compose_v1() -> bool:
    import shutil

    return shutil.which("docker-compose") is not None


def api_post_form(path: str, data: dict[str, Any], headers: dict[str, str] | None = None) -> dict[str, Any]:
    resp = requests.post(f"{BASE_URL}{path}", data=data, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.json()


def api_post(path: str, payload: dict[str, Any], headers: dict[str, str] | None = None) -> dict[str, Any]:
    resp = requests.post(f"{BASE_URL}{path}", json=payload, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.json()


def api_get(path: str, headers: dict[str, str] | None = None) -> dict[str, Any]:
    resp = requests.get(f"{BASE_URL}{path}", headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.json()


# ------------------------------------------------------------------
# Worker simulation helpers (for integration test)
# ------------------------------------------------------------------

def _create_fake_result_tar() -> str:
    """Create a temporary fake result.tar.gz and return its path."""
    fd, path = tempfile.mkstemp(suffix="_result.tar.gz")
    os.close(fd)
    with tarfile.open(path, "w:gz") as tar:
        dummy_data = b"This is a fake simulation result for integration testing.\n"
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


def _try_heartbeat(worker_id: str, api_key: str) -> dict[str, Any] | None:
    """Try heartbeat with JSON payload and X-Worker-API-Key header."""
    try:
        payload = {
            "worker_id": str(worker_id),
            "status": "online",
            "capabilities_snapshot": {},
        }
        headers = {"X-Worker-API-Key": api_key}
        resp = requests.post(
            f"{BASE_URL}/workers/heartbeat", json=payload, headers=headers, timeout=30
        )
        resp.raise_for_status()
        data = resp.json()
        assigned = data.get("assigned_work_unit")
        if assigned:
            return assigned
    except Exception as exc:
        print(f"  [INFO] Heartbeat failed: {exc}")
    return None


def _try_claim_unit(api_key: str) -> dict[str, Any] | None:
    """Try claim-unit via form data."""
    try:
        resp = requests.post(
            f"{BASE_URL}/workers/claim-unit", data={"api_key": api_key}, timeout=30
        )
        resp.raise_for_status()
        data = resp.json()
        work_unit = data.get("work_unit")
        if work_unit:
            return work_unit
        if data.get("work_unit_id"):
            return data
    except Exception as exc:
        print(f"  [INFO] Claim-unit failed: {exc}")
    return None


def step_worker_process(job_id: str, worker_id: str, api_key: str) -> dict[str, Any] | None:
    print("\n[STEP 5] Simulating worker processing ...")

    # 5a. Heartbeat
    print("  [5a] Sending heartbeat ...")
    assigned_unit = _try_heartbeat(worker_id, api_key)
    if assigned_unit:
        print(f"  [INFO] Heartbeat returned work unit: {assigned_unit.get('work_unit_id')}")
        log("Worker heartbeat", True, f"assigned unit {assigned_unit.get('work_unit_id')}")
    else:
        print("  [INFO] Heartbeat did not return a work unit (will try claim-unit)")
        log("Worker heartbeat", True, "no unit assigned (continuing to claim)")

    # 5b. Claim unit
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

        # 5e. Submit result
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
                resp = requests.post(
                    f"{BASE_URL}/workers/submit-result", data=data, files=files, timeout=60
                )
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
# 1. Start all services
# ------------------------------------------------------------------
def step_start_services() -> bool:
    print("\n[STEP 1] Starting all services via docker-compose ...")
    rc = docker_compose(["up", "-d", "--build"])
    if rc != 0:
        log("Start services", False, f"docker-compose up failed (rc={rc})")
        return False

    # Wait for API health endpoint
    print("[STEP 1] Waiting for API health endpoint ...")
    for _ in range(40):
        try:
            r = requests.get(f"{BASE_URL}/health", timeout=5)
            if r.status_code == 200:
                log("Start services", True, "API healthy")
                return True
        except requests.RequestException:
            pass
        time.sleep(2)

    log("Start services", False, "API health endpoint never became ready")
    return False


# ------------------------------------------------------------------
# 2. Register a test worker
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
        # 409 (already exists) is acceptable if re-running tests
        if exc.response is not None and exc.response.status_code == 409:
            print("[STEP 3] Researcher already exists; continuing to login.")
        else:
            log("Register researcher", False, str(exc))
            return None

    try:
        # /auth/login accepts both JSON and form data
        data = api_post_form("/auth/login", {"username": RESEARCHER_EMAIL, "password": RESEARCHER_PASSWORD})
        token = data.get("access_token")
        log("Researcher login", True, f"token received (len={len(token) if token else 0})")
        return {"token": token}
    except Exception as exc:
        log("Researcher login", False, str(exc))
        return None


# ------------------------------------------------------------------
# 4. Submit a test job (physics-sim example)
# ------------------------------------------------------------------
def step_submit_job(token: str) -> dict[str, Any] | None:
    print("\n[STEP 4] Submitting test job (physics-sim) ...")
    # The physics-sim example: python /workspace/input/sim.py --output /workspace/output/result.npy
    job_payload = {
        "name": "integration-test-physics-sim",
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
# 6. Poll job status until completed / failed / timeout
# ------------------------------------------------------------------
def step_poll_job(job_id: str, token: str) -> dict[str, Any] | None:
    print(f"\n[STEP 6] Polling job status (timeout={TIMEOUT_SEC}s) ...")
    headers = {"Authorization": f"Bearer {token}"}
    start = time.time()
    final_status = None
    while time.time() - start < TIMEOUT_SEC:
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
        log("Poll job completion", False, f"timeout after {TIMEOUT_SEC}s")
        return {"status": "timeout"}


# ------------------------------------------------------------------
# 7. Download results and validate
# ------------------------------------------------------------------
def step_download_results(job_id: str, token: str) -> bool:
    print(f"\n[STEP 7] Downloading results for job {job_id} ...")
    headers = {"Authorization": f"Bearer {token}"}
    try:
        # Fetch presigned download URL
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
# 8. Check worker credits
# ------------------------------------------------------------------
def step_check_worker_credits(worker_id: str, api_key: str) -> bool:
    print(f"\n[STEP 8] Checking worker credits for {worker_id} ...")
    start = time.time()
    poll_timeout = 60
    while time.time() - start < poll_timeout:
        try:
            headers = {"X-Worker-API-Key": api_key}
            data = api_get(f"/workers/profile", headers=headers)
            total_credits = data.get("total_credits_earned", 0)
            if total_credits > 0:
                log("Worker credits", True, f"total_credits_earned={total_credits}")
                return True
            print(f"  credits={total_credits}, waiting for scheduler ... (elapsed={int(time.time() - start)}s)")
        except Exception as exc:
            print(f"  poll error: {exc}")
        time.sleep(3)
    log("Worker credits", False, f"total_credits_earned=0 after {poll_timeout}s")
    return False


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------
def main() -> int:
    print("=" * 60)
    print("ComputeSwarm Integration Test")
    print("=" * 60)

    # 1. Start services
    if not step_start_services():
        return 1

    # 2. Register worker
    worker_info = step_register_worker()
    if worker_info is None:
        return 1

    # 3. Register researcher
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
        pass  # Continue to poll and report

    # 6. Poll job
    poll_info = step_poll_job(job_id, token)
    if poll_info is None or poll_info.get("status") != "completed":
        # Still continue to print summary
        pass

    # 7. Download results (best-effort even if failed/timeout)
    step_download_results(job_id, token)

    # 8. Check worker credits
    step_check_worker_credits(worker_info["worker_id"], worker_info["api_key"])

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

    # Tear down (optional — keep running for inspection if failed)
    print("\n[TEARDOWN] Stopping services ...")
    docker_compose(["down", "-v"])

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
