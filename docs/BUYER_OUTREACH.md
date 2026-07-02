# Where to Find Established Molecular Dataset Buyers

## The Hard Truth

You have **33 molecules**. No pharma company, biotech, or research lab will buy 33 molecules. The minimum viable dataset is **1,000 molecules**. Attractive datasets are **5,000-50,000**. 

**Your first job is not finding buyers. Your first job is harvesting 1,000+ molecules.**

---

## Phase 1: Build Inventory (Do This First)

Run the SaaS harvester for a few hours to get to 1,000+ molecules. Or use the bulk script below.

```powershell
# Fast bulk harvest using local server (no PubChem rate limits)
cd D:\Qmol-3
D:\qmol\.venv\Scripts\python -m uvicorn api:app --host 0.0.0.0 --port 8000

# In another terminal, run 20 batch loops
for ($i=1; $i -le 20; $i++) {
    D:\qmol\.venv\Scripts\python D:\Qmol-3\scripts\harvest_self.py
    Start-Sleep -Seconds 60
}
```

**Target: 1,000 molecules before you contact anyone.**

---

## Phase 2: Where the Buyers Actually Are

### 1. AI Drug Discovery Startups (Best Target — They NEED Data)

These companies train ML models on molecular datasets. They buy data constantly.

| Company | What They Need | How to Contact |
|---------|---------------|----------------|
| **Recursion** (recursion.com) | Large labeled datasets for phenomics | LinkedIn: Recursion Pharma + CEO Chris Gibson |
| **Insitro** (insitro.com) | ML-ready molecular features | LinkedIn: Daphne Koller + team |
| **Exscientia** (exscientia.com) | AI-designed molecules | Business development email on site |
| **BenevolentAI** (benevolent.com) | Knowledge graph + molecular data | LinkedIn outreach |
| **Atomwise** (atomwise.com) | Virtual screening libraries | Contact form + LinkedIn |
| **Valo Health** (valohealth.com) | Integrated datasets | LinkedIn |
| **Schrödinger** (schrodinger.com) | Docking/scoring datasets | Business development |
| **Relay Therapeutics** (relaytx.com) | Protein-motion datasets | LinkedIn |
| **Isomorphic Labs** (isomorphiclabs.com) | DeepMind spinout — massive data appetite | LinkedIn |
| **Generate Biomedicines** (generatebiomedicines.com) | Generative AI training data | LinkedIn |

**Approach:** Send LinkedIn connection request with: *"Hi [Name], I've built a curated molecular dataset of [N] drug-like molecules with full ADMET descriptors (logP, TPSA, QED, Lipinski, PAINS). Would you be interested in a preview for your ML pipeline?"*

### 2. Contract Research Organizations (CROs)

CROs run virtual screening campaigns for pharma clients. They need diverse compound libraries.

| Company | Focus | Contact Strategy |
|---------|-------|------------------|
| **WuXi AppTec** | China's largest CRO | LinkedIn + email |
| **Evotec** | European CRO, AI-heavy | Business development |
| **Charles River** | Preclinical CRO | LinkedIn |
| **Crown Bioscience** | Oncology-focused | LinkedIn |
| **Syngene** | Indian CRO | LinkedIn |
| **Eurofins** | Analytical + screening | LinkedIn |
| **Sai Life Sciences** | Indian CRO | LinkedIn |
| **Jubilant Biosys** | Indian CRO | LinkedIn |

**Approach:** Email their business development with: *"We're offering a curated virtual screening library of [N] Lipinski-compliant molecules with PAINS filtering. Available as CSV/SDF. Can we send a sample?"*

### 3. Academic Labs (Buy with Grant Money)

University labs have NIH/NSF funding and regularly buy compound libraries for virtual screening.

**Where to find them:**
- **ResearchGate** — Post your dataset with a "for sale" note
- **Academic Twitter/X** — Search "virtual screening" + "compound library"
- **Google Scholar** — Search "virtual screening" + "molecular docking" + 2024/2025, email the first authors
- **ChemRxiv** — Preprint server, authors are active researchers
- **BioRxiv** — Same

**Search queries:**
- Google Scholar: `virtual screening + "molecular library" + 2024`
- Twitter/X: `virtual screening compound library`
- Reddit: r/bioinformatics, r/drugdiscovery, r/chemistry

### 4. Data Marketplaces (List Once, Buyers Come)

| Platform | How | Audience |
|----------|-----|----------|
| **Kaggle** | Upload CSV as dataset | Data scientists, ML engineers |
| **Data.world** | Public dataset listing | Enterprise data buyers |
| **AWS Data Exchange** | List as commercial product | AWS customers (enterprises) |
| **Google Dataset Search** | Index your CSV | Academic researchers |
| **Zenodo** | DOI + citable | Academic citations (free exposure) |
| **Figshare** | Academic data sharing | University researchers |
| **MolPort** | Chemical marketplace | Pharma chemists |
| **Mcule** | Chemical database | Virtual screening community |
| **Enamine** | Compound library vendor | Drug discovery labs |
| **ChemSpace** | Chemical marketplace | Hit discovery teams |

