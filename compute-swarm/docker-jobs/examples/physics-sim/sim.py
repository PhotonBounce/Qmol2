#!/usr/bin/env python3
"""
2D Heat Equation Simulation — ComputeSwarm Physics Job

Reads an initial condition from /workspace/input/initial.npy (if present),
otherwise generates a default Gaussian heat source.
Simulates N timesteps (env var SIM_STEPS, default 1000) and writes:
  - /workspace/output/result.npy
  - /workspace/output/result.png
"""

import os
import sys
from datetime import datetime, timezone

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def main() -> int:
    # ── Configuration ─────────────────────────────────────
    sim_steps = int(os.environ.get("SIM_STEPS", "1000"))
    grid_size = int(os.environ.get("GRID_SIZE", "128"))
    alpha = float(os.environ.get("DIFFUSIVITY", "0.25"))  # thermal diffusivity

    input_dir = "/workspace/input"
    output_dir = "/workspace/output"
    os.makedirs(output_dir, exist_ok=True)

    print(f"[computeswarm-physics] SIM_STEPS={sim_steps}, GRID_SIZE={grid_size}, DIFFUSIVITY={alpha}")

    # ── Load or generate initial condition ──────────────────
    initial_path = os.path.join(input_dir, "initial.npy")
    if os.path.isfile(initial_path):
        try:
            u = np.load(initial_path)
            print(f"[computeswarm-physics] Loaded initial condition from {initial_path} shape={u.shape}")
        except Exception as exc:
            print(f"[computeswarm-physics] ERROR loading initial.npy: {exc}", file=sys.stderr)
            return 1
    else:
        print(f"[computeswarm-physics] No initial.npy found; generating default Gaussian heat source.")
        x = np.linspace(-1, 1, grid_size)
        y = np.linspace(-1, 1, grid_size)
        X, Y = np.meshgrid(x, y)
        u = np.exp(-10 * (X**2 + Y**2))

    if u.ndim != 2:
        print(f"[computeswarm-physics] ERROR: initial condition must be 2D, got shape {u.shape}", file=sys.stderr)
        return 1

    # ── 2D Heat Equation (explicit FTCS) ────────────────────
    # u_new[i,j] = u[i,j] + alpha * (u[i+1,j] + u[i-1,j] + u[i,j+1] + u[i,j-1] - 4*u[i,j])
    # with zero-flux (Neumann) boundary conditions.

    u_current = u.astype(np.float64)
    ny, nx = u_current.shape

    print(f"[computeswarm-physics] Starting simulation on {ny}x{nx} grid for {sim_steps} steps...")
    start_time = datetime.now(timezone.utc)

    for step in range(1, sim_steps + 1):
        u_new = u_current.copy()
        # interior update
        u_new[1:-1, 1:-1] = (
            u_current[1:-1, 1:-1]
            + alpha * (
                u_current[2:, 1:-1]
                + u_current[:-2, 1:-1]
                + u_current[1:-1, 2:]
                + u_current[1:-1, :-2]
                - 4 * u_current[1:-1, 1:-1]
            )
        )
        # zero-flux boundaries (Neumann)
        u_new[0, :] = u_new[1, :]
        u_new[-1, :] = u_new[-2, :]
        u_new[:, 0] = u_new[:, 1]
        u_new[:, -1] = u_new[:, -2]

        u_current = u_new

        if step % 100 == 0:
            elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
            print(f"[computeswarm-physics] Step {step}/{sim_steps} ({elapsed:.1f}s elapsed)")

    # ── Save results ────────────────────────────────────────
    result_npy = os.path.join(output_dir, "result.npy")
    try:
        np.save(result_npy, u_current)
        print(f"[computeswarm-physics] Saved result to {result_npy}")
    except Exception as exc:
        print(f"[computeswarm-physics] ERROR saving result.npy: {exc}", file=sys.stderr)
        return 1

    result_png = os.path.join(output_dir, "result.png")
    try:
        fig, ax = plt.subplots(figsize=(6, 5))
        im = ax.imshow(u_current, cmap="hot", origin="lower")
        ax.set_title("2D Heat Equation — Final State")
        fig.colorbar(im, ax=ax, label="Temperature")
        fig.tight_layout()
        fig.savefig(result_png, dpi=150)
        plt.close(fig)
        print(f"[computeswarm-physics] Saved plot to {result_png}")
    except Exception as exc:
        print(f"[computeswarm-physics] ERROR saving result.png: {exc}", file=sys.stderr)
        return 1

    print("[computeswarm-physics] Simulation complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
