"""pKa prediction using empirical SMARTS-based methods.

Based on the ChemAxon pKa plugin approach: identify ionizable groups,
apply empirical pKa values, adjust for structural context.
"""
from __future__ import annotations

from rdkit import Chem

# Known pKa values for functional groups (mean, std)
PKA_TABLE = {
    "carboxylic_acid": (4.0, 1.0),
    "phenol": (9.5, 1.0),
    "aliphatic_amine": (10.0, 1.5),
    "aniline": (4.5, 1.0),
    "sulfonamide": (10.0, 1.0),
    "tetrazole": (4.5, 0.5),
    "guanidine": (12.5, 0.5),
    "amide": (15.0, 1.0),
    "alcohol": (15.0, 2.0),
    "thiol": (10.0, 1.0),
}

SMARTS_PATTERNS = {
    "carboxylic_acid": "[CX3](=O)[OX2H1]",
    "phenol": "c[OX2H1]",
    "aliphatic_amine": "[NX3;H2,H1;!$(NC=O)]",
    "aniline": "c[NX3;H2,H1]",
    "sulfonamide": "[SX4](=[OX1])(=[OX1])[NX3]",
    "tetrazole": "c1nnn[nH]1",
    "guanidine": "[NX3]=C(N)N",
    "thiol": "[SX2H1]",
}


def predict_pka(smiles: str) -> dict:
    """Predict pKa values for ionizable groups in a molecule."""
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return {"error": "Invalid SMILES", "smiles": smiles}

    ionizable_groups = []
    for group_name, smarts in SMARTS_PATTERNS.items():
        pattern = Chem.MolFromSmarts(smarts)
        if pattern:
            matches = mol.GetSubstructMatches(pattern)
            for match in matches:
                pka_mean, pka_std = PKA_TABLE.get(group_name, (7.0, 2.0))
                ionizable_groups.append({
                    "group": group_name,
                    "atom_index": int(match[0]),
                    "pKa": round(pka_mean, 1),
                    "pKa_range": f"{pka_mean - pka_std:.1f} - {pka_mean + pka_std:.1f}",
                    "type": "acidic" if pka_mean < 7.0 else "basic",
                })

    # Sort by pKa
    ionizable_groups.sort(key=lambda x: x["pKa"])

    # Calculate ionization state at pH 7.4
    for group in ionizable_groups:
        ph = 7.4
        pka = group["pKa"]
        if group["type"] == "acidic":
            fraction_ionized = 1 / (1 + 10 ** (pka - ph))
        else:
            fraction_ionized = 1 / (1 + 10 ** (ph - pka))
        group["fraction_ionized_at_ph_7.4"] = round(fraction_ionized, 3)

    acidic = [g for g in ionizable_groups if g["type"] == "acidic"]
    basic = [g for g in ionizable_groups if g["type"] == "basic"]

    return {
        "smiles": smiles,
        "ionizable_groups": ionizable_groups,
        "n_ionizable": len(ionizable_groups),
        "strongest_acid_pKa": min((g["pKa"] for g in acidic), default=None),
        "strongest_base_pKa": max((g["pKa"] for g in basic), default=None),
    }
