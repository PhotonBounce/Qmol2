"""
Q-Mol Message Templates
Personalized, human-sounding outreach templates for molecular dataset sales.
"""
import random
from typing import List, Optional

# Company context
QMOL_URL = "https://photon-bounce.com/qmol/"
WALLET = "0x75B30d0dE751D9628510f3cb273F09f7137f9E3F"
MINING_OUTPUT = "2,800+"


def pick_variation(options: List[str]) -> str:
    return random.choice(options)


# --- Opening lines (personalized based on target type) ---
OPENERS_RESEARCHER = [
    "Hi {name}, I came across your research on {topic} - really impressive work.",
    "Hi {name}, your recent paper on {topic} caught my attention.",
    "Hi {name}, I've been following your contributions in {topic}.",
    "Hi {name}, great to connect with another researcher in {topic}.",
]

OPENERS_PHARMA = [
    "Hi {name}, I noticed {company}'s pipeline in {topic} - exciting direction.",
    "Hi {name}, {company} is doing fascinating work in {topic}.",
    "Hi {name}, your team's approach to {topic} stands out in the industry.",
]

OPENERS_BIOTECH = [
    "Hi {name}, {company}'s platform in {topic} looks very promising.",
    "Hi {name}, been tracking {company}'s progress in {topic} - impressive.",
]

OPENERS_GENERAL = [
    "Hi {name}, hope you're doing well.",
    "Hi {name}, great to connect here on LinkedIn.",
    "Hi {name}, thanks for connecting.",
]

# --- Value proposition (Q-Mol pitch) ---
VALUE_PROPS = [
    "I run Q-Mol, a platform generating {count} novel molecules weekly via AI-driven mining bots. "
    "We're building curated molecular datasets for teams like yours - "
    "each molecule comes with computed properties ready for screening.",

    "I'm building Q-Mol - an autonomous molecular discovery pipeline producing {count} novel structures per week. "
    "We sell curated, property-tagged datasets for virtual screening and lead optimization.",

    "Q-Mol is my project - AI mining bots that generate {count} drug-like molecules weekly, "
    "each pre-tagged with key physicochemical descriptors. "
    "It might complement your {topic} workflow nicely.",
]

# --- Closing lines ---
CLOSERS = [
    "No pressure - happy to share a sample dataset if you're curious. Here's the catalog: {url}",
    "If you ever need fresh molecular scaffolds for screening, feel free to browse: {url}",
    "Would love your feedback on the dataset quality. You can preview structures here: {url}",
    "Let me know if you'd like a sample batch - always open to collaborations: {url}",
]

# --- Soft/opt-out closers ---
SOFT_CLOSERS = [
    "If this isn't relevant, no worries at all - just thought I'd share.",
    "Feel free to ignore if this isn't your area - but wanted to reach out just in case.",
    "Only reaching out because your profile suggests real expertise in this space.",
]

# --- Signatures ---
SIGNATURES = [
    "Best,\nDmitriy",
    "Cheers,\nDmitriy Buchman",
    "Kind regards,\nDmitriy",
    "Best regards,\nDmitriy",
]


def generate_message(
    name: str,
    target_type: str = "researcher",  # researcher | pharma | biotech | general
    topic: str = "drug discovery",
    company: Optional[str] = None,
    include_wallet: bool = False,
    tone: str = "professional",  # professional | casual
) -> str:
    """
    Generate a unique, human-like outreach message for Q-Mol.
    Each call produces a different variation to avoid detection.
    """
    # Pick opener
    if target_type == "researcher":
        opener = pick_variation(OPENERS_RESEARCHER).format(name=name, topic=topic)
    elif target_type == "pharma":
        opener = pick_variation(OPENERS_PHARMA).format(
            name=name, company=company or "your company", topic=topic
        )
    elif target_type == "biotech":
        opener = pick_variation(OPENERS_BIOTECH).format(
            name=name, company=company or "your company", topic=topic
        )
    else:
        opener = pick_variation(OPENERS_GENERAL).format(name=name)

    value = pick_variation(VALUE_PROPS).format(count=MINING_OUTPUT, topic=topic)
    closer = pick_variation(CLOSERS).format(url=QMOL_URL)
    soft = pick_variation(SOFT_CLOSERS)
    sig = pick_variation(SIGNATURES)

    parts = [opener, "", value]

    if random.random() < 0.4:
        parts.append("")
        parts.append(soft)

    parts.append("")
    parts.append(closer)
    parts.append("")
    parts.append(sig)

    if include_wallet:
        parts.append(f"\nCrypto wallet for direct purchases: {WALLET}")

    return "\n".join(parts)


def generate_connection_note(
    name: str,
    target_type: str = "researcher",
    topic: str = "drug discovery",
) -> str:
    """Short connection request note (LinkedIn has ~300 char limit for free accounts)."""
    notes = [
        f"Hi {name}, I'm building Q-Mol - an AI platform generating {MINING_OUTPUT} molecules weekly for drug discovery. Would love to connect!",
        f"Hi {name}, I run Q-Mol, selling curated molecular datasets. Your work in {topic} is impressive - would love to connect.",
        f"Hi {name}, working on Q-Mol (molecular dataset marketplace). Would value your perspective on {topic}.",
    ]
    note = random.choice(notes)
    return note[:280] if len(note) > 280 else note


def generate_follow_up(
    name: str,
    days_since_first: int = 7,
) -> str:
    """Follow-up message for non-responders."""
    if days_since_first < 7:
        return ""

    followups = [
        f"Hi {name}, just following up on my previous message about Q-Mol. "
        f"We've added {MINING_OUTPUT} new molecules since then. "
        f"Still happy to share a sample if you're interested: {QMOL_URL}",

        f"Hi {name}, quick follow-up - wanted to make sure my previous message didn't get buried. "
        f"Q-Mol's dataset is growing weekly. Let me know if you'd like to explore: {QMOL_URL}",

        f"Hi {name}, circling back - no pressure at all, just wanted to check if Q-Mol's molecular datasets "
        f"might be useful for your work. Sample data available here: {QMOL_URL}",
    ]
    return random.choice(followups)
