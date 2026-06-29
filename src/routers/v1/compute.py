from fastapi import APIRouter, Request, Header, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import List, Annotated
import uuid
import time

from src import compute, storage, result_cache, ratelimit
from src.dependencies import (
    _client_ip, _rl, check_free_limit, check_paid_limit, check_quota,
    record_usage, require_api_key_or_env, API_KEYS, FREE_LIMIT, PAID_LIMIT
)
import config

router = APIRouter(tags=["compute"])


class ComputeIn(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={"example": {"smiles": ["CCO", "c1ccccc1"]}}
    )
    smiles: List[str] = Field(..., min_length=1, max_length=50000)

    @field_validator("smiles")
    @classmethod
    def validate_smiles(cls, v: List[str]) -> List[str]:
        from rdkit import Chem
        invalid = [s for s in v if Chem.MolFromSmiles(s) is None]
        if invalid:
            raise ValueError(f"Invalid SMILES: {invalid[:5]}")
        return v


class QuantumComputeIn(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "smiles": ["[H]"],
                "basis": "sto-3g",
                "backend": "local",
            }
        }
    )
    smiles: List[str] = Field(..., min_length=1, max_length=500)
    basis: str = Field(default="sto-3g", max_length=20)
    backend: str = Field(default="local", max_length=20)
    # backend: "local" | "ibm" | "aws"

    @field_validator("smiles")
    @classmethod
    def validate_smiles(cls, v: List[str]) -> List[str]:
        from rdkit import Chem
        invalid = [s for s in v if Chem.MolFromSmiles(s) is None]
        if invalid:
            raise ValueError(f"Invalid SMILES: {invalid[:5]}")
        return v

    @field_validator("backend")
    @classmethod
    def validate_backend(cls, v: str) -> str:
        if v not in ("local", "ibm", "aws"):
            raise ValueError("backend must be one of: local, ibm, aws")
        return v


def _run_compute(smiles_list: list[str]) -> list[dict]:
    out = []
    for i, smi in enumerate(smiles_list):
        d = result_cache.memoize(
            "compute", smi,
            lambda i=i, smi=smi: compute.compute_molecule(
                cid=-(i + 1), smiles=smi
            ).to_dict(),
        )
        out.append(d)
    return out


def _run_quantum_compute(
    smiles_list: list[str], basis: str = "sto-3g", backend: str = "local"
) -> list[dict]:
    """Run quantum VQE for each SMILES, generating certificates."""
    from src import quantum
    from src.quantum.provenance import generate_certificate, store_certificate

    out = []
    for i, smi in enumerate(smiles_list):
        job_id = f"q_{uuid.uuid4().hex[:16]}"
        t0 = time.time()
        result = compute.compute_molecule(
            cid=-(i + 1),
            smiles=smi,
            basis=basis,
            use_vqe=True,
            backend=backend,
        ).to_dict()
        runtime = time.time() - t0

        # Generate and store certificate if VQE succeeded
        if result.get("vqe_circuit_hash") and result.get("vqe_energy_hartree") is not None:
            cert = generate_certificate(
                job_id=job_id,
                smiles=smi,
                circuit_hash=result["vqe_circuit_hash"],
                energy=result["vqe_energy_hartree"],
                timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                backend=backend,
                basis=basis,
            )
            store_certificate(job_id, cert)
            result["quantum_certificate"] = cert
            result["quantum_job_id"] = job_id

        result["runtime_seconds"] = runtime
        out.append(result)
    return out


@router.post("/compute")
def compute_free(body: ComputeIn, request: Request):
    ip = _client_ip(request)
    _rl(f"free:{ip}", limit=60, window=60.0)
    check_free_limit(len(body.smiles))
    return {"results": _run_compute(body.smiles)}


@router.post("/compute/premium")
def compute_paid(
    body: ComputeIn,
    x_api_key: Annotated[str | None, Header(default=None)] = None,
):
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing x-api-key header")
    _rl(f"paid:{x_api_key}", limit=600, window=60.0)
    if x_api_key in API_KEYS:
        check_paid_limit(len(body.smiles))
        return {"results": _run_compute(body.smiles)}
    from src import keys as keysdb
    info = keysdb.lookup(x_api_key)
    if not info or not info.active:
        raise HTTPException(status_code=401, detail="Invalid or inactive API key")
    used = keysdb.month_usage(x_api_key)
    if used + len(body.smiles) > info.monthly_quota:
        raise HTTPException(
            status_code=402,
            detail=f"Monthly quota exceeded ({used}/{info.monthly_quota}). Upgrade tier at /checkout.",
        )
    check_paid_limit(len(body.smiles))
    results = _run_compute(body.smiles)
    record_usage(x_api_key, "/compute/premium", len(body.smiles))
    return {
        "results": results,
        "quota": {
            "used_this_month": used + len(body.smiles),
            "monthly_quota": info.monthly_quota,
            "tier": info.tier,
        },
    }


# ---------------------------------------------------------------------------
# Quantum tier endpoints
# ---------------------------------------------------------------------------

@router.post("/compute/quantum")
def compute_quantum(
    body: QuantumComputeIn,
    x_api_key: Annotated[str | None, Header(default=None)] = None,
):
    """Quantum-certified compute. Charged at 50× per molecule.

    Runs VQE for each molecule and returns a quantum provenance certificate.
    """
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing x-api-key header")
    _rl(f"paid:{x_api_key}", limit=60, window=60.0)

    if x_api_key in API_KEYS:
        check_paid_limit(len(body.smiles))
    else:
        from src import keys as keysdb
        info = keysdb.lookup(x_api_key)
        if not info or not info.active:
            raise HTTPException(status_code=401, detail="Invalid or inactive API key")
        used = keysdb.month_usage(x_api_key)
        charge = len(body.smiles) * 50
        if used + charge > info.monthly_quota:
            raise HTTPException(
                status_code=402,
                detail=f"Monthly quota exceeded ({used}/{info.monthly_quota}). Upgrade tier at /checkout.",
            )
        check_paid_limit(len(body.smiles))
        record_usage(x_api_key, "/compute/quantum", charge)

    # Cloud fallback: if IBM queue is too long, switch to local
    backend = body.backend
    if backend == "ibm":
        from src import quantum
        check = quantum.cloud.check_cloud_fallback("ibm")
        if not check.get("use_cloud"):
            backend = "local"

    results = _run_quantum_compute(body.smiles, basis=body.basis, backend=backend)
    return {
        "results": results,
        "backend_used": backend,
        "charge_per_molecule": 50,
    }


@router.get("/compute/quantum/{job_id}/certificate")
def get_quantum_certificate(job_id: str):
    """Download a quantum provenance certificate by job_id."""
    from src.quantum.provenance import load_certificate
    cert = load_certificate(job_id)
    if cert is None:
        raise HTTPException(status_code=404, detail="Certificate not found")
    return cert


@router.get("/quantum/status")
def get_quantum_status():
    """Return IBM Quantum queue status."""
    from src import quantum
    if not quantum.HAS_QISKIT:
        return {
            "qiskit_available": False,
            "ibm_status": {"available": False, "error": "qiskit not installed"},
        }
    return {
        "qiskit_available": True,
        "ibm_status": quantum.cloud.get_ibm_queue_status(),
    }
