# Agent Bus Helm Chart

This Helm chart deploys the Agent Bus AI-powered software development automation system on Kubernetes.

## Prerequisites

- Kubernetes 1.20+
- Helm 3.8+
- PV provisioner support in the underlying infrastructure (for persistence)
- (Optional) NVIDIA GPU operator for GPU workloads

## Installing the Chart

### Quick Start (Development)

```bash
# Install with default values
helm install agent-bus ./helm/agent-bus

# Or with dev values
helm install agent-bus ./helm/agent-bus -f ./helm/agent-bus/values-dev.yaml
```

### Production Install

```bash
# Create namespace
kubectl create namespace agent-bus

# Install with production values
helm install agent-bus ./helm/agent-bus \
  --namespace agent-bus \
  -f ./helm/agent-bus/values-prod.yaml \
  --set secrets.anthropicApiKey=<YOUR_API_KEY>
```

## Configuration

The following table lists the configurable parameters and their default values.

### Image Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `image.repository` | Image repository | `ghcr.io/tefj-fun/agent-bus` |
| `image.tag` | Image tag | `latest` |
| `image.pullPolicy` | Image pull policy | `IfNotPresent` |

### Replica Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `replicaCount.api` | Number of API replicas | `2` |
| `replicaCount.cpuWorker` | Number of CPU worker replicas | `3` |

### Service Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `service.type` | Service type | `LoadBalancer` |
| `service.port` | Service port | `80` |
| `service.targetPort` | Container port | `8000` |

### Ingress Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `ingress.enabled` | Enable ingress | `false` |
| `ingress.className` | Ingress class | `nginx` |
| `ingress.hosts` | Ingress hosts | `[{host: agent-bus.local, paths: [{path: /, pathType: Prefix}]}]` |

### Resource Limits

| Parameter | Description | Default |
|-----------|-------------|---------|
| `resources.api.requests.cpu` | API CPU request | `1000m` |
| `resources.api.requests.memory` | API memory request | `1Gi` |
| `resources.cpuWorker.requests.cpu` | Worker CPU request | `1000m` |
| `resources.cpuWorker.requests.memory` | Worker memory request | `2Gi` |

### Redis Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `redis.enabled` | Enable Redis | `true` |
| `redis.master.persistence.enabled` | Enable persistence | `true` |
| `redis.master.persistence.size` | PVC size | `8Gi` |

### PostgreSQL Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `postgresql.enabled` | Enable PostgreSQL | `true` |
| `postgresql.auth.username` | Database username | `agent_bus` |
| `postgresql.auth.password` | Database password | `changeme` |
| `postgresql.auth.database` | Database name | `agent_bus` |
| `postgresql.primary.persistence.size` | PVC size | `10Gi` |

### Application Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `config.logLevel` | Log level | `INFO` |
| `config.anthropicModel` | Anthropic model | `claude-3-5-sonnet-20241022` |
| `secrets.anthropicApiKey` | Anthropic API key | `""` (must be set) |

### GPU Worker Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `gpuWorker.enabled` | Enable GPU workers | `false` |
| `gpuWorker.nodeSelector` | Node selector for GPU nodes | `{nvidia.com/gpu: "true"}` |

### Persistence

| Parameter | Description | Default |
|-----------|-------------|---------|
| `persistence.enabled` | Enable persistence | `true` |
| `persistence.size` | PVC size | `20Gi` |
| `persistence.storageClass` | Storage class | `""` (default) |

### Monitoring

| Parameter | Description | Default |
|-----------|-------------|---------|
| `metrics.enabled` | Enable metrics endpoint | `true` |
| `metrics.serviceMonitor.enabled` | Enable ServiceMonitor | `false` |

## Examples

### Install with custom values

```bash
helm install agent-bus ./helm/agent-bus \
  --set replicaCount.api=3 \
  --set replicaCount.cpuWorker=5 \
  --set secrets.anthropicApiKey=$ANTHROPIC_API_KEY
```

### Enable GPU workers

```bash
helm install agent-bus ./helm/agent-bus \
  --set gpuWorker.enabled=true \
  --set secrets.anthropicApiKey=$ANTHROPIC_API_KEY
```

### Enable ingress with TLS

```bash
helm install agent-bus ./helm/agent-bus \
  --set ingress.enabled=true \
  --set ingress.hosts[0].host=agent-bus.example.com \
  --set ingress.tls[0].secretName=agent-bus-tls \
  --set ingress.tls[0].hosts[0]=agent-bus.example.com
```

### Production deployment with autoscaling

```bash
helm install agent-bus ./helm/agent-bus \
  -f ./helm/agent-bus/values-prod.yaml \
  --set secrets.anthropicApiKey=$ANTHROPIC_API_KEY \
  --set autoscaling.enabled=true \
  --set autoscaling.minReplicas=3 \
  --set autoscaling.maxReplicas=20
```

## Upgrading

```bash
# Upgrade with new values
helm upgrade agent-bus ./helm/agent-bus \
  --reuse-values \
  --set image.tag=v0.2.0
```

## Uninstalling

```bash
# Uninstall the release
helm uninstall agent-bus

# Optionally delete PVCs
kubectl delete pvc -l app.kubernetes.io/instance=agent-bus
```

## Architecture

The chart deploys the following components:

- **API Server**: FastAPI application serving REST API (multiple replicas)
- **CPU Workers**: Worker pool for general tasks (multiple replicas)
- **GPU Workers**: Optional GPU-accelerated workers for ML workloads (job-based)
- **Redis**: Task queue and caching (StatefulSet)
- **PostgreSQL**: Persistent storage (StatefulSet)

## Troubleshooting

### Check pod status

```bash
kubectl get pods -l app.kubernetes.io/name=agent-bus
```

### View logs

```bash
# API logs
kubectl logs -l app.kubernetes.io/component=api

# Worker logs
kubectl logs -l app.kubernetes.io/component=cpu-worker

# Redis logs
kubectl logs -l app.kubernetes.io/component=redis
```

### Check health

```bash
# Port forward to API
kubectl port-forward svc/agent-bus-api 8000:80

# Check health endpoint
curl http://localhost:8000/health
```

### Common Issues

**Pod stuck in Pending**: Check PVC status and storage class availability
```bash
kubectl get pvc
kubectl describe pvc agent-bus-data
```

**API unhealthy**: Check Redis and PostgreSQL connectivity
```bash
kubectl logs -l app.kubernetes.io/component=api --tail=100
```

**GPU workers not scheduling**: Ensure GPU nodes are available and labeled
```bash
kubectl get nodes -l nvidia.com/gpu=true
```

## Monitoring

The chart exposes Prometheus metrics at `/metrics` endpoint.

### ServiceMonitor

Enable Prometheus Operator ServiceMonitor:

```bash
helm upgrade agent-bus ./helm/agent-bus \
  --set metrics.serviceMonitor.enabled=true
```

### Metrics Available

- `agent_bus_projects_total` - Total projects created
- `agent_bus_projects_by_stage` - Projects by workflow stage
- `agent_bus_stage_duration_seconds` - Stage completion time
- `agent_bus_agent_invocations_total` - Agent invocations
- `agent_bus_llm_tokens_total` - LLM token usage
- `agent_bus_errors_total` - Error counts
- And more...

## License

See repository LICENSE file.
