# Q-Mol: Molecular Informatics API

[![API Version](https://img.shields.io/badge/api-v2.0.0-blue)](https://api.qmol.app/v1/health)
[![License](https://img.shields.io/badge/license-Apache%202.0-green)](LICENSE)

Q-Mol is a production-grade molecular informatics platform for drug discovery research. 
Compute molecular descriptors, predict ADMET properties, design novel molecules, and analyze 
drug-target interactions — all via a modern REST API.

## Quick Start

```bash
# Get a free API key
curl -X POST https://api.qmol.app/v1/signup \
  -H "Content-Type: application/json" \
  -d '{"email": "you@example.com"}'

# Compute molecular properties
curl -X POST https://api.qmol.app/v1/compute \
  -H "x-api-key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"smiles": ["CCO"]}'

# Predict ADMET properties
curl -X POST https://api.qmol.app/v1/predict/ml \
  -H "x-api-key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"smiles": ["c1ccccc1"]}'
```

## Features

- **50+ Molecular Descriptors**: MW, logP, TPSA, QED, Lipinski rules, and more
- **ML ADMET Predictions**: logS, BBB, hERG, CYP450, PPB, Ames (validated models)
- **Drug-Target Interactions**: Screen against EGFR, AChE, BACE1
- **De Novo Design**: Generate novel molecules and optimize leads
- **Natural Language Queries**: "Find molecules like aspirin with good BBB"
- **3D Conformers**: Generate and export PDB, MOL2, CIF
- **Batch Processing**: Process up to 50,000 molecules via async jobs
- **Real-time Progress**: SSE streaming for job monitoring
- **Team Collaboration**: Share molecule collections
- **Export Formats**: CSV, SDF, Parquet, PDB, FDA report

## Pricing

| Tier | Price | Quota | Features |
|------|-------|-------|----------|
| Free | $0 | 500/mo | Basic descriptors |
| Trial | $0 | 10,000 | 7 days, all features |
| Research | $20/mo ($180/yr) | 10,000/mo | All descriptors + ML predictions |
| Commercial | $50/mo ($450/yr) | 50,000/mo | Priority queue + team sharing |
| Enterprise | Custom | Unlimited | SSO, custom models, SLA, on-premise |

[Start free trial](https://qmol.app) | [View API docs](https://qmol.app/docs) | [Enterprise inquiry](https://qmol.app/enterprise)

## Self-Hosting

```bash
git clone https://github.com/PhotonBounce/Qmol2.git
cd Qmol2

# Option 1: Docker Compose (recommended for development)
docker-compose up --build

# Option 2: Kubernetes (production)
helm install qmol ./helm/qmol
```

## Documentation

- [API Reference](docs/API.md)
- [Migration Guide](docs/MIGRATION.md)
- [Security Policy](docs/SECURITY.md)
- [Contributing](docs/CONTRIBUTING.md)
- [Changelog](CHANGELOG.md)

## Support

- Email: support@qmol.app
- GitHub Issues: [PhotonBounce/Qmol2](https://github.com/PhotonBounce/Qmol2/issues)
- Enterprise: [Contact Sales](https://qmol.app/enterprise)

## License

Apache 2.0. See [LICENSE](LICENSE).
