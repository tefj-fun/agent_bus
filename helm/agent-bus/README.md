# Agent Bus Helm Chart

Helm chart for deploying the Agent Bus multi-agent SWE engineering system to Kubernetes.

## Prerequisites

- Kubernetes 1.28+
- Helm 3.10+
- PV provisioner support in the underlying infrastructure
- NGINX Ingress Controller (for ingress)
- cert-manager (for TLS certificates, optional)

## Installing the Chart

### Development

```bash
helm install agent-bus ./helm/agent-bus \
  --namespace agent-bus-dev \
  --create-namespace \
  --values ./helm/agent-bus/values-dev.yaml \
  --set secrets.anthropic.value="sk-ant-your-key" \
  --set secrets.postgres.value="dev-password"
```

### Production

```bash
# Ensure secrets are created first (see Secrets Management below)

helm install agent-bus ./helm/agent-bus \
  --namespace agent-bus \
  --create-namespace \
  --values ./helm/agent-bus/values-prod.yaml
```

## Upgrading

```bash
helm upgrade agent-bus ./helm/agent-bus \
  --namespace agent-bus \
  --values ./helm/agent-bus/values-prod.yaml
```

## Uninstalling

```bash
helm uninstall agent-bus --namespace agent-bus
```

## Configuration

The following table lists the configurable parameters and their default values.

### Global Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `global.imagePullSecrets` | Image pull secrets | `[]` |
| `global.storageClass` | Storage class for PVCs | `standard` |
| `namespace` | Kubernetes namespace | `agent-bus` |

### Image Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `image.repository` | Image repository | `agent_bus` |
| `image.tag` | Image tag | `latest` |
| `image.pullPolicy` | Image pull policy | `IfNotPresent` |

### API Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `api.enabled` | Enable API deployment | `true` |
| `api.replicaCount` | Number of replicas | `2` |
| `api.autoscaling.enabled` | Enable HPA | `true` |
| `api.autoscaling.minReplicas` | Minimum replicas | `2` |
| `api.autoscaling.maxReplicas` | Maximum replicas | `10` |
| `api.resources.requests.cpu` | CPU request | `1000m` |
| `api.resources.requests.memory` | Memory request | `1Gi` |
| `api.service.type` | Service type | `ClusterIP` |
| `api.service.port` | Service port | `8000` |

### Worker Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `worker.enabled` | Enable worker deployment | `true` |
| `worker.replicaCount` | Number of replicas | `3` |
| `worker.autoscaling.enabled` | Enable HPA | `true` |
| `worker.autoscaling.minReplicas` | Minimum replicas | `3` |
| `worker.autoscaling.maxReplicas` | Maximum replicas | `20` |
| `worker.persistence.size` | Workspace PVC size | `20Gi` |

### PostgreSQL Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `postgresql.enabled` | Enable embedded PostgreSQL | `true` |
| `postgresql.external.enabled` | Use external PostgreSQL | `false` |
| `postgresql.external.host` | External PostgreSQL host | `""` |
| `postgresql.persistence.size` | PVC size | `10Gi` |

### Redis Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `redis.enabled` | Enable embedded Redis | `true` |
| `redis.external.enabled` | Use external Redis | `false` |
| `redis.external.host` | External Redis host | `""` |
| `redis.persistence.size` | PVC size | `5Gi` |

### Secrets Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `secrets.anthropic.existingSecret` | Use existing secret for Anthropic API key | `""` |
| `secrets.anthropic.value` | Anthropic API key (if not using existingSecret) | `""` |
| `secrets.postgres.existingSecret` | Use existing secret for PostgreSQL password | `""` |
| `secrets.postgres.value` | PostgreSQL password (if not using existingSecret) | `""` |

### Ingress Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `ingress.enabled` | Enable ingress | `false` |
| `ingress.className` | Ingress class name | `nginx` |
| `ingress.hosts[0].host` | Hostname | `agent-bus.example.com` |
| `ingress.tls` | TLS configuration | See values.yaml |

For a complete list of parameters, see [values.yaml](values.yaml).

## Secrets Management

### Development (Not Recommended for Production)

