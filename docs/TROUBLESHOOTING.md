# Troubleshooting

## Common Issues

### "Invalid API key" (401)
- Check that the key is copied correctly (no extra spaces)
- Keys are case-sensitive
- Free keys expire after 30 days of inactivity

### "Quota exceeded" (402)
- Check your usage: `GET /v1/usage`
- Upgrade your plan at https://qmol.app/checkout
- Request a quota increase for enterprise accounts

### "Rate limit exceeded" (429)
- Wait and retry (Retry-After header indicates wait time)
- Use batch endpoints instead of individual calls
- Upgrade to Commercial tier for higher limits

### Job stuck in "queued" status
- Check Celery worker status: `GET /v1/health`
- If worker is down, restart it: `docker-compose restart worker`
- Jobs older than 24 hours are auto-cancelled

### "Invalid SMILES" (400)
- Use canonical SMILES (RDKit-validated)
- Common issues: aromatic notation `c1ccccc1`, explicit H `[H]`, stereochemistry `@@`
- Validate first: `POST /v1/standardize`

### ML model returns 503
- Model not yet loaded. Wait 30 seconds and retry.
- If persistent, check model status: `GET /v1/models`
