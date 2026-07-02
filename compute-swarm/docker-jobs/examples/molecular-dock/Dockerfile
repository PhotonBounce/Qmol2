# syntax=docker/dockerfile:1

# ───────────────────────────────────────────────────────────
# ComputeSwarm — Molecular Docking Job (AutoDock Vina)
# ───────────────────────────────────────────────────────────
FROM computeswarm/base:latest

USER root

# Install Open Babel for format conversion
RUN apt-get update && apt-get install -y --no-install-recommends \
    openbabel \
    && rm -rf /var/lib/apt/lists/*

# Download and install AutoDock Vina (latest stable binary release)
ARG VINA_VERSION=1.2.5
ARG VINA_URL=https://github.com/ccsb-scripps/AutoDock-Vina/releases/download/v${VINA_VERSION}/vina_${VINA_VERSION}_linux_x86_64
RUN wget -q "$VINA_URL" -O /usr/local/bin/vina && \
    chmod +x /usr/local/bin/vina && \
    vina --version

WORKDIR /workspace

RUN chown -R computeswarm:computeswarm /workspace
USER computeswarm

ENTRYPOINT ["/workspace/entrypoint.sh"]
CMD ["vina", \
     "--receptor", "/workspace/input/receptor.pdbqt", \
     "--ligand", "/workspace/input/ligand.pdbqt", \
     "--out", "/workspace/output/result.pdbqt", \
     "--log", "/workspace/output/vina.log", \
     "--center_x", "0", \
     "--center_y", "0", \
     "--center_z", "0", \
     "--size_x", "20", \
     "--size_y", "20", \
     "--size_z", "20", \
     "--exhaustiveness", "8"]
