# Q-Mol Upgrade Recommendations

**Date:** 2026-06-29  
**App:** Q-Mol Dataset Factory & Molecular Informatics SaaS  
**Version:** 1.2.0 (API) / 1.0.0 (package)  
**Lines of Code:** ~1,800 (api.py) + ~50 modules in src/ + ~1,000 (CLI) + ~1,200 (landing)

---

## Executive Summary

Q-Mol is an ambitious dual-product platform (dataset factory + SaaS API) with a strong RDKit compute core, sensible API key gating, Stripe billing, and multi-channel distribution (HuggingFace, Kaggle, Gumroad). The architecture is pragmatic for a solo/early-stage build, but several critical bottlenecks will block growth past ~100 concurrent users or ~10k molecules/day. The biggest opportunities are: **(1) replacing SQLite with PostgreSQL + Redis**, **(2) implementing a real job queue**, **(3) adding ML/AI prediction models**, **(4) building a proper React/Vue dashboard**, and **(5) implementing the quantum VQE tier** that the branding promises.

| Priority | Category | Impact | Effort |
|----------|----------|--------|--------|
| P0 | Database & Caching | Blocks all scaling | Medium |
| P0 | Async Job Queue | Blocks large-batch UX | Medium |
| P1 | ML Property Prediction | 10x product value | High |
| P1 | React/Vue Dashboard | Required for enterprise | High |
| P1 | Vector Search (pgvector) | Similarity at scale | Medium |
| P2 | Quantum VQE Implementation | Fulfills brand promise | High |
| P2 | Kubernetes / Helm | Production deployment | Medium |
| P3 | Mobile App Completion | Channel expansion | High |
| P3 | Graph Database (Neo4j) | Retrosynthesis power | High |

---

## P0 — Critical (Do These First)

### 1. Replace SQLite with PostgreSQL + Connection Pooling

**Current State:** All data lives in SQLite (`data/qmol.sqlite`, `data/keys.sqlite`, `data/jobs.sqlite`). Every module opens/closes its own connection. `keys.py` notes this is "the obvious first bottleneck if scaled."

