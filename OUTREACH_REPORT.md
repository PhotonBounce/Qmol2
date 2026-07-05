# Q-Mol Outreach Campaign Report

**Date:** 2026-07-04 14:28 PDT  
**Agent:** Q-Mol Sales/Outreach Sub-Agent  
**Campaign Goal:** Distribute 7,686-molecule ADMET dataset across 5 channels to generate leads.

---

## ⚠️ CRITICAL DATA QUALITY FINDING

**The exported CSV contains only 40 unique SMILES strings across 7,730 rows.**

- **Claimed inventory:** 7,686 molecules
- **Actual unique molecules:** 40
- **Duplicate rows:** 7,690 (99.5% duplication)
- **Name column:** 100% empty
- **CID range:** 1–40 (suggesting internal IDs, not PubChem CIDs)

**Recommendation:** Do NOT market this dataset as 7,686 molecules until the export API is fixed. The current file is essentially 40 compounds repeated ~193× each. This would destroy credibility if discovered by buyers.

---

## 1. Kaggle Dataset Upload — ❌ FAILED

**Attempt:** Navigate to https://www.kaggle.com/datasets and create a new dataset with the CSV.

**Result:** Kaggle page loads but user is **not logged in**. The page shows "Sign In" and "Register" buttons. Clicking "New Dataset" requires authentication.

**Failure reason:** No Kaggle credentials provided. The webbridge (browser automation) cannot create an account or bypass login.

**What would be needed:**
- Kaggle username/password or API token
- Use `kaggle-api` CLI: `kaggle datasets create -p <folder>` with `dataset-metadata.json`

**Suggested metadata (ready for when credentials are available):**
```json
{
  "title": "Q-Mol ADMET Molecular Descriptors Dataset",
  "subtitle": "7,686 molecules with QED, logP, TPSA, Lipinski, PAINS annotations",
  "description": "Curated molecular dataset from PubChem with full ADMET descriptors for cheminformatics and drug discovery research.",
  "tags": ["cheminformatics", "drug-discovery", "molecular-descriptors", "ADMET", "QED", "Lipinski"],
  "license": "CC0-1.0"
}
```

---

## 2. LinkedIn Pharma Outreach — ❌ FAILED

**Attempt:** Use kimi-webbridge to search LinkedIn for "AI drug discovery", "computational chemistry", and "cheminformatics" professionals, then send 20 connection requests with the provided template.

**Result:**
- LinkedIn feed was detected in an earlier tab, but tab switching became unstable.
- Navigated to `https://www.linkedin.com/search/results/people/?keywords=AI%20drug%20discovery`
- Search results loaded, but individual people cards and "Connect" buttons were not accessible via standard DOM queries (LinkedIn uses lazy-loaded React components with obfuscated selectors).
- Screenshot captured the Kaggle page instead of LinkedIn due to tab context confusion.

**Failure reasons:**
1. **Anti-bot complexity:** LinkedIn's people search results are heavily obfuscated and rely on infinite scroll / lazy loading.
2. **Rate limits:** Even if automation worked, sending 20 connection requests in a short window would trigger LinkedIn's rate limits and potentially flag the account.
3. **"Add a note" modal:** Each connection request with a custom message requires clicking through a multi-step modal that changes dynamically.
4. **Tab instability:** The webbridge session switched between Kaggle and LinkedIn unexpectedly.

**What would be needed:**
- Manual LinkedIn Sales Navigator search
- Export profile URLs using a tool like Phantombuster or LinkedHelper (with rate limiting)
- Manual personalized connection requests (recommended for quality)

---

## 3. Reddit Drug Discovery Post — ❌ FAILED

**Attempt:** Navigate to `reddit.com/r/drugdiscovery/submit` and create a post titled:  
`[OC] I built a molecular dataset platform — 7,686 molecules with ADMET descriptors, free academic preview`

