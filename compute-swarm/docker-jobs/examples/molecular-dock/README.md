# Molecular Docking Job — ComputeSwarm (AutoDock Vina)

This Docker image runs **AutoDock Vina** for protein-ligand docking using pre-prepared `.pdbqt` files.

---

## Quick Test (Standalone)

```bash
docker build -t computeswarm/molecular-dock:latest .
mkdir -p input output
# Place your prepared files:
# cp receptor.pdbqt input/receptor.pdbqt
# cp ligand.pdbqt input/ligand.pdbqt
docker run \
  -e CENTER_X=12.5 -e CENTER_Y=34.1 -e CENTER_Z=-5.0 \
  -e SIZE_X=20 -e SIZE_Y=20 -e SIZE_Z=20 \
  -e EXHAUSTIVENESS=32 \
  -v $(pwd)/input:/workspace/input \
  -v $(pwd)/output:/workspace/output \
  computeswarm/molecular-dock:latest
```

---

## Preparing `.pdbqt` Files

Vina requires receptor and ligand structures in **PDBQT** format (contains partial charges and atom types).

### Receptor Preparation

1. Download your protein structure (e.g., from RCSB PDB).
2. Remove water, ligands, and hetero-atoms if desired.
3. Add polar hydrogens and Gasteiger charges using **AutoDockTools** or **MGLTools**:

```bash
# Using MGLTools prepare_receptor4.py
pythonsh prepare_receptor4.py -r protein.pdb -o receptor.pdbqt
```

Or use **Open Babel** (installed in this image):

```bash
obabel protein.pdb -O receptor.pdbqt -p 7.4
```

> **Note:** Open Babel does not add Gasteiger charges by default. For best results, use MGLTools or the ADT graphical interface.

### Ligand Preparation

```bash
# Using MGLTools
pythonsh prepare_ligand4.py -l ligand.mol2 -o ligand.pdbqt

# Or Open Babel
obabel ligand.sdf -O ligand.pdbqt -p 7.4 --gen3d
```

---

## Submitting as a ComputeSwarm Job

```json
{
  "name": "Virtual Screen Batch",
  "docker_image": "computeswarm/molecular-dock:latest",
  "command": "vina --receptor /workspace/input/receptor.pdbqt --ligand /workspace/input/ligand.pdbqt --out /workspace/output/result.pdbqt --log /workspace/output/vina.log --center_x {CENTER_X} --center_y {CENTER_Y} --center_z {CENTER_Z} --size_x {SIZE_X} --size_y {SIZE_Y} --size_z {SIZE_Z} --exhaustiveness {EXHAUSTIVENESS}",
  "env_vars": {
    "CENTER_X": "12.5",
    "CENTER_Y": "34.1",
    "CENTER_Z": "-5.0",
    "SIZE_X": "20",
    "SIZE_Y": "20",
    "SIZE_Z": "20",
    "EXHAUSTIVENESS": "8"
  },
  "input_files": ["s3://.../docking_library.tar.gz"],
  "work_unit_count": 100,
  "reward_per_unit": 3.0
}
```

For a **virtual screening** campaign, each work unit receives a different ligand; the receptor is shared.

---

## Environment Variables

| Variable         | Default | Description                                      |
|------------------|---------|--------------------------------------------------|
| `CENTER_X`       | `0`     | X coordinate of the search box center            |
| `CENTER_Y`       | `0`     | Y coordinate of the search box center            |
| `CENTER_Z`       | `0`     | Z coordinate of the search box center            |
| `SIZE_X`         | `20`    | Search box size in X (Å)                         |
| `SIZE_Y`         | `20`    | Search box size in Y (Å)                         |
| `SIZE_Z`         | `20`    | Search box size in Z (Å)                         |
| `EXHAUSTIVENESS` | `8`     | Search exhaustiveness (higher = slower, better)  |

> **Important:** The orchestrator (or the entrypoint wrapper) should substitute these env vars into the `vina` command. The default `CMD` in the Dockerfile uses hardcoded defaults; override them at runtime.

---

## Expected Output Files

- `result.pdbqt` — Docked poses (sorted by binding affinity)
- `vina.log` — Vina scoring log with affinity estimates
- `computeswarm-meta.json` — Job metadata

---

## Post-Processing

```bash
# Extract top pose using Open Babel
obabel output/result.pdbqt -O top_pose.pdb -l 1

# Or analyze all poses with a Python script (RDKit, Pandas, etc.)
```

---

## Tips for Production Runs

- **Exhaustiveness**: Set to `32` or `64` for final docking; `8` is fine for quick screens.
- **Box Size**: The search box should be large enough to contain the binding pocket but not the whole protein; 20–30 Å per side is typical.
- **Receptor Flexibility**: This image uses the rigid-receptor Vina binary. For flexible side chains, use Vina's `vina_split` or prepare separate flexible/rigid receptor files.
