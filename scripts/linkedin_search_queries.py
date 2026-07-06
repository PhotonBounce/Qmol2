#!/usr/bin/env python3
"""
Q-Mol LinkedIn Search Query Definitions
========================================
Curated search queries targeting prospects in the molecular data / drug
discovery space. These are used by the prospect extractor.

Categories:
    - PRIMARY: Directly relevant to Q-Mol's core offering
    - SECONDARY: Adjacent fields with high conversion potential
    - NICHE: Specialized roles and emerging areas

Usage:
    from linkedin_search_queries import get_search_batches
    batches = get_search_batches()
"""

from typing import List, Dict


# ---------------------------------------------------------------------------
# Search Query Definitions
# ---------------------------------------------------------------------------

PRIMARY_KEYWORDS = [
    # Core cheminformatics
    ["cheminformatics", "drug discovery"],
    ["computational chemistry", "virtual screening"],
    ["molecular modeling", "medicinal chemistry"],
    ["ADMET", "QSAR", "pharmaceutical"],
    ["docking", "molecular dynamics"],
    ["compound library", "screening", "ML"],
    ["RDKit", "Python", "drug design"],
    ["AI drug discovery", "machine learning", "molecules"],
    ["CADD", "computer aided drug design"],
    ["hit identification", "lead optimization"],
    ["pharmacophore", "SAR"],
    ["high throughput screening", "HTS"],
    ["in silico", "drug design"],
    ["molecular descriptors", "ADMET prediction"],
]

SECONDARY_KEYWORDS = [
    # Adjacent but high value
    ["bioinformatics", "target identification"],
    ["structural biology", "protein structure"],
    ["crystallography", "drug design"],
    ["NMR", "fragment based drug design"],
    ["peptide design", "therapeutics"],
    ["antibody design", "computational biology"],
    ["toxicology", "safety assessment"],
    ["DMPK", "drug metabolism"],
    ["formulation", "drug delivery"],
    ["patent analytics", "pharma intelligence"],
]

NICHE_KEYWORDS = [
    # Emerging and specialized
    ["generative chemistry", "de novo design"],
    ["deep learning", "molecular property prediction"],
    ["reinforcement learning", "molecule generation"],
    ["variational autoencoder", "chemical space"],
    ["graph neural network", "molecules"],
    ["transformer", "chemistry"],
    ["large language model", "chemistry"],
    ["quantum computing", "drug discovery"],
    ["federated learning", "pharma"],
    ["digital twin", "pharmaceutical"],
]

# Job titles to combine with keywords for precision targeting
TARGET_TITLES = [
    "Scientist",
    "Senior Scientist", 
    "Principal Scientist",
    "Director",
    "Founder",
    "CTO",
    "CEO",
    "Head of Chemistry",
    "Cheminformatician",
    "Computational Chemist",
    "Medicinal Chemist",
    "Data Scientist",
    "ML Engineer",
    "Research Scientist",
    "Group Leader",
    "VP Research",
    "Chief Scientific Officer",
    "Research Fellow",
    "Postdoctoral",
    "Professor",
]

# Geographic targets (LinkedIn geo URNs)
GEO_TARGETS = [
    {"name": "United States", "urn": "urn:li:geo:103644278", 
     "cities": ["Boston", "San Francisco", "San Diego", "New York", "New Jersey", "Seattle", "Cambridge"]},
    {"name": "United Kingdom", "urn": "urn:li:geo:101165590",
     "cities": ["Cambridge", "London", "Oxford", "Manchester"]},
    {"name": "Germany", "urn": "urn:li:geo:101282230",
     "cities": ["Munich", "Heidelberg", "Berlin", "Frankfurt"]},
    {"name": "Switzerland", "urn": "urn:li:geo:106693272",
     "cities": ["Basel", "Zurich", "Geneva"]},
    {"name": "Canada", "urn": "urn:li:geo:101174741",
     "cities": ["Toronto", "Vancouver", "Montreal"]},
    {"name": "Netherlands", "urn": "urn:li:geo:102890719",
     "cities": ["Amsterdam", "Rotterdam"]},
    {"name": "France", "urn": "urn:li:geo:105015875",
     "cities": ["Paris", "Lyon"]},
    {"name": "Israel", "urn": "urn:li:geo:101620260",
     "cities": ["Tel Aviv", "Jerusalem"]},
    {"name": "India", "urn": "urn:li:geo:102713980",
     "cities": ["Bangalore", "Hyderabad", "Mumbai", "Delhi"]},
]

