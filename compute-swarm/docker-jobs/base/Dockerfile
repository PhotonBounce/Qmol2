# syntax=docker/dockerfile:1

# ───────────────────────────────────────────────────────────
# ComputeSwarm — Base Scientific Job Image
# ───────────────────────────────────────────────────────────
FROM python:3.11-slim

# Prevent interactive apt prompts
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies + OpenMPI for parallel simulations
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    wget \
    curl \
    ca-certificates \
    libopenmpi-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Install common scientific Python packages
RUN pip install --no-cache-dir \
    numpy \
    scipy \
    pandas \
    matplotlib \
    pillow \
    requests \
    tqdm

# Working directory and I/O directories
WORKDIR /workspace
RUN mkdir -p /workspace/input /workspace/output

# Add non-root user and fix ownership
RUN groupadd -r computeswarm && \
    useradd -r -g computeswarm -d /workspace -s /bin/bash computeswarm && \
    chown -R computeswarm:computeswarm /workspace

# Copy the helper entrypoint script (available for child images to use)
COPY --chmod=755 entrypoint.sh /workspace/entrypoint.sh

# Default: drop to bash so interactive dev / orchestrator override works.
# Child images should set ENTRYPOINT ["/workspace/entrypoint.sh"].
ENTRYPOINT ["/bin/bash"]
CMD []
