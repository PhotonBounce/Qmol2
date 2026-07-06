#!/usr/bin/env python3
"""
Q-Mol Daily Blog Generator
Generates SEO-optimized blog posts about molecular informatics and drug discovery.
Posts to the Q-Mol microsite. Runs via cron daily.

Usage:
    python blog_generator.py --generate
    python blog_generator.py --deploy
    python blog_generator.py --generate-and-deploy
"""

import random
import os
import argparse
import json
import requests
from datetime import datetime, timedelta
from pathlib import Path

# Config
PROJECT_DIR = Path(__file__).parent.parent
BLOG_DIR = PROJECT_DIR / "deploy" / "blog"
DATA_DIR = PROJECT_DIR / "data"
CPANEL_TOKEN = "cpanel photonb:OYOQ3JK7HI9C6CNO84T0RH8JUKHHIBZ1"
CPANEL_URL = "https://photon-bounce.com:2083/execute/Fileman"
WEBSITE_BASE = "https://photon-bounce.com/qmol"

# Blog topics - mix of technical and marketing
BLOG_TOPICS = [
    {
        "title": "10 Drug-Like Molecules You Should Know for Virtual Screening",
        "category": "virtual-screening",
        "tags": ["virtual screening", "drug-like molecules", "cheminformatics", "RDKit"],
        "template": "molecule_spotlight"
    },
    {
        "title": "Lipinski's Rule of Five: Still Relevant in 2024?",
        "category": "admet",
        "tags": ["Lipinski", "ADMET", "drug design", "rule of five"],
        "template": "educational"
    },
    {
        "title": "How to Filter PAINS Compounds from Your Screening Library",
        "category": "filtering",
        "tags": ["PAINS", "filtering", "compound quality", "screening"],
        "template": "how_to"
    },
    {
        "title": "QED Score Explained: Quantifying Drug-Likeness",
        "category": "admet",
        "tags": ["QED", "drug-likeness", "descriptor", "QSAR"],
        "template": "educational"
    },
    {
        "title": "Building a Kinase Inhibitor Library: Scaffold Selection Strategies",
        "category": "library-design",
        "tags": ["kinase inhibitors", "scaffolds", "library design", "medicinal chemistry"],
        "template": "technical"
    },
    {
        "title": "CNS-Penetrant Compounds: What Makes a Molecule Cross the BBB?",
        "category": "admet",
        "tags": ["CNS", "blood-brain barrier", "BBB", "logP", "TPSA"],
        "template": "educational"
    },
    {
        "title": "From SMILES to CSV: Automated Molecular Dataset Curation",
        "category": "automation",
        "tags": ["SMILES", "automation", "Python", "RDKit", "dataset"],
        "template": "how_to"
    },
    {
        "title": "Machine Learning for Drug Discovery: Training Data Quality Matters",
        "category": "machine-learning",
        "tags": ["machine learning", "ML", "training data", "drug discovery", "AI"],
        "template": "technical"
    },
    {
        "title": "Q-Mol Update: Our Molecule Database Grows to {count} Compounds",
        "category": "product-update",
        "tags": ["Q-Mol", "product update", "molecule database", "cheminformatics"],
        "template": "product_update"
    },
    {
        "title": "Comparing Free vs. Paid Molecular Datasets: What's Worth It?",
        "category": "market",
        "tags": ["datasets", "market", "pricing", "comparison"],
        "template": "comparison"
    },
    {
        "title": "The Hidden Cost of Manual Compound Curation",
        "category": "business",
        "tags": ["cost", "efficiency", "curation", "automation", "ROI"],
        "template": "business"
    },
    {
        "title": "5 Python Libraries Every Cheminformaticist Should Know",
        "category": "tools",
        "tags": ["Python", "RDKit", "Open Babel", "cheminformatics", "libraries"],
        "template": "listicle"
    },
    {
        "title": "Solubility Prediction: From Rule-of-Thumb to Machine Learning",
        "category": "admet",
        "tags": ["solubility", "ADMET", "prediction", "ML", "QSAR"],
        "template": "educational"
    },
    {
        "title": "Q-Mol Feature Spotlight: Real-Time Molecule Mining from PubChem",
        "category": "product-update",
        "tags": ["Q-Mol", "PubChem", "mining", "real-time", "features"],
        "template": "product_spotlight"
    },
    {
        "title": "How Startups Can Accelerate Hit-to-Lead with Better Data",
        "category": "business",
        "tags": ["startup", "hit-to-lead", "drug discovery", "data", "biotech"],
        "template": "business"
    }
]


