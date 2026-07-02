#!/bin/bash
set -euo pipefail

# ============================================================================
# ComputeSwarm — Health Check Script
# ============================================================================
# Usage: ./scripts/health-check.sh
#   Set API_URL env var to override the target endpoint.
#
# Exit codes:
#   0 — all checks passed
#   1 — one or more checks failed
#
# Integrate with UptimeRobot, Pingdom, or a cron job for uptime monitoring.
# ============================================================================

API_URL="${API_URL:-https://api.yourdomain.com}"

FAILED=0

echo "=== ComputeSwarm Health Check ==="
echo "Target: ${API_URL}"
echo ""

# --- Health endpoint --------------------------------------------------------
echo -n "Checking /health ... "
if curl -fsS "${API_URL}/health" > /dev/null 2>&1; then
    echo "OK"
else
    echo "FAILED"
    FAILED=1
fi

# --- Metrics endpoint -------------------------------------------------------
echo -n "Checking /metrics ... "
if curl -fsS "${API_URL}/metrics" > /dev/null 2>&1; then
    echo "OK"
else
    echo "FAILED"
    FAILED=1
fi

# --- Dashboard (optional, if APP_URL is set) --------------------------------
if [ -n "${APP_URL:-}" ]; then
    echo -n "Checking dashboard (${APP_URL}) ... "
    if curl -fsS "${APP_URL}" > /dev/null 2>&1; then
        echo "OK"
    else
        echo "FAILED"
        FAILED=1
    fi
fi

echo ""
if [ "$FAILED" -eq 0 ]; then
    echo "All checks passed."
    exit 0
else
    echo "One or more checks FAILED."
    exit 1
fi
