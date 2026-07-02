# Q-Mol Lite Docker Image
# ========================
# Minimal image for free-tier hosting (Render, Fly.io, Oracle Cloud).
# Removes heavy optional packages to fit in < 512 MB RAM.
#
# Build: docker build -f deploy/lite.Dockerfile -t qmol:lite .
# Run:   docker run -p 8000:8000 -v qmol-data:/app/data qmol:lite

FROM python:3.12-slim

# Install system deps for RDKit
RUN apt-get update && apt-get install -y --no-install-recommends \
    libxrender1 \
    libxext6 \
    libsm6 \
    libfontconfig1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first (for layer caching)
COPY requirements.txt requirements-lite.txt ./
RUN pip install --no-cache-dir -r requirements-lite.txt

# Copy app code
COPY api.py config.py ./
COPY src/ ./src/
COPY data/ ./data/ || true
COPY landing/ ./landing/ || true

# Create data directory
RUN mkdir -p /app/data /app/logs

# Environment
ENV PYTHONUNBUFFERED=1
ENV USE_POSTGRES=false
ENV PORT=8000

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run with uvicorn
CMD ["python", "-m", "uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
