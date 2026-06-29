"""Molecular optimization using local search in chemical space.

A simple genetic-algorithm engine that mutates a seed molecule toward a
target property (or a weighted combination of targets).  All mutation
operators are chemically meaningful and produce RDKit-valid structures.
"""
from __future__ import annotations

import random
from typing import Callable

from rdkit import Chem
from rdkit.Chem import AllChem, Descriptors, QED

from . import scorer

# ------------------------------------------------------------------
# Public API
# ------------------------------------------------------------------

def optimize_molecule(
    smiles: str,
    target_property: str,  # e.g. "logP", "MW", "TPSA", "QED"
    target_value: float,
    max_steps: int = 50,
    population_size: int = 20,
) -> dict:
    """Optimize a single molecule toward a target property using GA.

    Returns the best molecule found and the full optimization trajectory.
    """
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise ValueError(f"Invalid SMILES: {smiles}")

    # Build the single-objective scorer
    _scorer = _build_single_objective_scorer(target_property, target_value)

    # Initialize population
    population = [(mol, _scorer(mol))]
    for _ in range(population_size - 1):
        mutated = _mutate(mol, random.choice(_MUTATION_OPS))
        if mutated:
            population.append((mutated, _scorer(mutated)))

    best = max(population, key=lambda x: x[1])
    trajectory = []

    for step in range(max_steps):
        # Tournament selection (pick best of 3 random individuals)
        tourney_size = min(3, len(population))
        parent = max(random.sample(population, tourney_size), key=lambda x: x[1])[0]
        child = _mutate(parent, random.choice(_MUTATION_OPS))
        if child is None:
            continue
        child_score = _scorer(child)
        population.append((child, child_score))
        if child_score > best[1]:
            best = (child, child_score)
        trajectory.append({
            "step": step,
            "smiles": Chem.MolToSmiles(child),
            "score": child_score,
        })
        # Keep population size fixed (elitist truncation)
        population = sorted(population, key=lambda x: x[1], reverse=True)[:population_size]

    return {
        "original_smiles": smiles,
        "optimized_smiles": Chem.MolToSmiles(best[0]),
        "original_score": _scorer(mol),
        "optimized_score": best[1],
        "trajectory": trajectory,
        "steps": len(trajectory),
        "target_property": target_property,
        "target_value": target_value,
    }


def optimize_lead(
    smiles: str,
    objectives: dict[str, tuple[float, float]],
    max_steps: int = 100,
    population_size: int = 20,
) -> dict:
    """Multi-objective lead optimization.

    *objectives* maps property name -> (target, tolerance).
    e.g.  {"logP": (2.5, 1.0), "MW": (400, 50), "QED": (0.8, 0.2)}
    """
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise ValueError(f"Invalid SMILES: {smiles}")

    # Build objective callables from the (target, tolerance) tuples
    objective_fns: dict[str, Callable[[Chem.Mol], float]] = {}
    for prop, (target, tolerance) in objectives.items():
        if prop == "logP":
            objective_fns[prop] = scorer.logp_objective(target, tolerance)
        elif prop == "MW":
            objective_fns[prop] = scorer.mw_objective(target, tolerance)
        elif prop == "QED":
            objective_fns[prop] = scorer.qed_objective()
        elif prop == "TPSA":
            objective_fns[prop] = scorer.tpsa_objective(target, tolerance)
        elif prop == "synth":
            objective_fns[prop] = scorer.synthesizability_objective()
        else:
            objective_fns[prop] = scorer.mw_objective(target, tolerance)  # fallback

    # Composite scorer = sum of individual objective scores (all [0,1])
    def composite_score(m):
        return sum(fn(m) for fn in objective_fns.values())

    population = [(mol, composite_score(mol))]
    for _ in range(population_size - 1):
        mutated = _mutate(mol, random.choice(_MUTATION_OPS))
        if mutated:
            population.append((mutated, composite_score(mutated)))

    best = max(population, key=lambda x: x[1])
    trajectory = []

    for step in range(max_steps):
        tourney_size = min(3, len(population))
        parent = max(random.sample(population, tourney_size), key=lambda x: x[1])[0]
        child = _mutate(parent, random.choice(_MUTATION_OPS))
        if child is None:
            continue
        child_score = composite_score(child)
        population.append((child, child_score))
        if child_score > best[1]:
            best = (child, child_score)
        trajectory.append({
            "step": step,
            "smiles": Chem.MolToSmiles(child),
            "score": child_score,
            "objective_scores": {name: fn(child) for name, fn in objective_fns.items()},
        })
        population = sorted(population, key=lambda x: x[1], reverse=True)[:population_size]

    return {
        "original_smiles": smiles,
        "optimized_smiles": Chem.MolToSmiles(best[0]),
        "original_score": composite_score(mol),
        "optimized_score": best[1],
        "trajectory": trajectory,
        "steps": len(trajectory),
        "objectives": objectives,
    }


