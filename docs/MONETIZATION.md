# Q-Mol Monetization Strategy & Deployment Guide
# ==============================================
# How Q-Mol earns money while providing free molecular computation tools.
#
# Document version: 2.0.0
# Date: 2026-06-30

## Table of Contents
1. [The Revenue Model](#1-the-revenue-model)
2. [Deployment Options](#2-deployment-options)
3. [Data Harvesting Architecture](#3-data-harvesting-architecture)
4. [Dataset Pricing & Target Markets](#4-dataset-pricing--target-markets)
5. [Go-to-Market Plan](#5-go-to-market-plan)
6. [Technical Setup Steps](#6-technical-setup-steps)

---

## 1. The Revenue Model

Q-Mol operates on a **"freemium data harvesting"** model:

> Users get free cheminformatics tools. We get their molecular data. Over time, the database becomes a sellable asset.

### 1.1 Revenue Streams (Ranked by Priority)

| # | Stream | Price Point | Monthly Potential | Effort |
|---|--------|-------------|-------------------|--------|
| 1 | **API Subscriptions** | $20-500/mo | $2,000-10,000 | Low |
| 2 | **Dataset Sales** | $500-5,000 each | $1,000-15,000 | Medium |
| 3 | **Enterprise Contracts** | $5,000-50,000/yr | $5,000-25,000 | High |
| 4 | **Referral Commissions** | $50-200/signup | $500-2,000 | Low |
| 5 | **Crypto Payments** | Variable | $100-1,000 | Low |

### 1.2 The Value Exchange

**Users get (free tier):**
- 500 SMILES/month of molecular descriptors
- Drug-likeness screening (Lipinski, Veber, PAINS)
- ADMET predictions (logS, hERG, pKa)
- Similarity search, clustering, diversity picking
- SDF/Parquet/CSV exports

**We get (automatically):**
- Every SMILES → stored in harvest database
- Every computed property → indexed and searchable
- Every query → market intelligence (what are people screening for?)
- Over time → sellable datasets for pharma

### 1.3 Why Pharma Will Pay

Pharmaceutical companies spend **$2.6 billion** on average to develop a new drug. They need:

1. **Lead compound libraries** — diverse molecules with good properties
2. **ADMET profiling datasets** — preclinical safety data
3. **SAR (Structure-Activity Relationship) series** — analogs around a scaffold
4. **Virtual screening libraries** — ready-to-screen compound sets
5. **Diversity sets** — non-redundant collections for hit discovery

Q-Mol's harvest database provides ALL of these. Every user query enriches the database.

---

## 2. Deployment Options

### 2.1 Option A: Your PC (Immediate, Free)

**Best for:** Getting started, testing, harvesting while you sleep
**Cost:** $0 + ~$15-30/month electricity
**Setup time:** 15 minutes

Your PC is probably more powerful than any free VPS. A modern PC with 8-16 GB RAM can handle thousands of molecular computations per day.

**Architecture:**
```
User's browser → photon-bounce.com/qmol/ (PHP microsite)
                    ↓ JavaScript fetch
            Cloudflare Tunnel → Your PC (port 8000)
                    ↓
            Q-Mol API (FastAPI + RDKit + SQLite)
                    ↓
            harvest.sqlite (grows over time)
```

**Setup:** See `deploy/CLOUDFLARE_TUNNEL.md` for step-by-step.

**Pros:**
- Zero recurring cost
- Full data control (molecules never leave your hardware)
- Your PC is probably more powerful than free VPSes
- Works through any router (no port forwarding)

**Cons:**
- PC must stay on 24/7 for harvesting
- No redundancy if PC crashes
- Upload bandwidth limited by ISP

**Power optimization:**
```powershell
# Disable sleep (run as admin)
powercfg /change standby-timeout-ac 0
powercfg /change hibernate-timeout-ac 0
# This keeps PC awake even when you leave it
```

### 2.2 Option B: Oracle Cloud Free Tier (24/7 Production)

**Best for:** Always-on production, team use, backup
**Cost:** $0 forever (Always Free tier)
**Setup time:** 30 minutes

Oracle Cloud gives you **24 GB RAM + 4 ARM cores** for free. This is more than enough for Q-Mol.

**Architecture:**
```
User's browser → photon-bounce.com/qmol/ (PHP microsite)
                    ↓ JavaScript fetch
            Oracle Cloud VM (ARM, Ubuntu 22.04)
                    ↓ Docker
            Q-Mol API + Redis + Celery Worker
                    ↓
            Persistent SQLite volume
```

**Setup:** See `deploy/oracle-cloud-init.sh` for automated cloud-init script.

**Steps:**
1. Sign up: https://www.oracle.com/cloud/free/
2. Create VM: Shape = VM.Standard.A1.Flex, 1 OCPU, 6 GB RAM
3. Open ports: 22 (SSH), 8000 (API), 443 (HTTPS)
4. SSH in and run the cloud-init script
5. (Optional) Add Cloudflare Tunnel to get HTTPS without managing certificates

**Pros:**
- 24/7 availability without your PC running
- 24 GB RAM handles large molecules + ML models
- Full Linux environment with root access
- Independent from your ISP

**Cons:**
- Requires signup (email + phone verification)
- ARM architecture (Docker images work fine though)
- Must log in every 30 days to keep "Always Free" status

### 2.3 Option C: Hybrid (PC + Oracle Cloud Backup)

**Best for:** Maximum reliability + data safety
**Cost:** $0 (PC) + $0 (Oracle) = $0

Run Q-Mol on your PC as primary, with Oracle Cloud as a hot backup. If your PC goes down, users still access the API.

**Data sync:**
- Periodically rsync `data/harvest.sqlite` to Oracle Cloud
- Or use SQLite's built-in replication (SQLite RSync or Litestream)

---

## 3. Data Harvesting Architecture

### 3.1 How It Works

Every time a user calls `/compute`, `/predict`, `/screen`, or `/similarity`, Q-Mol automatically stores the molecule and its properties in the harvest database.

```python
# Inside compute_molecule() — happens automatically:
from src import harvest
harvest.ingest(smiles, descriptors, source_endpoint="/compute")
```

The harvest database is a separate SQLite file (`data/harvest.sqlite`) that grows over time. It's independent from the operational database, so it doesn't affect API performance.

### 3.2 What Gets Stored

For every molecule submitted:

| Field | Description | Why Pharma Cares |
|-------|-------------|-----------------|
| `smiles` | Canonical SMILES | Universal identifier |
| `inchikey` | Hashed InChI | Deduplication |
| `mw` | Molecular weight | Oral bioavailability |
| `logp` | Lipophilicity | Blood-brain barrier |
| `tpsa` | Polar surface area | Intestinal absorption |
| `hbd` | Hydrogen bond donors | Drug-likeness |
| `hba` | Hydrogen bond acceptors | Drug-likeness |
| `qed` | Quantitative drug-likeness | Overall quality score |
| `lipinski_pass` | Lipinski's Rule of 5 | Oral drug feasibility |
| `veber_pass` | Veber rules | Oral bioavailability |
| `pains_hit` | PAINS filter | Avoid toxic/artifactual compounds |
| `fsp3` | Fraction sp3 carbons | Synthetic accessibility |
| `source_endpoint` | Which API was used | Market intelligence |
| `submitted_at` | Timestamp | Trend analysis |

### 3.3 Dataset Creation

When you have enough molecules (target: 1,000+), you create curated datasets:

```python
# Example: Create a dataset of high-quality drug candidates
dataset = harvest.create_dataset(
    name="High-QED Drug Candidates",
    description="Molecules with QED >= 0.7, Lipinski pass, no PAINS",
    filter_sql="qed >= 0.7 AND lipinski_pass = 1 AND pains_hit = 0",
    max_molecules=5000,
)
# Returns: dataset_id, price_usd, molecule_count, preview
```

The admin dashboard (`/harvest/stats`) shows:
- Total molecules harvested
- Unique molecules (by InChIKey)
- Drug-likeness distribution
- Source endpoint breakdown
- Last 7 days activity

### 3.4 Market Intelligence

Q-Mol also tracks what users are searching for (anonymized):

```python
# When a user searches for "similarity to aspirin"
harvest.record_market_intelligence(
    endpoint="/similarity",
    query_summary="aspirin-like molecules"
)
```

This tells you what the market is interested in. If 100 people search for "BBB-penetrating molecules", you know there's demand for a CNS drug dataset.

---

## 4. Dataset Pricing & Target Markets

### 4.1 Pricing Tiers

| Dataset Size | Price | Description |
|-------------|-------|-------------|
| < 100 molecules | $99 | Niche target (e.g., kinase inhibitors) |
| 100-1,000 | $299 | Scaffold-focused series |
| 1,000-10,000 | $999 | Diverse virtual screening library |
| 10,000-100,000 | $2,999 | Large-scale lead compound set |
| 100,000+ | $4,999+ | Full diversity library |

### 4.2 Target Buyers

| Buyer Type | What They Need | How to Reach Them |
|------------|----------------|-----------------|
| **Small biotechs** | Lead compounds for a specific target | LinkedIn outreach, biotech forums |
| **CROs (Contract Research)** | Diverse screening libraries | Direct email, industry conferences |
| **Academic labs** | Training datasets for ML models | University mailing lists, GitHub |
| **AI drug discovery startups** | Large labeled datasets | TechCrunch, YC, AngelList |
| **Big pharma** | Pre-validated compound sets | LinkedIn Sales Navigator, RFPs |

### 4.3 Example Sales Pitch

> "We have a curated dataset of 12,000 drug-like molecules with full ADMET profiles (logP, solubility, hERG, pKa). All molecules pass Lipinski's Rule of 5 and have QED > 0.6. No PAINS hits. Ready for virtual screening. Price: $999."

### 4.4 Delivery Format

Datasets are delivered as:
- **CSV** — Universal, loads into Excel/Python/R
- **SDF** — For chemistry software (ChemDraw, Maestro, MOE)
- **Parquet** — For big data/ML pipelines
- **SQLite** — For embedded applications

---

## 5. Go-to-Market Plan

### Phase 1: Bootstrap (Month 1-2) — FREE

**Goal:** Get 100+ users submitting molecules

- Deploy on your PC + Cloudflare Tunnel
- Post on Reddit: r/chemistry, r/drugdiscovery, r/MachineLearning
- Post on LinkedIn: cheminformatics, computational chemistry groups
- Share on Twitter/X: #cheminformatics #drugdiscovery
- Publish on GitHub with README + live demo link
- Answer questions on Stack Overflow / Chemistry Stack Exchange

**Metrics to track:**
- Daily active users
- Molecules submitted per day
- Most popular endpoints
- Geographic distribution

### Phase 2: Monetization (Month 3-6) — PAID

**Goal:** First paying customers + first dataset sale

- Launch paid tiers: $20/month (Research), $50/month (Commercial)
- Add crypto payment option (already built via microsite)
- Create first curated dataset (target: 5,000 molecules)
- Reach out to 50 biotechs with dataset offer
- Publish a blog post: "Building a Molecular Database from Free API Usage"

**Pricing psychology:**
- Free tier: 500 SMILES/month (enough to get hooked)
- Research: $20/month for 10,000 (10x more, 20x cheaper per molecule)
- Commercial: $50/month for 50,000 + team features

### Phase 3: Scale (Month 6-12) — ENTERPRISE

**Goal:** $5,000-10,000/month recurring revenue

- Enterprise tier: $500/month + custom models
- On-premise deployment option
- SLA + dedicated support
- White-label API for CROs
- Partner with AI drug discovery platforms (Atomwise, BenevolentAI)

---

## 6. Technical Setup Steps

### 6.1 Immediate (Today)

```powershell
# 1. Start Q-Mol on your PC
cd D:\Qmol-3
.venv\Scripts\python -m uvicorn api:app --host 0.0.0.0 --port 8000

# 2. Set up Cloudflare Tunnel (see deploy/CLOUDFLARE_TUNNEL.md)
# This gives you: https://api.photon-bounce.com

# 3. Update the microsite to point to the real API
# Edit landing page JS: API_BASE = "https://api.photon-bounce.com/v1"

# 4. Set admin token (secure this!)
# Add to .env: QMOL_ADMIN_TOKEN=your-very-long-random-string

# 5. Disable sleep on your PC
powercfg /change standby-timeout-ac 0
powercfg /change hibernate-timeout-ac 0
```

### 6.2 This Week

- Create a Twitter/X account for Q-Mol
- Write a LinkedIn post introducing the tool
- Share on Reddit r/chemistry with a demo link
- Add Google Analytics or similar to the microsite
- Set up a simple email list (Mailchimp free tier)

### 6.3 This Month

- Target: 50+ users, 5,000+ molecules harvested
- Create first curated dataset
- Start outreach to 20 biotech companies
- Set up Stripe for credit card payments (if you want non-crypto)
- Consider Google Cloud Free Tier as backup

### 6.4 Ongoing (Weekly)

- Check harvest stats: `/harvest/stats` (admin only)
- Export new datasets as they grow
- Monitor API usage and adjust rate limits
- Respond to user feedback on GitHub
- Post updates on social media

---

## 7. Security & Compliance

### 7.1 Data Privacy

- **Anonymize all data:** API keys are hashed before storage. Only first 8 chars kept.
- **No PII:** We don't store user names, emails, or company info in the harvest DB.
- **Aggregate only:** Individual user queries are not sold. Only aggregated datasets.
- **GDPR/CCPA compliant:** Users can request deletion of their data.

### 7.2 Terms of Service

Add this to your signup page:

> "By using Q-Mol, you grant us a non-exclusive, perpetual license to use anonymized molecular data for research and commercial dataset creation. Your identity is never disclosed. You may opt out by contacting support."

### 7.3 Data Retention

- Raw molecules: Kept forever (they're chemical structures, not personal data)
- User queries: Anonymized after 90 days
- API logs: Deleted after 30 days
- Market intelligence: Kept indefinitely (aggregated)

---

## 8. Financial Projections (Conservative)

| Month | Users | Molecules | Revenue | Source |
|-------|-------|-----------|---------|--------|
| 1 | 50 | 5,000 | $0 | Free only |
| 2 | 100 | 15,000 | $0 | Free + referrals |
| 3 | 200 | 40,000 | $200 | 2 paid subscribers |
| 4 | 350 | 80,000 | $500 | 5 paid + 1 dataset sale |
| 5 | 500 | 150,000 | $1,000 | 10 paid + 2 datasets |
| 6 | 800 | 300,000 | $2,500 | 20 paid + 5 datasets |
| 12 | 2,000 | 1,000,000 | $8,000 | 50 paid + 10 datasets + 1 enterprise |

**Year 1 total: ~$50,000**
**Year 2 total: ~$150,000** (with enterprise contracts)

---

## 9. Quick Start Checklist

- [ ] Deploy Q-Mol on your PC (already done!)
- [ ] Set up Cloudflare Tunnel (`deploy/CLOUDFLARE_TUNNEL.md`)
- [ ] Update microsite to point to real API URL
- [ ] Set `QMOL_ADMIN_TOKEN` in `.env`
- [ ] Disable PC sleep mode
- [ ] Post on social media (Reddit, LinkedIn, Twitter)
- [ ] Monitor harvest stats weekly
- [ ] Create first dataset when you hit 1,000 molecules
- [ ] Reach out to 10 biotech companies
- [ ] Set up Stripe or crypto payment processing
- [ ] Consider Oracle Cloud Free Tier for 24/7 backup

---

## 10. Resources

| Document | Purpose |
|----------|---------|
| `deploy/CLOUDFLARE_TUNNEL.md` | PC hosting via Cloudflare |
| `deploy/oracle-cloud-init.sh` | Oracle Cloud automated setup |
| `docs/FREE_HOSTING.md` | All free hosting options ranked |
| `src/harvest.py` | Data harvesting engine |
| `src/routers/v1/harvest.py` | Admin dataset management API |
| `docs/GITHUB_SETUP.md` | GitHub repo setup guide |

---

*Remember: Every molecule submitted is a potential dollar. The database IS the product.*
