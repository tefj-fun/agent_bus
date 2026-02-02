# Configuration and Secrets Strategy (KAN-64)

## Overview

This document outlines the configuration and secrets management strategy for agent_bus.

## Configuration Layers

### 1. Environment Variables
Primary configuration method. All services read from environment variables:
- `REDIS_HOST`, `REDIS_PORT`
- `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`
- `OPENAI_API_KEY`, `OPENAI_MODEL`
- `LLM_MODE` (mock, openai, anthropic)
- `WORKER_TYPE` (cpu, gpu, api)

### 2. Configuration Files
For complex, structured configuration:
- `config/settings.yaml` - Application settings
- `config/workers.yaml` - Worker pool configuration
- `config/routing.yaml` - Task routing rules

### 3. Secrets Management

#### Development
- `.env` files (gitignored)
- Docker Compose environment variables
- Local files in `~/.agent_bus/secrets/`

#### Production
**Kubernetes:**
- Use Kubernetes Secrets for sensitive data
- Mount secrets as files or environment variables
- Example:
  ```yaml
  apiVersion: v1
  kind: Secret
  metadata:
    name: agent-bus-secrets
  type: Opaque
  data:
    postgres-password: <base64-encoded>
    openai-api-key: <base64-encoded>
  ```

**Docker Swarm:**
- Use Docker Secrets
- Example:
  ```bash
  echo "password" | docker secret create postgres_password -
  ```

**Cloud Providers:**
- AWS Secrets Manager
- Azure Key Vault
- GCP Secret Manager

### 4. ConfigMaps (K8s)
For non-sensitive configuration:
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: agent-bus-config
data:
  REDIS_HOST: "redis-service"
  POSTGRES_HOST: "postgres-service"
  LLM_MODE: "openai"
```

## Best Practices

1. **Never commit secrets to Git**
   - Use `.gitignore` for `.env`, `secrets/`, etc.
   - Scan commits with `git-secrets` or `truffleHog`

2. **Use strong, unique passwords**
   - Generate with `openssl rand -base64 32`
   - Rotate regularly

3. **Principle of least privilege**
   - Each service gets only the secrets it needs
   - Use separate database users for API, workers

4. **Environment-specific secrets**
   - Dev, staging, prod use different credentials
   - Never reuse production secrets in dev

5. **Audit and monitor**
   - Log access to secrets (without logging the secrets themselves)
   - Alert on unauthorized access attempts

## Implementation Guide

### Local Development
```bash
# Create .env file
cat > .env <<EOF
POSTGRES_PASSWORD=devpassword
OPENAI_API_KEY=sk-...
EOF

# Use with Docker Compose
docker compose --env-file .env up
```

### Kubernetes Deployment
```bash
# Create secret
kubectl create secret generic agent-bus-secrets \
  --from-literal=postgres-password='...' \
  --from-literal=openai-api-key='sk-...' \
  -n agent-bus

# Reference in deployment
spec:
  containers:
    - name: api
      env:
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: agent-bus-secrets
              key: postgres-password
```

### Configuration Validation
Implement config validation on startup:
```python
from pydantic import BaseSettings, SecretStr

class Settings(BaseSettings):
    postgres_password: SecretStr
    openai_api_key: SecretStr
    redis_host: str = "localhost"
    
    class Config:
        env_file = '.env'
```

## Security Checklist

- [ ] No secrets in Git history
- [ ] Secrets encrypted at rest
- [ ] Secrets encrypted in transit (TLS)
- [ ] Access control on secrets
- [ ] Regular rotation schedule
- [ ] Secrets scanning in CI/CD
- [ ] Backup and recovery plan
- [ ] Audit logging enabled

## See Also
- [12-Factor App Config](https://12factor.net/config)
- [Kubernetes Secrets](https://kubernetes.io/docs/concepts/configuration/secret/)
- [Docker Secrets](https://docs.docker.com/engine/swarm/secrets/)
