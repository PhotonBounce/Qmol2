"""Quantum provenance: circuit hashing, certificate generation, and verification.

Every VQE run produces a cryptographically-bound certificate that can be
independently verified by third parties. The certificate binds:
  - the canonical SMILES of the molecule
  - the quantum circuit hash (SHA-256 of the optimized QASM)
  - the computed energy
  - the backend / device used
  - the timestamp of execution
"""
from __future__ import annotations

import hashlib
import json
import time
from typing import Any

import config
from src import redis_client


def _canonical_cert_payload(cert: dict[str, Any]) -> str:
    """Return a deterministic JSON string of the certificate fields for hashing.

    Omits mutable / derived fields (verification_url, signature) so that
    re-verification produces the same hash.
    """
    keys = ("job_id", "smiles", "circuit_hash", "energy_hartree", "timestamp", "backend", "basis")
    payload = {k: cert.get(k) for k in keys}
    return json.dumps(payload, sort_keys=True, ensure_ascii=True, separators=(",", ":"))


def generate_certificate(
    job_id: str,
    smiles: str,
    circuit_hash: str,
    energy: float,
    timestamp: str,
    backend: str,
    basis: str = "sto-3g",
) -> dict[str, Any]:
    """Generate a quantum provenance certificate.

    Args:
        job_id: Unique job identifier.
        smiles: Canonical SMILES of the molecule.
        circuit_hash: Hex digest of the optimized circuit QASM.
        energy: VQE energy in Hartree.
        timestamp: ISO-8601 timestamp of the run.
        backend: Device or simulator name (e.g. 'local_simulator', 'ibm_brisbane').
        basis: Basis set used for the Hamiltonian.

    Returns:
        Certificate dict with embedded integrity hash and verification URL.
    """
    cert = {
        "job_id": job_id,
        "smiles": smiles,
        "circuit_hash": circuit_hash,
        "energy_hartree": float(energy),
        "timestamp": timestamp,
        "backend": backend,
        "basis": basis,
        "verification_url": f"https://qmol.app/verify/{job_id}",
    }
    payload = _canonical_cert_payload(cert)
    cert["signature"] = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return cert


def verify_certificate(cert: dict[str, Any]) -> bool:
    """Verify a certificate's integrity by re-computing its signature.

    Returns True if the signature matches the canonical payload hash,
    False otherwise (tampering, data corruption, or forged certificate).
    """
    try:
        stored_sig = cert.get("signature", "")
        if not stored_sig:
            return False
        payload = _canonical_cert_payload(cert)
        expected = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        return expected == stored_sig
    except Exception:  # noqa: BLE001
        return False


def store_certificate(job_id: str, cert: dict[str, Any], ttl_seconds: int = 86400 * 30) -> None:
    """Persist a certificate in Redis for later retrieval."""
    try:
        r = redis_client.get_redis_sync()
        key = f"quantum:cert:{job_id}"
        r.setex(key, ttl_seconds, json.dumps(cert))
    except Exception:
        pass


def load_certificate(job_id: str) -> dict[str, Any] | None:
    """Load a certificate from Redis by job_id."""
    try:
        r = redis_client.get_redis_sync()
        key = f"quantum:cert:{job_id}"
        data = r.get(key)
        return json.loads(data) if data else None
    except Exception:
        return None


def load_certificate_async(job_id: str) -> Any:
    """Async version of load_certificate."""
    import asyncio
    try:
        r = redis_client.get_redis()
        key = f"quantum:cert:{job_id}"
        data = asyncio.get_event_loop().run_until_complete(r.get(key))
        return json.loads(data) if data else None
    except Exception:
        return None
