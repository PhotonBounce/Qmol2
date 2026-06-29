# Q-Mol ONNX Models

This directory houses the ONNX runtime models used by the `MLPredictor`.

## Expected files

| Filename                  | Property        | Type       | Input dim | Source benchmark |
|---------------------------|-----------------|------------|-----------|------------------|
| `logs_regressor.onnx`     | logS            | regressor  | 2068      | Delaney ESOL 2004 |
| `bbb_classifier.onnx`     | BBB+/-          | classifier | 2068      | Li et al. 2018   |
| `herg_classifier.onnx`    | hERG risk       | classifier | 2068      | ChEMBL hERG      |
| `gi_classifier.onnx`     | GI absorption   | classifier | 20        | SwissADME        |
| `sa_regressor.onnx`      | SA score        | regressor  | 2068      | SYNLIB-lite      |
| `ad_representatives.json`| AD fingerprints | —          | —         | Training set reps |

## How to download pre-trained models

Run the provided script (no training needed):

```bash
python scripts/download_models.py
```

This pulls the latest ONNX artifacts from the Hugging Face model hub:
- Repository: `qmol-org/qmol-admet-onnx` (public, MIT-licensed)
- Each model is ~2–5 MB; total download ≈ 15 MB.

## How to generate your own models

If you prefer to train from scratch:

```bash
# 1. Install training dependencies
pip install scikit-learn onnx onnxruntime skl2onnx

# 2. Run the training pipeline stub
python scripts/train_models.py --data-dir ./data --output-dir ./src/ml/models
```

See `scripts/train_models.py` for the full pipeline description.

## Feature mode reference

Models were trained with one of three feature modes:
- **morgan** (2048): Morgan/ECFP4 fingerprint only.
- **descriptors** (20): Canonical RDKit 2D descriptors only.
- **concat** (2068): Concatenation of both.

The `MLPredictor` peeks at the ONNX input dimension at load time to
auto-detect the correct mode; no manual configuration is required.

## Applicability Domain (AD)

`ad_representatives.json` contains a small set of Morgan fingerprints
representing the training-set chemical space. It is used to compute
Tanimoto similarity and flag out-of-domain queries. The file is optional;
if absent, AD scores default to 0.5 (neutral).

## Model versioning

All ONNX files are named with a `-v{N}` suffix (e.g., `onnx-logs-v1`).
When upgrading, place the new `.onnx` in this directory and increment
the version in `src/ml/model_cards.py`.
