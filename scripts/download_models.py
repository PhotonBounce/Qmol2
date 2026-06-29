"""Download pre-trained ONNX models from Hugging Face Hub.

Usage:
    python scripts/download_models.py [--repo-id qmol-org/qmol-admet-onnx]
                                      [--local-dir src/ml/models]

Requires:
    pip install huggingface_hub requests tqdm

The script is idempotent — it skips files that already exist.
"""
from __future__ import annotations
import argparse
import os
import sys
from pathlib import Path

# Allow running from repo root without installing the package
SCRIPT_DIR = Path(__file__).parent.resolve()
REPO_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(REPO_ROOT))

from config import HF_TOKEN  # noqa: E402


# Default model files to fetch.
MODEL_FILES = [
    "logs_regressor.onnx",
    "bbb_classifier.onnx",
    "herg_classifier.onnx",
    "gi_classifier.onnx",
    "sa_regressor.onnx",
    "ad_representatives.json",
]

DEFAULT_REPO_ID = "qmol-org/qmol-admet-onnx"
DEFAULT_LOCAL_DIR = REPO_ROOT / "src" / "ml" / "models"


def download_models(
    repo_id: str = DEFAULT_REPO_ID,
    local_dir: Path = DEFAULT_LOCAL_DIR,
    token: str | None = None,
) -> None:
    """Download ONNX models from Hugging Face Hub.

    Args:
        repo_id: Hugging Face repo ID (e.g., "org/repo").
        local_dir: Where to save the downloaded files.
        token: HF API token (or None for public repos).
    """
    try:
        from huggingface_hub import hf_hub_download, HfApi
        from huggingface_hub.utils import RepositoryNotFoundError
    except ImportError:
        print("ERROR: huggingface_hub is not installed.")
        print("  pip install huggingface_hub")
        sys.exit(1)

    local_dir = Path(local_dir)
    local_dir.mkdir(parents=True, exist_ok=True)

    print(f"Downloading models from {repo_id} → {local_dir}")
    print(f"Using token: {'yes (HF_TOKEN)' if token else 'no (public repo)'}")

    api = HfApi()
    try:
        repo_info = api.repo_info(repo_id=repo_id, token=token)
        print(f"  Repo found: {repo_info.id}")
    except RepositoryNotFoundError:
        print(f"WARNING: Repo '{repo_id}' not found on Hugging Face Hub.")
        print("  This is expected for a placeholder repo. The models will need")
        print("  to be trained manually (see scripts/train_models.py).")
        print()
        # Write a stub AD file so the system doesn't crash on missing files.
        _write_stub_ad_file(local_dir)
        return

    for filename in MODEL_FILES:
        dest = local_dir / filename
        if dest.exists():
            print(f"  SKIP (already exists): {filename}")
            continue
        try:
            downloaded = hf_hub_download(
                repo_id=repo_id,
                filename=filename,
                local_dir=str(local_dir),
                local_dir_use_symlinks=False,
                token=token,
            )
            print(f"  OK: {filename} → {downloaded}")
        except Exception as e:  # noqa: BLE001
            print(f"  FAIL: {filename} — {e}")

    print("Done.")


def _write_stub_ad_file(local_dir: Path) -> None:
    """Write a minimal applicability-domain file so the system boots."""
    ad_path = local_dir / "ad_representatives.json"
    if ad_path.exists():
        return
    import json

    # Minimal example: one representative per property (benzene fingerprint)
    stub = {
        "aqueous_logs": ["AAAAAAAAAAAAAAAAAAAAAA=="],
        "bbb_probability": ["AAAAAAAAAAAAAAAAAAAAAA=="],
        "herg_risk": ["AAAAAAAAAAAAAAAAAAAAAA=="],
        "gi_absorption": ["AAAAAAAAAAAAAAAAAAAAAA=="],
        "sa_score_lite": ["AAAAAAAAAAAAAAAAAAAAAA=="],
    }
    with open(ad_path, "w", encoding="utf-8") as fh:
        json.dump(stub, fh, indent=2)
    print(f"  Created stub AD file: {ad_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download Q-Mol ONNX ADMET models from Hugging Face Hub"
    )
    parser.add_argument(
        "--repo-id",
        default=os.getenv("HF_REPO_ID", DEFAULT_REPO_ID),
        help="Hugging Face repository ID (default: qmol-org/qmol-admet-onnx)",
    )
    parser.add_argument(
        "--local-dir",
        type=Path,
        default=DEFAULT_LOCAL_DIR,
        help="Local directory to save models (default: src/ml/models)",
    )
    parser.add_argument(
        "--token",
        default=HF_TOKEN or None,
        help="Hugging Face API token (or set HF_TOKEN env var)",
    )
    args = parser.parse_args()

    download_models(repo_id=args.repo_id, local_dir=args.local_dir, token=args.token)


if __name__ == "__main__":
    main()