# Company size codes for LinkedIn (B=1-10, C=11-50, D=51-200, E=201-500, F=501-1000, G=1001-5000, H=5001-10000, I=10001+)
COMPANY_SIZES = {
    "startup": "B,C",      # 1-50 employees (most likely early adopters)
    "small": "C,D",        # 11-200 employees
    "mid": "D,E",          # 51-500 employees
    "large": "E,F,G,H,I",  # 201+
}

# High-value company names (known buyers of molecular data)
HIGH_VALUE_COMPANIES = [
    "Schrödinger", "Atomwise", "Recursion", "Relay Therapeutics",
    "BenevolentAI", "Exscientia", "Insitro", "Isomorphic Labs",
    "DeepMind", "Valo Health", "Insilico Medicine", "Lantern Pharma",
    "Cyclica", "Iktos", "Entos", "Terray Therapeutics",
    "WuXi AppTec", "Evotec", "Charles River", "Syngene",
    "Sai Life Sciences", "Pharmaron", "ChemPartner",
    "Genentech", "Roche", "Novartis", "Pfizer", "Merck",
    "AstraZeneca", "GSK", "Sanofi", "Bayer", "Boehringer",
    "Takeda", "Eli Lilly", "Johnson & Johnson", "Biogen",
    "Flagship Pioneering", "Third Rock Ventures", "a16z bio",
    "GV", "Bessemer Venture Partners", "Lux Capital",
]


# ---------------------------------------------------------------------------
# Batch Configuration
# ---------------------------------------------------------------------------

def get_search_batches() -> List[Dict]:
    """
    Returns a list of search batch configurations.
    Each batch is designed to run in a single session.
    
    Batching strategy:
        - Batch 1: Primary keywords + US/UK (highest value)
        - Batch 2: Primary keywords + EU (Germany, Switzerland)
        - Batch 3: Secondary keywords + US/UK
        - Batch 4: Niche/AI keywords + all geos
        - Batch 5: Title-targeted searches
    """
    batches = []
    
    # Batch 1: Primary, US + UK
    batch1_queries = []
    for kw in PRIMARY_KEYWORDS[:7]:
        for geo in GEO_TARGETS[:2]:  # US, UK
            batch1_queries.append({
                "keywords": kw,
                "geo_urn": geo["urn"],
                "geo_name": geo["name"],
                "label": f"{' '.join(kw)} | {geo['name']}"
            })
    batches.append({
        "name": "Primary_US_UK",
        "priority": 1,
        "queries": batch1_queries,
        "description": "Core cheminformatics searches in US and UK"
    })
    
    # Batch 2: Primary, EU
    batch2_queries = []
    for kw in PRIMARY_KEYWORDS[:7]:
        for geo in GEO_TARGETS[2:5]:  # Germany, Switzerland, Canada
            batch2_queries.append({
                "keywords": kw,
                "geo_urn": geo["urn"],
                "geo_name": geo["name"],
                "label": f"{' '.join(kw)} | {geo['name']}"
            })
    batches.append({
        "name": "Primary_EU",
        "priority": 2,
        "queries": batch2_queries,
        "description": "Core cheminformatics searches in EU"
    })
    
    # Batch 3: Secondary, US/UK
    batch3_queries = []
    for kw in SECONDARY_KEYWORDS[:5]:
        for geo in GEO_TARGETS[:2]:
            batch3_queries.append({
                "keywords": kw,
                "geo_urn": geo["urn"],
                "geo_name": geo["name"],
                "label": f"{' '.join(kw)} | {geo['name']}"
            })
    batches.append({
        "name": "Secondary_US_UK",
        "priority": 3,
        "queries": batch3_queries,
        "description": "Adjacent fields in US and UK"
    })
    
    # Batch 4: Niche/AI, all geos
    batch4_queries = []
    for kw in NICHE_KEYWORDS[:5]:
        for geo in GEO_TARGETS[:5]:
            batch4_queries.append({
                "keywords": kw,
                "geo_urn": geo["urn"],
                "geo_name": geo["name"],
                "label": f"{' '.join(kw)} | {geo['name']}"
            })
    batches.append({
        "name": "Niche_AI_All",
        "priority": 4,
        "queries": batch4_queries,
        "description": "AI/ML drug discovery across all target geos"
    })
    
    # Batch 5: Title-targeted (high precision, lower volume)
    batch5_queries = []
    key_titles = ["Head of Chemistry", "Cheminformatician", "Computational Chemist", 
                  "Director Drug Discovery", "VP Chemistry", "CADD"]
    for title in key_titles:
        for geo in GEO_TARGETS[:3]:  # US, UK, Germany
            batch5_queries.append({
                "keywords": [title],
                "geo_urn": geo["urn"],
                "geo_name": geo["name"],
                "label": f"{title} | {geo['name']}"
            })
    batches.append({
        "name": "Title_Targeted",
        "priority": 5,
        "queries": batch5_queries,
        "description": "Title-specific searches for senior roles"
    })
    
    return batches


