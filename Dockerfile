FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PORT=8000

WORKDIR /app

# System libs RDKit needs at runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    libxrender1 libxext6 libsm6 libglib2.0-0 ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# Security: run as non-root user
RUN groupadd -r qmol && useradd -r -g qmol -d /app qmol \
 && mkdir -p /app/data /app/logs /app/jobs \
 && chown -R qmol:qmol /app

USER qmol

COPY requirements.txt ./
RUN pip install -r requirements.txt \
 && pip install "fastapi>=0.110" "uvicorn>=0.27" "email-validator>=2" "python-multipart>=0.0.20"

COPY . .

# Persistent volumes for DB / logs / job outputs
# This image is dual-use: the default CMD runs the FastAPI server.
# For Celery workers, override CMD in docker-compose (see docker-compose.yml).
VOLUME ["/app/data", "/app/logs", "/app/jobs"]

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import os,urllib.request,sys; \
sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:'+os.environ.get('PORT','8000')+'/health',timeout=3).status==200 else 1)"

CMD ["sh", "-c", "uvicorn api:app --host 0.0.0.0 --port ${PORT}"]
