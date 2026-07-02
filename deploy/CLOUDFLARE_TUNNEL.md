# Q-Mol Deployment Guide + Cloudflare Tunnel
# ===========================================
# Deploy Q-Mol on YOUR PC (free, always-on) and expose it via Cloudflare Tunnel
# No port forwarding, no dynamic DNS, no IP changes — just a stable URL.
#
# Your app runs at: https://api.photon-bounce.com (or any subdomain you want)
# Your microsite stays at: https://photon-bounce.com/qmol/

## Prerequisites
- Windows 10/11 PC with 8+ GB RAM
- Q-Mol installed and running locally (`python -m uvicorn api:app --host 0.0.0.0 --port 8000`)
- Cloudflare account (free at https://dash.cloudflare.com/sign-up)
- Domain: photon-bounce.com (already configured in Cloudflare)

## Step 1: Download Cloudflare Tunnel (cloudflared)

Open PowerShell as Administrator:

```powershell
# Download the latest Windows binary
$version = "2025.6.0"  # Check https://github.com/cloudflare/cloudflared/releases for latest
$url = "https://github.com/cloudflare/cloudflared/releases/download/$version/cloudflared-windows-amd64.exe"
$out = "$env:TEMP\cloudflared.exe"
Invoke-WebRequest -Uri $url -OutFile $out
Copy-Item $out "$env:LOCALAPPDATA\Microsoft\WindowsApps\cloudflared.exe" -Force
cloudflared --version
```

## Step 2: Login and Create Tunnel

```powershell
# Login (opens browser, select photon-bounce.com zone)
cloudflared tunnel login

# Create a tunnel named "qmol"
cloudflared tunnel create qmol
# Note the Tunnel ID (looks like a UUID) — save it!
```

## Step 3: Configure DNS Route

```powershell
# Route api.photon-bounce.com to your tunnel
# Replace <TUNNEL_ID> with the actual UUID from Step 2
cloudflared tunnel route dns qmol api.photon-bounce.com
```

## Step 4: Create Config File

```powershell
# Create config directory
$cloudflareDir = "$env:USERPROFILE\.cloudflared"
New-Item -ItemType Directory -Force -Path $cloudflareDir

# Write config (replace <TUNNEL_ID> with actual UUID)
$config = @"
tunnel: <TUNNEL_ID>
credentials-file: $cloudflareDir\<TUNNEL_ID>.json

# Auto-start on Windows boot
# (Install as a service — see Step 7)

ingress:
  # Route API requests to your local Q-Mol server
  - hostname: api.photon-bounce.com
    service: http://localhost:8000
    originRequest:
      noTLSVerify: true
  
  # Route the dashboard to the React app (if you want it on a subdomain)
  # - hostname: dash.photon-bounce.com
  #   service: http://localhost:3000

  # Catch-all: return 404
  - service: http_status:404
"@

$config | Out-File -FilePath "$cloudflareDir\config.yml" -Encoding utf8
```

## Step 5: Start Everything

Open TWO PowerShell windows:

**Window 1 — Q-Mol Server:**
```powershell
cd D:\Qmol-3
.venv\Scripts\python -m uvicorn api:app --host 0.0.0.0 --port 8000 --workers 1
```

**Window 2 — Cloudflare Tunnel:**
```powershell
cloudflared tunnel run qmol
```

## Step 6: Verify

Open your browser:
- https://api.photon-bounce.com/health → should return `{"status": "ok", "version": "2.0.0"}`
- https://api.photon-bounce.com/v1/compute (POST with SMILES) → should compute descriptors
- https://api.photon-bounce.com/docs → FastAPI Swagger UI

## Step 7: Run as Windows Service (Auto-start on Boot)

```powershell
# Install as a Windows service (requires admin)
cloudflared service install
# Start the service
cloudflared service start
# Set to auto-start
Set-Service -Name "cloudflared" -StartupType Automatic
```

Then create a Windows Task Scheduler entry for Q-Mol:
1. Open Task Scheduler → Create Basic Task
2. Name: `Q-Mol Server`
3. Trigger: `When the computer starts`
4. Action: `Start a program`
5. Program: `D:\Qmol-3\.venv\Scripts\python.exe`
6. Arguments: `-m uvicorn api:app --host 0.0.0.0 --port 8000 --workers 1`
7. Start in: `D:\Qmol-3`
8. Check "Run whether user is logged on or not"
9. Check "Run with highest privileges"

## Step 8: Update Your Microsite

Your PHP microsite at `photon-bounce.com/qmol/` should point to the API:

```javascript
// In your microsite JS, change API URL from placeholder to real:
const API_BASE = "https://api.photon-bounce.com/v1";

// Example: signup
fetch(`${API_BASE}/signup`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ email: "user@example.com" })
})
```

## Step 9: Keep PC Running 24/7

For a harvesting instance that earns money, your PC needs to stay on:

1. **Disable sleep mode:**
   ```powershell
   powercfg /change standby-timeout-ac 0
   powercfg /change hibernate-timeout-ac 0
   ```

2. **Use a UPS (Uninterruptible Power Supply):** ~$60-100 for basic 600VA unit. Keeps server running through power outages.

3. **Enable automatic restart:** Windows Update can reboot. Set active hours or disable automatic reboots.

## Monitoring

Add these to the microsite or a separate status page:

```bash
# Check if API is alive
curl https://api.photon-bounce.com/health

# Check if tunnel is running
cloudflared tunnel info qmol
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Tunnel says "ERR_CONNECTION_REFUSED" | Q-Mol server isn't running on port 8000 |
| `cloudflared tunnel login` fails | Browser popup blocked. Use `cloudflared tunnel login --url` |
| API works but microsite shows CORS errors | Add `ALLOWED_ORIGINS=https://photon-bounce.com` to `.env` |
| PC sleeps overnight | Disable sleep in Power Settings |
| Tunnel disconnects | Check internet connection. Use `cloudflared service install` for auto-restart |

## Cost Breakdown

| Item | Cost | Notes |
|------|------|-------|
| Cloudflare account | $0 | Free plan includes tunnels |
| Cloudflare Tunnel | $0 | Unlimited bandwidth, free |
| Domain (photon-bounce.com) | Already paid | Via hostupon.com |
| Your PC electricity | ~$15-30/month | 24/7 PC ~50-100W = 36-72 kWh/month |
| UPS (optional) | ~$60 one-time | Protects from power outages |
| **Total monthly** | **$15-30** | vs $50-100 for equivalent VPS |

## Next: Oracle Cloud (Backup / Scale)

If your PC goes down or you want redundancy, spin up Oracle Cloud Free Tier as a hot backup:
- See `deploy/oracle-cloud-init.sh` for automated setup
- Same Cloudflare Tunnel can point to Oracle Cloud as failover

---
*Last updated: 2026-06-30*
