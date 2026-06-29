"""Training pipeline orchestrator for Q-Mol ONNX ADMET models.

Runs the full end-to-end training pipeline for available endpoints.

Usage:
    python scripts/train_models.py --no-dry-run

Prerequisites:
    pip install scikit-learn onnx onnxruntime skl2onnx pandas numpy rdkit
"""
from __future__ import annotations
import argparse
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
REPO_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(REPO_ROOT))


def run_script(name: str, description: str) -> bool:
    """Run a training script and report success/failure."""
    script_path = SCRIPT_DIR / name
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Script: {script_path}")
    print(f"{'='*60}")
    
    result = subprocess.run(
        [sys.executable, str(script_path)],
        cwd=REPO_ROOT,
        capture_output=False,
    )
    return result.returncode == 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Q-Mol ONNX model training pipeline"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Print pipeline steps without executing",
    )
    parser.add_argument(
        "--steps",
        nargs="+",
        choices=["download", "logs", "herg", "export", "ad", "all"],
        default=["all"],
        help="Which pipeline steps to run",
    )
    args = parser.parse_args()

    if args.dry_run:
        print("=" * 60)
        print("Q-Mol ONNX Training Pipeline — DRY RUN")
        print("=" * 60)
        print("\nSteps that would run:")
        print("  1. download  — Download ESOL dataset")
        print("  2. logs      — Train aqueous solubility (logS) model")
        print("  3. herg      — Train hERG model")
        print("  4. export    — Export models to ONNX")
        print("  5. ad        — Generate applicability domain representatives")
        print("\nUse --no-dry-run to execute.")
        return

    steps = set(args.steps)
    if "all" in steps:
        steps = {"download", "logs", "herg", "export", "ad"}

    results = {}

    if "download" in steps:
        results["download"] = run_script("download_esol.py", "Download ESOL dataset")

    if "logs" in steps:
        results["logs"] = run_script("train_logs_model.py", "Train logS model")

    if "herg" in steps:
        results["herg"] = run_script("train_herg_model.py", "Train hERG model")

    if "export" in steps:
        results["export"] = run_script("export_onnx.py", "Export models to ONNX")

    if "ad" in steps:
        results["ad"] = run_script("generate_ad_representatives.py", "Generate AD representatives")

    print("\n" + "=" * 60)
    print("Pipeline Summary")
    print("=" * 60)
    for step, success in results.items():
        status = "OK" if success else "FAIL"
        print(f"  {step:12s} : {status}")
    
    all_ok = all(results.values())
    print(f"\nOverall: {'SUCCESS' if all_ok else 'SOME STEPS FAILED'}")
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