**Result:**
- Reddit submit page loaded successfully (`Submit to r/DrugDiscovery`)
- "Create post" button and user avatar visible, suggesting user is logged in.
- **Title textbox fill failed:** `fill: Uncaught` error. Reddit's post form uses a custom React contenteditable component that does not expose standard `<input>` or `<textarea>` elements to DOM automation.
- No standard DOM textareas or inputs for the title/body were found via `document.querySelectorAll`.

**Failure reason:** Reddit's new UI is built with React and uses custom `contenteditable` wrappers or shadow DOM that resist programmatic text injection. This is an intentional anti-bot design.

**What would be needed:**
- Manual post creation via the UI
- Or use Reddit's PRAW API (requires Reddit API credentials + app registration at https://www.reddit.com/prefs/apps)

**Suggested post content (ready for manual/API posting):**
```
Title: [OC] I built a molecular dataset platform — 7,686 molecules with ADMET descriptors, free academic preview

Body:
Hi r/DrugDiscovery,

I built Q-Mol (http://photon-bounce.com/qmol/marketplace.html), a platform that harvests molecular data from PubChem and curates sellable datasets with full ADMET descriptors (QED, logP, TPSA, Lipinski, PAINS).

We currently have 7,686 molecules in inventory, all Lipinski-passed, Veber-passed, and PAINS-clean.

For academics: I'm offering a free 50-molecule preview CSV for your screening pipeline. Just DM me or drop a comment.

For CROs/industry: We license subsets starting at $299 for 2,899 molecules. Full CSV delivery.

Would love feedback from the community!
```

---

## 4. Academic Email Campaign — ⚠️ PARTIALLY SUCCEEDED

**Goal:** Find 10 recent papers on virtual screening / molecular docking, extract first authors, and find their emails.

**Result:** Successfully identified 10+ relevant papers and their first authors using arXiv and Google Scholar APIs. **However, direct email addresses were not obtainable** through these search APIs alone.

### Papers & Authors Found

| # | Title | First Author | Year | URL |
|---|-------|-------------|------|-----|
| 1 | From In Silico to In Vitro: Evaluating Molecule Generative Models for Hit Generation | **Nagham Osman** | 2025 | https://arxiv.org/pdf/2512.22031v1 |
| 2 | Quantum Encoding of Three-Dimensional Ligand Poses for Exhaustive Configuration Enumeration | **Pei-Kun Yang** | 2025 | https://arxiv.org/pdf/2512.12573v1 |
| 3 | Toward Closed-loop Molecular Discovery via Language Model, Property Alignment and Strategic Search | **Junkai Ji** | 2025 | https://arxiv.org/pdf/2512.09566v3 |
| 4 | OMTRA: A Multi-Task Generative Model for Structure-Based Drug Design | **Ian Dunn** | 2025 | https://arxiv.org/pdf/2512.05080v1 |
| 5 | The Role and Mechanism of Deep Statistical Machine Learning In Biological Target Screening... | **Pengwei Zhu** | 2025 | https://arxiv.org/pdf/2511.05904v1 |
| 6 | TRIDS: AI-native molecular docking framework for accelerating high-throughput virtual screening | **Xuhan Liu** | 2025 | https://arxiv.org/pdf/2510.24186v2 |
| 7 | Parallelizing Drug Discovery: HPC Pipelines for Alzheimer's Molecular Docking and Simulation | **Paul Ruiz Alliata** | 2025 | https://arxiv.org/pdf/2509.00937v1 |
| 8 | Boltzina: Efficient and Accurate Virtual Screening via Docking-Guided Binding Prediction with Boltz-2 | **Kairi Furui** | 2025 | https://arxiv.org/pdf/2508.17555v1 |
| 9 | Sesame: Opening the door to protein pockets | **Raúl Miñán** | 2025 | https://arxiv.org/pdf/2509.05302v1 |
| 10 | HelixVS: Deep Learning-Enhanced Structure-Based Platform for Screening and Design | **Shanzhuo Zhang** | 2025 | https://arxiv.org/pdf/2508.10262v2 |
| 11 | ML-based virtual screening of novel NLRP3 inhibitors for epilepsy (Heliyon) | **M Zulfat** | 2024 | https://www.cell.com/heliyon/fulltext/S2405-8440(24)10441-0 |
| 12 | Structure-based virtual screening of quinazoline derivatives for anti-EGFR activity | **AA Shah** | 2024 | https://www.benthamdirect.com/content/journals/cmc/10.2174/0929867330666230309143711 |

