"""Q-Mol Quantum Chemistry Package — VQE implementations with provenance.

Exports:
  - run_vqe_qiskit: Qiskit Nature VQE (preferred)
  - run_vqe_pyqpanda: pyQPanda VQE (fallback)
  - provenance: certificate generation and verification
  - cloud: IBM Quantum / AWS Braket submission helpers
  - utils: molecular geometry, qubit counting, resource estimation
"""
from __future__ import annotations

# Qiskit VQE (preferred backend)
try:
    from .vqe_qiskit import run_vqe as run_vqe_qiskit
    HAS_QISKIT = True
except Exception:  # noqa: BLE001
    HAS_QISKIT = False
    run_vqe_qiskit = None  # type: ignore

# pyQPanda VQE (fallback backend)
try:
    from .vqe_pyqpanda import run_vqe as run_vqe_pyqpanda
    HAS_PYQPANDA = True
except Exception:  # noqa: BLE001
    HAS_PYQPANDA = False
    run_vqe_pyqpanda = None  # type: ignore

from .provenance import generate_certificate, verify_certificate
from .cloud import (
    submit_ibm_quantum,
    submit_aws_braket,
    get_ibm_queue_status,
    get_ibm_backend_status,
)
from .utils import (
    smiles_to_xyz,
    count_qubits,
    estimate_vqe_resources,
    canonical_smiles,
)

__all__ = [
    "run_vqe_qiskit",
    "run_vqe_pyqpanda",
    "HAS_QISKIT",
    "HAS_PYQPANDA",
    "generate_certificate",
    "verify_certificate",
    "submit_ibm_quantum",
    "submit_aws_braket",
    "get_ibm_queue_status",
    "get_ibm_backend_status",
    "smiles_to_xyz",
    "count_qubits",
    "estimate_vqe_resources",
    "canonical_smiles",
]
