# Q-Mol Free Hosting Guide
# ==========================
# Ranked by: cost, independence, ease of setup, suitability for Q-Mol
#
# Last updated: 2026-06-29

## TL;DR — Best Options for Q-Mol

| Rank | Platform | Cost | RAM | Best For | Setup Time |
|------|----------|------|-----|----------|------------|
| 1 | **Your PC + Cloudflare Tunnel** | FREE | Whatever you have | Primary / demo | 5 min |
| 2 | **Oracle Cloud Free Tier** | FREE forever | 24 GB ARM | 24/7 production | 30 min |
| 3 | **Render** | FREE | 512 MB | Easy deploy, sleeps | 10 min |
| 4 | **PythonAnywhere** | FREE | 512 MB | Simple Python hosting | 15 min |
| 5 | **Fly.io** | FREE | 256 MB | Docker-native | 20 min |
| 6 | **Google Cloud Run** | FREE tier | 2 GB | Serverless, scales | 30 min |

---

## Option 1: Your PC + Cloudflare Tunnel (RECOMMENDED)

**Cost:** $0
**Independence:** MAXIMUM — runs on your hardware
**Best for:** Primary hosting, demos, harvesting

### Why This Wins
- Zero recurring cost
- Full control over data (molecules never leave your PC)
- Works through any router/NAT (no port forwarding)
- Secure HTTPS tunnel (Cloudflare handles TLS)
- Your PC is probably more powerful than free VPSes

### Setup
```powershell
# 1. Download cloudflared
#    https://github.com/cloudflare/cloudflared/releases
#    Download cloudflared-windows-amd64.exe, rename to cloudflared.exe

# 2. Open PowerShell, authenticate
.\cloudflared.exe tunnel login

# 3. Create a tunnel
.\cloudflared.exe tunnel create qmol

# 4. Route traffic (replace <TUNNEL_ID> with the ID from step 3)
.\cloudflared.exe tunnel route dns qmol photon-bounce.com

# 5. Create config file
mkdir "$env:USERPROFILE\.cloudflared"
@"
tunnel: <TUNNEL_ID>
credentials-file: $env:USERPROFILE\.cloudflared\<TUNNEL_ID>.json
ingress:
  - hostname: qmol.photon-bounce.com
    service: http://localhost:8000
  - service: http_status:404
"@ | Out-File -FilePath "$env:USERPROFILE\.cloudflared\config.yml" -Encoding utf8

# 6. Run the tunnel (in a separate window)
.\cloudflared.exe tunnel run qmol

# 7. In another window, start Q-Mol
cd D:\Qmol-3
.\.venv\Scripts\python -m uvicorn api:app --host 0.0.0.0 --port 8000
```

### Pros
- Truly free, no signup needed beyond Cloudflare (free account)
- Your PC's RAM is the limit (8-32 GB typical)
- Can run 24/7 if you leave PC on
- Data stays local

### Cons
- PC must stay on
- No redundancy if PC crashes
- Your ISP may have upload limits

---

## Option 2: Oracle Cloud Free Tier (BEST for 24/7)

**Cost:** $0 forever (Always Free tier)
**RAM:** 24 GB ARM instance (!)
**Best for:** 24/7 production, team use

### Why This Wins
- 24 GB RAM — enough for Q-Mol + RDKit + ONNX models comfortably
- 4 ARM OCPUs + 24 GB RAM = more powerful than most paid VPSes
- Truly free forever, no credit card tricks
- Full root access (install anything)

### Setup
```bash
# 1. Sign up: https://www.oracle.com/cloud/free/
# 2. Create an Always Free ARM instance (VM.Standard.A1.Flex)
#    Shape: 1 OCPU, 6 GB RAM (minimum) or 4 OCPU, 24 GB RAM (max free)
#    Image: Ubuntu 22.04
# 3. SSH into the instance
# 4. Run the cloud-init script (see deploy/oracle-cloud-init.sh)
```

### Pros
- 24/7 availability without your PC running
- 24 GB RAM handles large molecules + ML models
- Full Linux environment
- Independent from your ISP

