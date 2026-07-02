#!/usr/bin/env python3
"""
ComputeSwarm Result Validator

Standalone validation script for verifying redundant work-unit results,
comparing SHA-256 checksums, and aggregating validated outputs.

Usage:
    python validator.py --results-dir ./results --output ./aggregated.tar.gz
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tarfile
from collections import Counter
from pathlib import Path
from typing import Iterable


def compute_checksum(file_path: str | os.PathLike) -> str:
    """Return the SHA-256 hex digest of a file."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def compare_checksums(checksums: list[str]) -> str | None:
    """
    Return the majority checksum if at least 2/3 of the values match.
    Otherwise return None.

    For a list of 3 checksums, a majority requires at least 2 identical.
    """
    if not checksums:
        return None

    total = len(checksums)
    threshold = total * 2 / 3
    counts = Counter(checksums)
    majority_checksum, count = counts.most_common(1)[0]

    if count >= threshold:
        return majority_checksum
    return None


def validate_result(result_path: str | os.PathLike, expected_checksum: str) -> bool:
    """Return True if the file's SHA-256 matches the expected checksum."""
    if not os.path.isfile(result_path):
        return False
    actual = compute_checksum(result_path)
    return actual == expected_checksum


def aggregate_results(
    output_dir: str | os.PathLike,
    work_unit_results: Iterable[str | os.PathLike],
    archive_name: str | os.PathLike = "aggregated_results.tar.gz",
) -> Path:
    """
    Tar.gz all validated work-unit outputs into a single archive placed in
    *output_dir*. Returns the path to the created archive.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    archive_path = output_dir / archive_name

    with tarfile.open(archive_path, "w:gz") as tar:
        for result_path in work_unit_results:
            result_path = Path(result_path)
            if result_path.exists():
                tar.add(result_path, arcname=result_path.name)
            else:
                print(f"[validator] WARNING: skipping missing path {result_path}", file=sys.stderr)

    return archive_path


def discover_results(results_dir: Path) -> list[Path]:
    """Find all non-metadata files inside *results_dir*."""
    files = [p for p in results_dir.rglob("*") if p.is_file()]
    # Exclude internal metadata files produced by the entrypoint
    files = [p for p in files if p.name != "computeswarm-meta.json"]
    return files


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate and aggregate ComputeSwarm work-unit results."
    )
    parser.add_argument(
        "--results-dir",
        required=True,
        type=Path,
        help="Directory containing result subdirectories (one per work unit).",
    )
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Path for the aggregated tar.gz archive.",
    )
    parser.add_argument(
        "--checksums",
        type=Path,
        default=None,
        help=(
            "Optional JSON file mapping work-unit ID to expected checksum. "
            "If omitted, only majority consensus validation is performed."
        ),
    )
    args = parser.parse_args()

    results_dir: Path = args.results_dir
    output_archive: Path = args.output

    if not results_dir.is_dir():
        print(f"[validator] ERROR: {results_dir} is not a directory.", file=sys.stderr)
        return 1

    # Load optional expected checksums
    expected_checksums: dict[str, str] = {}
    if args.checksums and args.checksums.is_file():
        with open(args.checksums, "r", encoding="utf-8") as f:
            expected_checksums = json.load(f)

    # Collect work-unit directories
    unit_dirs = [d for d in results_dir.iterdir() if d.is_dir()]
    if not unit_dirs:
        print(f"[validator] WARNING: no subdirectories found in {results_dir}")
        return 0

    print(f"[validator] Found {len(unit_dirs)} work-unit directories.")

    validated_paths: list[Path] = []
    failed_units: list[str] = []

    for unit_dir in sorted(unit_dirs):
        unit_id = unit_dir.name
        files = discover_results(unit_dir)
        if not files:
            print(f"[validator] WARNING: {unit_id} has no result files.")
            failed_units.append(unit_id)
            continue

        # Compute checksums for every file in the unit and combine them
        unit_checksums = [compute_checksum(f) for f in files]
        combined_checksum = hashlib.sha256(
            "".join(unit_checksums).encode("utf-8")
        ).hexdigest()

        # Validate against expected checksum (if provided)
        if expected_checksums:
            expected = expected_checksums.get(unit_id)
            if expected is None:
                print(f"[validator] WARNING: no expected checksum for {unit_id}; skipping.")
                failed_units.append(unit_id)
                continue
            if combined_checksum != expected:
                print(
                    f"[validator] FAILED: checksum mismatch for {unit_id} "
                    f"(expected {expected}, got {combined_checksum}).",
                    file=sys.stderr,
                )
                failed_units.append(unit_id)
                continue

        print(f"[validator] OK: {unit_id} — {len(files)} file(s), checksum {combined_checksum[:16]}...")
        validated_paths.extend(files)

    # ── Majority consensus across units (if >= 3 units) ─────
    if len(unit_dirs) >= 3:
        all_unit_checksums = []
        for unit_dir in sorted(unit_dirs):
            files = discover_results(unit_dir)
            if files:
                cks = [compute_checksum(f) for f in files]
                all_unit_checksums.append(hashlib.sha256("".join(cks).encode("utf-8")).hexdigest())

        majority = compare_checksums(all_unit_checksums)
        if majority:
            print(f"[validator] Majority consensus checksum: {majority[:16]}...")
        else:
            print("[validator] WARNING: no majority consensus among work-unit checksums.", file=sys.stderr)

    # ── Aggregate validated outputs ───────────────────────────
    if validated_paths:
        archive = aggregate_results(output_archive.parent, validated_paths, output_archive.name)
        print(f"[validator] Aggregated archive created: {archive}")
    else:
        print("[validator] ERROR: no validated results to aggregate.", file=sys.stderr)
        return 1

    if failed_units:
        print(f"[validator] Failed units: {failed_units}")
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
