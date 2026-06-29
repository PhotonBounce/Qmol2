# Migration Guide

## v1 → v2 API

### Endpoint Changes

All endpoints now require `/v1/` prefix. Legacy endpoints redirect automatically:

| Old | New | Status |
|-----|-----|--------|
| `POST /compute` | `POST /v1/compute` | 307 redirect |
| `POST /predict` | `POST /v1/predict` | 307 redirect |
| `POST /jobs` | `POST /v1/jobs` | 307 redirect |

### Breaking Changes

1. **Response format**: `results` array now wraps all endpoint responses (was top-level for some)
2. **Error format**: Now includes `request_id` and `timestamp` fields
3. **Quota**: Free tier reduced from unlimited to 500/month

### Client Migration

```python
# Old (v1)
import requests
r = requests.post("https://api.qmol.app/compute", json={"smiles": ["CCO"]})

# New (v2)
import requests
r = requests.post("https://api.qmol.app/v1/compute", 
    headers={"x-api-key": "YOUR_KEY"},
    json={"smiles": ["CCO"]})
```

## SQLite → PostgreSQL

If you have existing SQLite data, run the migration script:

```bash
python scripts/migrate_sqlite_to_postgres.py
```

This will:
1. Read all data from `data/*.sqlite` files
2. Write to PostgreSQL with batch inserts
3. Preserve all existing API keys and usage records

**Note**: API keys will be re-hashed with bcrypt during migration. Old keys will still work.
