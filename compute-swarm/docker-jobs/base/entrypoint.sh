#!/usr/bin/env bash
# ComputeSwarm Job Entrypoint Helper
# Usage: Set as ENTRYPOINT; the job command is passed as CMD / args.

set -euo pipefail

META_FILE="/workspace/output/computeswarm-meta.json"
START_TIME=""
END_TIME=""
EXIT_CODE=0

log_meta() {
    END_TIME=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    cat > "$META_FILE" <<EOF
{
    "start_time": "$START_TIME",
    "end_time": "$END_TIME",
    "exit_code": $EXIT_CODE,
    "command": "$*"
}
EOF
}

cleanup() {
    log_meta
}

trap cleanup EXIT

# ── Input validation ──────────────────────────────────────
if [[ ! -d /workspace/input ]]; then
    echo "[computeswarm] ERROR: /workspace/input does not exist." >&2
    exit 1
fi

if [[ -z "$(ls -A /workspace/input 2>/dev/null || true)" ]]; then
    echo "[computeswarm] WARNING: /workspace/input is empty." >&2
fi

# Ensure output directory exists
mkdir -p /workspace/output

START_TIME=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

echo "[computeswarm] Starting job at $START_TIME"
echo "[computeswarm] Command: $*"

# ── Run the command ─────────────────────────────────────────
set +e
"$@"
EXIT_CODE=$?
set -e

if [[ $EXIT_CODE -eq 0 ]]; then
    echo "[computeswarm] Job completed successfully."
else
    echo "[computeswarm] Job failed with exit code $EXIT_CODE." >&2
fi

# ── Ensure output is not empty (warning only) ─────────────
if [[ -z "$(ls -A /workspace/output 2>/dev/null || true)" ]]; then
    echo "[computeswarm] WARNING: /workspace/output is empty." >&2
fi

exit $EXIT_CODE