**Problem:** SQLite locks the entire DB on write. At ~50 concurrent API requests, writers will queue and latency will spike to seconds. It also prevents horizontal scaling (multiple API containers can't share a SQLite file reliably over network storage).

**Upgrade Path:**

```python
# Add to requirements.txt
asyncpg>=0.29
sqlalchemy[asyncio]>=2.0
alembic>=1.13

# In config.py, add:
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/qmol")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
```

**Migration Steps:**
1. Add SQLAlchemy 2.0 async models mirroring the current schema
2. Use Alembic for migrations (critical for zero-downtime deploys)
3. Replace `keys._connect()` with an async SQLAlchemy session pool
4. Update `storage.py`, `jobs.py`, `teams.py` to use the shared pool
5. Keep SQLite as a **fallback mode** for local dev / single-machine workers

**Why not just `sqlite` with WAL?** WAL helps reads but still single-writer. You need PostgreSQL for concurrent writes and connection pooling.

---

### 2. Add Redis for Caching, Rate Limits, and Session Store

**Current State:** Rate limits are in-memory token buckets (`ratelimit.py`). Result cache is in-memory (`cache.py`). These are per-process, so scaling to 2+ API containers breaks quota enforcement.

**Upgrade:**

```python
# redis_client.py
import redis.asyncio as redis
from config import REDIS_URL

redis_pool = redis.from_url(REDIS_URL, decode_responses=True)
```

| Use Case | Current | Upgrade |
|----------|---------|---------|
| Rate limit | `dict` in memory | Redis `ZADD` with sliding window |
| Result cache | `dict` keyed by InChIKey | Redis `GET/SETEX` with TTL (24h) |
| API key lookup | SQLite query every request | Redis `HGET` with LRU fallback |
| Async job status | SQLite poll | Redis `PUBLISH` / `SUBSCRIBE` + SSE |
| Admin dashboard metrics | SQLite aggregation | Redis time-series + daily rollup |

**Implementation for rate limits:**

```python
# src/ratelimit.py — Redis-backed sliding window
import redis.asyncio as redis
from config import REDIS_URL

async def check(key: str, max_requests: int, window_seconds: int) -> bool:
    r = redis.from_url(REDIS_URL)
    now = time.time()
    window_start = now - window_seconds
    
    pipe = r.pipeline()
    pipe.zremrangebyscore(key, 0, window_start)
    pipe.zcard(key)
    pipe.zadd(key, {str(now): now})
    pipe.expire(key, window_seconds)
    _, current_count, _, _ = await pipe.execute()
    
    return current_count < max_requests
```

---

### 3. Proper Async Job Queue (Celery / RQ / Arq)

**Current State:** `jobs.py` stores jobs in SQLite and runs them... somewhere? The job runner appears to be missing or embedded in the API process. Large batches block the HTTP response or require polling.

**Upgrade:** Use **Celery** with Redis broker or **Arq** (async-native, fits FastAPI well) for background jobs.

```python
# arq example (better for async FastAPI)
# worker.py
from arq import create_pool
from arq.connections import RedisSettings

async def compute_job(ctx, smiles: list[str], job_id: str):
    # runs in a separate worker process
    results = [compute_molecule(cid=-i, smiles=s) for i, s in enumerate(smiles)]
    await store_results(job_id, results)

# api.py
@app.post("/jobs")
async def create_job(in: JobIn, key: str = Header(...)):
    job = await redis.enqueue_job('compute_job', in.smiles, job_id=uuid4())
    return {"job_id": job.job_id, "status": "queued"}
```

**Benefits:**
- Large batches (50k SMILES) don't time out HTTP connections
- API containers stay lightweight; heavy compute runs on worker nodes
- Can scale workers independently (K8s HPA on CPU)
- Job retries, dead-letter queues, monitoring out of the box

---

### 4. Add Pydantic v2 + Strict Input Validation

**Current State:** `api.py` uses Pydantic v1 patterns (`BaseModel` with `Field`). Pydantic v2 is ~5x faster on validation and has better JSON schema generation.

**Upgrade:** Bump to `pydantic>=2.0` and `fastapi>=0.110` (already satisfied). Update models to use `ConfigDict` and `field_validator` where needed. This is mostly a search-replace but improves throughput measurably.

---

## P1 — High Value (Do These Next)

### 5. ML-Based Property Prediction (Replace Heuristics)

**Current State:** `predict.py` uses rule-based ADMET heuristics (logS from simple descriptors, BBB from MW/logP thresholds, hERG from PAINS-like filters). These are fast but inaccurate. The "quantum-verified" branding is aspirational — PySCF is optional and VQE is unimplemented.

**Upgrade:** Add a **model serving tier** alongside the FastAPI app. Options:

**Option A: OnnxRuntime (recommended)**
- Convert pre-trained chemprop/RDKit models to ONNX
- Run inference in the same process (fast, no network hop)
- Models: chemprop for solubility, hERG, BBB; DeepDL for toxicity

```python
# src/predict_ml.py
import onnxruntime as ort
import numpy as np
from rdkit import Chem
from rdkit.Chem import AllChem

class MLPredictor:
    def __init__(self, model_path: str):
        self.sess = ort.InferenceSession(model_path)
    
    def predict(self, smiles: str) -> dict:
        mol = Chem.MolFromSmiles(smiles)
        fp = AllChem.GetMorganFingerprintAsBitVect(mol, 2, 2048)
        arr = np.array(fp, dtype=np.float32).reshape(1, -1)
        logS, bbb, hERG = self.sess.run(None, {"input": arr})
        return {"logS": float(logS), "bbb": float(bbb), "hERG": float(hERG)}
```

**Option B: Separate Model Service**
- Triton Inference Server or BentoML for GPU inference
- Call via HTTP from FastAPI (adds ~20ms latency, scales independently)
- Good for large transformers (ChemBERTa, MolFormer)

**Models to add:**
| Property | Model | Expected R² vs exp. |
|----------|-------|---------------------|
| Aqueous solubility (logS) | ESOL + chemprop ensemble | 0.85–0.90 |
| Blood-brain barrier | MoleculeNet BBB benchmark | 0.80–0.88 |
| hERG inhibition | DeepDL / RNN-hERG | 0.82–0.91 |
| CYP450 inhibition | DeepDL multi-task | 0.75–0.85 |
| Human plasma protein binding | chemprop regression | 0.70–0.80 |
| Ames mutagenicity | DTU / MoleculeNet | 0.80–0.88 |
| Synthetic accessibility (SAscore) | Already exists via RDKit | — |

**Business Impact:** Enterprise pharma buyers won't pay for heuristic predictions. ML models with >0.80 R² are table stakes for a paid ADMET API.

---

### 6. Vector Search with pgvector (Similarity at Scale)

**Current State:** `similarity.py` searches over the SQLite dataset using RDKit fingerprints loaded into memory. This works for ~100k molecules but fails at 1M+.

**Upgrade:** Store ECFP4 fingerprints as `bit(2048)` or `vector(512)` in PostgreSQL with `pgvector` extension, or use a dedicated vector DB.

```sql
-- PostgreSQL + pgvector
CREATE EXTENSION IF NOT EXISTS vector;
CREATE TABLE molecule_fps (
    cid BIGINT PRIMARY KEY,
    smiles TEXT,
    fp_bit bit(2048),
    fp_vec vector(512)  -- dimensionality-reduced for L2/ivfflat
);
CREATE INDEX ON molecule_fps USING ivfflat (fp_vec vector_l2_ops);
```

```python
# FastAPI endpoint
@app.post("/similarity")
async def similarity_search(query: str, top_k: int = 20):
    mol = Chem.MolFromSmiles(query)
    fp = AllChem.GetMorganFingerprintAsBitVect(mol, 2, 2048)
    # Convert to vector, search
    vec = fp_to_vec(fp)  # e.g., PCA or raw float bits
    rows = await db.fetch(
        "SELECT cid, smiles, fp_vec <-> $1 AS dist FROM molecule_fps ORDER BY dist LIMIT $2",
        vec, top_k
    )
    return [{"cid": r["cid"], "similarity": 1 - r["dist"]} for r in rows]
```

**Alternative:** Use **Milvus** or **Weaviate** if you need billion-scale similarity with hybrid search (SMILES + properties).

---

### 7. React/Vue Dashboard (Replace Static HTML)

**Current State:** `landing/*.html` are static pages with no real interactivity. `dashboard.html` and `portal.html` are likely basic forms. The admin page is static.

**Upgrade:** Build a **single-page application (SPA)** with:
- **React 18 + TypeScript + Vite** (fastest dev experience)
- **TanStack Query** for server state (caching, refetching, pagination)
- **Plotly.js or Nivo** for molecular visualization and charts
- **MUI or shadcn/ui** for component library

**Pages to build:**
| Page | Features |
|------|----------|
| `/app` (main dashboard) | SMILES input, batch upload (CSV/SDF), results table with export |
| `/app/jobs` | Async job queue: submit, monitor, cancel, download |
| `/app/usage` | Quota meter, usage history, invoice list |
| `/app/teams` | Member management, quota sharing, role assignments |
| `/app/admin` | Key provisioning, metrics, revenue chart, health status |
| `/app/molecule/{id}` | Full property card, 2D/3D viewer, similarity search |

**3D Molecule Viewer:** Use **3Dmol.js** or **RDKit's MiniMol** (if available) for browser-side rendering.

```tsx
// Example: MoleculeCard.tsx
import { useQuery } from '@tanstack/react-query';

export function MoleculeCard({ smiles }: { smiles: string }) {
  const { data } = useQuery({
    queryKey: ['compute', smiles],
    queryFn: () => api.compute(smiles),
  });
  
  return (
    <div className="card">
      <div className="smiles">{smiles}</div>
      <div className="props">
        <span>MW: {data?.mw}</span>
        <span>logP: {data?.logp}</span>
        <span>QED: {data?.qed}</span>
      </div>
      <MoleculeViewer smiles={smiles} />
    </div>
  );
}
```

**Monetization Integration:** Embed the Stripe Checkout in the dashboard so users can upgrade tiers without leaving the app.

---

### 8. OpenAPI Client Generation & SDKs

**Current State:** The API has `openapi.json` but no published client SDKs. Developers must hand-write `curl` or `requests` calls.

**Upgrade:** Use **OpenAPI Generator** to auto-publish:
- `qmol-python` (already have `qmol_client.py`, but make it pip-installable)
- `qmol-typescript` (for the React dashboard)
- `qmol-r` (for bioinformatics researchers)
- `qmol-java` (for enterprise pharma stacks)

```yaml
# .github/workflows/sdk-publish.yml
- name: Generate Python SDK
  run: |
    docker run --rm -v $(pwd):/local openapitools/openapi-generator-cli generate \
      -i /local/landing/openapi.json \
      -g python -o /local/sdks/python
- name: Publish to PyPI
  run: cd sdks/python && pip install build twine && python -m build && twine upload dist/*
```

---

### 9. Add WebSocket / Server-Sent Events for Real-Time Jobs

**Current State:** Users poll `/jobs/{id}` for async job status. This is inefficient and slow-UX.

**Upgrade:** Add SSE endpoint for job progress streaming.

```python
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
import asyncio

@app.get("/jobs/{job_id}/stream")
async def job_stream(job_id: str, key: str = Header(...)):
    async def event_generator():
        while True:
            status = await get_job_status(job_id)
            yield f"data: {json.dumps(status)}\n\n"
            if status["done"]:
                break
            await asyncio.sleep(1)
    
    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

---

### 10. Implement Proper API Versioning

**Current State:** Version is hardcoded as `1.2.0` in `api.py` but no URL path versioning.

**Upgrade:** Add `/v1/` prefix to all routes. This lets you ship breaking changes in `/v2/` without breaking existing customers.

```python
app = FastAPI(title="Q-Mol API", version="2.0.0")
v1 = APIRouter(prefix="/v1")

@v1.post("/compute")
async def compute_v1(...): ...

app.include_router(v1)
```

---

## P2 — Strategic (Do These for Competitive Moat)

### 11. Implement the Quantum VQE Tier (Fulfilling the Brand Promise)

**Current State:** `src/compute.py` has `HAS_PYQPANDA` flag but `_run_vqe_pyqpanda` is not implemented. The "quantum-verified" claim is unsupported.

**Upgrade:** Implement a real VQE loop using **pyQPanda** or **Qiskit**.

```python
# src/compute.py
from qiskit import QuantumCircuit
from qiskit.primitives import Estimator
from qiskit_nature.second_q.drivers import PySCFDriver
from qiskit_nature.second_q.mappers import JordanWignerMapper

def _run_vqe_qiskit(mol, basis: str, max_qubits: int = 12):
    """Run VQE for molecules up to max_qubits."""
    from qiskit_algorithms import VQE
    from qiskit_algorithms.optimizers import SLSQP
    from qiskit_nature.second_q.circuit.library import UCCSD
    from qiskit_nature.second_q.hamiltonians import ElectronicStructureProblem
    
    driver = PySCFDriver(atom=mol_to_xyz(mol), basis=basis)
    problem = driver.run()
    
    num_spin_orbitals = problem.num_spin_orbitals
    if num_spin_orbitals > max_qubits:
        return {"error": "Too many qubits for VQE"}
    
    mapper = JordanWignerMapper()
    hamiltonian = mapper.map(problem.hamiltonian.second_q_op())
    ansatz = UCCSD(num_spin_orbitals, problem.num_particles, mapper)
    
    estimator = Estimator()
    vqe = VQE(estimator, ansatz, SLSQP())
    result = vqe.compute_minimum_eigenvalue(hamiltonian)
    
    return {
        "energy_hartree": result.eigenvalue.real,
        "num_qubits": hamiltonian.num_qubits,
        "method": "VQE-UCCSD",
        "quantum_provenance": True,
    }
```

**Business Note:** True quantum chemistry is still slower and less accurate than classical CCSD for most molecules. The value is **provenance** and **marketing** — pharma companies auditing AI-generated data need "quantum" in the audit trail. You should:
1. Run classical CCSD as the ground truth
2. Run VQE as a "signature" or "stamp" on the result
3. Store the quantum circuit hash as a certificate of provenance

**Quantum Cloud Integration:** If you don't have quantum hardware, partner with **IBM Quantum** or **AWS Braket** and run VQE on their simulators / QPUs. Charge 10x for "quantum-certified" molecules.

---

### 12. Add GPU-Accelerated Conformer Generation

**Current State:** `conformers.py` uses RDKit's MMFF, which is CPU-only and slow for >50 conformers.

**Upgrade:** Add **Open Babel** or **TorchANI** (PyTorch + ANI neural network potential) for GPU-accelerated geometry optimization. This is 10–100x faster for large batches.

```python
# Optional dependency: torchani
import torch
import torchani

def optimize_conformer_gpu(mol: Chem.Mol) -> dict:
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model = torchani.models.ANI2x(periodic_table_index=True).to(device)
    # ...convert RDKit coords to torch tensor, run optimization...
```

---

### 13. Kubernetes + Helm Chart for Production

**Current State:** `Dockerfile` and `docker-compose.yml` exist. `render.yaml` suggests Render.com deployment. No K8s config.

**Upgrade:** Add a Helm chart for production deployment on any cloud provider.

```yaml
# helm/qmol/values.yaml
replicaCount:
  api: 3
  worker: 5

image:
  repository: ghcr.io/yourname/qmol
  tag: latest

resources:
  api:
    requests: {cpu: 500m, memory: 512Mi}
    limits: {cpu: 2000m, memory: 2Gi}
  worker:
    requests: {cpu: 1000m, memory: 2Gi}
    limits: {cpu: 4000m, memory: 8Gi}

autoscaling:
  api:
    enabled: true
    minReplicas: 2
    maxReplicas: 20
    targetCPUUtilizationPercentage: 70

env:
  DATABASE_URL: "postgresql://..."
  REDIS_URL: "redis://..."
```

**Add:**
- **Prometheus + Grafana** monitoring (already have `prom.py` metrics, but need a dashboard)
- **Loki** for log aggregation
- **Cert-manager** for TLS
- **Istio/Linkerd** for service mesh (if you add microservices later)

---

### 14. Multi-Region Deployment + CDN

**Current State:** Single Render.com instance (US-based).

**Upgrade:** Deploy to 2+ regions (US East, EU West, APAC) with:
- **Cloudflare** or **AWS CloudFront** in front for static assets and DDoS protection
- **Geo-routing** to the nearest API instance
- **EU data residency** for GDPR compliance (see Compliance section)

---

### 15. Graph Database for Retrosynthesis (Neo4j)

**Current State:** `retro.py` exists but likely implements simple SMARTS-based retrosynthesis. Real retrosynthesis needs reaction databases and graph traversal.

**Upgrade:** Load **Reaxys** or **USPTO** reaction data into **Neo4j**.

```cypher
// Neo4j schema
CREATE (m1:Molecule {smiles: 'CCO', inchikey: '...'})
CREATE (m2:Molecule {smiles: 'CC(=O)O', inchikey: '...'})
CREATE (r:Reaction {name: 'Ester hydrolysis', yield: 0.85})
CREATE (m1)-[:PRODUCT_OF {stoichiometry: 1}]->(r)
CREATE (r)-[:REQUIRES {stoichiometry: 1}]->(m2)
```

Add endpoint: `POST /retro/graph` that does a BFS from target molecule to purchasable precursors, ranking routes by cost and yield.

**Business Impact:** Retrosynthesis is a top-3 use case for medicinal chemists. A working API here is worth $500–$2,000/month per seat.

---

## P3 — Future / Nice-to-Have

### 16. Complete the Flutter Mobile App

**Current State:** `mobile/` has a `pubspec.yaml` with `in_app_purchase` configured but no actual Dart source reviewed. It's essentially a skeleton.

**Upgrade:** Build out the mobile app with:
- **SMILES input** (text + camera using OCR for chemical structures)
- **Batch processing** (upload CSV from phone storage)
- **Offline mode** (cache results, queue jobs when reconnecting)
- **In-app purchases** (Google Play / Apple App Store for API key tiers)
- **Push notifications** (job completion alerts)
- **Molecule sketcher** (integrate **Ketcher** or **ChemDoodle** web view)

**Monetization:** Mobile users are often field chemists. Sell them a "Field Chemist" tier with offline batch processing and priority queue.

---

### 17. Automated Patent / Literature Prior Art Search

**Current State:** Not implemented.

**Upgrade:** Add a `/prior-art` endpoint that:
1. Takes a target SMILES / scaffold
2. Searches **SureChEMBL**, **PatentsView**, **Google Patents** API
3. Returns patents with similar molecules, ranked by structural similarity
4. Highlights freedom-to-operate risks

**Integration:** Use `kimi_search_v2` or a dedicated patent API (e.g., **IFI CLAIMS**).

---

### 18. Synthetic Accessibility with Route Scoring

**Current State:** `predict.py` has a basic SA score from RDKit.

**Upgrade:** Integrate **AiZynthFinder** or **ASKCOS** (open-source retrosynthesis engines) for full route planning with reagent costs, step counts, and commercial availability.

```python
# aizynthfinder integration (optional dependency)
from aizynthfinder.aizynthfinder import AiZynthFinder
finder = AiZynthFinder()
finder.target_smiles = "your_target"
finder.tree_search()
routes = finder.routes
```

---

### 19. Data Marketplace API (AWS Data Exchange)

**Current State:** Mentioned in README but not implemented.

**Upgrade:** Once you hit >10k rows, list on **AWS Data Exchange**:
1. Create a data product with Parquet/CSV/JSONL variants
2. Auto-update via API on every snapshot
3. Charge $0.01–$0.10 per molecule-record (enterprise pricing)

---

### 20. Custom Model Training for Enterprise Clients

**Current State:** Not implemented.

**Upgrade:** Offer a **private model training** service:
- Client uploads proprietary assay data (IC50, solubility, etc.)
- Q-Mol trains a custom chemprop model on their data + public data
- Model is deployed as a private endpoint (`/predict/custom/{client_id}`)
- Charge $5k–$50k setup + $0.01/prediction

This is the highest-margin tier and justifies enterprise contracts.

---

## DevOps & Quality Improvements

### 21. Comprehensive Test Coverage

**Current State:** 15 pytest files, but many call real RDKit embedding and PubChem (slow, flaky).

**Upgrade:**
- Use **pytest-vcr** or **responses** to mock PubChem HTTP calls
- Use **sqlite3** `:memory:` for unit tests; use **testcontainers** for PostgreSQL integration tests
- Add **property-based testing** with Hypothesis for SMILES parsing edge cases
- Add **load testing** with Locust or k6:

```python
# locustfile.py
from locust import HttpUser, task

class QMolUser(HttpUser):
    @task
    def compute(self):
        self.client.post("/v1/compute", json={"smiles": ["CCO"]})
```

**Target:** 80% line coverage, <5 min test suite, load tests at 2x expected peak traffic.

---

### 22. CI/CD Pipeline Improvements

**Current State:** `.github/workflows/ci.yml` runs pytest → dump OpenAPI → docker build → smoke test.

**Upgrade:**
- Add **security scanning** (`safety`, `bandit`, `trivy` for Docker images)
- Add **type checking** (`mypy --strict` or `pyright`)
- Add **linting** (`ruff` instead of `flake8` — it's 100x faster)
- Add **auto-formatting** (`black` or `ruff format`)
- Add **pre-commit hooks** so developers can't push broken code
- Add **semantic release** (auto-bump version from commit messages, auto-generate changelog)
- Add **multi-arch Docker builds** (`linux/amd64`, `linux/arm64`) for Apple Silicon and Graviton

```yaml
# .github/workflows/ci.yml (additions)
- name: Security scan
  uses: aquasecurity/trivy-action@master
  with:
    image-ref: qmol-api:latest
    format: 'sarif'
    output: 'trivy-results.sarif'
```

---

### 23. Structured Logging & Observability

**Current State:** Uses `logging.basicConfig` with simple format. `audit.py` exists but is fire-and-forget.

**Upgrade:**
- Use **structlog** for JSON-structured logs
- Send logs to **Datadog / Logtail / Grafana Loki**
- Add **OpenTelemetry** tracing for every request (trace ID propagates through middleware → DB → cache)
- Add **Sentry** for error tracking and performance monitoring

```python
# middleware with OpenTelemetry
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

tracer = trace.get_tracer(__name__)
FastAPIInstrumentor.instrument_app(app)
```

---

### 24. Database Backups & Disaster Recovery

**Current State:** SQLite files in `data/`. No automated backup strategy mentioned.

**Upgrade:**
- PostgreSQL: **pg_dump** daily to S3, **Point-in-Time Recovery** (PITR) via WAL archiving
- SQLite (for worker): **litestream** (replicates SQLite to S3 in real-time)
- Define **RPO/RTO** targets: RPO < 1 hour, RTO < 4 hours

---

## Compliance & Security

### 25. GDPR / SOC 2 / HIPAA Readiness

**Current State:** `privacy.html` exists but no formal compliance framework.

**Upgrade:**
- **GDPR:** Add data deletion endpoint (`DELETE /account` — hard delete or anonymize)
- **SOC 2:** Implement access logging, encryption at rest (already have HTTPS), annual penetration testing
- **HIPAA:** If you plan to handle clinical data, add BAA support, encryption in transit with TLS 1.3, audit trails for 7 years
- **Add a security.txt** and vulnerability disclosure policy
- **Add rate-limiting by IP** for unauthenticated endpoints (DDoS protection)
- **Add API key rotation** (already have `rotate.py`, but add automatic expiry reminders)
- **Hash API keys with bcrypt** instead of storing them plaintext (check `keys.py` — currently keys may be stored as-is)

---

## Quick Wins (Can Ship This Week)

These require minimal effort but improve UX and credibility immediately:

1. **Fix dead code** in `api.py` lines 457–464 (unreachable block after `return`)
2. **Add `/health` and `/ready` probes** separately — `/ready` checks DB + Redis connectivity
3. **Add `Retry-After` header** on `429` responses (currently mentioned in docs but may not be implemented)
4. **Add OpenAPI examples** to every Pydantic model for better Swagger docs
5. **Add `x-request-id` middleware** for tracing support
6. **Compress API responses** with `gzip` or `brotli` (FastAPI has `GZipMiddleware`)
7. **Add API response caching headers** for immutable endpoints (`/descriptors/names`)
8. **Add a `CHANGELOG.md`** and start semantic versioning properly
9. **Add `.env.example` comments** explaining every variable
10. **Add a `CONTRIBUTING.md`** for open-source contributors

---

## Recommended Roadmap

| Quarter | Focus | Deliverables |
|---------|-------|--------------|
| **Q3 2026** | Foundation | PostgreSQL + Redis migration, Celery job queue, React dashboard v1, Pydantic v2 upgrade |
| **Q4 2026** | Intelligence | ML models (chemprop), pgvector similarity, GPU conformer gen, API v2 with versioning |
| **Q1 2027** | Scale | K8s + Helm, multi-region, CDN, Triton model serving, enterprise SSO (SAML/OIDC) |
| **Q2 2027** | Moat | VQE quantum tier, Neo4j retrosynthesis, custom model training, AWS Data Exchange |
| **Q3 2027** | Ecosystem | Complete mobile app, SDKs (TypeScript, R, Java), patent search, community marketplace |

---

## Appendix: File-by-File Upgrade Notes

| File | Current | Recommended |
|------|---------|-------------|
| `api.py` | 1,800 lines, Pydantic v1, no versioning | Split into `routers/`, add `/v1/`, Pydantic v2 |
| `config.py` | SQLite-only, sync | Add PostgreSQL + Redis URLs, async support |
| `src/compute.py` | Heuristics + optional PySCF | Add ONNX ML tier, GPU tier, VQE tier |
| `src/storage.py` | SQLite schema | Add SQLAlchemy models, Alembic migrations |
| `src/keys.py` | SQLite, plaintext keys? | PostgreSQL + bcrypt hashing + Redis cache |
| `src/ratelimit.py` | In-memory dict | Redis sliding window |
| `src/cache.py` | In-memory dict | Redis with TTL |
| `src/jobs.py` | SQLite store | Celery/Arq with Redis broker |
| `worker.py` | Single-threaded loop | Distributed worker with Celery + K8s HPA |
| `landing/*.html` | Static HTML | React SPA with Vite |
| `mobile/` | Skeleton Flutter app | Full app with Ketcher, IAP, offline mode |
| `Dockerfile` | Single-stage, no healthcheck | Multi-stage, distroless, healthcheck |
| `docker-compose.yml` | Basic | Add PostgreSQL, Redis, worker services |
| `.github/workflows/ci.yml` | pytest + docker | Add security scan, type check, semantic release |
| `stripe_webhook.py` | Basic delivery | Add idempotency keys, webhook retry logic, event archive |

---

*Document generated by analysis of the Q-Mol codebase. For implementation, prioritize P0 items in order, then P1. Each section can be delegated to a specialist sub-agent for parallel execution.*
