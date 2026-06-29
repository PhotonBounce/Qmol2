#!/bin/bash
set -euo pipefail

# Q-Mol Kubernetes Deploy Script
# Usage: ./scripts/deploy_k8s.sh <image_tag>
# Requires: helm, kubectl, env vars QMOL_ADMIN_TOKEN, STRIPE_SECRET_KEY

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CHART_DIR="${SCRIPT_DIR}/../helm/qmol"
NAMESPACE="qmol"
IMAGE_TAG="${1:-latest}"

echo "=== Q-Mol Kubernetes Deployment ==="
echo "Namespace: ${NAMESPACE}"
echo "Image tag: ${IMAGE_TAG}"
echo "Chart: ${CHART_DIR}"
echo ""

# Check dependencies
for cmd in helm kubectl; do
  if ! command -v "${cmd}" &>/dev/null; then
    echo "Error: ${cmd} is not installed." >&2
    exit 1
  fi
done

# Check required secrets
if [[ -z "${QMOL_ADMIN_TOKEN:-}" ]]; then
  echo "Warning: QMOL_ADMIN_TOKEN is not set." >&2
fi
if [[ -z "${STRIPE_SECRET_KEY:-}" ]]; then
  echo "Warning: STRIPE_SECRET_KEY is not set." >&2
fi

# Ensure namespace exists
echo "Ensuring namespace ${NAMESPACE}..."
kubectl create namespace "${NAMESPACE}" --dry-run=client -o yaml | kubectl apply -f -

# Deploy raw manifests
echo "Applying raw K8s manifests..."
kubectl apply -f "${SCRIPT_DIR}/../k8s/namespace.yaml" --namespace "${NAMESPACE}"
kubectl apply -f "${SCRIPT_DIR}/../k8s/rbac.yaml" --namespace "${NAMESPACE}"
kubectl apply -f "${SCRIPT_DIR}/../k8s/network-policy.yaml" --namespace "${NAMESPACE}"
kubectl apply -f "${SCRIPT_DIR}/../k8s/pdb.yaml" --namespace "${NAMESPACE}"

# Deploy Helm chart
echo "Deploying Helm chart..."
helm upgrade --install qmol "${CHART_DIR}" \
  --namespace "${NAMESPACE}" \
  --set image.tag="${IMAGE_TAG}" \
  --set secrets.qmol_admin_token="${QMOL_ADMIN_TOKEN:-change-me}" \
  --set secrets.stripe_secret_key="${STRIPE_SECRET_KEY:-}" \
  --set secrets.stripe_webhook_secret="${STRIPE_WEBHOOK_SECRET:-}" \
  --set secrets.mailgun_api_key="${MAILGUN_API_KEY:-}" \
  --set secrets.mailgun_domain="${MAILGUN_DOMAIN:-}" \
  --set secrets.hf_token="${HF_TOKEN:-}" \
  --set secrets.hf_repo_id="${HF_REPO_ID:-}" \
  --set secrets.ibm_quantum_token="${IBM_QUANTUM_TOKEN:-}" \
  --set secrets.aws_braket_role_arn="${AWS_BRAKET_ROLE_ARN:-}" \
  --wait \
  --timeout 600s

# Deploy observability
echo "Deploying observability stack..."
kubectl apply -f "${SCRIPT_DIR}/../k8s/prometheus/servicemonitor.yaml" --namespace "${NAMESPACE}"
kubectl apply -f "${SCRIPT_DIR}/../k8s/prometheus/prometheus-rules.yaml" --namespace "${NAMESPACE}"
kubectl apply -f "${SCRIPT_DIR}/../k8s/loki/promtail-daemonset.yaml" --namespace "${NAMESPACE}"
kubectl apply -f "${SCRIPT_DIR}/../k8s/jaeger/jaeger-deployment.yaml" --namespace "${NAMESPACE}"

echo ""
echo "=== Deployment complete ==="
echo "API:        https://qmol.app"
echo "Dashboard:  https://qmol.app/dashboard"
echo "Flower:     https://qmol.app/flower"
echo "Jaeger:     https://traces.qmol.app"
echo ""
echo "Check status:"
echo "  kubectl get pods -n ${NAMESPACE}"
echo "  kubectl get svc -n ${NAMESPACE}"
echo "  kubectl get ingress -n ${NAMESPACE}"
