# Q-Mol SDKs

This directory contains auto-generated SDKs from the OpenAPI spec.

## Local Generation

Requires Docker.

### Python SDK

```bash
docker run --rm -v $(pwd):/local openapitools/openapi-generator-cli generate \
  -i /local/landing/openapi.json \
  -g python \
  -o /local/sdks/python
```

### TypeScript SDK

```bash
docker run --rm -v $(pwd):/local openapitools/openapi-generator-cli generate \
  -i /local/landing/openapi.json \
  -g typescript-axios \
  -o /local/sdks/typescript
```

## CI / CD

The `.github/workflows/sdk-publish.yml` runs automatically on every GitHub release, regenerating and publishing both SDKs to PyPI and npm.
