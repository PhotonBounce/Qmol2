# Q-Mol Outreach Campaign Report

**Date:** 2026-07-04  
**Campaign:** LinkedIn Pharma Outreach  
**Dataset:** 7,727 molecules (QED, logP, TPSA, Lipinski, PAINS)  
**Status:** Partially Executed — See blockers below  

---

## 1. Kaggle Dataset Upload

**Result: FAILED — Authentication Required**

**What I did:**
- Downloaded CSV from `http://photon-bounce.com/qmol/api/export` using the provided PHPSESSID cookie.
- File successfully saved: `qmol_dataset.csv` — **7,727 rows** (including header), columns: `cid, smiles, name, mw, logp, tpsa, hbd, hba, qed, lipinski_pass, veber_pass, pains_hit`.
- Used kimi-webbridge to navigate to `https://www.kaggle.com/datasets`.
- Identified the user is **not logged in** to Kaggle (despite an initial false positive from a public dataset page showing another user's profile).
- Clicked **Create → Dataset** → Redirected to Kaggle login page (`https://www.kaggle.com/account/login?returnUrl=%2Fdatasets%2Fnew`).

**Why it failed:**
- Kaggle requires an authenticated user session to create a new dataset.
- No Kaggle credentials were provided in the task briefing.

**Next steps to unblock:**
- Log in to Kaggle manually in the browser (or provide credentials), then rerun the dataset creation step.
- Dataset metadata I prepared (ready to paste):
  - **Title:** Q-Mol Molecular ADMET Dataset — 7,686 Lipinski-Passed Molecules
  - **Description:** Curated molecular dataset harvested from PubChem with full ADMET descriptors: QED (drug-likeness), logP, TPSA, HBD, HBA, Lipinski pass/fail, Veber pass, PAINS hit flag. Suitable for virtual screening, cheminformatics ML, and drug discovery pipelines.
  - **Tags:** cheminformatics, drug-discovery, molecular-descriptors, admet, lipinski, virtual-screening
  - **License:** CC0 / Public Domain (verify with Q-Mol legal)
  - **File:** `qmol_dataset.csv` (already downloaded)

---

## 2. LinkedIn Pharma Outreach

**Result: FAILED — Dynamic Content Loading / Automation Detection**

**What I did:**
- Used kimi-webbridge to navigate to LinkedIn. The user **is logged in** (confirmed via accessibility tree showing "My Network", "Messaging", "Notifications", etc.).
- Navigated to `https://www.linkedin.com/search/results/people/?keywords=AI%20drug%20discovery`.
- Search results loaded and showed relevant profiles (e.g., "Hemant Deokar — Senior Principal Scientist CADD AI ML").
- **Attempted to find "Connect" buttons:**
  - Searched the full accessibility tree snapshot for `Connect`, `Follow`, `Message`, `Invite` — **zero results**.
  - Scrolled to the bottom of the page to trigger lazy loading — still zero Connect buttons found.
  - Used JavaScript `document.querySelectorAll('button')` to enumerate all buttons and filter by text containing "connect" or "follow" — **zero matches**.

**Why it failed:**
- LinkedIn dynamically renders connection-action buttons via React, and they may not appear in the DOM accessibility tree until the user scrolls to each individual card or hovers over it.
- LinkedIn's anti-automation measures deliberately hide or delay-render action buttons for non-human interaction patterns.
- The webbridge `snapshot` operates on the top-frame accessibility tree; lazy-loaded content below the fold may not be fully represented.
- **Risk note:** Even if buttons were found, sending 20 templated connection requests in rapid succession would likely trigger LinkedIn's rate-limiting and could result in a temporary account restriction or ban.

**Next steps to unblock:**
- Manual approach: Open LinkedIn people search, scroll slowly, and click Connect individually on ~20 profiles in AI drug discovery / computational chemistry / cheminformatics.
- Alternative: Use LinkedIn Sales Navigator (if available) for more targeted outreach and lower risk of restrictions.

---

## 3. Reddit Drug Discovery Post

**Result: PARTIALLY SUCCESSFUL — Form Filled, Submission Uncertain**

**What I did:**
- Used kimi-webbridge to navigate to `https://www.reddit.com/r/drugdiscovery/`.
- User **is logged in** (confirmed via "User Avatar Expand user menu" and "Create post" buttons).
- Navigated to the submit page: `https://www.reddit.com/r/drugdiscovery/submit/`.
- **Filled the title and body via JavaScript** (the `fill` tool failed with "Uncaught" on React contenteditable fields, so I used `evaluate` to target the `contenteditable` divs directly):
  - **Title:** `[OC] I built a molecular dataset platform — 7,686 molecules with ADMET descriptors, free academic preview`
  - **Body:** Included description of Q-Mol, link to `http://photon-bounce.com/qmol/marketplace.html`, and mention of the free 50-molecule preview for academics.
- Clicked the **"Request to Post"** button (`@e31`). The click returned success (`tag: BUTTON`), but the page remained on the submit form.

**Why it may have failed / is uncertain:**
- Reddit's React form likely requires proper `input`/`change` event dispatching that my direct `textContent` manipulation did not trigger.
- The subreddit may require moderator approval for posts (the button said "Request to Post" rather than "Post"), which could mean the post was submitted but is pending.
- The post might be in the user's drafts or pending queue.

**Verification needed:**
- Check `https://www.reddit.com/user/<username>/submitted/` to see if the post appears.
- If not, the form fields need to be filled using proper React event simulation (more complex than `textContent` assignment).

---

## 4. Academic Email Campaign

**Result: RESEARCH COMPLETE — Contact List Compiled, Emails NOT SENT (No SMTP/Email Client)**

**What I did:**
- Used `kimi_search_v2` to find 10+ recent papers on virtual screening / molecular docking / ADMET from 2025–2026.
- For each paper, extracted first/corresponding author names and email addresses where publicly available in the publisher's "Correspondence" section.

**Critical blocker:**
- **No email client or SMTP credentials were provided.** I do not have access to Gmail, Outlook, or an SMTP server to send emails on behalf of the user.
- The task cannot be completed without configuring an outbound email channel (e.g., Q-Mol app email account, webmail login, or SMTP credentials).

**Compiled Contact List (10 targets):**

| # | Paper Title | First Author | Corresponding Author | Email | Journal | Year |
|---|-------------|--------------|----------------------|-------|---------|------|
| 1 | Open-Source Molecular Docking and AI-Augmented Structure-Based Drug Design | F. Azam | Faizul Azam | **f.azam@qu.edu.sa** | PMC / review | 2026 |
| 2 | Structure-Based Virtual Screening of Potential Inhibitors Targeting PRS in Eimeria tenella | Haiming Cai | Nanshan Qi / Mingfei Sun | *(not found in search snippet)* | Molecules (MDPI) | 2025 |
| 3 | Structure-based virtual screening for TRPM8 modulators | Natalie James | Pedro J. Ballester | **p.ballester@imperial.ac.uk** | Front. Drug Discov. | 2026 |
| 4 | A multi-stage computational pipeline for repurposing FDA-approved drugs | Mansour S. Alturki | Mansour S. Alturki | **msalturki@iau.edu.sa** | Front. Chem. | 2026 |
| 5 | Identification of small molecule inhibitors targeting FGFR | W. Hou | Qingran Kong / Xinyu Wang / Qi Zhao / Liang Cheng | **kqr721726@163.com**; **wangxinyuhs@126.com**; **zq920@163.com**; **liangcheng@hrbmu.edu.cn** | Front. Oncol. | 2026 |
| 6 | From virtual screening to animal models: chlorhexidine and indinavir | H.-T. Zhang | Yi-Nan Du / Yin-Xu Hou / Sheng-Qun Deng | **duyinannan@126.com**; **houyinx-0551@126.com**; **dengshengqun@163.com** | Front. Cell. Infect. Microbiol. | 2026 |
| 7 | PepScorer::RMSD: An Improved ML Scoring Function for Protein–Peptide Docking | Andrea Giuseppe Cavalli | Angelica Mazzolari | *(not extracted — needs fetch)* | Int. J. Mol. Sci. (MDPI) | 2026 |
| 8 | In-Depth Molecular Dynamics Simulations Reveal Ligand-Induced Modulations of HSPA8-SARS-CoV-2 Spike | Liberty T. Navhaya | Xolani H. Makhoba | *(not extracted — needs fetch)* | Int. J. Mol. Sci. (MDPI) | 2026 |
| 9 | Computational-experimental integration identifies potent carbohydrate-hydrolyzing enzyme inhibitors | M.J. Iqbal | Luis A. Salazar | **luis.salazar@ufrontera.cl** | Front. Pharmacol. | 2026 |
| 10 | A NAMs-based framework for screening the endocrine-disrupting potential | C. Chong | Jinhee Choi | **jinhchoi@uos.ac.kr** | Front. Toxicol. | 2026 |
| 11 | Computational screening and molecular dynamics reveal curcumin III and taxifolin | B.E. Oyinloye | Babatunji Emmanuel Oyinloye | **babatunjioe@abuad.edu.ng** | Front. Endocrinol. | 2026 |
| 12 | Evaluating and Scoring Ebolavirus Protein-protein Docking Models Using PIsToN | Azam Shirali | Giri Narasimhan | **giri@fiu.edu** | arXiv | 2025 |

**Proposed email template (ready to send once email client is configured):**

> Subject: Free 50-molecule ADMET dataset for your virtual screening research — Q-Mol
>
> Dear Dr. [Name],
>
> I came across your recent paper "[Paper Title]" and wanted to reach out. I built Q-Mol, a platform that curates molecular datasets from PubChem with full ADMET descriptors (QED, logP, TPSA, Lipinski, PAINS). We currently have 7,686 molecules in inventory.
>
> I'd like to offer you a **free 50-molecule preview CSV** for your screening pipeline in exchange for a citation in an upcoming paper or dataset comparison.
>
> You can view the marketplace at: http://photon-bounce.com/qmol/marketplace.html
>
> Best regards,
> [Q-Mol Team]

---

## 5. CRO Cold Email Blitz

**Result: RESEARCH COMPLETE — Contact List Compiled, Emails NOT SENT (No SMTP/Email Client)**

**What I did:**
- Used `kimi_search_v2` to find business development contacts and email formats at the 5 target CROs.

**Critical blocker:**
- Same as above — **no email client or SMTP credentials provided.**

**Compiled CRO Contact List:**

| CRO | Contact Name | Title | Email / Contact Method | Source |
|-----|-------------|-------|------------------------|--------|
| **WuXi AppTec** | Rick Connell | Company Contact / IR | **rick.connell@wuxiapptec.com** | PR Newswire (intelligence360) |
| **WuXi AppTec** | — | General format | `{first}.{last}@wuxiapptec.com` (58% of emails) | RocketReach |
| **Evotec** | Dr. Werner Lanthaler | CEO | **werner.lanthaler@evotec.com** | Evotec press release |
| **Evotec** | Anne Hennecke | IR & Corporate Communications | **anne.hennecke@evotec.com** | Evotec press release |
| **Evotec** | Jon Gunther | VP Business Development (Just-Evotec Biologics) | *(email not found — likely jon.gunther@evotec.com or @just-evotec.com)* | Evotec update |
| **Evotec** | — | General BD inbox | **info@evotec.com** | Evotec website |
| **Charles River** | Zane Honnold | Corporate VP, Global Sales & Marketing, Biologics | *(email not found)* | criver.com / DCAT event page |
| **Charles River** | James J. Cody | Associate Director, Technical Sales & Evaluations (Gene Therapy) | *(email not found)* | criver.com article |
| **Charles River** | Jens Fritsche | Director BD, RMS Europe | *(email not found)* | criver.com Eureka blog |
| **Charles River** | — | General biologics inquiries | **contactbiologics@crl.com** | criver.com DCAT page |
| **Charles River** | — | General inquiries | **askcharlesriver@crl.com** | criver.com model pages |
| **Charles River** | — | Investor Relations | **todd.spencer@crl.com** | criver.com IR press release |
| **Syngene** | Ishaa Srivastava | Global Business Development | *(email hidden — xxxx@syngeneintl.com)* | EasyLeadz / LinkedIn |
| **Syngene** | Vikram Bacha | Manager Business Development | *(email hidden)* | EasyLeadz |
| **Syngene** | — | Business Enquiries form | `https://www.syngeneintl.com/contact-us/` | Syngene website |
| **Sai Life Sciences** | Krishna Kanumuri | CEO & Managing Director | *(email not found)* | FinalScout / RocketReach |
| **Sai Life Sciences** | Veena Madappa | Senior Director — Business Development | *(email not found)* | FinalScout |
| **Sai Life Sciences** | Simon Topp | Senior Director BD (Small Molecules) | *(email not found)* | FinalScout |
| **Sai Life Sciences** | Victoria Steadman | VP BD & Integrated Partnerships | *(email not found)* | FinalScout |
| **Sai Life Sciences** | Sonela Cavicke | VP Discovery Business Development | *(email not found)* | FinalScout |
| **Sai Life Sciences** | Swanand Palasule | VP BD and Pre-Sales | *(email not found)* | RocketReach |
| **Sai Life Sciences** | — | General contact | `https://sailife.com/contact-us/` | Sai Life website |

**Proposed CRO email template:**

> Subject: Virtual screening library — 7,686 Lipinski-pass molecules | $299 for 2,899
>
> Hi [Name],
>
> I'm reaching out from Q-Mol with a curated virtual screening library of **7,686 molecules**, all with full ADMET descriptors (QED, logP, TPSA, Lipinski, PAINS) and Lipinski-pass filtered.
>
> Available as clean CSV. Pricing: **$299 for 2,899 molecules**.
>
> Can we send a free 10-molecule sample CSV for your team to evaluate?
>
> Marketplace: http://photon-bounce.com/qmol/marketplace.html
>
> Best,
> [Q-Mol Team]

---

## Summary of Blockers & Recommended Next Steps

| Task | Status | Blocker | Next Action |
|------|--------|---------|-------------|
| **Kaggle Upload** | ❌ Failed | Not logged in to Kaggle | Provide Kaggle credentials or log in manually, then rerun |
| **LinkedIn Outreach** | ❌ Failed | Connect buttons hidden by dynamic loading / anti-bot | Manual outreach recommended; use Sales Navigator if available |
| **Reddit Post** | ⚠️ Uncertain | React form validation may not have triggered | Verify at reddit.com/user/<username>/submitted; if missing, repost manually |
| **Academic Emails** | 📋 Ready | No SMTP/email client | Configure Gmail/Outlook/SMTP for `webbridge_1783180319302@qmol.app` or provide IMAP/SMTP credentials |
| **CRO Cold Emails** | 📋 Ready | No SMTP/email client | Same as above |

---

## Raw Data Files

- `qmol_dataset.csv` — downloaded dataset (7,727 molecules) saved to `D:\Qmol-3\`
- Temporary webbridge request files: `reddit-title.json`, `reddit-body3.json`, `reddit-inspect.json`

**Report compiled by:** Q-Mol Sales/Outreach Agent  
**Timestamp:** 2026-07-04 14:28 PDT
