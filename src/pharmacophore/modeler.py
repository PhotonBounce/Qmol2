"""Pharmacophore modeling and 2D/3D feature extraction."""
from __future__ import annotations
from typing import Any

from rdkit import Chem
from rdkit.Chem import AllChem, ChemicalFeatures
from rdkit.Chem.Pharm2D import SigFactory, Generate
from rdkit import RDConfig
import os


def _get_factory() -> ChemicalFeatures.MolChemicalFeatureFactory | None:
    """Load the default RDKit feature factory."""
    try:
        fdef_path = os.path.join(RDConfig.RDDataDir, "BaseFeatures.fdef")
        if os.path.exists(fdef_path):
            return ChemicalFeatures.BuildFeatureFactory(fdef_path)
    except Exception:
        pass
    return None


def generate_pharmacophore(smiles: str) -> dict[str, Any]:
    """Generate 2D pharmacophore fingerprint and feature list from a molecule."""
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return {"error": "Invalid SMILES", "smiles": smiles}

    factory = _get_factory()
    features = []
    if factory:
        feats = factory.GetFeaturesForMol(mol)
        for f in feats:
            features.append({
                "family": f.GetFamily(),
                "type": f.GetType(),
                "atom_ids": list(f.GetAtomIds()),
            })
    else:
        # Fallback: heuristic feature detection
        from rdkit.Chem import Lipinski, rdMolDescriptors
        donors = Lipinski.NumHDonors(mol)
        acceptors = Lipinski.NumHAcceptors(mol)
        rings = rdMolDescriptors.CalcNumRings(mol)
        aromatic = rdMolDescriptors.CalcNumAromaticRings(mol)
        if donors > 0:
            features.append({"family": "Donor", "type": "HBondDonor", "atom_ids": []})
        if acceptors > 0:
            features.append({"family": "Acceptor", "type": "HBondAcceptor", "atom_ids": []})
        if aromatic > 0:
            features.append({"family": "Aromatic", "type": "Aromatic", "atom_ids": []})
        if rings > aromatic:
            features.append({"family": "Hydrophobe", "type": "Hydrophobe", "atom_ids": []})

    # 2D pharmacophore fingerprint
    fp = None
    try:
        if factory:
            sig_factory = SigFactory(factory, minPointCount=2, maxPointCount=3, trianglePruneBins=False)
            sig_factory.SetBins([(0, 2), (2, 5), (5, 8)])
            sig_factory.Init()
            fp = Generate.Gen2DFingerprint(mol, sig_factory).ToBitString()
    except Exception:
        fp = None

    return {
        "smiles": smiles,
        "features": features,
        "n_features": len(features),
        "pharmacophore_fp": fp,
    }


def smiles_to_pharmacophore_3d(smiles: str) -> dict[str, Any]:
    """Generate 3D pharmacophore features with coordinates."""
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return {"error": "Invalid SMILES", "smiles": smiles}

    mol = Chem.AddHs(mol)
    AllChem.EmbedMolecule(mol, AllChem.ETKDG())
    AllChem.MMFFOptimizeMolecule(mol)

    factory = _get_factory()
    features_3d = []
    if factory:
        feats = factory.GetFeaturesForMol(mol)
        for f in feats:
            atom_ids = list(f.GetAtomIds())
            if atom_ids:
                conf = mol.GetConformer()
                xs = [conf.GetAtomPosition(aid).x for aid in atom_ids]
                ys = [conf.GetAtomPosition(aid).y for aid in atom_ids]
                zs = [conf.GetAtomPosition(aid).z for aid in atom_ids]
                cx, cy, cz = sum(xs) / len(xs), sum(ys) / len(ys), sum(zs) / len(zs)
                features_3d.append({
                    "family": f.GetFamily(),
                    "type": f.GetType(),
                    "center": [round(cx, 3), round(cy, 3), round(cz, 3)],
                    "atom_ids": atom_ids,
                })

    return {
        "smiles": smiles,
        "features_3d": features_3d,
        "n_features_3d": len(features_3d),
    }
