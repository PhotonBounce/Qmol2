# Backend Dockerfile — FastAPI + Alembic + Uvicorn
# Build context: ./backend

FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies (including curl for runtime healthchecks)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# ---

FROM python:3.11-slim AS production

WORKDIR /app

# Install runtime dependencies (curl needed by docker-compose healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed Python packages from builder
COPY --from=builder /root/.local /root/.local

# Copy application code
COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini .

# Ensure scripts in .local are usable
ENV PATH=/root/.local/bin:$PATH

EXPOSE 8000

# Run migrations then start Uvicorn (docker-compose can override this CMD)
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
