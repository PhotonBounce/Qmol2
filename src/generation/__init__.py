"""De novo molecular generation engine for Q-Mol.

Lightweight, RDKit-only implementations of:
- Character-level Markov/RNN SMILES generation
- Genetic-algorithm molecular optimization
- Multi-objective scoring (activity, solubility, synthesizability, etc.)
"""
from __future__ import annotations

from .rnn_generator import RNNGenerator, sample_smiles
from .optimizer import optimize_molecule, optimize_lead
from .scorer import multi_objective_score

__all__ = [
    "RNNGenerator",
    "sample_smiles",
    "optimize_molecule",
    "optimize_lead",
    "multi_objective_score",
]