def get_molecule_count():
    """Get current molecule count from the database."""
    try:
        import sqlite3
        db_path = DATA_DIR / "saas.sqlite"
        if db_path.exists():
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(DISTINCT smiles) FROM molecules")
            count = cursor.fetchone()[0] or 0
            conn.close()
            return count
    except Exception:
        pass
    return 2800


def generate_molecule_spotlight():
    """Generate a molecule spotlight post."""
    molecules = [
        {"name": "Aspirin", "smiles": "CC(=O)Oc1ccccc1C(=O)O", "mw": 180, "logp": 1.2, "qed": 0.85, "fact": "One of the oldest synthetic drugs, still widely used as an anti-inflammatory."},
        {"name": "Ibuprofen", "smiles": "CC(C)Cc1ccc(cc1)C(C)C(=O)O", "mw": 206, "logp": 3.5, "qed": 0.72, "fact": "A non-steroidal anti-inflammatory drug (NSAID) with over 50 years of clinical use."},
        {"name": "Caffeine", "smiles": "CN1C=NC2=C1C(=O)N(C(=O)N2C)C", "mw": 194, "logp": -0.1, "qed": 0.78, "fact": "The world's most consumed psychoactive substance, also a phosphodiesterase inhibitor."},
        {"name": "Quinine", "smiles": "COC1=CC2=CC=CC=C2C=C1O", "mw": 324, "logp": 2.8, "qed": 0.65, "fact": "Historically used to treat malaria, the first known chemotherapeutic agent."},
        {"name": "Metformin", "smiles": "CN(C)C(=N)N=C(N)N", "mw": 129, "logp": -1.4, "qed": 0.55, "fact": "The most prescribed antidiabetic drug, with potential anti-aging properties being studied."},
        {"name": "Penicillin G", "smiles": "CC1(C(N2C(S1)C(C2=O)NC(=O)Cc3ccccc3)C(=O)O)C", "mw": 334, "logp": 1.8, "qed": 0.60, "fact": "The first true antibiotic, discovered by Alexander Fleming in 1928."},
        {"name": "Diazepam", "smiles": "CN1C(=O)CN=C(c2ccccc2)c3ccccc13", "mw": 284, "logp": 2.8, "qed": 0.70, "fact": "A classic benzodiazepine, one of the most prescribed medications of all time."},
        {"name": "Simvastatin", "smiles": "CCC(C)(C)C(=O)C(C)C1C(=O)C(C)C(C)C(C)C1C", "mw": 418, "logp": 4.7, "qed": 0.50, "fact": "A HMG-CoA reductase inhibitor that revolutionized cardiovascular medicine."},
        {"name": "Artemisinin", "smiles": "C1C2C3C4(COC(O2)C3O)C5C(O1)C(O5)C4C", "mw": 282, "logp": 3.0, "qed": 0.45, "fact": "A sesquiterpene lactone from sweet wormwood, Nobel Prize-winning antimalarial."},
        {"name": "Tamoxifen", "smiles": "CN(C)CCOC(c1ccccc1)c2ccccc2", "mw": 371, "logp": 6.3, "qed": 0.40, "fact": "A selective estrogen receptor modulator, cornerstone of breast cancer treatment."}
    ]
    
    selected = random.sample(molecules, 5)
    content = "<h2>Spotlight on 5 Screening-Worthy Molecules</h2>\n\n"
    for mol in selected:
        content += f"<h3>{mol['name']}</h3>\n"
        content += f"<p><strong>SMILES:</strong> <code>{mol['smiles']}</code><br>\n"
        content += f"<strong>MW:</strong> {mol['mw']} | <strong>LogP:</strong> {mol['logp']} | <strong>QED:</strong> {mol['qed']}</p>\n"
        content += f"<p>{mol['fact']}</p>\n\n"
    
    content += "<p><em>All these molecules and {count:,} more are available in the Q-Mol database. "
    content += "<a href='/qmol/marketplace.html'>Browse the marketplace →</a></em></p>"
    return content


