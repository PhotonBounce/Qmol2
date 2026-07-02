# syntax=docker/dockerfile:1

# ───────────────────────────────────────────────────────────
# ComputeSwarm — Blender Rendering Job
# ───────────────────────────────────────────────────────────
FROM computeswarm/base:latest

USER root

# Install Blender dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libxi6 \
    libxrender1 \
    libxfixes3 \
    libxkbcommon0 \
    libsm6 \
    libfreetype6 \
    libfontconfig1 \
    xz-utils \
    && rm -rf /var/lib/apt/lists/*

# Download and install Blender 4.2 LTS (latest stable LTS as of 2024)
ARG BLENDER_VERSION=4.2.3
ARG BLENDER_URL=https://download.blender.org/release/Blender4.2/blender-${BLENDER_VERSION}-linux-x64.tar.xz
RUN wget -q "$BLENDER_URL" -O /tmp/blender.tar.xz && \
    tar -xJf /tmp/blender.tar.xz -C /opt && \
    rm /tmp/blender.tar.xz && \
    ln -s /opt/blender-${BLENDER_VERSION}-linux-x64/blender /usr/local/bin/blender

WORKDIR /workspace

# Switch back to non-root user
RUN chown -R computeswarm:computeswarm /workspace
USER computeswarm

ENTRYPOINT ["/workspace/entrypoint.sh"]
CMD ["blender", "-b", "/workspace/input/scene.blend", "-o", "/workspace/output/frame_####", "-f", "1"]