```bash
helm install agent-bus ./helm/agent-bus \
  --set secrets.anthropic.value="sk-ant-your-key" \
  --set secrets.postgres.value="your-password"
```

### Production - External Secrets Operator

1. Install External Secrets Operator:
```bash
helm repo add external-secrets https://charts.external-secrets.io
helm install external-secrets external-secrets/external-secrets \
  -n external-secrets-system --create-namespace
```

2. Create SecretStore (AWS example):
```yaml
apiVersion: external-secrets.io/v1beta1
kind: SecretStore
metadata:
  name: aws-secrets-manager
  namespace: agent-bus
spec:
  provider:
    aws:
      service: SecretsManager
      region: us-east-1
      auth:
        jwt:
          serviceAccountRef:
            name: external-secrets
```

3. Create ExternalSecret:
```yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: anthropic-api-key
  namespace: agent-bus
spec:
  secretStoreRef:
    name: aws-secrets-manager
    kind: SecretStore
  target:
    name: anthropic-api-key
  data:
  - secretKey: api-key
    remoteRef:
      key: agent-bus/anthropic
      property: api_key
```

4. Install chart with external secrets:
```bash
helm install agent-bus ./helm/agent-bus \
  --values values-prod.yaml \
  --set secrets.anthropic.existingSecret=anthropic-api-key
```

### Production - Sealed Secrets

1. Install Sealed Secrets controller:
```bash
kubectl apply -f https://github.com/bitnami-labs/sealed-secrets/releases/download/v0.24.0/controller.yaml
```

2. Create and seal secret:
```bash
kubectl create secret generic agent-bus-secrets \
  --from-literal=ANTHROPIC_API_KEY=sk-ant-your-key \
  --dry-run=client -o yaml | \
  kubeseal -o yaml > sealed-secret.yaml

kubectl apply -f sealed-secret.yaml
```

## Examples

### Minimal Development Deployment

```bash
helm install agent-bus ./helm/agent-bus \
  --values values-dev.yaml \
  --set secrets.anthropic.value="sk-ant-dev-key" \
  --set secrets.postgres.value="devpass123"
```

### Production with Managed Databases

```bash
helm install agent-bus ./helm/agent-bus \
  --values values-prod.yaml \
  --set postgresql.enabled=false \
  --set postgresql.external.enabled=true \
  --set postgresql.external.host="prod-db.rds.amazonaws.com" \
  --set redis.enabled=false \
  --set redis.external.enabled=true \
  --set redis.external.host="prod-cache.elasticache.amazonaws.com"
```

### Custom Resource Limits

```bash
helm install agent-bus ./helm/agent-bus \
  --set api.resources.limits.memory=4Gi \
  --set worker.resources.limits.cpu=4000m
```

## Monitoring

Enable Prometheus ServiceMonitor:

```bash
helm install agent-bus ./helm/agent-bus \
  --set serviceMonitor.enabled=true
```

## Troubleshooting

### Check Deployment Status

```bash
helm status agent-bus -n agent-bus
kubectl get pods -n agent-bus
```

### View Logs

```bash
kubectl logs -n agent-bus -l app.kubernetes.io/component=api
kubectl logs -n agent-bus -l app.kubernetes.io/component=worker
```

### Debug Rendering

```bash
helm template agent-bus ./helm/agent-bus --values values-dev.yaml --debug
```

### Common Issues

**Pods in CrashLoopBackOff:**
- Check secrets are properly configured
- Verify database connectivity
- Check resource limits

**Database Connection Refused:**
- Ensure PostgreSQL/Redis pods are running
- Check service names in ConfigMap
- Verify network policies if enabled

## Upgrading

### Upgrade Strategy

The chart uses RollingUpdate strategy by default. To upgrade:

```bash
# Pull latest image
docker pull agent_bus:latest

# Upgrade chart
helm upgrade agent-bus ./helm/agent-bus \
  --values values-prod.yaml \
  --set image.tag=v1.1.0
```

### Rollback

```bash
helm rollback agent-bus -n agent-bus
```

## Contribution

See the main repository [README](../../README.md) for contribution guidelines.

## License

MIT