### Email Finding Status

| Method | Result |
|--------|--------|
| arXiv API | Provides author names but **no emails** |
| Google Scholar API | Provides author names but **no emails** |
| Direct paper PDF fetch | Would require downloading each PDF and parsing the author affiliation block |
| University directory guess | Would require knowing each author's institution (e.g., `firstname.lastname@university.edu`) |

**Next step to get emails:**
1. Download the arXiv source files (often contain `.tex` with `\email{}` fields)
2. Use a tool like Hunter.io or RocketReach to verify institutional emails
3. Search PubMed/PMC for corresponding author emails in the full text

**Email template (ready to send once emails are found):**
```
Subject: Free 50-molecule ADMET dataset for your virtual screening research

Dear Dr. [First Author],

I came across your recent paper "[Paper Title]" and was impressed by your work on virtual screening / molecular docking.

I built Q-Mol — a platform that harvests molecular data from PubChem and curates datasets with full ADMET descriptors (QED, logP, TPSA, Lipinski, PAINS). We currently have 7,686 molecules in inventory.

Would you be interested in a free 50-molecule preview CSV for your screening pipeline? In exchange, we would greatly appreciate a citation or acknowledgment if the data proves useful.

Best regards,
[Your Name]
Q-Mol Platform
http://photon-bounce.com/qmol/marketplace.html
```

---

## 5. CRO Cold Email Blitz — ⚠️ PARTIALLY SUCCEEDED

**Goal:** Find business development emails at WuXi AppTec, Evotec, Charles River, Syngene, and Sai Life Sciences, then send a cold email offering the dataset.

**Result:** Found general contact information and some BD leads, but **no direct verified BD email addresses** for all targets. The email-sending step itself was not attempted because no verified personal email addresses were found.

### CRO Contact Intelligence

| CRO | Contact Found | Details | Source |
|-----|---------------|---------|--------|
| **WuXi AppTec** | ⚠️ Partial | Email format: `first.last@wuxiapptec.com` (58%). PR contact: `Rick Connell`, `pr@wuxiapptec.com`, `ir@wuxiapptec.com`. General: `+86 21 2066 3734` | RocketReach, PR Newswire |
| **Evotec** | ✅ General BD | `info@evotec.com`, Business Development UK: `+44 (0)1235 851561` | Evotec PDF |
| **Charles River** | ✅ General | `askcharlesriver@crl.com`, `susan.hardy@crl.com` (IR), `amy.cianciaruso@crl.com` (PR). HQ: `+1 781-222-6000` | Bioanalysis-Zone, IR pages |
| **Syngene** | ✅ Web form only | Business enquiries via web form at https://www.syngeneintl.com/contact-us/ — no direct email found | Syngene website |
| **Sai Life Sciences** | ✅ General BD | `contact@sailife.com`, `saibd@sailife.com` (legacy BD), `bd@sailife.com` (inferred). CEO: Krishna Kanumuri. VP BD: Swanand Palasule, Veena Madappa, Simon Topp, Sonela Cavicke | sailife.com, RocketReach, FinalScout |

### Recommended CRO Email Targets

Based on the search, the **most reachable** general BD emails are:

1. `saibd@sailife.com` (Sai Life Sciences — confirmed in older PBR storefront)
2. `contact@sailife.com` (Sai Life Sciences — current contact page)
3. `info@evotec.com` (Evotec — general business development)
4. `askcharlesriver@crl.com` (Charles River — general inquiry)
5. `pr@wuxiapptec.com` (WuXi AppTec — media/PR, can forward to BD)

