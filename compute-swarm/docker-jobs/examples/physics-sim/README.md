# Physics Simulation Job — ComputeSwarm

This Docker image runs a lightweight 2D heat-equation simulation written in Python + NumPy.

---

## Quick Test (Standalone)

```bash
docker build -t computeswarm/physics-sim:latest .
mkdir -p input output
# Optionally place a custom initial condition:
# cp my_initial.npy input/initial.npy
docker run \
  -e SIM_STEPS=500 \
  -v $(pwd)/input:/workspace/input \
  -v $(pwd)/output:/workspace/output \
  computeswarm/physics-sim:latest
```

---

## How It Works

The container executes `python /workspace/input/sim.py` (you can also mount your own `sim.py` into `/workspace/input/`).

The built-in `sim.py` performs a **2D explicit heat equation** solver:

1. Reads `/workspace/input/initial.npy` (if present) or generates a default Gaussian heat source.
2. Steps forward in time using the Forward-Time Central-Space (FTCS) scheme with zero-flux (Neumann) boundaries.
3. Saves the final temperature field to `/workspace/output/result.npy`.
4. Saves a `hot` colormap plot to `/workspace/output/result.png`.

---

## Environment Variables

| Variable      | Default | Description                                    |
|---------------|---------|------------------------------------------------|
| `SIM_STEPS`   | `1000`  | Number of simulation timesteps                 |
| `GRID_SIZE`   | `128`   | Grid resolution (only for default initial cond) |
| `DIFFUSIVITY` | `0.25`  | Thermal diffusivity constant (alpha)           |

---

## Submitting as a ComputeSwarm Job

```json
{
  "name": "Heat Sim Batch",
  "docker_image": "computeswarm/physics-sim:latest",
  "command": "python /workspace/input/sim.py",
  "env_vars": {"SIM_STEPS": "5000", "DIFFUSIVITY": "0.2"},
  "input_files": ["s3://.../initial_conditions.tar.gz"],
  "work_unit_count": 10,
  "reward_per_unit": 1.0
}
```

If you want each work unit to run a **different initial condition**, pack each condition into its own `.tar.gz` and let the orchestrator assign one per work unit.

---

## Expected Output Files

- `result.npy` — Final 2D NumPy array (`float64`)
- `result.png` — Matplotlib visualization of the final state
- `computeswarm-meta.json` — Job metadata (start time, end time, exit code)

---

## Custom Simulations

Replace `sim.py` with your own physics code. Requirements:

- Read input from `/workspace/input/`
- Write output to `/workspace/output/`
- Exit `0` on success, non-zero on failure

Mount your custom script:

```bash
docker run \
  -v $(pwd)/my_custom_sim.py:/workspace/input/sim.py \
  -v $(pwd)/output:/workspace/output \
  computeswarm/physics-sim:latest
```
