## Kubernetes Deployment for Agent Bus

This directory contains Kubernetes manifests for deploying the Agent Bus system.

### Structure

```
k8s/
├── base/                    # Base manifests (environment-agnostic)
│   ├── namespace.yaml
│   ├── configmap.yaml
│   ├── secret.yaml
│   ├── postgres-deployment.yaml
│   ├── redis-deployment.yaml
│   ├── api-deployment.yaml
│   ├── orchestrator-deployment.yaml
│   ├── worker-deployment.yaml
│   ├── ingress.yaml
│   └── kustomization.yaml
├── overlays/
│   ├── dev/                 # Development environment
│   │   └── kustomization.yaml
│   ├── staging/             # Staging environment
│   │   └── kustomization.yaml
│   └── prod/                # Production environment
│       ├── kustomization.yaml
│       └── hpa.yaml
└── README.md
```

### Prerequisites

- Kubernetes cluster (1.28+)
- kubectl configured
- kustomize (built into kubectl 1.14+)
- NGINX Ingress Controller (for ingress)
- cert-manager (for TLS certificates)

### Quick Start

#### Development Deployment

```bash
# Apply all manifests
kubectl apply -k k8s/overlays/dev

# Check deployment status
kubectl get pods -n agent-bus-dev

# Check services
kubectl get svc -n agent-bus-dev

# Port forward to access API locally
kubectl port-forward -n agent-bus-dev svc/dev-api-service 8000:8000
```

#### Production Deployment

```bash
# Update secrets first (see Secrets Management below)
kubectl apply -k k8s/overlays/prod

# Monitor deployment
kubectl rollout status deployment/api -n agent-bus
kubectl rollout status deployment/worker -n agent-bus

# Check HPA status
kubectl get hpa -n agent-bus
```

### Components

#### API (FastAPI)
- **Replicas**: 2 (dev), 3 (prod)
- **Resources**: 1-2 CPU, 1-2Gi memory
- **Auto-scaling**: 2-10 pods (prod)
- **Health checks**: /health endpoint

#### Worker (CPU)
- **Replicas**: 1 (dev), 5 (prod)
- **Resources**: 1-2 CPU, 1-2Gi memory
- **Auto-scaling**: 3-20 pods (prod)

#### Orchestrator
- **Replicas**: 1
- **Resources**: 0.5-1 CPU, 512Mi-1Gi memory

#### PostgreSQL
- **Replicas**: 1
- **Resources**: 0.5-1 CPU, 512Mi-1Gi memory
- **Storage**: 10Gi PVC
- **Note**: Use managed DB in production (RDS, Cloud SQL, etc.)

#### Redis
- **Replicas**: 1
- **Resources**: 0.25-0.5 CPU, 256-512Mi memory
- **Storage**: 5Gi PVC
- **Note**: Use managed Redis in production (ElastiCache, MemoryStore, etc.)

### Secrets Management

**IMPORTANT**: The base secrets are placeholders. Replace them before deployment.

#### Option 1: Manual Update (Development)

```bash
# Create secret with real values
kubectl create secret generic agent-bus-secrets \
  --from-literal=ANTHROPIC_API_KEY=sk-ant-your-key \
  --from-literal=POSTGRES_PASSWORD=your-password \
  -n agent-bus --dry-run=client -o yaml | kubectl apply -f -
```

#### Option 2: Sealed Secrets (Recommended for GitOps)

```bash
# Install sealed-secrets controller
kubectl apply -f https://github.com/bitnami-labs/sealed-secrets/releases/download/v0.24.0/controller.yaml

# Create sealed secret
echo -n 'sk-ant-your-key' | kubectl create secret generic agent-bus-secrets \
  --dry-run=client --from-file=ANTHROPIC_API_KEY=/dev/stdin -o yaml | \
  kubeseal -o yaml > sealed-secret.yaml

# Apply sealed secret
kubectl apply -f sealed-secret.yaml -n agent-bus
```

#### Option 3: External Secrets Operator

```bash
# Install external-secrets
helm repo add external-secrets https://charts.external-secrets.io
helm install external-secrets external-secrets/external-secrets -n external-secrets-system --create-namespace

# Create ExternalSecret pointing to your secrets backend (AWS Secrets Manager, Vault, etc.)
```

### Resource Requirements

#### Minimum Cluster Spec (Development)
- Nodes: 2
- CPU: 4 cores per node
- Memory: 8Gi per node
- Storage: 50Gi

#### Recommended Cluster Spec (Production)
- Nodes: 5-10 (auto-scaling)
- CPU: 8 cores per node
- Memory: 16Gi per node
- Storage: 200Gi+
- GPU nodes: For KAN-89 (GPU workers)

### Networking

#### Ingress
The system uses NGINX Ingress Controller with:
- TLS termination (cert-manager)
- Path-based routing
- SSL redirect

Update the host in `k8s/base/ingress.yaml`:
```yaml
spec:
  tls:
  - hosts:
    - your-domain.com  # Change this
```

#### Services
- `postgres-service`: ClusterIP on 5432
- `redis-service`: ClusterIP on 6379
- `api-service`: ClusterIP on 8000
- Ingress: External access to API

### Monitoring

See [KAN-90](../../docs/K8S.md#monitoring) for Prometheus/Grafana setup.

### Troubleshooting

#### Pods Not Starting

```bash
# Check pod status
kubectl get pods -n agent-bus

# Check logs
kubectl logs -n agent-bus deployment/api
kubectl logs -n agent-bus deployment/worker

# Describe pod for events
kubectl describe pod -n agent-bus <pod-name>
```

#### Database Connection Issues

```bash
# Check postgres pod
kubectl logs -n agent-bus deployment/postgres

# Test connection
kubectl run -it --rm debug --image=postgres:15-alpine --restart=Never -n agent-bus -- \
  psql -h postgres-service -U agent_bus -d agent_bus
```

#### Health Check Failures

```bash
# Check API health endpoint
kubectl port-forward -n agent-bus svc/api-service 8000:8000
curl http://localhost:8000/health
```

### Scaling

#### Manual Scaling

```bash
# Scale API pods
kubectl scale deployment/api --replicas=5 -n agent-bus

# Scale workers
kubectl scale deployment/worker --replicas=10 -n agent-bus
```

#### Auto-Scaling (Production)

HPA is configured for production:
- API: 2-10 pods (70% CPU, 80% memory)
- Workers: 3-20 pods (75% CPU, 85% memory)

Monitor:
```bash
kubectl get hpa -n agent-bus -w
```

### Cleanup

```bash
# Delete development deployment
kubectl delete -k k8s/overlays/dev

# Delete production deployment
kubectl delete -k k8s/overlays/prod

# Delete namespace (WARNING: Deletes all resources)
kubectl delete namespace agent-bus
```

### Next Steps

- [KAN-88](../../docs/HELM.md) - Helm chart deployment
- [KAN-89](../../docs/GPU.md) - GPU worker configuration
- [KAN-90](../../docs/MONITORING.md) - Observability setup