**The most important: List on Kaggle and Zenodo.** These get indexed by Google Dataset Search and drive organic traffic forever.

### 5. Cheminformatics Communities (Free Marketing)

| Platform | Action | Expected Result |
|----------|--------|-----------------|
| **RDKit mailing list** | Post: "Curated dataset of [N] molecules with RDKit descriptors for sale" | Direct responses from researchers |
| **Open Babel forum** | Same pitch | Open-source community |
| **CCL.net** | Chemistry computational list | Academic chemists |
| **LinkedIn groups** | "Cheminformatics", "Drug Discovery", "Molecular Modelling" | Connections with buyers |
| **Reddit** | r/drugdiscovery, r/bioinformatics, r/chemistry | Traffic + potential buyers |
| **Hacker News** | "Show HN: I built a molecular dataset marketplace" | Tech-savvy biotech founders |
| **Indie Hackers** | Post about your journey | Bootstrapped founder community |

---

## Phase 3: Ready-to-Use Outreach Templates

### Cold Email Template (Use with Hunter.io or Apollo.io to find emails)

```
Subject: [N] Drug-Like Molecules with ADMET Profiles — Free Preview

Hi [Name],

I'm [Your Name], building Q-Mol — a molecular informatics platform. 

We have a curated dataset of [N] molecules with full descriptors:
- MW, logP, TPSA, QED, HBD, HBA
- Lipinski pass/fail
- PAINS filtering
- RDKit-validated SMILES

Available as CSV/SDF/Parquet. Prices start at $99 for 50 molecules, 
$299 for 1,000, $999 for 10,000.

Can I send you a 10-molecule preview CSV?

Best,
[Your Name]
[Your Website]
[Your LinkedIn]
```

### LinkedIn Connection Message

```
Hi [Name], I've built a curated molecular dataset with full ADMET 
descriptors (QED, logP, TPSA, Lipinski, PAINS). [N] molecules, 
RDKit-validated. Would you be interested in a preview for your 
screening pipeline?
```

### Reddit Post Template

```
Title: [OC] I built a molecular dataset marketplace — sell drug-like molecules to pharma

I built Q-Mol, a platform that harvests molecular data and sells 
curated datasets to pharma/biotech. 

Current datasets:
- 50 High-QED drug candidates ($99)
- 30 CNS-penetrant molecules ($199)
- 25 Kinase scaffolds ($149)
- 40 Natural product fragments ($79)

All include MW, logP, TPSA, QED, HBD, HBA, Lipinski, PAINS.

What's the best way to reach pharma buyers? 

[Link to marketplace]
```

### Hacker News "Show HN" Post

```
Title: Show HN: SaaS molecular harvester that sells datasets to pharma

Built a browser-based tool that harvests molecules from PubChem, 
computes descriptors, and packages them into sellable datasets.

No server needed. No install. Runs in browser. Harvests real 
data from NIH. Creates CSVs. Lists them on a marketplace.

Accepts crypto payments.

Demo: [link]

Would love feedback from anyone in cheminformatics.
```

---

## Phase 4: Fastest Path to First Sale

### Day 1: Harvest
- Run SaaS harvester for 3-4 hours → aim for 1,000 molecules
- Create "High-QED Drug Candidates" dataset
- Export CSV

### Day 2: List
- Upload to Kaggle (free, gets traffic forever)
- Upload to Zenodo (free, gets DOI, looks credible)
- Post on Reddit r/drugdiscovery
- Post on Indie Hackers

### Day 3: Outreach
- LinkedIn: Connect with 20 people at AI drug discovery startups
- Send cold emails to 10 CROs
- Post on RDKit mailing list

### Day 4-7: Follow Up
- Respond to all inquiries
- Send preview CSVs
- Iterate pricing based on feedback

**Expected first sale: 1-4 weeks** with consistent outreach.

---

## Phase 5: Scaling the Pipeline

**What you need to scale:**
- 10,000+ molecules → $999 dataset
- 50,000+ molecules → $2,999 enterprise dataset
- Custom filtering by target → $5,000+ per contract
- Monthly refresh → subscription model

**To get there fast:**
- Run the harvester 24/7 on your PC (disable sleep)
- Ask friends/colleagues to run the harvester too (it costs them nothing)
- Post on Reddit asking users to submit molecules (free tier = free labor)
- Partner with academic labs (they submit molecules, you share revenue)

---

## The Bottom Line

**You don't have buyers yet because you don't have inventory.**

Get to 1,000 molecules. Then start outreach. The buyers exist — you just need to have something worth buying.

**Your next 3 actions:**
1. Start the harvester and let it run for 4 hours
2. Create a dataset when you hit 1,000
3. Send 20 LinkedIn connection requests to people at AI drug discovery companies

---

*Updated: 2026-07-02*
