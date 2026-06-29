"""Global config loaded from .env"""
from __future__ import annotations
import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).parent.resolve()
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

load_dotenv(ROOT / ".env")

API_KEY_PEPPER = os.getenv("API_KEY_PEPPER", "")

HF_TOKEN = os.getenv("HF_TOKEN", "")
HF_REPO_ID = os.getenv("HF_REPO_ID", "")
HF_PRIVATE = os.getenv("HF_PRIVATE", "true").lower() == "true"

PUBCHEM_START_CID = int(os.getenv("PUBCHEM_START_CID", "1"))
PUBCHEM_BATCH_SIZE = int(os.getenv("PUBCHEM_BATCH_SIZE", "50"))
MAX_HEAVY_ATOMS = int(os.getenv("MAX_HEAVY_ATOMS", "8"))

BASIS_SET = os.getenv("BASIS_SET", "sto-3g")
USE_VQE_UP_TO_QUBITS = int(os.getenv("USE_VQE_UP_TO_QUBITS", "12"))
MAX_CPU_SECONDS_PER_MOL = int(os.getenv("MAX_CPU_SECONDS_PER_MOL", "120"))

# Quantum cloud credentials (optional)
IBM_QUANTUM_TOKEN = os.getenv("IBM_QUANTUM_TOKEN", "")
AWS_BRAKET_ROLE_ARN = os.getenv("AWS_BRAKET_ROLE_ARN", "")

PUBLISH_EVERY_N_MOLECULES = int(os.getenv("PUBLISH_EVERY_N_MOLECULES", "100"))
SNAPSHOT_EVERY_HOURS = int(os.getenv("SNAPSHOT_EVERY_HOURS", "6"))

# Database mode: PostgreSQL for production, SQLite for dev
USE_POSTGRES = os.getenv("USE_POSTGRES", "false").lower() == "true"
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://qmol:qmol@localhost:5432/qmol")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Async PostgreSQL URL (ensure +asyncpg driver)
ASYNC_DATABASE_URL = DATABASE_URL
if ASYNC_DATABASE_URL.startswith("postgresql+psycopg2://"):
    ASYNC_DATABASE_URL = ASYNC_DATABASE_URL.replace("postgresql+psycopg2://", "postgresql+asyncpg://", 1)
elif ASYNC_DATABASE_URL.startswith("postgresql://"):
    ASYNC_DATABASE_URL = ASYNC_DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

# SQLite fallback paths (used when USE_POSTGRES=false)
DB_PATH = DATA_DIR / "qmol.sqlite"
PARQUET_PATH = DATA_DIR / "qmol.parquet"
STATE_PATH = DATA_DIR / "state.json"

KEYS_DB_PATH = Path(os.getenv("QMOL_KEYS_DB", DATA_DIR / "keys.sqlite"))
JOBS_DB_PATH = Path(os.getenv("QMOL_JOBS_DB", DATA_DIR / "jobs.sqlite"))

# ML model directory (overridable for external model mounts)
MODELS_DIR = Path(os.getenv("MODELS_DIR", ROOT / "src" / "ml" / "models"))

# TrustedHostMiddleware (comma-separated; empty = disabled)
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "")
