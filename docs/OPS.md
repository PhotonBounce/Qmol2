# Q-Mol Operations Guide (OPS.md)

## Table of Contents
- [Overview](#overview)
- [Deployment Guide](#deployment-guide)
- [Scaling Instructions](#scaling-instructions)
- [Monitoring Setup](#monitoring-setup)
- [Troubleshooting Runbook](#troubleshooting-runbook)
- [Backup / Restore Procedures](#backup--restore-procedures)

---

## Overview

Q-Mol runs on Kubernetes as a Helm-managed application with the following stack:

| Layer | Component | Notes |
|---|---|---|
| Ingress | nginx-ingress + cert-manager | TLS termination via Let's Encrypt |
| API | FastAPI (3 replicas default) | HPA: 2–20 pods |
| Workers | Celery (5 replicas default) | HPA: 2–30 pods |
| Quantum Worker | Celery `-Q quantum` (1 replica) | Dedicated queue for quantum jobs |
| Dashboard | React + Nginx (2 replicas) | Static build served by Nginx |
| Flower | Celery monitoring (1 replica) | `/flower` path via ingress |
| Database | PostgreSQL (Bitnami sub-chart) | 50Gi PVC |
| Cache | Redis (Bitnami sub-chart) | 10Gi PVC, standalone mode |
| Observability | Prometheus + Grafana + Loki + Jaeger | ServiceMonitors, alerts, dashboards |

All services run in the `qmol` namespace.

---

## Deployment Guide

### Prerequisites

- Kubernetes 1.28+ cluster
- Helm 3.14+
- kubectl configured
- nginx-ingress controller installed
- cert-manager installed (for TLS)
- Prometheus Operator installed (for ServiceMonitors and PrometheusRules)

### Environment Variables

Export these before running `deploy_k8s.sh`:

```bash
export QMOL_ADMIN_TOKEN="your-secure-token"
export STRIPE_SECRET_KEY="sk_live_..."
export STRIPE_WEBHOOK_SECRET="whsec_..."
export MAILGUN_API_KEY="key-..."
export MAILGUN_DOMAIN="mg.qmol.app"
export HF_TOKEN="hf_..."
export HF_REPO_ID="photonbounce/qmol-dataset"
export IBM_QUANTUM_TOKEN="ibm_..."
export AWS_BRAKET_ROLE_ARN="arn:aws:iam::..."
```

### Quick Deploy

```bash
# Deploy everything
./scripts/deploy_k8s.sh v2.0.1

# Or deploy manually with Helm
helm upgrade --install qmol ./helm/qmol \
  --namespace qmol --create-namespace \
  --set image.tag=v2.0.1 \
  --set secrets.qmol_admin_token=$QMOL_ADMIN_TOKEN \
  --set secrets.stripe_secret_key=$STRIPE_SECRET_KEY
```

### Verify Deployment

```bash
kubectl get pods -n qmol
kubectl get svc -n qmol
kubectl get ingress -n qmol
helm list -n qmol
helm test qmol -n qmol
```

---

## Scaling Instructions

### Horizontal Scaling (HPA)

The API and workers are configured with HPA out of the box.

```bash
# View current HPA status
kubectl get hpa -n qmol

# Manually scale API (if HPA is disabled)
kubectl scale deployment qmol-api --replicas=5 -n qmol

# Manually scale workers
kubectl scale deployment qmol-worker --replicas=10 -n qmol
```

### Vertical Scaling (Resource Limits)

Edit `helm/qmol/values.yaml` or override at deploy time:

```bash
helm upgrade --install qmol ./helm/qmol \
  --set resources.api.limits.cpu=3000m \
  --set resources.api.limits.memory=4Gi \
  --set resources.worker.limits.cpu=6000m \
  --set resources.worker.limits.memory=12Gi
```

### Queue-Triggered Scaling (KEDA)

For advanced scaling based on Celery queue depth, install KEDA:

```bash
helm repo add kedacore https://kedacore.github.io/charts
helm install keda kedacore/keda --namespace keda --create-namespace
```

Then apply a `ScaledObject` for the worker:

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: qmol-worker-scaledobject
  namespace: qmol
spec:
  scaleTargetRef:
    name: qmol-worker
  pollingInterval: 10
  cooldownPeriod: 300
  minReplicaCount: 2
  maxReplicaCount: 30
  triggers:
    - type: redis
      metadata:
        address: qmol-redis-master:6379
        listName: celery
        listLength: "100"
```

---

## Monitoring Setup

### Prometheus + Grafana

1. **Install Prometheus Operator** (if not already installed):
   ```bash
   helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
   helm install prometheus prometheus-community/kube-prometheus-stack \
     --namespace monitoring --create-namespace
   ```

2. **Apply Q-Mol monitoring resources**:
   ```bash
   kubectl apply -f k8s/prometheus/servicemonitor.yaml -n qmol
   kubectl apply -f k8s/prometheus/prometheus-rules.yaml -n qmol
   ```

3. **Import Grafana dashboard**:
   - Go to Grafana → Dashboards → Import
   - Upload `k8s/grafana/dashboards/qmol-api.json`
   - Select your Prometheus data source

### Loki (Log Aggregation)

1. **Install Loki**:
   ```bash
   helm install loki grafana/loki --namespace monitoring --create-namespace
   ```

2. **Deploy Promtail** (log shipping):
   ```bash
   kubectl apply -f k8s/loki/promtail-daemonset.yaml -n qmol
   ```

3. **Query logs in Grafana**:
   ```
   {namespace="qmol", app="qmol"}
   {namespace="qmol", container="api"} |= "ERROR"
   {namespace="qmol", component="worker"} |= "task succeeded"
   ```

### Jaeger (Distributed Tracing)

1. **Deploy Jaeger**:
   ```bash
   kubectl apply -f k8s/jaeger/jaeger-deployment.yaml -n qmol
   ```

2. **Access Jaeger UI**: `https://traces.qmol.app`

3. **Instrument FastAPI** (add to `api.py` if not already present):
   ```python
   from opentelemetry import trace
   from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
   FastAPIInstrumentor.instrument_app(app)
   ```

---

## Troubleshooting Runbook

### 1. Pods Not Starting

```bash
# Check pod status and events
kubectl describe pod -l app.kubernetes.io/name=qmol -n qmol
kubectl logs -l app.kubernetes.io/component=api -n qmol --tail=100

# Common causes:
# - ImagePullBackOff: Check image tag and registry credentials
# - CrashLoopBackOff: Check app logs and readiness/liveness probes
# - Pending: Check resource quotas and node capacity
```

### 2. High Latency (P95 > 2s)

```bash
# Check DB connection pool
kubectl exec -it deploy/qmol-api -n qmol -- python -c "import asyncio; from src.db import check_pool; asyncio.run(check_pool())"

# Check Redis latency
kubectl exec -it deploy/qmol-redis-master -n qmol -- redis-cli --latency

# Check for slow queries in PostgreSQL
kubectl exec -it deploy/qmol-postgresql-0 -n qmol -- psql -U qmol -c "SELECT * FROM pg_stat_activity WHERE state = 'active';"
```

### 3. High Error Rate (5xx > 5%)

```bash
# Get recent error logs
kubectl logs -l app.kubernetes.io/component=api -n qmol --tail=500 | grep -i "error\|exception\|traceback"

# Check if DB is reachable
kubectl exec -it deploy/qmol-api -n qmol -- python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8000/health').read())"

# Restart API pods if needed
kubectl rollout restart deployment/qmol-api -n qmol
```

### 4. Celery Queue Backlog

```bash
# Check queue depth
kubectl exec -it deploy/qmol-flower -n qmol -- celery -A src.celery_app inspect active
kubectl exec -it deploy/qmol-flower -n qmol -- celery -A src.celery_app inspect reserved

# Scale workers
kubectl scale deployment qmol-worker --replicas=20 -n qmol

# Purge queue (emergency only)
kubectl exec -it deploy/qmol-worker -n qmol -- celery -A src.celery_app purge
```

### 5. Database Connection Saturation

```bash
# Check active connections
kubectl exec -it deploy/qmol-postgresql-0 -n qmol -- psql -U qmol -c "SELECT count(*) FROM pg_stat_activity;"

# Increase max_connections (temporary)
kubectl exec -it deploy/qmol-postgresql-0 -n qmol -- psql -U qmol -c "ALTER SYSTEM SET max_connections = 200; SELECT pg_reload_conf();"

# Long-term: increase connection pool size in API or add PgBouncer
```

### 6. TLS / Ingress Issues

```bash
# Check certificate status
kubectl get certificate -n qmol
kubectl describe certificate qmol-tls -n qmol

# Check ingress
kubectl get ingress -n qmol
kubectl describe ingress qmol -n qmol

# Force certificate renewal
kubectl delete secret qmol-tls -n qmol
kubectl cert-manager renew --namespace=qmol
```

### 7. Worker Pod Crash Looping

```bash
# Check worker logs
kubectl logs -l app.kubernetes.io/component=worker -n qmol --previous --tail=200

# Check for OOMKilled
kubectl get pods -n qmol -o wide | grep worker
kubectl describe pod <worker-pod-name> -n qmol | grep -A 5 "Last State"

# Increase memory limits if OOMKilled
helm upgrade qmol ./helm/qmol --set resources.worker.limits.memory=12Gi -n qmol
```

---

## Backup / Restore Procedures

### PostgreSQL Backup

```bash
# Create a backup
kubectl exec -it deploy/qmol-postgresql-0 -n qmol -- pg_dump -U qmol -d qmol > qmol-backup-$(date +%Y%m%d-%H%M%S).sql

# Automated backup via CronJob
kubectl apply -f - <<EOF
apiVersion: batch/v1
kind: CronJob
metadata:
  name: qmol-pg-backup
  namespace: qmol
spec:
  schedule: "0 2 * * *"
  jobTemplate:
    spec:
      template:
        spec:
          containers:
            - name: pg-backup
              image: postgres:15-alpine
              command:
                - sh
                - -c
                - "pg_dump -h qmol-postgresql -U qmol -d qmol | gzip > /backup/qmol-$(date +%Y%m%d).sql.gz"
              env:
                - name: PGPASSWORD
                  valueFrom:
                    secretKeyRef:
                      name: qmol-secrets
                      key: postgres-password
              volumeMounts:
                - name: backup
                  mountPath: /backup
          volumes:
            - name: backup
              persistentVolumeClaim:
                claimName: qmol-backup-pvc
          restartPolicy: OnFailure
EOF
```

### PostgreSQL Restore

```bash
# Restore from backup
kubectl exec -i deploy/qmol-postgresql-0 -n qmol -- psql -U qmol -d qmol < qmol-backup-20240628.sql

# Or restore with pg_restore (if using custom format)
kubectl exec -i deploy/qmol-postgresql-0 -n qmol -- pg_restore -U qmol -d qmol --clean --if-exists < qmol-backup.dump
```

### Redis Backup

```bash
# Trigger BGSAVE
kubectl exec -it deploy/qmol-redis-master -n qmol -- redis-cli BGSAVE

# Copy RDB file
kubectl cp qmol/qmol-redis-master-0:/data/dump.rdb ./redis-backup-$(date +%Y%m%d).rdb
```

### Disaster Recovery (DR)

For full disaster recovery, ensure:
1. PostgreSQL backups are stored off-cluster (S3, GCS, etc.)
2. Redis persistence is enabled (AOF + RDB)
3. Q-Mol data volumes (`/app/data`, `/app/jobs`) are backed up
4. Helm values and K8s manifests are version-controlled in Git

```bash
# Example: sync backups to S3
aws s3 sync ./backups/ s3://qmol-backups/production/
```

---

## Security Checklist

- [ ] Secrets are managed via K8s Secrets or external secret manager (Vault, AWS SM)
- [ ] NetworkPolicies restrict pod-to-pod traffic to minimum required
- [ ] PodSecurityContext enforces `runAsNonRoot: true`
- [ ] SecurityContext drops all capabilities
- [ ] Ingress uses TLS 1.2+ with strong cipher suites
- [ ] HPA prevents resource exhaustion under load
- [ ] PDBs ensure minimum availability during node drains
- [ ] Trivy scans run in CI for every build
- [ ] Prometheus alerts are configured and routed to PagerDuty/Opsgenie

---

## Contact

- **On-call**: `oncall@qmol.app`
- **Slack**: `#qmol-ops`
- **Runbook**: `https://wiki.qmol.app/runbooks`
