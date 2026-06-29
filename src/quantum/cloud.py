"""Cloud submission helpers for IBM Quantum and AWS Braket.

All functions are optional — the app works even if neither
qiskit-ibm-runtime nor amazon-braket-sdk is installed.
"""
from __future__ import annotations

import logging
import time
from typing import Any

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# IBM Quantum
# ---------------------------------------------------------------------------

try:
    from qiskit_ibm_runtime import QiskitRuntimeService
    HAS_IBM_RUNTIME = True
except Exception:  # noqa: BLE001
    HAS_IBM_RUNTIME = False


def get_ibm_queue_status(token: str | None = None) -> dict[str, Any]:
    """Return IBM Quantum queue status for available backends.

    If token is not provided, falls back to config.IBM_QUANTUM_TOKEN.
    """
    if not HAS_IBM_RUNTIME:
        return {"available": False, "error": "qiskit-ibm-runtime not installed"}

    try:
        import config
        effective_token = token or config.IBM_QUANTUM_TOKEN
        if not effective_token:
            return {"available": False, "error": "IBM_QUANTUM_TOKEN not set"}

        service = QiskitRuntimeService(channel="ibm_quantum", token=effective_token)
        backends = service.backends(operational=True, simulator=False)
        status = []
        for backend in backends:
            bs = backend.status()
            status.append({
                "name": backend.name,
                "operational": bs.operational,
                "pending_jobs": bs.pending_jobs,
                "queue_info": str(bs.status_msg),
            })
        return {"available": True, "backends": status}
    except Exception as e:  # noqa: BLE001
        log.warning("IBM Quantum status check failed: %s", e)
        return {"available": False, "error": str(e)}


def get_ibm_backend_status(token: str | None = None, backend_name: str = "ibm_brisbane") -> dict[str, Any]:
    """Return detailed status for a single IBM Quantum backend."""
    if not HAS_IBM_RUNTIME:
        return {"available": False, "error": "qiskit-ibm-runtime not installed"}

    try:
        import config
        effective_token = token or config.IBM_QUANTUM_TOKEN
        if not effective_token:
            return {"available": False, "error": "IBM_QUANTUM_TOKEN not set"}

        service = QiskitRuntimeService(channel="ibm_quantum", token=effective_token)
        backend = service.backend(backend_name)
        bs = backend.status()
        return {
            "available": True,
            "name": backend.name,
            "operational": bs.operational,
            "pending_jobs": bs.pending_jobs,
            "queue_info": str(bs.status_msg),
            "qubits": len(backend.configuration().qubits) if hasattr(backend, "configuration") else None,
        }
    except Exception as e:  # noqa: BLE001
        log.warning("IBM backend status check failed: %s", e)
        return {"available": False, "error": str(e)}


def submit_ibm_quantum(
    circuit: Any,
    token: str | None = None,
    backend_name: str = "ibm_brisbane",
    shots: int = 1024,
) -> dict[str, Any]:
    """Submit a compiled Qiskit circuit to IBM Quantum.

    Returns a dict with job_id, status, and estimated queue time.
    If the queue is > 1 hour, returns a recommendation to fall back to simulator.
    """
    if not HAS_IBM_RUNTIME:
        return {"success": False, "error": "qiskit-ibm-runtime not installed"}

    try:
        import config
        effective_token = token or config.IBM_QUANTUM_TOKEN
        if not effective_token:
            return {"success": False, "error": "IBM_QUANTUM_TOKEN not set"}

        service = QiskitRuntimeService(channel="ibm_quantum", token=effective_token)
        backend = service.backend(backend_name)
        bs = backend.status()

        # Fallback recommendation: if pending jobs > 200, queue is likely > 1 hr
        if bs.pending_jobs > 200:
            log.warning(
                "IBM Quantum %s queue is long (%d jobs). Consider local simulator.",
                backend_name, bs.pending_jobs,
            )
            return {
                "success": False,
                "error": f"Queue too long ({bs.pending_jobs} jobs). Use local simulator.",
                "queue_jobs": bs.pending_jobs,
                "fallback_recommended": True,
            }

        # Use the Sampler primitive for VQE (or Estimator for energy)
        from qiskit_ibm_runtime import EstimatorV2 as Estimator, Session

        with Session(backend=backend) as session:
            estimator = Estimator(session=session)
            # Note: actual VQE with IBM Runtime requires transpiling and parameter binding
            # This function returns a job handle; the caller manages the VQE loop.
            job = estimator.run([circuit], shots=shots)
            return {
                "success": True,
                "job_id": job.job_id(),
                "backend": backend_name,
                "status": "submitted",
                "queue_jobs": bs.pending_jobs,
            }
    except Exception as e:  # noqa: BLE001
        log.warning("IBM Quantum submission failed: %s", e)
        return {"success": False, "error": str(e)}