# ------------------------------------------------------------------
# Scoring helpers
# ------------------------------------------------------------------

def _build_single_objective_scorer(target_property: str, target_value: float):
    """Return a scoring function that rewards proximity to *target_value*."""
    if target_property == "logP":
        return lambda m: max(0.0, 1.0 - abs(Descriptors.MolLogP(m) - target_value) / 2.0)
    elif target_property == "MW":
        return lambda m: max(0.0, 1.0 - abs(Descriptors.MolWt(m) - target_value) / 100.0)
    elif target_property == "QED":
        return lambda m: QED.qed(m)
    elif target_property == "TPSA":
        return lambda m: max(0.0, 1.0 - abs(Descriptors.TPSA(m) - target_value) / 40.0)
    else:
        return lambda m: 0.0


# ------------------------------------------------------------------
# Mutation operators
# ------------------------------------------------------------------

_MUTATION_OPS = []


def _mutate(mol, mutation_fn):
    """Apply a mutation, returning None if the result is invalid."""
    try:
        new_mol = mutation_fn(mol)
        if new_mol is None:
            return None
        smi = Chem.MolToSmiles(new_mol)
        # Round-trip validation
        if Chem.MolFromSmiles(smi) is None:
            return None
        return new_mol
    except Exception:
        return None


def _add_atom(mol):
    """Add a terminal atom (C / N / O / S) to an atom with available valence."""
    emol = Chem.EditableMol(mol)
    atoms = list(mol.GetAtoms())
    random.shuffle(atoms)
    for atom in atoms:
        valence = atom.GetTotalValence()
        max_valence = {6: 4, 7: 3, 8: 2, 16: 2, 9: 1, 17: 1, 35: 1, 53: 1}.get(
            atom.GetAtomicNum(), 4
        )
        if valence >= max_valence:
            continue
        # Pick a new atom type (biased toward carbon, but allows heteroatoms)
        new_atomic_num = random.choice([6, 6, 6, 7, 7, 8, 8, 16])
        new_atom = Chem.Atom(new_atomic_num)
        idx = atom.GetIdx()
        new_idx = emol.AddAtom(new_atom)
        emol.AddBond(idx, new_idx, Chem.BondType.SINGLE)
        try:
            new_mol = emol.GetMol()
            Chem.SanitizeMol(new_mol)
            return new_mol
        except Exception:
            continue
    return None


def _remove_atom(mol):
    """Remove a terminal non-H atom (degree == 1)."""
    terminals = [a for a in mol.GetAtoms() if a.GetDegree() == 1 and a.GetAtomicNum() != 1]
    if not terminals:
        return None
    random.shuffle(terminals)
    for atom in terminals:
        emol = Chem.EditableMol(mol)
        emol.RemoveAtom(atom.GetIdx())
        try:
            new_mol = emol.GetMol()
            Chem.SanitizeMol(new_mol)
            return new_mol
        except Exception:
            continue
    return None


def _replace_atom(mol):
    """Replace a carbon with a heteroatom (N / O / S / F / Cl), preserving valence."""
    carbons = [a for a in mol.GetAtoms() if a.GetAtomicNum() == 6]
    if not carbons:
        return None
    random.shuffle(carbons)
    replacements = {7: 3, 8: 2, 16: 2, 9: 1, 17: 1, 35: 1}
    for atom in carbons:
        valence = atom.GetTotalValence()
        for new_atomic_num in random.sample(list(replacements.keys()), len(replacements)):
            if valence <= replacements[new_atomic_num]:
                emol = Chem.EditableMol(mol)
                new_atom = Chem.Atom(new_atomic_num)
                new_atom.SetFormalCharge(atom.GetFormalCharge())
                emol.ReplaceAtom(atom.GetIdx(), new_atom)
                try:
                    new_mol = emol.GetMol()
                    Chem.SanitizeMol(new_mol)
                    return new_mol
                except Exception:
                    continue
    return None