def generate_educational_post(topic):
    """Generate an educational post."""
    educational_content = {
        "Lipinski's Rule of Five": """
<h2>What is Lipinski's Rule of Five?</h2>
<p>In 1997, Christopher Lipinski analyzed 2,245 drug candidates and identified four physicochemical properties that correlate with oral bioavailability:</p>
<ul>
<li><strong>Molecular Weight ≤ 500 Da</strong> — Larger molecules struggle with absorption</li>
<li><strong>LogP ≤ 5</strong> — Too lipophilic = poor solubility and metabolism issues</li>
<li><strong>H-Bond Donors ≤ 5</strong> — Excessive hydrogen bonding reduces membrane permeability</li>
<li><strong>H-Bond Acceptors ≤ 10</strong> — Similar rationale to donors</li>
</ul>
<h3>Is It Still Relevant?</h3>
<p>Yes — but with caveats. The rule was designed for <em>oral</em> drugs. CNS drugs, injectables, and natural products often violate it. Modern approaches like QED (Quantitative Estimate of Drug-likeness) provide a more nuanced 0-1 score.</p>
<p>At Q-Mol, every molecule in our database is scored with both Lipinski and QED, so you can filter by your project's specific requirements.</p>
""",
        "QED Score": """
<h2>QED: A Better Measure of Drug-Likeness</h2>
<p>QED (Quantitative Estimate of Drug-likeness) was developed by Bickerton et al. in 2012 as a continuous alternative to Lipinski's binary pass/fail.</p>
<h3>How It Works</h3>
<p>QED combines 8 molecular properties into a single score from 0 to 1:</p>
<ul>
<li>Molecular weight</li>
<li>LogP</li>
<li>H-bond donors & acceptors</li>
<li>Rotatable bonds</li>
<li>Aromatic rings</li>
<li>Alerts for unwanted structural features</li>
</ul>
<p>A QED > 0.7 indicates a highly drug-like molecule. In our Q-Mol database, we flag molecules by QED tier so you can quickly filter for quality.</p>
""",
        "PAINS Compounds": """
<h2>What Are PAINS Compounds?</h2>
<p>PAINS (Pan-Assay Interference Compounds) are molecules that give false positives in biochemical screens due to reactivity, aggregation, or photophysical properties rather than specific target binding.</p>
<h3>Common PAINS Families</h3>
<ul>
<li>Rhodanines — frequent hitters in kinase screens</li>
<li>Curcuminoids — unstable and non-specific</li>
<li>Enones/Michael acceptors — reactive electrophiles</li>
<li>Alkylidene rhodanines — promiscuous binders</li>
</ul>
<p>The Q-Mol database runs every molecule through PAINS filters using RDKit. We tag hits so you can exclude them before they waste your screening budget.</p>
"""
    }
    
    for key, content in educational_content.items():
        if key.lower() in topic.lower():
            return content
    
    return "<p>Educational content about " + topic + " coming soon.</p>"