# ---------------------------------------------------------------------------
# AWS Braket
# ---------------------------------------------------------------------------

try:
    from braket.aws import AwsQuantumTask, AwsSession
    HAS_BRAKET = True
except Exception:  # noqa: BLE001
    HAS_BRAKET = False


def submit_aws_braket(
    circuit: Any,
    role_arn: str | None = None,
    device_arn: str = "arn:aws:braket:::device/quantum-simulator/amazon/sv1",
    shots: int = 1024,
    s3_bucket: str = "qmol-quantum-results",
    s3_prefix: str = "vqe",
) -> dict[str, Any]:
    """Submit a circuit to AWS Braket.

    Returns a dict with task_arn, status, and S3 result location.
    """
    if not HAS_BRAKET:
        return {"success": False, "error": "amazon-braket-sdk not installed"}

    try:
        import config
        effective_role = role_arn or config.AWS_BRAKET_ROLE_ARN
        if not effective_role:
            return {"success": False, "error": "AWS_BRAKET_ROLE_ARN not set"}

        # Build an AWS Braket circuit from a Qiskit circuit (requires conversion)
        # For now, we assume the caller has already converted or we use the
        # braket transpiler if available.
        try:
            from qiskit_braket_provider import AWSBraketProvider
            provider = AWSBraketProvider()
            backend = provider.get_backend(device_arn.split("/")[-1])
            job = backend.run(circuit, shots=shots)
            return {
                "success": True,
                "task_arn": job.id(),
                "backend": device_arn,
                "status": "submitted",
                "s3_bucket": s3_bucket,
                "s3_prefix": s3_prefix,
            }
        except Exception as e:  # noqa: BLE001
            log.warning("Braket provider submission failed: %s", e)
            return {"success": False, "error": str(e)}
    except Exception as e:  # noqa: BLE001
        log.warning("AWS Braket submission failed: %s", e)
        return {"success": False, "error": str(e)}


def check_cloud_fallback(backend: str, token: str | None = None) -> dict[str, Any]:
    """Check if a cloud backend queue is too long and recommend fallback.

    Returns a dict with:
      - use_cloud: bool — whether cloud submission is viable
      - fallback_reason: str | None — why fallback is recommended
      - queue_info: dict — raw queue status
    """
    if backend == "ibm":
        status = get_ibm_queue_status(token)
        if not status.get("available"):
            return {"use_cloud": False, "fallback_reason": status.get("error"), "queue_info": status}
        # Check if any backend has a reasonable queue
        backends = status.get("backends", [])
        short_queue = [b for b in backends if b.get("pending_jobs", 999) <= 50]
        if not short_queue:
            return {
                "use_cloud": False,
                "fallback_reason": "All IBM backends have queues > 50 jobs (likely > 1 hour).",
                "queue_info": status,
            }
        return {"use_cloud": True, "fallback_reason": None, "queue_info": status}

    if backend == "aws":
        # AWS Braket SV1 is usually fast; no queue check needed for simulators
        return {"use_cloud": True, "fallback_reason": None, "queue_info": {"available": True}}

    return {"use_cloud": False, "fallback_reason": f"Unknown backend: {backend}", "queue_info": {}}
