#!/bin/bash
set -euo pipefail

# ============================================================================
# ComputeSwarm — Database Backup Script
# ============================================================================
# Usage: ./scripts/backup-db.sh
#
# Backs up the PostgreSQL database to a timestamped gzip file.
# Optionally uploads to MinIO/S3 if the MinIO client (mc) is available.
#
# Cron example (run daily at 03:00):
#   0 3 * * * /opt/computeswarm/scripts/backup-db.sh >> /var/log/computeswarm-backup.log 2>&1
# ============================================================================

# --- Configuration ------------------------------------------------------------
BACKUP_DIR="${BACKUP_DIR:-/opt/computeswarm/backups}"
DB_CONTAINER="${DB_CONTAINER:-computeswarm-db}"
DB_NAME="${DB_NAME:-computeswarm}"
DB_USER="${DB_USER:-computeswarm}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"

# Optional MinIO upload settings
MINIO_ALIAS="${MINIO_ALIAS:-local}"
MINIO_BUCKET="${MINIO_BACKUP_BUCKET:-computeswarm-backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
FILENAME="computeswarm_backup_${TIMESTAMP}.sql.gz"
BACKUP_PATH="${BACKUP_DIR}/${FILENAME}"

mkdir -p "${BACKUP_DIR}"

echo "=== ComputeSwarm DB Backup ==="
echo "Timestamp: ${TIMESTAMP}"
echo "Target:    ${BACKUP_PATH}"

# --- Run pg_dump inside the container ---------------------------------------
docker exec "${DB_CONTAINER}" pg_dump -U "${DB_USER}" -d "${DB_NAME}" | gzip > "${BACKUP_PATH}"

BACKUP_SIZE=$(du -h "${BACKUP_PATH}" | cut -f1)
echo "Backup size: ${BACKUP_SIZE}"

# --- Optional: Upload to MinIO --------------------------------------------
if command -v mc >/dev/null 2>&1; then
    echo "Uploading to MinIO (${MINIO_ALIAS}/${MINIO_BUCKET}) ..."
    mc cp "${BACKUP_PATH}" "${MINIO_ALIAS}/${MINIO_BUCKET}/${FILENAME}" || echo "MinIO upload failed (check alias config)."
fi

# --- Cleanup old backups ----------------------------------------------------
CLEANED=$(find "${BACKUP_DIR}" -name "computeswarm_backup_*.sql.gz" -mtime +${RETENTION_DAYS} -print | wc -l)
find "${BACKUP_DIR}" -name "computeswarm_backup_*.sql.gz" -mtime +${RETENTION_DAYS} -delete
echo "Cleaned up ${CLEANED} old backup(s) (> ${RETENTION_DAYS} days)."

echo "Backup complete."
