"""Utility helpers for quantum chemistry workflows.

Provides SMILES→XYZ conversion, qubit counting, and resource estimation
without requiring any quantum SDK to be installed.
"""
from __future__ import annotations

import logging
from collections import Counter
from typing import Any

from rdkit import Chem
from rdkit.Chem import AllChem

log = logging.getLogger(__name__)

# Rough atomic basis counts for sto-3g (used for quick estimation)
_BASIS_STO3G: dict[str, int] = {
    "H": 1, "He": 1,
    "Li": 5, "Be": 5, "B": 5, "C": 5, "N": 5, "O": 5, "F": 5, "Ne": 5,
    "Na": 9, "Mg": 9, "Al": 9, "Si": 9, "P": 9, "S": 9, "Cl": 9, "Ar": 9,
}

_ATOMIC_NUMBERS: dict[str, int] = {
    "H": 1, "He": 2, "Li": 3, "Be": 4, "B": 5, "C": 6, "N": 7, "O": 8, "F": 9, "Ne": 10,
    "Na": 11, "Mg": 12, "Al": 13, "Si": 14, "P": 15, "S": 16, "Cl": 17, "Ar": 18,
}


def canonical_smiles(smiles: str) -> str | None:
    """Return canonical SMILES, or None if invalid."""
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    return Chem.MolToSmiles(mol, canonical=True)


def smiles_to_xyz(
    smiles: str, optimize: bool = True, seed: int = 42
) -> tuple[list[tuple[str, tuple[float, float, float]]], int]:
    """Convert SMILES to a list of (element, (x, y, z)) tuples and atom count.

    Args:
        smiles: Input SMILES string.
        optimize: Whether to MMFF-optimize the 3D geometry.
        seed: Random seed for EmbedMolecule.

    Returns:
        Tuple of (atoms list, total atom count including H).

    Raises:
        ValueError: If SMILES is invalid.
        RuntimeError: If 3D embedding fails.
    """
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise ValueError(f"Invalid SMILES: {smiles}")
    mol = Chem.AddHs(mol)
    if AllChem.EmbedMolecule(mol, randomSeed=seed) != 0:
        raise RuntimeError("Failed to embed 3D geometry for SMILES: " + smiles)
    if optimize:
        AllChem.MMFFOptimizeMolecule(mol, maxIters=200)
    conf = mol.GetConformer()
    atoms = []
    for a in mol.GetAtoms():
        pos = conf.GetAtomPosition(a.GetIdx())
        atoms.append((a.GetSymbol(), (float(pos.x), float(pos.y), float(pos.z))))
    return atoms, mol.GetNumAtoms()


def count_qubits(num_electrons: int, num_spatial_orbitals: int) -> int:
    """Return qubit count for Jordan-Wigner mapping.

    Jordan-Wigner requires 2 qubits per spatial orbital (one for spin-up,
    one for spin-down).
    """
    return 2 * num_spatial_orbitals


def estimate_vqe_resources(smiles: str, basis: str = "sto-3g") -> dict[str, Any]:
    """Estimate qubits and parameters for a VQE run on a given molecule.

    Uses a rough heuristic based on atomic composition and basis-set size.
    For an accurate count, use the full Hamiltonian builder in vqe_qiskit.

    Returns:
        Dict with estimated num_atoms, num_electrons, nao, qubits, and feasibility flag.
    """
    try:
        atoms, num_atoms = smiles_to_xyz(smiles)
        elem_counts = Counter(e for e, _ in atoms)
        nao = sum(_BASIS_STO3G.get(e, 5) * c for e, c in elem_counts.items())
        nelec = sum(_ATOMIC_NUMBERS.get(e, 6) * c for e, c in elem_counts.items())
        n_qubits = 2 * nao
        return {
            "num_atoms": num_atoms,
            "num_electrons": nelec,
            "estimated_nao": nao,
            "estimated_qubits": n_qubits,
            "feasible": n_qubits <= 12,  # default budget
            "basis": basis,
        }
    except Exception as e:  # noqa: BLE001
        log.warning("VQE resource estimation failed: %s", e)
        return {"feasible": False, "error": str(e), "basis": basis}


def format_pyscf_atom(atoms: list[tuple[str, tuple[float, float, float]]]) -> str:
    """Format atom list into PySCF 'atom' string: 'H 0 0 0; H 0 0 0.74'."""
    return "; ".join(
        f"{sym} {x} {y} {z}" for sym, (x, y, z) in atoms
    )