def get_quick_searches() -> List[Dict]:
    """Returns a small set of high-yield searches for quick testing."""
    return [
        {
            "keywords": ["cheminformatics", "drug discovery"],
            "geo_urn": GEO_TARGETS[0]["urn"],
            "geo_name": GEO_TARGETS[0]["name"],
            "label": "cheminformatics drug discovery | US"
        },
        {
            "keywords": ["computational chemistry", "virtual screening"],
            "geo_urn": GEO_TARGETS[1]["urn"],
            "geo_name": GEO_TARGETS[1]["name"],
            "label": "computational chemistry virtual screening | UK"
        },
        {
            "keywords": ["AI drug discovery", "machine learning"],
            "geo_urn": GEO_TARGETS[0]["urn"],
            "geo_name": GEO_TARGETS[0]["name"],
            "label": "AI drug discovery ML | US"
        },
    ]


def get_company_search_urls() -> List[str]:
    """
    Returns LinkedIn company page URLs for high-value targets.
    Useful for manual prospecting from company employee lists.
    """
    base = "https://www.linkedin.com/company/{}/people/"
    company_slugs = [
        "schrödinger", "atomwiseinc", "recursion-pharma", "relay-therapeutics",
        "benevolentai", "exscientia", "insitro", "isomorphic-labs",
        "insilico-medicine", "terray-therapeutics",
        "wuxi-apptec", "evotec", "charles-river-laboratories",
        "genentech", "roche", "novartis", "pfizer", "astrazeneca",
    ]
    return [base.format(slug) for slug in company_slugs]


# ---------------------------------------------------------------------------
# Export for CLI use
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import json
    
    print("# Q-Mol LinkedIn Search Query Definitions")
    print(f"\n## Primary Keywords ({len(PRIMARY_KEYWORDS)} sets)")
    for i, kw in enumerate(PRIMARY_KEYWORDS, 1):
        print(f"  {i}. {' '.join(kw)}")
    
    print(f"\n## Secondary Keywords ({len(SECONDARY_KEYWORDS)} sets)")
    for i, kw in enumerate(SECONDARY_KEYWORDS, 1):
        print(f"  {i}. {' '.join(kw)}")
    
    print(f"\n## Niche Keywords ({len(NICHE_KEYWORDS)} sets)")
    for i, kw in enumerate(NICHE_KEYWORDS, 1):
        print(f"  {i}. {' '.join(kw)}")
    
    print(f"\n## Geographic Targets ({len(GEO_TARGETS)} regions)")
    for geo in GEO_TARGETS:
        print(f"  - {geo['name']}: {geo['urn']}")
    
    print(f"\n## Search Batches ({len(get_search_batches())} batches)")
    for batch in get_search_batches():
        print(f"  - {batch['name']}: {len(batch['queries'])} queries (P{batch['priority']})")
    
    print(f"\n## High-Value Companies ({len(HIGH_VALUE_COMPANIES)})")
    for company in HIGH_VALUE_COMPANIES:
        print(f"  - {company}")