def _add_bond(mol):
    """Increase a single bond to a double bond, or add a ring-closing bond."""
    # 1) Try increasing existing single bond to double
    single_bonds = [b for b in mol.GetBonds() if b.GetBondType() == Chem.BondType.SINGLE]
    random.shuffle(single_bonds)
    for bond in single_bonds:
        a1, a2 = bond.GetBeginAtom(), bond.GetEndAtom()
        if not (_can_increase_valence(a1) and _can_increase_valence(a2)):
            continue
        emol = Chem.EditableMol(mol)
        emol.RemoveBond(a1.GetIdx(), a2.GetIdx())
        emol.AddBond(a1.GetIdx(), a2.GetIdx(), Chem.BondType.DOUBLE)
        try:
            new_mol = emol.GetMol()
            Chem.SanitizeMol(new_mol)
            return new_mol
        except Exception:
            continue

    # 2) Try adding a ring-closing bond between atoms 2-3 bonds apart
    atoms = list(mol.GetAtoms())
    random.shuffle(atoms)
    for a1 in atoms:
        for a2 in atoms:
            if a1.GetIdx() >= a2.GetIdx():
                continue
            if mol.GetBondBetweenAtoms(a1.GetIdx(), a2.GetIdx()):
                continue
            # shortest path distance (in bonds)
            try:
                path = Chem.GetShortestPath(mol, a1.GetIdx(), a2.GetIdx())
            except Exception:
                continue
            if path is None or len(path) < 3 or len(path) > 5:
                continue
            if not (_can_increase_valence(a1) and _can_increase_valence(a2)):
                continue
            emol = Chem.EditableMol(mol)
            emol.AddBond(a1.GetIdx(), a2.GetIdx(), Chem.BondType.SINGLE)
            try:
                new_mol = emol.GetMol()
                Chem.SanitizeMol(new_mol)
                return new_mol
            except Exception:
                continue
    return None


def _remove_bond(mol):
    """Decrease a double bond to single, or remove a non-critical single bond."""
    # 1) Decrease double bond
    double_bonds = [b for b in mol.GetBonds() if b.GetBondType() == Chem.BondType.DOUBLE]
    random.shuffle(double_bonds)
    for bond in double_bonds:
        a1, a2 = bond.GetBeginAtom(), bond.GetEndAtom()
        emol = Chem.EditableMol(mol)
        emol.RemoveBond(a1.GetIdx(), a2.GetIdx())
        emol.AddBond(a1.GetIdx(), a2.GetIdx(), Chem.BondType.SINGLE)
        try:
            new_mol = emol.GetMol()
            Chem.SanitizeMol(new_mol)
            return new_mol
        except Exception:
            continue

    # 2) Remove a single bond that doesn't disconnect the molecule
    single_bonds = [b for b in mol.GetBonds() if b.GetBondType() == Chem.BondType.SINGLE]
    random.shuffle(single_bonds)
    for bond in single_bonds:
        a1, a2 = bond.GetBeginAtom(), bond.GetEndAtom()
        if a1.GetDegree() <= 1 or a2.GetDegree() <= 1:
            continue
        emol = Chem.EditableMol(mol)
        emol.RemoveBond(a1.GetIdx(), a2.GetIdx())
        try:
            new_mol = emol.GetMol()
            # Ensure molecule remains in one connected component
            frags = Chem.GetMolFrags(new_mol, asMols=False, sanitizeFrags=False)
            if len(frags) == 1:
                Chem.SanitizeMol(new_mol)
                return new_mol
        except Exception:
            continue
    return None


def _can_increase_valence(atom) -> bool:
    """Return True if the atom can support one more bond."""
    valence = atom.GetTotalValence()
    max_valence = {6: 4, 7: 3, 8: 2, 16: 2, 9: 1, 17: 1, 35: 1, 53: 1}.get(
        atom.GetAtomicNum(), 4
    )
    return valence < max_valence


# Populate the global mutation operator list
_MUTATION_OPS = [_add_atom, _remove_atom, _replace_atom, _add_bond, _remove_bond]