def generate_product_update(count):
    """Generate a product update post."""
    return f"""
<h2>Q-Mol Database Update: {count:,} Molecules and Growing</h2>
<p>Our automated mining infrastructure just hit a milestone: <strong>{count:,} unique drug-like molecules</strong> now in the Q-Mol database, with new compounds added every 5 minutes.</p>
<h3>What's in the Database?</h3>
<ul>
<li>Full RDKit descriptors (MW, LogP, TPSA, HBD, HBA, rotatable bonds, QED)</li>
<li>Lipinski and Veber filter flags</li>
<li>PAINS screening tags</li>
<li>PubChem source IDs for traceability</li>
<li>CSV export ready for docking, ML, or assay prep</li>
</ul>
<h3>How We Mine</h3>
<p>10 parallel mining bots continuously harvest from PubChem, filter by drug-likeness, and validate with RDKit. The entire pipeline is automated — no manual curation bottleneck.</p>
<p><a href='/qmol/app/' class='btn'>Try the free 7-day trial →</a></p>
"""


def generate_blog_post():
    """Generate a complete blog post."""
    topic = random.choice(BLOG_TOPICS)
    count = get_molecule_count()
    
    date_str = datetime.now().strftime("%Y-%m-%d")
    slug = topic["title"].lower().replace(" ", "-").replace("?", "").replace(":", "").replace("'", "")[:50]
    filename = f"{date_str}-{slug}.html"
    
    title = topic["title"].replace("{count}", f"{count:,}")
    
    # Generate content based on template
    if topic["template"] == "molecule_spotlight":
        body = generate_molecule_spotlight()
    elif topic["template"] == "educational":
        body = generate_educational_post(title)
    elif topic["template"] == "product_update":
        body = generate_product_update(count)
    elif topic["template"] == "product_spotlight":
        body = generate_product_update(count)
    else:
        body = f"<p>{title} — detailed analysis and insights for cheminformatics professionals.</p>"
        body += f"<p>The Q-Mol platform currently hosts <strong>{count:,} molecules</strong> with full ADMET descriptors.</p>"
    
    # Build full HTML
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} | Q-Mol Blog</title>
<meta name="description" content="{title} — Q-Mol molecular informatics blog for drug discovery professionals.">
<meta name="keywords" content="{', '.join(topic['tags'])}">
<link rel="canonical" href="https://photon-bounce.com/qmol/blog/{filename}">
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ font-family: 'Segoe UI', system-ui, sans-serif; background:#0f172a; color:#e2e8f0; min-height:100vh; line-height:1.7; }}
  .container {{ max-width:800px; margin:0 auto; padding:24px; }}
  header {{ text-align:center; padding:40px 0; border-bottom:1px solid #1e293b; margin-bottom:24px; }}
  h1 {{ font-size:1.8rem; background:linear-gradient(90deg,#06b6d4,#10b981); -webkit-background-clip:text; -webkit-text-fill-color:transparent; margin-bottom:12px; }}
  .meta {{ color:#64748b; font-size:13px; margin-bottom:24px; }}
  .tag {{ display:inline-block; background:#1e293b; border:1px solid #334155; color:#94a3b8; padding:4px 12px; border-radius:20px; font-size:12px; margin-right:8px; margin-bottom:8px; }}
  .content {{ background:#1e293b; border:1px solid #334155; border-radius:16px; padding:28px; margin-bottom:24px; }}
  .content h2 {{ color:#38bdf8; font-size:1.3rem; margin:24px 0 12px; }}
  .content h3 {{ color:#fbbf24; font-size:1.1rem; margin:20px 0 10px; }}
  .content p {{ margin-bottom:16px; color:#cbd5e1; }}
  .content ul {{ margin:12px 0 12px 24px; color:#cbd5e1; }}
  .content li {{ margin-bottom:8px; }}
  .content code {{ background:#0f172a; padding:2px 6px; border-radius:4px; font-family:monospace; font-size:13px; color:#fbbf24; }}
  .content a {{ color:#38bdf8; text-decoration:none; }}
  .content a:hover {{ text-decoration:underline; }}
  .cta {{ background:linear-gradient(135deg,#1e293b,#0f172a); border:2px solid #f59e0b; border-radius:16px; padding:24px; text-align:center; margin-top:24px; }}
  .cta h3 {{ color:#fbbf24; margin-bottom:12px; }}
  .cta p {{ color:#cbd5e1; margin-bottom:16px; }}
  .btn {{ display:inline-block; padding:12px 24px; background:#f59e0b; color:#0f172a; border-radius:10px; font-weight:600; text-decoration:none; margin:4px; }}
  .btn:hover {{ background:#fbbf24; }}
  .nav {{ display:flex; justify-content:space-between; align-items:center; padding:16px 0; border-bottom:1px solid #1e293b; margin-bottom:24px; }}
  .nav a {{ color:#94a3b8; text-decoration:none; font-size:14px; }}
  .nav a:hover {{ color:#38bdf8; }}
  footer {{ text-align:center; padding:24px; color:#64748b; font-size:13px; border-top:1px solid #1e293b; margin-top:24px; }}
</style>
</head>
<body>
<div class="container">
  <nav class="nav">
    <a href="/qmol/">← Q-Mol Home</a>
    <a href="/qmol/blog/">Blog Index →</a>
  </nav>
  
  <header>
    <h1>{title}</h1>
    <div class="meta">Published {date_str} | Q-Mol Blog | {count:,} molecules in database</div>
    <div>
      {' '.join([f'<span class="tag">{tag}</span>' for tag in topic['tags']])}
    </div>
  </header>
  
  <div class="content">
    {body}
  </div>
  
  <div class="cta">
    <h3>🚀 Try Q-Mol Free for 7 Days</h3>
    <p>Access {count:,} drug-like molecules with full ADMET descriptors. No credit card required.</p>
    <a href="/qmol/app/" class="btn">Start Free Trial</a>
    <a href="/qmol/marketplace.html" class="btn">Browse Marketplace</a>
  </div>
  
  <footer>
    <p>Q-Mol | Molecular Informatics for Drug Discovery</p>
    <p><a href="mailto:qmol@photon-bounce.com">qmol@photon-bounce.com</a></p>
  </footer>
</div>
</body>
</html>
"""
    
    return filename, html, title


def deploy_post(filename, html):
    """Deploy blog post to server via cPanel API."""
    # Save locally first
    BLOG_DIR.mkdir(parents=True, exist_ok=True)
    local_path = BLOG_DIR / filename
    with open(local_path, "w", encoding="utf-8") as f:
        f.write(html)
    
    # Upload via cPanel API
    try:
        import subprocess
        cmd = [
            "curl", "-s", "-H", f"Authorization: {CPANEL_TOKEN}",
            "-X", "POST", f"{CPANEL_URL}/upload_files",
            "-F", "dir=public_html/qmol/blog",
            "-F", f"file=@{local_path};filename={filename}",
            "-F", "overwrite=1"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if '"status":1' in result.stdout:
            print(f"✅ Deployed: https://photon-bounce.com/qmol/blog/{filename}")
            return True
        else:
            print(f"⚠️ Deploy response: {result.stdout[:200]}")
            return False
    except Exception as e:
        print(f"❌ Deploy failed: {e}")
        return False


def update_blog_index():
    """Update the blog index page with all posts."""
    BLOG_DIR.mkdir(parents=True, exist_ok=True)
    posts = []
    
    for f in sorted(BLOG_DIR.glob("*.html"), reverse=True):
        # Extract title from file
        content = f.read_text(encoding="utf-8")
        title_match = content.find("<title>")
        if title_match > 0:
            title_end = content.find("</title>", title_match)
            title = content[title_match+7:title_end].replace(" | Q-Mol Blog", "")
        else:
            title = f.stem
        
        date_str = f.stem[:10] if len(f.stem) >= 10 else ""
        posts.append({
            "file": f.name,
            "title": title,
            "date": date_str,
            "url": f"/qmol/blog/{f.name}"
        })
    
    # Build index HTML
    index_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Q-Mol Blog — Molecular Informatics for Drug Discovery</title>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ font-family: 'Segoe UI', system-ui, sans-serif; background:#0f172a; color:#e2e8f0; min-height:100vh; }}
  .container {{ max-width:900px; margin:0 auto; padding:24px; }}
  header {{ text-align:center; padding:40px 0; border-bottom:1px solid #1e293b; margin-bottom:24px; }}
  h1 {{ font-size:2rem; background:linear-gradient(90deg,#06b6d4,#10b981); -webkit-background-clip:text; -webkit-text-fill-color:transparent; }}
  .subtitle {{ color:#94a3b8; margin-top:8px; }}
  .post {{ background:#1e293b; border:1px solid #334155; border-radius:12px; padding:20px; margin-bottom:16px; transition:all .15s; }}
  .post:hover {{ border-color:#38bdf8; }}
  .post a {{ color:#e2e8f0; text-decoration:none; display:block; }}
  .post h2 {{ color:#38bdf8; font-size:1.1rem; margin-bottom:8px; }}
  .post .date {{ color:#64748b; font-size:12px; }}
  .nav {{ display:flex; justify-content:space-between; padding:16px 0; border-bottom:1px solid #1e293b; margin-bottom:24px; }}
  .nav a {{ color:#94a3b8; text-decoration:none; }}
  .nav a:hover {{ color:#38bdf8; }}
  footer {{ text-align:center; padding:24px; color:#64748b; font-size:13px; border-top:1px solid #1e293b; margin-top:24px; }}
</style>
</head>
<body>
<div class="container">
  <nav class="nav">
    <a href="/qmol/">← Q-Mol Home</a>
    <a href="/qmol/app/">Try the App →</a>
  </nav>
  
  <header>
    <h1>Q-Mol Blog</h1>
    <p class="subtitle">Cheminformatics, drug discovery, and molecular informatics</p>
  </header>
  
  <div class="posts">
"""
    
    for post in posts:
        index_html += f"""
    <div class="post">
      <a href="{post['url']}">
        <h2>{post['title']}</h2>
        <div class="date">{post['date']}</div>
      </a>
    </div>
"""
    
    index_html += """  </div>
  
  <footer>
    <p>Q-Mol | Molecular Informatics</p>
  </footer>
</div>
</body>
</html>
"""
    
    index_path = BLOG_DIR / "index.html"
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(index_html)
    
    # Deploy index
    try:
        import subprocess
        cmd = [
            "curl", "-s", "-H", f"Authorization: {CPANEL_TOKEN}",
            "-X", "POST", f"{CPANEL_URL}/upload_files",
            "-F", "dir=public_html/qmol/blog",
            "-F", f"file=@{index_path};filename=index.html",
            "-F", "overwrite=1"
        ]
        subprocess.run(cmd, capture_output=True, timeout=30)
        print(f"✅ Blog index updated: https://photon-bounce.com/qmol/blog/")
    except Exception as e:
        print(f"❌ Index deploy failed: {e}")


def main():
    parser = argparse.ArgumentParser(description="Q-Mol Daily Blog Generator")
    parser.add_argument("--action", choices=["generate", "deploy", "generate-and-deploy", "update-index"], default="generate-and-deploy")
    args = parser.parse_args()
    
    if args.action == "generate":
        filename, html, title = generate_blog_post()
        BLOG_DIR.mkdir(parents=True, exist_ok=True)
        with open(BLOG_DIR / filename, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"Generated: {filename}")
        print(f"Title: {title}")
    
    elif args.action == "deploy":
        # Deploy all un-deployed posts
        update_blog_index()
    
    elif args.action == "generate-and-deploy":
        filename, html, title = generate_blog_post()
        BLOG_DIR.mkdir(parents=True, exist_ok=True)
        with open(BLOG_DIR / filename, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"Generated: {filename}")
        print(f"Title: {title}")
        deploy_post(filename, html)
        update_blog_index()
    
    elif args.action == "update-index":
        update_blog_index()


if __name__ == "__main__":
    main()
