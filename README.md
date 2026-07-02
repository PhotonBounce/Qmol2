# Q-Mol v2.0.0

**Molecular Informatics & Drug Discovery Platform**

Compute molecular descriptors, predict ADMET properties with ML, screen drug-target interactions, and design novel molecules — all from your own machine. No cloud lock-in. No data leaks.

[![Python](https://img.shields.io/badge/python-3.12-blue)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110-009688)](https://fastapi.tiangolo.com)
[![RDKit](https://img.shields.io/badge/RDKit-2024.3-2C8C8C)](https://rdkit.org)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

---

## 🚀 What Q-Mol Can Do

| Feature | Description |
|---------|-------------|
| **50+ Descriptors** | MW, logP, TPSA, QED, Lipinski rules, ring counts, aromaticity — powered by RDKit |
| **ML ADMET** | Solubility (logS, R²=0.892), hERG inhibition (R²=0.800), BBB, CYP450 — validated models |
| **Drug-Target Screening** | EGFR, AChE, BACE1 binding affinity predictions with confidence intervals |
| **De Novo Design** | Generate novel molecules from seed scaffolds, optimize with genetic algorithms |
| **Similarity Search** | Tanimoto similarity with ECFP4 fingerprints, PubChem integration |
| **3D Dashboard** | React + NGL viewer for interactive molecule visualization |

---

## 📦 Quick Start (Windows)

### Option 1: Setup Wizard (Recommended)

```powershell
cd D:\Qmol-3
setup.bat
```

This installs Python dependencies, creates the database, and sets up the environment automatically.

### Option 2: Manual

```powershell
# 1. Create virtual environment
python -m venv .venv

# 2. Activate
.venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Start the server
python -m uvicorn api:app --reload
```

### Access the API

- **Docs:** http://localhost:8000/v1/docs
- **Health:** http://localhost:8000/health
- **Compute:** POST to http://localhost:8000/v1/compute with `{"smiles": ["CCO"]}`

---

## 🌐 Make It Public (Free)

Run this to get a free HTTPS URL for your local PC:

```powershell
deploy\cloudflare-tunnel-setup.bat
```

No port forwarding. No cloud server. Your PC becomes the server with a Cloudflare-secured URL.

For 24/7 hosting, see [docs/FREE_HOSTING.md](docs/FREE_HOSTING.md) — 6 free options ranked by performance.

---

## 💰 Payments (Crypto)

**Wallet:** `0x75B30d0dE751D9628510f3cb273F09f7137f9E3F`

| Plan | Price | What's Included |
|------|-------|-----------------|
| **Free** | $0 | All descriptors, ML predictions, local storage, community support |
| **Research** | $20 (one-time) | Premium API key (10K requests), DTI screening, de novo generation, email support |
| **Enterprise** | $100 (one-time) | Unlimited requests, custom models, team accounts, priority support |
| **Android** | $15 (one-time) | Google Play unlock, mobile dashboard, offline compute |

One-time payment. No subscription. No recurring fees.

---

## 📱 Mobile App

### Android APK

```powershell
build-apk.bat
```

This builds and signs the Android APK. Requires Flutter SDK (auto-downloaded if missing).

### Google Play Store

Coming soon. Contact us for beta access.

---

## 🏗️ Architecture

```
Q-Mol v2.0.0
├── api.py                 # FastAPI entry point
├── src/
│   ├── db.py              # Async SQLite/PostgreSQL
│   ├── models.py          # SQLAlchemy ORM
│   ├── compute.py         # RDKit descriptor engine
│   ├── predictor.py       # ML prediction (ONNX + scikit-learn)
│   ├── pubchem.py         # PubChem integration
│   ├── storage.py         # SQLite persistence
│   ├── keys.py            # API key management (bcrypt hashed)
│   ├── middleware.py      # Security middleware
│   └── routers/v1/        # 31 REST API endpoints
├── tests/                 # 35+ integration tests
├── dashboard/             # React frontend (builds to static)
├── mobile/                # Flutter Android app
├── deploy/                # Hosting scripts & Docker files
└── docs/                  # Documentation
```

---

## 🔧 Requirements

### Minimum (Free Tier / SQLite)

- Python 3.12
- 2 GB RAM (4 GB recommended with RDKit)
- Windows 10/11, Linux, or macOS

### Full Stack (Production)

- PostgreSQL 14+
- Redis 7+ (for caching, rate limiting, job queue)
- Celery + Flower (for background tasks)

See `requirements.txt` (core), `requirements-postgres.txt` (production add-ons), `requirements-lite.txt` (absolute minimum).

---

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific test
pytest tests/integration/test_api.py -v
```

---

## 🛡️ Security

- API keys are bcrypt-hashed with optional pepper
- Rate limiting on all endpoints
- SSRF protection for external URLs
- Path traversal protection
- CORS configured per environment
- HSTS headers in production

See `docs/SECURITY.md` for full details.

---

## 📚 Documentation

| File | Description |
|------|-------------|
| `docs/FREE_HOSTING.md` | 6 free hosting options ranked |
| `docs/GITHUB_SETUP.md` | Step-by-step GitHub repo setup |
| `docs/SECURITY.md` | Security hardening guide |
| `docs/MIGRATION.md` | Upgrading from v1.x |

---

## 🤝 Contributing

1. Fork the repo
2. Create a feature branch (`git checkout -b feature/amazing`)
3. Commit (`git commit -am 'Add amazing feature'`)
4. Push (`git push origin feature/amazing`)
5. Open a Pull Request

---

## 📄 License

MIT License. See [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgments

- [RDKit](https://rdkit.org) — Cheminformatics toolkit
- [FastAPI](https://fastapi.tiangolo.com) — Web framework
- [ONNX Runtime](https://onnxruntime.ai) — ML inference
- [NGL Viewer](https://nglviewer.org) — 3D molecule rendering

---

**Built with Python, RDKit, and FastAPI. Self-hosted. No data lock-in.**