### Cons
- Requires signup (email + phone verification)
- ARM architecture (need to build Docker images for ARM)
- Can be terminated if idle for 30 days (just log in monthly)

---

## Option 3: Render (EASIEST)

**Cost:** $0 (free tier)
**RAM:** 512 MB
**Best for:** Quick demo, testing

### Setup
1. Fork/push Q-Mol to GitHub
2. Sign up at https://render.com
3. Create a Web Service, connect your repo
4. Use `render.yaml` (see deploy/render.yaml)

### Pros
- Native Git-based deployment
- Auto-deploys on push
- Built-in HTTPS

### Cons
- **Sleeps after 15 minutes of inactivity** — first request takes ~30s to wake up
- 512 MB RAM may be tight with RDKit (OOM risk)
- No persistent disk (SQLite resets on deploy)

**Workaround for sleep:** Use a cron job to ping /health every 10 minutes.

---

## Option 4: PythonAnywhere (SIMPLEST)

**Cost:** $0 (free tier)
**RAM:** 512 MB
**Best for:** Simple Python apps, learning

### Setup
1. Sign up at https://pythonanywhere.com
2. Upload files via web UI or Git clone
3. Create a web app with Manual Configuration + Python 3.12
4. Set WSGI to use uvicorn + FastAPI
5. Install requirements in a Bash console

### Pros
- Beginner-friendly web UI
- Free MySQL database included
- Good for small-scale testing

### Cons
- Free domain is `yourname.pythonanywhere.com`
- Cannot install RDKit (no conda on free tier) — Q-Mol won't work fully
- Only 1 web app on free tier

---

## Option 5: Fly.io (DOCKER-NATIVE)

**Cost:** $0 (free tier: 3 shared VMs)
**RAM:** 256 MB per VM
**Best for:** Docker containers, edge deployment

### Setup
1. Install flyctl: `powershell -Command "iwr https://fly.io/install.ps1 -useb | iex"`
2. Sign up: `fly auth signup`
3. Deploy: `fly deploy --config deploy/fly.toml`

### Pros
- Docker-native (fly.toml is simple)
- No sleep (VMs stay running)
- Global edge network (fast worldwide)

### Cons
- **256 MB RAM is too small for RDKit** — will likely OOM
- Need to build ARM images for free tier (AMD is paid)
- Fly.io free tier is for hobby projects, not guaranteed

---

## Option 6: Google Cloud Run (SERVERLESS)

**Cost:** $0 (2 million requests/month free)
**RAM:** Up to 2 GB per instance
**Best for:** Event-driven, bursty traffic

### Setup
1. Sign up for Google Cloud Free tier
2. Build and push Docker image to GCR
3. Deploy to Cloud Run

### Pros
- Scales to zero (no cost when idle)
- Generous free tier
- 2 GB RAM option available

### Cons
- **Cold starts** — RDKit initialization takes 5-10s per request
- No persistent storage (SQLite won't work)
- Complex setup (needs gcloud CLI)

---

## Memory Reality Check

Q-Mol memory usage:
- Python + FastAPI: ~50 MB
- RDKit shared libs: ~150-300 MB
- ONNX runtime: ~100 MB
- NumPy/Pandas: ~100 MB
- **Total baseline: ~400-550 MB**
- **With large molecules: +200-500 MB**

**Conclusion:** Free tiers under 512 MB are risky. Your PC or Oracle Cloud (24 GB) are the safest bets.

---

## Recommendation by Use Case

| Use Case | Recommended Setup |
|----------|-------------------|
| Personal research | Your PC + Cloudflare Tunnel |
| Team/company (24/7) | Oracle Cloud Free Tier |
| Quick demo for investors | Render + uptime ping |
| Learning/experimenting | PythonAnywhere (limited RDKit) |
| Mobile app backend | Your PC (always-on) or Oracle Cloud |

---

## Notes
- All free tiers have limits. Read the terms.
- Oracle Cloud "Always Free" genuinely means forever free (as of 2026).
- Cloudflare Tunnel requires a Cloudflare account but no paid plan.
- For self-hosting on your PC, consider a UPS for power outages.
