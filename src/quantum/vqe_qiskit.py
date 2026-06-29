"""Qiskit Nature VQE implementation for Q-Mol.

Runs Variational Quantum Eigensolver (VQE) using:
  1. PySCFDriver to build the molecular Hamiltonian
  2. Jordan-Wigner mapping to qubits
  3. UCCSD ansatz with Hartree-Fock initial state
  4. SLSQP optimizer
  5. Qiskit primitives Estimator (local statevector simulation)

The returned energy is the variational ground-state energy. For H₂ in
sto-3g, this converges to the FCI reference within ~1 mHa.
"""
from __future__ import annotations

import hashlib
import logging
import time
from typing import Any

log = logging.getLogger(__name__)


def run_vqe(smiles: str, basis: str = "sto-3g", max_qubits: int = 12) -> dict[str, Any]:
    """Run VQE for a molecule using Qiskit Nature. Returns energy + provenance.

    Args:
        smiles: Canonical SMILES of the molecule.
        basis: Basis set for the electronic structure calculation.
        max_qubits: Maximum number of qubits allowed. If the molecule requires
            more qubits than this, the run is skipped with an error.

    Returns:
        Dict with keys: success, method, basis, energy_hartree, num_qubits,
        num_electrons, num_spatial_orbitals, circuit_hash, runtime_seconds,
        optimal_parameters.
    """
    t0 = time.time()

    try:
        from qiskit.primitives import Estimator
        from qiskit_algorithms import VQE
        from qiskit_algorithms.optimizers import SLSQP
        from qiskit_nature.second_q.drivers import PySCFDriver
        from qiskit_nature.second_q.units import DistanceUnit
        from qiskit_nature.second_q.mappers import JordanWignerMapper
        from qiskit_nature.second_q.circuit.library import UCCSD, HartreeFock
    except ImportError as e:
        raise RuntimeError(f"Qiskit VQE dependencies not available: {e}")

    from .utils import smiles_to_xyz, format_pyscf_atom

    # 1. Convert SMILES to XYZ
    atoms, _ = smiles_to_xyz(smiles)

    # 2. Build Hamiltonian with PySCFDriver
    atom_str = format_pyscf_atom(atoms)
    driver = PySCFDriver(
        atom=atom_str,
        unit=DistanceUnit.ANGSTROM,
        charge=0,
        spin=0,
        basis=basis,
    )
    problem = driver.run()

    # 3. Check qubit count
    mapper = JordanWignerMapper()
    qubit_op = mapper.map(problem.hamiltonian.second_q_op())
    num_qubits = qubit_op.num_qubits

    if num_qubits > max_qubits:
        return {
            "success": False,
            "error": f"Qubit count {num_qubits} exceeds budget {max_qubits}",
            "num_qubits": num_qubits,
            "method": "VQE-Qiskit/skipped",
        }

    # 4. Build UCCSD ansatz with Hartree-Fock initial state
    initial_state = HartreeFock(
        num_spatial_orbitals=problem.num_spatial_orbitals,
        num_particles=problem.num_particles,
        qubit_mapper=mapper,
    )

    ansatz = UCCSD(
        num_spatial_orbitals=problem.num_spatial_orbitals,
        num_particles=problem.num_particles,
        qubit_mapper=mapper,
        reps=1,
        initial_state=initial_state,
    )

    # 5. Run VQE with SLSQP optimizer
    estimator = Estimator()
    optimizer = SLSQP(maxiter=100)
    vqe = VQE(estimator, ansatz, optimizer)

    result = vqe.compute_minimum_eigenvalue(qubit_op)
    energy = float(result.eigenvalue)

    # 6. Circuit hash for provenance
    try:
        optimal_circuit = ansatz.assign_parameters(result.optimal_parameters)
        try:
            from qiskit.qasm2 import dumps
            circuit_qasm = dumps(optimal_circuit)
        except Exception:
            circuit_qasm = str(optimal_circuit)
        circuit_hash = hashlib.sha256(circuit_qasm.encode()).hexdigest()[:32]
    except Exception as e:  # noqa: BLE001
        log.warning("Could not generate circuit hash: %s", e)
        circuit_hash = "n/a"

    runtime = time.time() - t0

    return {
        "success": True,
        "method": "VQE-Qiskit",
        "basis": basis,
        "energy_hartree": energy,
        "num_qubits": num_qubits,
        "num_electrons": problem.num_particles,
        "num_spatial_orbitals": problem.num_spatial_orbitals,
        "circuit_hash": circuit_hash,
        "runtime_seconds": runtime,
        "optimal_parameters": {k: float(v) for k, v in result.optimal_parameters.items()},
    }
