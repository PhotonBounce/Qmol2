"""Pre-defined drug target database for DTI prediction."""
TARGETS = {
    " EGFR": {"name": "Epidermal Growth Factor Receptor", "uniprot": "P00533", "family": "Kinase", "disease_areas": ["cancer", "inflammation"]},
    "HER2": {"name": "Human Epidermal Growth Factor Receptor 2", "uniprot": "P04626", "family": "Kinase", "disease_areas": ["cancer"]},
    "AChE": {"name": "Acetylcholinesterase", "uniprot": "P22303", "family": "Hydrolase", "disease_areas": ["Alzheimer", "myasthenia_gravis"]},
    "COX2": {"name": "Cyclooxygenase-2", "uniprot": "P35354", "family": "Oxidoreductase", "disease_areas": ["inflammation", "pain"]},
    "5HT2A": {"name": "5-Hydroxytryptamine Receptor 2A", "uniprot": "P28223", "family": "GPCR", "disease_areas": ["psychiatric", "CNS"]},
    "D2": {"name": "Dopamine Receptor D2", "uniprot": "P14416", "family": "GPCR", "disease_areas": ["psychiatric", "Parkinson"]},
    "BACE1": {"name": "Beta-Secretase 1", "uniprot": "P56817", "family": "Protease", "disease_areas": ["Alzheimer"]},
    "PI3K": {"name": "Phosphatidylinositol-4,5-bisphosphate 3-kinase", "uniprot": "P42336", "family": "Kinase", "disease_areas": ["cancer", "inflammation"]},
    "mTOR": {"name": "Mechanistic Target of Rapamycin", "uniprot": "P42345", "family": "Kinase", "disease_areas": ["cancer", "autoimmune"]},
    "JAK2": {"name": "Janus Kinase 2", "uniprot": "O60674", "family": "Kinase", "disease_areas": ["cancer", "inflammation", "myeloproliferative"]},
}


def list_targets():
    """Return all available targets as a list with their IDs."""
    return [{"id": k, **v} for k, v in TARGETS.items()]


def get_target_info(target_id: str):
    """Return information for a single target by ID."""
    return TARGETS.get(target_id)
