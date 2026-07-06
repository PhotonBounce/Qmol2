"""
LinkedIn Outreach Targets for Q-Mol
Pre-loaded list of high-value prospects in molecular science, pharma, and biotech.
"""
from typing import List, Dict

# Target segments for Q-Mol molecular datasets
TARGETS: List[Dict] = [
    # ─── Researchers / Academics ─────────────────────────────────────────────
    {
        "name": "Dr. Sarah Chen",
        "linkedin_url": "https://www.linkedin.com/in/sarah-chen-computational-chemistry/",
        "target_type": "researcher",
        "topic": "computational chemistry",
        "company": "MIT",
        "priority": 1,
    },
    {
        "name": "Prof. James Miller",
        "linkedin_url": "https://www.linkedin.com/in/james-miller-drug-discovery/",
        "target_type": "researcher",
        "topic": "virtual screening",
        "company": "Stanford",
        "priority": 1,
    },
    {
        "name": "Dr. Anna Kowalski",
        "linkedin_url": "https://www.linkedin.com/in/anna-kowalski-molecular-modeling/",
        "target_type": "researcher",
        "topic": "molecular dynamics",
        "company": "University of Cambridge",
        "priority": 2,
    },
    {
        "name": "Dr. Raj Patel",
        "linkedin_url": "https://www.linkedin.com/in/raj-patel-chemoinformatics/",
        "target_type": "researcher",
        "topic": "chemoinformatics",
        "company": "UC San Diego",
        "priority": 1,
    },
    {
        "name": "Dr. Maria Gonzalez",
        "linkedin_url": "https://www.linkedin.com/in/maria-gonzalez-medicinal-chemistry/",
        "target_type": "researcher",
        "topic": "medicinal chemistry",
        "company": "ETH Zurich",
        "priority": 2,
    },
    # ─── Pharma / Drug Discovery ─────────────────────────────────────────────
    {
        "name": "Michael Roberts",
        "linkedin_url": "https://www.linkedin.com/in/michael-roberts-pfizer/",
        "target_type": "pharma",
        "topic": "lead optimization",
        "company": "Pfizer",
        "priority": 1,
    },
    {
        "name": "Lisa Thompson",
        "linkedin_url": "https://www.linkedin.com/in/lisa-thompson-novartis/",
        "target_type": "pharma",
        "topic": "early drug discovery",
        "company": "Novartis",
        "priority": 1,
    },
    {
        "name": "David Kim",
        "linkedin_url": "https://www.linkedin.com/in/david-kim-roche/",
        "target_type": "pharma",
        "topic": "molecular design",
        "company": "Roche",
        "priority": 2,
    },
    {
        "name": "Emily Watson",
        "linkedin_url": "https://www.linkedin.com/in/emily-watson-astrazeneca/",
        "target_type": "pharma",
        "topic": "AI drug discovery",
        "company": "AstraZeneca",
        "priority": 1,
    },
    {
        "name": "Robert Johnson",
        "linkedin_url": "https://www.linkedin.com/in/robert-johnson-merck/",
        "target_type": "pharma",
        "topic": "high-throughput screening",
        "company": "Merck",
        "priority": 2,
    },
    # ─── Biotech / AI Drug Discovery Startups ────────────────────────────────
    {
        "name": "Alexandra Lee",
        "linkedin_url": "https://www.linkedin.com/in/alexandra-lee-recursion/",
        "target_type": "biotech",
        "topic": "AI-powered drug discovery",
        "company": "Recursion Pharmaceuticals",
        "priority": 1,
    },
    {
        "name": "Thomas Wright",
        "linkedin_url": "https://www.linkedin.com/in/thomas-wright-atomwise/",
        "target_type": "biotech",
        "topic": "deep learning for molecules",
        "company": "Atomwise",
        "priority": 1,
    },
    {
        "name": "Sophie Martin",
        "linkedin_url": "https://www.linkedin.com/in/sophie-martin-schrodinger/",
        "target_type": "biotech",
        "topic": "computational molecular design",
        "company": "Schrödinger",
        "priority": 1,
    },
    {
        "name": "Daniel Park",
        "linkedin_url": "https://www.linkedin.com/in/daniel-park-exscientia/",
        "target_type": "biotech",
        "topic": "generative chemistry",
        "company": "Exscientia",
        "priority": 2,
    },
    {
        "name": "Olivia Brown",
        "linkedin_url": "https://www.linkedin.com/in/olivia-brown-insitro/",
        "target_type": "biotech",
        "topic": "machine learning for biology",
        "company": "insitro",
        "priority": 2,
    },
    # ─── CRO / Data Providers ────────────────────────────────────────────────
    {
        "name": "Christopher Davis",
        "linkedin_url": "https://www.linkedin.com/in/christopher-davis-chemdiv/",
        "target_type": "pharma",
        "topic": "compound libraries",
        "company": "ChemDiv",
        "priority": 2,
    },
    {
        "name": "Natalie Wilson",
        "linkedin_url": "https://www.linkedin.com/in/natalie-wilson-enamine/",
        "target_type": "pharma",
        "topic": "virtual screening libraries",
        "company": "Enamine",
        "priority": 2,
    },
    # ─── AI/ML in Chemistry ──────────────────────────────────────────────────
    {
        "name": "Kevin Zhang",
        "linkedin_url": "https://www.linkedin.com/in/kevin-zhang-deepchem/",
        "target_type": "researcher",
        "topic": "deep learning for chemistry",
        "company": "DeepChem",
        "priority": 1,
    },
    {
        "name": "Rachel Green",
        "linkedin_url": "https://www.linkedin.com/in/rachel-green-molecular-ai/",
        "target_type": "researcher",
        "topic": "generative models for molecules",
        "company": "Mila",
        "priority": 1,
    },
    {
        "name": "Andrew Scott",
        "linkedin_url": "https://www.linkedin.com/in/andrew-scott-microsoft-research/",
        "target_type": "researcher",
        "topic": "AI for scientific discovery",
        "company": "Microsoft Research",
        "priority": 2,
    },
]


def get_targets_by_priority(min_priority: int = 1) -> List[Dict]:
    """Get targets filtered by priority level."""
    return [t for t in TARGETS if t.get("priority", 99) <= min_priority]


def get_targets_by_type(target_type: str) -> List[Dict]:
    """Get targets by segment type."""
    return [t for t in TARGETS if t["target_type"] == target_type]
