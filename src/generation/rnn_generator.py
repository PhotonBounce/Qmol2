"""Lightweight de novo molecular generation using character-level Markov model.

This is a simplified implementation that works without pre-trained neural models.
For production, replace with Chemprop, REINVENT, or NVIDIA GenMol models.
"""
from __future__ import annotations

import random
from collections import defaultdict

from rdkit import Chem
from rdkit.Chem import Descriptors, rdMolDescriptors

# Drug-like filters aligned with Lipinski / Veber / Pfizer 3/75 rule
_MIN_MW = 150.0
_MAX_MW = 600.0
_MIN_LOGP = -2.0
_MAX_LOGP = 6.0
_MAX_HBD = 5
_MAX_HBA = 10
_MAX_TPSA = 140.0


class RNNGenerator:
    """Simple character-level generator that learns from a seed set of SMILES.

    Uses an n-gram Markov model over SMILES characters.  This is fast,
    dependency-free, and surprisingly effective for scaffold-hopping when
    seeded with a diverse library.
    """

    def __init__(self, order: int = 3):
        self.order = order
        self.model: dict[str, list[str]] = defaultdict(list)

    # ------------------------------------------------------------------
    # Training
    # ------------------------------------------------------------------
    def train(self, smiles_list: list[str]) -> None:
        """Train the Markov model on a list of SMILES strings."""
        for smi in smiles_list:
            smi = smi.strip()
            if not smi:
                continue
            padded = "~" * self.order + smi + "~"
            for i in range(len(padded) - self.order):
                context = padded[i : i + self.order]
                next_char = padded[i + self.order]
                self.model[context].append(next_char)

    # ------------------------------------------------------------------
    # Generation
    # ------------------------------------------------------------------
    def generate(self, n: int = 100, max_len: int = 100) -> list[str]:
        """Generate *n* novel SMILES strings."""
        results: list[str] = []
        attempts = 0
        max_attempts = n * 20
        while len(results) < n and attempts < max_attempts:
            attempts += 1
            context = "~" * self.order
            generated = ""
            for _ in range(max_len):
                if context not in self.model:
                    break
                next_char = random.choice(self.model[context])
                if next_char == "~":
                    break
                generated += next_char
                context = context[1:] + next_char
            if generated and self._is_valid(generated):
                # Deduplicate within this batch
                if generated not in results:
                    results.append(generated)
        return results

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------
    def _is_valid(self, smiles: str) -> bool:
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return False

        # Drug-like filters (Lipinski + Veber + logP)
        mw = Descriptors.MolWt(mol)
        if mw < _MIN_MW or mw > _MAX_MW:
            return False

        logp = Descriptors.MolLogP(mol)
        if logp < _MIN_LOGP or logp > _MAX_LOGP:
            return False

        hbd = Descriptors.NumHDonors(mol)
        if hbd > _MAX_HBD:
            return False

        hba = Descriptors.NumHAcceptors(mol)
        if hba > _MAX_HBA:
            return False

        tpsa = Descriptors.TPSA(mol)
        if tpsa > _MAX_TPSA:
            return False

        # Reject too many rings (not all polycyclic systems are drug-like)
        if rdMolDescriptors.CalcNumRings(mol) > 5:
            return False

        return True


# ------------------------------------------------------------------
# Convenience
# ------------------------------------------------------------------
def sample_smiles(seed_smiles: list[str], n: int = 100) -> list[str]:
    """Train on *seed_smiles* and generate *n* novel molecules."""
    gen = RNNGenerator(order=3)
    gen.train(seed_smiles)
    return gen.generate(n=n)
