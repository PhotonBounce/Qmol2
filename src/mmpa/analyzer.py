"""Matched Molecular Pair Analysis (MMPA) for SAR.

Uses RDKit's rdMMPA to find matched molecular pairs and report
transformations with associated property changes.
"""
from __future__ import annotations
from typing import Any

from rdkit import Chem
from rdkit.Chem import rdMMPA


def analyze_mmp(smiles_list: list[str]) -> list[dict[str, Any]]:
    """Find matched molecular pairs in a dataset.
    
    Returns a list of transformation records with left/right contexts
    and the property delta (if any).
    """
    mols = []
    for s in smiles_list:
        mol = Chem.MolFromSmiles(s)
        if mol:
            mols.append(mol)

    if len(mols) < 2:
        return []

    # Build MMPA index using RDKit
    # rdMMPA.MMPA returns pairs as (mol1_idx, mol2_idx, core_smiles, frag1, frag2)
    pairs = []
    try:
        # Generate MMPA pairs from a list of molecules
        # We use a simplified approach: generate all pairs and filter
        from rdkit.Chem import rdMMPA
        mmpa = rdMMPA.MMPA()
        for mol in mols:
            mmpa.AddMol(mol)
        
        raw_pairs = mmpa.GetPairs()
        for pair in raw_pairs:
            idx1, idx2, core, frag1, frag2 = pair
            mol1 = mols[idx1]
            mol2 = mols[idx2]
            pairs.append({
                "smiles_1": Chem.MolToSmiles(mol1),
                "smiles_2": Chem.MolToSmiles(mol2),
                "core": core,
                "fragment_1": frag1,
                "fragment_2": frag2,
                "transformation": f"{frag1} >> {frag2}",
                "size_1": mol1.GetNumHeavyAtoms(),
                "size_2": mol2.GetNumHeavyAtoms(),
                "delta_size": mol2.GetNumHeavyAtoms() - mol1.GetNumHeavyAtoms(),
            })
    except Exception:
        # Fallback: brute-force MMPA for small datasets
        pairs = _brute_force_mmpa(mols)

    return pairs


def _brute_force_mmpa(mols: list) -> list[dict[str, Any]]:
    """Fallback brute-force MMPA for small datasets."""
    pairs = []
    for i in range(len(mols)):
        for j in range(i + 1, len(mols)):
            mol1, mol2 = mols[i], mols[j]
            # Try to find a common core by MCS
            from rdkit.Chem import rdFMCS
            mcs = rdFMCS.FindMCS([mol1, mol2])
            if mcs.numAtoms < 1:
                continue
            core = Chem.MolFromSmarts(mcs.smartsString)
            if core is None:
                continue
            # Report pair with MCS info
            pairs.append({
                "smiles_1": Chem.MolToSmiles(mol1),
                "smiles_2": Chem.MolToSmiles(mol2),
                "core": mcs.smartsString,
                "fragment_1": "",
                "fragment_2": "",
                "transformation": "MCS-based pair",
                "size_1": mol1.GetNumHeavyAtoms(),
                "size_2": mol2.GetNumHeavyAtoms(),
                "delta_size": mol2.GetNumHeavyAtoms() - mol1.GetNumHeavyAtoms(),
            })
    return pairs
