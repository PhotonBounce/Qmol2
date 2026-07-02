# syntax=docker/dockerfile:1

# ───────────────────────────────────────────────────────────
# ComputeSwarm — Physics Simulation Job
# ───────────────────────────────────────────────────────────
FROM computeswarm/base:latest

USER root

# Install lightweight mesh I/O library (FEniCS is too heavy for a base worker image)
RUN pip install --no-cache-dir meshio

WORKDIR /workspace

# Copy sample simulation script to the input directory so the default CMD works
COPY sim.py /workspace/input/sim.py
RUN chmod 644 /workspace/input/sim.py

# Fix ownership
RUN chown -R computeswarm:computeswarm /workspace
USER computeswarm

ENTRYPOINT ["/workspace/entrypoint.sh"]
CMD ["python", "/workspace/input/sim.py"]
