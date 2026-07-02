#!/usr/bin/env bash
set -euo pipefail

# init-minio.sh — Idempotent MinIO bucket setup for ComputeSwarm
# Usage: ./scripts/init-minio.sh

MINIO_ENDPOINT="${MINIO_ENDPOINT:-http://localhost:9000}"
MINIO_ROOT_USER="${MINIO_ROOT_USER:-minioadmin}"
MINIO_ROOT_PASSWORD="${MINIO_ROOT_PASSWORD:-minioadmin}"
BUCKET_NAME="${MINIO_BUCKET:-computeswarm}"
ALIAS="csminio"

echo "[init-minio] Waiting for MinIO at ${MINIO_ENDPOINT} ..."

for i in $(seq 1 60); do
    if curl -sf "${MINIO_ENDPOINT}/minio/health/live" >/dev/null 2>&1; then
        echo "[init-minio] MinIO is up."
        break
    fi
    if [ "$i" -eq 60 ]; then
        echo "[init-minio] ERROR: MinIO did not become ready in time." >&2
        exit 1
    fi
    sleep 1
done

echo "[init-minio] Configuring mc alias ..."
# Use the standalone MinIO client (mc) if available; otherwise try docker run
if command -v mc >/dev/null 2>&1; then
    mc alias set "${ALIAS}" "${MINIO_ENDPOINT}" "${MINIO_ROOT_USER}" "${MINIO_ROOT_PASSWORD}" --api s3v4
else
    echo "[init-minio] mc not found locally, trying docker run minio/mc ..."
    # --network host works on Linux but not on Docker Desktop (Windows/Mac).
    # We try it first; if Docker Desktop rejects it, fall back to host.docker.internal.
    if docker run --rm --network host minio/mc \
            alias set "${ALIAS}" "${MINIO_ENDPOINT}" "${MINIO_ROOT_USER}" "${MINIO_ROOT_PASSWORD}" --api s3v4 2>/dev/null; then
        _MC_NETWORK="--network host"
    else
        echo "[init-minio] --network host not supported (Docker Desktop?), trying host.docker.internal ..."
        # Replace localhost with host.docker.internal for the container
        _CONTAINER_ENDPOINT="${MINIO_ENDPOINT/localhost/host.docker.internal}"
        docker run --rm minio/mc \
            alias set "${ALIAS}" "${_CONTAINER_ENDPOINT}" "${MINIO_ROOT_USER}" "${MINIO_ROOT_PASSWORD}" --api s3v4
        _MC_NETWORK=""
    fi
    # redefine mc to use docker
    mc() {
        docker run --rm ${_MC_NETWORK} minio/mc "$@"
    }
fi

echo "[init-minio] Checking if bucket '${BUCKET_NAME}' exists ..."
if mc ls "${ALIAS}/${BUCKET_NAME}" >/dev/null 2>&1; then
    echo "[init-minio] Bucket '${BUCKET_NAME}' already exists. Skipping creation."
else
    echo "[init-minio] Creating bucket '${BUCKET_NAME}' ..."
    mc mb "${ALIAS}/${BUCKET_NAME}"
fi

echo "[init-minio] Setting bucket policy to allow presigned uploads/downloads ..."
# mc policy set is deprecated in newer mc; use anonymous set, falling back to old syntax
mc anonymous set download "${ALIAS}/${BUCKET_NAME}" 2>/dev/null || mc policy set download "${ALIAS}/${BUCKET_NAME}" || true

echo "[init-minio] Done."
