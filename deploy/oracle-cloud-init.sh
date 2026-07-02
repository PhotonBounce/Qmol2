#!/bin/bash
# Q-Mol Oracle Cloud Free Tier Cloud-Init Script
# =============================================
# Run this on an Oracle Cloud Always Free ARM instance (Ubuntu 22.04)
# This sets up Q-Mol with Docker, RDKit, and auto-restart on boot.
#
# Steps BEFORE running this script:
# 1. Sign up at https://www.oracle.com/cloud/free/
# 2. Create a VM: Shape = VM.Standard.A1.Flex (1-4 OCPUs, 6-24 GB RAM)
# 3. Image = Ubuntu 22.04, Generate SSH key pair, download private key
# 4. Open ports 22 (SSH), 8000 (API), 443 (HTTPS) in security list
# 5. SSH into the instance: ssh -i ~/.ssh/your-key ubuntu@YOUR_PUBLIC_IP
# 6. Run this script: sudo bash oracle-cloud-init.sh

set -e

APP_DIR="/opt/qmol"
DATA_DIR="/opt/qmol/data"

echo "=== Q-Mol Oracle Cloud Deployment ==="
echo "This will install Docker, Python, and deploy Q-Mol on port 8000"

# 1. Update system
echo "[1/8] Updating system packages..."
apt-get update -qq
apt-get install -y -qq \
    git curl wget unzip python3 python3-pip python3-venv \
    build-essential libffi-dev libssl-dev \
    sqlite3 redis-tools

# 2. Install Docker (official Docker repo, not distro version)
echo "[2/8] Installing Docker..."
apt-get install -y -qq ca-certificates gnupg
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" > /etc/apt/sources.list.d/docker.list
apt-get update -qq
apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
systemctl enable docker
systemctl start docker
usermod -aG docker ubuntu

# 3. Create app directory
echo "[3/8] Setting up app directory..."
mkdir -p "$APP_DIR" "$DATA_DIR"
chown -R ubuntu:ubuntu "$APP_DIR" "$DATA_DIR"

# 4. Clone Q-Mol (or copy from local — replace with your repo when ready)
# For now, we'll create a placeholder. In production, you'd git clone your repo here.
echo "[4/8] Setting up Q-Mol code..."
cd "$APP_DIR"
# If you have a GitHub repo:
# git clone https://github.com/yourusername/qmol.git .
# For now, we'll create a note:
cat > README.txt << 'EOF'
Q-Mol Production Instance
=========================
Place the Q-Mol source code here:
  - api.py
  - src/
  - requirements.txt
  - config.py
  - .env

Then run:
  docker compose -f docker-compose.prod.yml up -d

The API will be available at http://localhost:8000
Use nginx or Cloudflare Tunnel for HTTPS.
EOF

# 5. Create production docker-compose
echo "[5/8] Creating production Docker Compose..."
cat > "$APP_DIR/docker-compose.prod.yml" << 'EOF'
version: "3.8"

services:
  qmol-api:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: qmol-api
    restart: always
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=sqlite+aiosqlite:///data/qmol.sqlite
      - USE_POSTGRES=false
      - REDIS_URL=redis://redis:6379/0
      - API_KEY_PEPPER=${API_KEY_PEPPER:-changeme}
      - QMOL_ADMIN_TOKEN=${QMOL_ADMIN_TOKEN:-admin-secret}
      - ALLOWED_ORIGINS=https://photon-bounce.com,https://api.photon-bounce.com
    volumes:
      - /opt/qmol/data:/app/data
      - /opt/qmol/logs:/app/logs
    depends_on:
      - redis
    command: >
      sh -c "python -m uvicorn api:app --host 0.0.0.0 --port 8000 --workers 1"

  redis:
    image: redis:7-alpine
    container_name: qmol-redis
    restart: always
    volumes:
      - redis-data:/data
    command: redis-server --appendonly yes --maxmemory 256mb --maxmemory-policy allkeys-lru

  worker:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: qmol-worker
    restart: always
    environment:
      - DATABASE_URL=sqlite+aiosqlite:///data/qmol.sqlite
      - USE_POSTGRES=false
      - REDIS_URL=redis://redis:6379/0
      - API_KEY_PEPPER=${API_KEY_PEPPER:-changeme}
    volumes:
      - /opt/qmol/data:/app/data
    depends_on:
      - redis
    command: >
      sh -c "celery -A src.celery_app worker --loglevel=info --concurrency=2"

volumes:
  redis-data:
EOF

# 6. Create production Dockerfile (if not already present)
echo "[6/8] Creating production Dockerfile..."
cat > "$APP_DIR/Dockerfile" << 'EOF'
FROM python:3.12-slim-bookworm

WORKDIR /app

# Install system deps for RDKit
RUN apt-get update -qq && apt-get install -y -qq \
    build-essential libffi-dev libssl-dev \
    sqlite3 libsqlite3-dev \
    && rm -rf /var/lib/apt/lists/*

# Install RDKit
RUN pip install --no-cache-dir rdkit==2024.3.1

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY . .

# Create data directory
RUN mkdir -p /app/data /app/logs

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
EOF

# 7. Create systemd service for auto-restart
echo "[7/8] Creating systemd service..."
cat > /etc/systemd/system/qmol.service << 'EOF'
[Unit]
Description=Q-Mol Molecular API Server
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/qmol
ExecStart=/usr/bin/docker compose -f docker-compose.prod.yml up -d
ExecStop=/usr/bin/docker compose -f docker-compose.prod.yml down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable qmol.service

# 8. Install nginx as reverse proxy (optional but recommended for SSL)
echo "[8/8] Installing nginx (optional reverse proxy)..."
apt-get install -y -qq nginx

cat > /etc/nginx/sites-available/qmol << 'EOF'
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /metrics {
        # Metrics are protected by API key
        proxy_pass http://localhost:8000/metrics;
    }
}
EOF

ln -sf /etc/nginx/sites-available/qmol /etc/nginx/sites-enabled/qmol
rm -f /etc/nginx/sites-enabled/default
systemctl enable nginx
systemctl restart nginx

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Next steps:"
echo "1. Copy your Q-Mol source code to /opt/qmol/"
echo "2. Set environment variables in /opt/qmol/.env"
echo "3. Run: sudo systemctl start qmol"
echo "4. The API will be available at: http://YOUR_PUBLIC_IP"
echo "5. For HTTPS, install certbot: sudo certbot --nginx -d your-domain.com"
echo ""
echo "To check status:"
echo "  sudo systemctl status qmol"
echo "  sudo docker logs -f qmol-api"
echo "  sudo docker logs -f qmol-worker"