**Cold email template (ready to send):**
```
Subject: Virtual screening library of 7,686 Lipinski-pass molecules — sample available

Hi [Name / Business Development Team],

I built Q-Mol, a platform that curates sellable molecular datasets harvested from PubChem with full ADMET descriptors (QED, logP, TPSA, Lipinski, PAINS).

We currently have a virtual screening library of 7,686 Lipinski-pass molecules, available as CSV.

Pricing: $299 for 2,899 molecules (bulk licensing available).

Can we send a 50-molecule sample CSV for evaluation?

Best,
[Your Name]
Q-Mol Platform
http://photon-bounce.com/qmol/marketplace.html
```

---

## Summary Table: What Worked vs. What Failed

| Task | Status | Details |
|------|--------|---------|
| **Download CSV** | ✅ Success | 386 KB, 7,730 rows, 12 columns. API: `http://photon-bounce.com/qmol/api/export` with PHPSESSID cookie |
| **Dataset QA** | ⚠️ Critical issue | Only 40 unique SMILES. 99.5% duplicates. Name column empty. **Do not market as 7,686 molecules yet.** |
| **Kaggle Upload** | ❌ Failed | User not logged into Kaggle. Needs Kaggle credentials or API token |
| **LinkedIn Outreach** | ❌ Failed | LinkedIn search results are obfuscated/lazy-loaded. Anti-bot measures prevent automation. Rate limits would block 20 requests |
| **Reddit Post** | ❌ Failed | Reddit's React form resists DOM text injection. Needs manual posting or Reddit API (PRAW) |
| **Academic Paper Search** | ✅ Success | Found 12 relevant papers + first authors via arXiv & Scholar APIs. Emails not included in API output |
| **CRO Contact Search** | ⚠️ Partial | Found general contact emails and some BD names. No verified personal BD emails for all 5 targets |
| **Any emails sent** | ❌ Not attempted | No verified personal emails found. Sending to generic `info@` addresses with cold offers is low-yield and spam-risky |

---

## Recommendations for Next Steps

### Immediate (Fix the Product)
1. **Fix the export API** before any marketing. 40 unique molecules ≠ 7,686. This is a credibility killer.
2. **Populate the `name` column** (currently all empty).
3. **Deduplicate the CSV** so each SMILES appears once.

### Short Term (Manual Outreach)
1. **Reddit:** Manually create the post in `r/drugdiscovery` using the draft provided above.
2. **LinkedIn:** Use LinkedIn Sales Navigator to manually find 20 computational chemistry professionals and send personalized connection requests (with the template).
3. **Kaggle:** Create a Kaggle account (or use an existing one), prepare the `dataset-metadata.json`, and upload via `kaggle datasets create`.

### Medium Term (Build Inbound)
1. **Academic emails:** Use Hunter.io or PubMed/PMC full-text extraction to find corresponding author emails for the 12 papers listed. Then send the academic email template.
2. **CRO emails:** Send to the verified general BD emails (`saibd@sailife.com`, `info@evotec.com`, `askcharlesriver@crl.com`) with the cold email template. For WuXi and Syngene, use their web contact forms.
3. **SEO/Content:** Write a blog post on the Q-Mol platform and submit to Hacker News, LinkedIn, and cheminformatics forums.

---

## Files Generated

| File | Path | Description |
|------|------|-------------|
| Q-Mol dataset CSV | `D:\Qmol-3\qmol_dataset.csv` | Original downloaded dataset (7,730 rows, 40 unique SMILES) |
| arXiv paper search | `D:\Qmol-3\arxiv_virtual_screening.csv` | 10 arXiv papers on virtual screening / docking (2024–2025) |
| Scholar paper search | `D:\Qmol-3\scholar_virtual_screening.csv` | 2 Google Scholar papers on virtual screening / docking |
| LinkedIn search screenshot | `D:\Qmol-3\linkedin_search.png` | Screenshot (accidentally captured Kaggle page due to tab confusion) |
| This report | `D:\Qmol-3\outreach_report.md` | Full campaign report |

---

*Report compiled by Q-Mol outreach sub-agent on 2026-07-04.*
