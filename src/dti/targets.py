"""Pre-defined drug target database for DTI prediction."""
TARGETS = {
    "EGFR": {"name": "Epidermal Growth Factor Receptor", "uniprot": "P00533", "family": "Kinase", "disease_areas": ["cancer", "inflammation"]},
    "AChE": {"name": "Acetylcholinesterase", "uniprot": "P22303", "family": "Hydrolase", "disease_areas": ["Alzheimer", "myasthenia_gravis"]},
    "BACE1": {"name": "Beta-Secretase 1", "uniprot": "P56817", "family": "Protease", "disease_areas": ["Alzheimer"]},
}

VALIDATED_TARGETS = set(TARGETS.keys())


def list_targets():
    """Return all available targets as a list with their IDs."""
    return [{"id": k, **v} for k, v in TARGETS.items()]


def get_target_info(target_id: str):
    """Return information for a single target by ID."""
    return TARGETS.get(target_id)


def validate_target(target_id: str) -> bool:
    """Check if a target is in the validated set."""
    return target_id in VALIDATED_TARGETS
