<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Q-Mol | Molecular Informatics Platform</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: #0f172a;
            color: #e2e8f0;
            line-height: 1.6;
        }
        .container { max-width: 1200px; margin: 0 auto; padding: 0 20px; }
        header {
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
            padding: 80px 0 60px;
            text-align: center;
            border-bottom: 1px solid #334155;
        }
        h1 {
            font-size: 4rem;
            font-weight: 800;
            background: linear-gradient(90deg, #06b6d4, #10b981);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 20px;
        }
        .tagline {
            font-size: 1.3rem;
            color: #94a3b8;
            max-width: 600px;
            margin: 0 auto 40px;
        }
        .cta-buttons {
            display: flex;
            gap: 16px;
            justify-content: center;
            flex-wrap: wrap;
        }
        .btn {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 14px 32px;
            border-radius: 8px;
            font-size: 1rem;
            font-weight: 600;
            text-decoration: none;
            transition: all 0.2s;
            border: none;
            cursor: pointer;
        }
        .btn-primary {
            background: linear-gradient(90deg, #06b6d4, #10b981);
            color: #fff;
        }
        .btn-primary:hover { transform: translateY(-2px); box-shadow: 0 8px 25px rgba(6, 182, 212, 0.3); }
        .btn-secondary {
            background: #1e293b;
            color: #e2e8f0;
            border: 1px solid #334155;
        }
        .btn-secondary:hover { background: #334155; }
        .features {
            padding: 80px 0;
            background: #0f172a;
        }
        .features h2 {
            text-align: center;
            font-size: 2.5rem;
            margin-bottom: 60px;
            color: #f1f5f9;
        }
        .feature-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 32px;
        }
        .feature-card {
            background: #1e293b;
            border: 1px solid #334155;
            border-radius: 12px;
            padding: 32px;
            transition: all 0.2s;
        }
        .feature-card:hover {
            border-color: #06b6d4;
            transform: translateY(-4px);
        }
        .feature-icon {
            font-size: 2.5rem;
            margin-bottom: 16px;
        }
        .feature-card h3 {
            font-size: 1.3rem;
            color: #f1f5f9;
            margin-bottom: 12px;
        }
        .feature-card p { color: #94a3b8; }
        .pricing {
            padding: 80px 0;
            background: #1e293b;
        }
        .pricing h2 {
            text-align: center;
            font-size: 2.5rem;
            margin-bottom: 60px;
            color: #f1f5f9;
        }
        .pricing-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 24px;
            max-width: 900px;
            margin: 0 auto;
        }
        .pricing-card {
            background: #0f172a;
            border: 1px solid #334155;
            border-radius: 12px;
            padding: 32px;
            text-align: center;
        }
        .pricing-card.popular {
            border-color: #06b6d4;
            position: relative;
        }
        .pricing-card.popular::before {
            content: "MOST POPULAR";
            position: absolute;
            top: -12px;
            left: 50%;
            transform: translateX(-50%);
            background: linear-gradient(90deg, #06b6d4, #10b981);
            color: #fff;
            font-size: 0.75rem;
            font-weight: 700;
            padding: 4px 16px;
            border-radius: 20px;
        }
        .pricing-card h3 { font-size: 1.5rem; color: #f1f5f9; margin-bottom: 8px; }
        .price { font-size: 3rem; font-weight: 800; color: #06b6d4; margin: 16px 0; }
        .price span { font-size: 1rem; color: #94a3b8; }
        .pricing-card ul {
            list-style: none;
            text-align: left;
            margin: 24px 0;
            padding: 0;
        }
        .pricing-card ul li {
            padding: 8px 0;
            color: #94a3b8;
            border-bottom: 1px solid #1e293b;
        }
        .pricing-card ul li::before {
            content: "✓";
            color: #10b981;
            margin-right: 8px;
            font-weight: bold;
        }
        .api-demo {
            padding: 80px 0;
            background: #0f172a;
        }
        .api-demo h2 {
            text-align: center;
            font-size: 2.5rem;
            margin-bottom: 40px;
            color: #f1f5f9;
        }
        .code-block {
            background: #1e293b;
            border: 1px solid #334155;
            border-radius: 8px;
            padding: 24px;
            font-family: 'Consolas', 'Monaco', monospace;
            font-size: 0.9rem;
            overflow-x: auto;
            color: #e2e8f0;
            max-width: 700px;
            margin: 0 auto;
        }
        .code-block .comment { color: #6b7280; }
        .code-block .string { color: #10b981; }
        .code-block .keyword { color: #06b6d4; }
        footer {
            background: #0f172a;
            border-top: 1px solid #334155;
            padding: 40px 0;
            text-align: center;
            color: #64748b;
        }
        .status {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            background: #1e293b;
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 0.85rem;
            margin-top: 20px;
        }
        .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #10b981;
            animation: pulse 2s infinite;
        }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        .local-notice {
            background: #1e293b;
            border: 1px solid #f59e0b;
            border-radius: 8px;
            padding: 20px;
            max-width: 600px;
            margin: 40px auto 0;
            text-align: center;
        }
        .local-notice h3 { color: #f59e0b; margin-bottom: 8px; }
        .local-notice p { color: #94a3b8; }
        .local-notice code {
            background: #0f172a;
            padding: 2px 8px;
            border-radius: 4px;
            font-family: monospace;
            color: #e2e8f0;
        }
        @media (max-width: 768px) {
            h1 { font-size: 2.5rem; }
            .tagline { font-size: 1rem; }
        }
    </style>
</head>
<body>
    <header>
        <div class="container">
            <h1>Q-Mol</h1>
            <p class="tagline">Molecular Informatics &amp; Drug Discovery Platform. Compute descriptors, predict ADMET, and design novel molecules — all from your browser.</p>
            <div class="cta-buttons">
                <a href="#download" class="btn btn-primary">Download for Windows</a>
                <a href="#api" class="btn btn-secondary">API Documentation</a>
            </div>
            <div class="status">
                <span class="status-dot"></span>
                <span>API v2.0.0 Online</span>
            </div>
        </div>
    </header>

    <section class="features">
        <div class="container">
            <h2>Everything You Need for Cheminformatics</h2>
            <div class="feature-grid">
                <div class="feature-card">
                    <div class="feature-icon">🧪</div>
                    <h3>50+ Molecular Descriptors</h3>
                    <p>MW, logP, TPSA, QED, Lipinski rules, and more. Instant computation for any SMILES string.</p>
                </div>
                <div class="feature-card">
                    <div class="feature-icon">🤖</div>
                    <h3>ML ADMET Predictions</h3>
                    <p>Validated models for solubility (logS), hERG inhibition, BBB penetration, and CYP450 metabolism.</p>
                </div>
                <div class="feature-card">
                    <div class="feature-icon">🎯</div>
                    <h3>Drug-Target Interactions</h3>
                    <p>Screen molecules against EGFR, AChE, and BACE1. Predict binding affinity with confidence scores.</p>
                </div>
                <div class="feature-card">
                    <div class="feature-icon">✨</div>
                    <h3>De Novo Design</h3>
                    <p>Generate novel molecules from seed structures. Optimize leads with genetic algorithms.</p>
                </div>
                <div class="feature-card">
                    <div class="feature-icon">🔍</div>
                    <h3>Similarity Search</h3>
                    <p>Find molecules similar to your query. Tanimoto similarity with ECFP4 fingerprints.</p>
                </div>
                <div class="feature-card">
                    <div class="feature-icon">💬</div>
                    <h3>Natural Language Queries</h3>
                    <p>Just type "find molecules like aspirin with good BBB penetration." The AI handles the rest.</p>
                </div>
            </div>
        </div>
    </section>

    <section class="api-demo" id="api">
        <div class="container">
            <h2>Simple, Powerful API</h2>
            <div class="code-block">
<span class="comment"># Get a free API key</span>
<span class="keyword">curl</span> -X POST https://api.qmol.app/v1/signup \
  -H <span class="string">"Content-Type: application/json"</span> \
  -d <span class="string">'{"email": "you@example.com"}'</span>

<span class="comment"># Compute molecular properties</span>
<span class="keyword">curl</span> -X POST https://api.qmol.app/v1/compute \
  -H <span class="string">"x-api-key: YOUR_KEY"</span> \
  -d <span class="string">'{"smiles": ["CCO"]}'</span>

<span class="comment"># Predict ADMET with ML</span>
<span class="keyword">curl</span> -X POST https://api.qmol.app/v1/predict/ml \
  -H <span class="string">"x-api-key: YOUR_KEY"</span> \
  -d <span class="string">'{"smiles": ["c1ccccc1"]}'</span>
            </div>

            <div class="local-notice" id="download">
                <h3>🏠 Self-Hosted Mode</h3>
                <p>Q-Mol is designed to run locally on your own PC. Download the app, run <code>start.bat</code>, and the API is available at <code>http://localhost:8000</code>.</p>
                <p style="margin-top: 12px;">No cloud dependencies. No data leaves your machine.</p>
            </div>
        </div>
    </section>

    <section class="pricing">
        <div class="container">
            <h2>Simple Pricing</h2>
            <div class="pricing-grid">
                <div class="pricing-card">
                    <h3>Free</h3>
                    <div class="price">$0<span>/month</span></div>
                    <ul>
                        <li>500 molecules/month</li>
                        <li>Basic descriptors</li>
                        <li>Community support</li>
                    </ul>
                </div>
                <div class="pricing-card popular">
                    <h3>Research</h3>
                    <div class="price">$20<span>/month</span></div>
                    <ul>
                        <li>10,000 molecules/month</li>
                        <li>All descriptors + ML</li>
                        <li>Email support</li>
                    </ul>
                </div>
                <div class="pricing-card">
                    <h3>Enterprise</h3>
                    <div class="price">Custom</div>
                    <ul>
                        <li>Unlimited molecules</li>
                        <li>SSO + custom models</li>
                        <li>Dedicated support</li>
                    </ul>
                </div>
            </div>
        </div>
    </section>

    <footer>
        <div class="container">
            <p>Q-Mol v2.0.0 &mdash; Molecular Informatics Platform</p>
            <p style="margin-top: 8px; font-size: 0.85rem;">Built with Python, RDKit, and FastAPI. Self-hosted. No data lock-in.</p>
        </div>
    </footer>
</body>
</html>
