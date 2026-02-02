## KAN-75: Security - Secrets Handling Guidelines

# Secrets Handling Guidelines

This document provides comprehensive guidelines for handling secrets, credentials, and sensitive data in the agent_bus platform.

## Table of Contents

1. [General Principles](#general-principles)
2. [What is a Secret?](#what-is-a-secret)
3. [Storage Strategies](#storage-strategies)
4. [Development vs Production](#development-vs-production)
5. [Rotation and Lifecycle](#rotation-and-lifecycle)
6. [Detection and Prevention](#detection-and-prevention)
7. [Incident Response](#incident-response)

## General Principles

### The Golden Rules

1. **Never commit secrets to version control**
2. **Never log secrets**
3. **Never transmit secrets unencrypted**
4. **Use the principle of least privilege**
5. **Rotate secrets regularly**
6. **Assume secrets will be compromised**

### Secret Hygiene Checklist

- [ ] Secret is not in Git history
- [ ] Secret is not in logs
- [ ] Secret is not in error messages
- [ ] Secret is encrypted at rest
- [ ] Secret is encrypted in transit
- [ ] Secret has expiration/rotation schedule
- [ ] Secret access is audited
- [ ] Secret has minimum required scope

## What is a Secret?

Secrets include:

- **API keys:** OpenAI, Anthropic, third-party services
- **Database credentials:** Passwords, connection strings
- **Encryption keys:** AES keys, RSA private keys
- **Authentication tokens:** JWT secrets, OAuth tokens
- **Certificates:** TLS/SSL certificates, private keys
- **Service account credentials**
- **Webhook secrets**

Not secrets (but still sensitive):

- Usernames (without passwords)
- Public API endpoints
- Non-privileged configuration

## Storage Strategies

### Development Environment

#### Option 1: Environment Files (.env)

```bash
# .env (add to .gitignore!)
POSTGRES_PASSWORD=dev_password_123
OPENAI_API_KEY=sk-...
JWT_SECRET=dev-jwt-secret-change-me
```

Load with:
```python
from dotenv import load_dotenv
load_dotenv()
```

#### Option 2: Local Secrets Directory

```bash
mkdir -p ~/.agent_bus/secrets
chmod 700 ~/.agent_bus/secrets

echo "my_password" > ~/.agent_bus/secrets/postgres_password
chmod 600 ~/.agent_bus/secrets/postgres_password
```

Load with:
```python
def load_secret(name: str) -> str:
    path = Path.home() / ".agent_bus" / "secrets" / name
    return path.read_text().strip()
```

#### Option 3: OS Keyring

```python
import keyring

# Store
keyring.set_password("agent_bus", "postgres_password", "my_password")

# Retrieve
password = keyring.get_password("agent_bus", "postgres_password")
```

### Production Environment

#### Kubernetes Secrets

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: agent-bus-secrets
  namespace: agent-bus
type: Opaque
data:
  postgres-password: <base64-encoded-value>
  openai-api-key: <base64-encoded-value>
```

Create from file:
```bash
kubectl create secret generic agent-bus-secrets \
  --from-file=postgres-password=./secrets/postgres_password \
  --from-file=openai-api-key=./secrets/openai_key \
  --namespace agent-bus
```

Reference in deployment:
```yaml
env:
  - name: POSTGRES_PASSWORD
    valueFrom:
      secretKeyRef:
        name: agent-bus-secrets
        key: postgres-password
```

#### Cloud Secret Managers

**AWS Secrets Manager:**
```python
import boto3

def get_secret(secret_name: str) -> str:
    client = boto3.client('secretsmanager')
    response = client.get_secret_value(SecretId=secret_name)
    return response['SecretString']
```

**Google Cloud Secret Manager:**
```python
from google.cloud import secretmanager

def get_secret(project_id: str, secret_id: str) -> str:
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
    response = client.access_secret_version(name=name)
    return response.payload.data.decode('UTF-8')
```

**Azure Key Vault:**
```python
from azure.keyvault.secrets import SecretClient
from azure.identity import DefaultAzureCredential

def get_secret(vault_url: str, secret_name: str) -> str:
    credential = DefaultAzureCredential()
    client = SecretClient(vault_url=vault_url, credential=credential)
    secret = client.get_secret(secret_name)
    return secret.value
```

#### HashiCorp Vault

```python
import hvac

def get_secret(vault_addr: str, token: str, path: str) -> dict:
    client = hvac.Client(url=vault_addr, token=token)
    response = client.secrets.kv.v2.read_secret_version(path=path)
    return response['data']['data']
```

## Development vs Production

### Development Secrets

- Use mock/dummy values when possible
- Clearly mark development credentials
- Keep separate from production
- Store in `.env` files (gitignored)

Example:
```
# Development
POSTGRES_PASSWORD=dev_password_not_for_prod
JWT_SECRET=dev-jwt-secret-insecure

# Production (stored in secret manager)
POSTGRES_PASSWORD=<from-vault>
JWT_SECRET=<from-vault>
```

### Production Secrets

- Use strong, randomly generated values
- Store in dedicated secret management system
- Implement automatic rotation
- Monitor access and usage
- Enable audit logging

## Rotation and Lifecycle

### Rotation Schedule

| Secret Type | Rotation Frequency | Method |
|-------------|-------------------|--------|
| API Keys | 90 days | Manual or automated |
| Database Passwords | 30 days | Automated |
| JWT Secrets | 180 days | Blue-green deployment |
| TLS Certificates | Before expiry | Automated (cert-manager) |
| Service Tokens | 7-30 days | Automated |

### Rotation Process

1. **Generate new secret**
2. **Deploy new secret** (both old and new active)
3. **Update applications** to use new secret
4. **Verify** applications work with new secret
5. **Revoke old secret**
6. **Audit** access logs

Example rotation script:
```bash
#!/bin/bash
# rotate_db_password.sh

NEW_PASSWORD=$(openssl rand -base64 32)

# Update in secret manager
kubectl create secret generic postgres-secret \
  --from-literal=password="$NEW_PASSWORD" \
  --dry-run=client -o yaml | kubectl apply -f -

# Update database
psql -c "ALTER USER agent_bus PASSWORD '$NEW_PASSWORD';"

# Restart pods to pick up new secret
kubectl rollout restart deployment agent-bus-api -n agent-bus
```

## Detection and Prevention

### Pre-commit Hooks

Install git-secrets:
```bash
git secrets --install
git secrets --register-aws
git secrets --add-provider -- cat .gitignore
```

Or use pre-commit:
```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.4.0
    hooks:
      - id: detect-secrets
```

### CI/CD Scanning

GitHub Actions:
```yaml
name: Secret Scan

on: [push, pull_request]

jobs:
  secret-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: TruffleHog Scan
        uses: trufflesecurity/trufflehog@main
        with:
          path: ./
```

### Code Review Checklist

- [ ] No hardcoded credentials
- [ ] No API keys in code
- [ ] Secrets loaded from environment/vault
- [ ] No secrets in log statements
- [ ] No secrets in error messages

## Incident Response

### If a Secret is Compromised

1. **Immediately revoke** the compromised secret
2. **Rotate** to a new secret
3. **Audit** access logs for unauthorized use
4. **Notify** relevant parties
5. **Investigate** how the compromise occurred
6. **Implement** preventive measures
7. **Document** the incident

### Emergency Revocation

```bash
# Kubernetes: Delete secret and restart pods
kubectl delete secret agent-bus-secrets -n agent-bus
kubectl create secret generic agent-bus-secrets --from-literal=...
kubectl rollout restart deployment -n agent-bus

# Cloud: Disable credential
aws secretsmanager update-secret-version-stage \
  --secret-id agent-bus/prod/api-key \
  --version-stage AWSCURRENT \
  --remove-from-version-id <compromised-version>
```

## Best Practices Summary

### Do ✅

- Use environment variables for secrets
- Store secrets in dedicated secret managers
- Encrypt secrets at rest and in transit
- Rotate secrets regularly
- Audit secret access
- Use different secrets per environment
- Implement least privilege access

### Don't ❌

- Commit secrets to Git
- Log secrets
- Email secrets
- Share secrets in chat
- Reuse secrets across environments
- Store secrets in plain text
- Hard-code credentials

## Tools and Resources

### Recommended Tools

- **Secret Detection:** TruffleHog, detect-secrets, git-secrets
- **Secret Management:** HashiCorp Vault, AWS Secrets Manager, Azure Key Vault
- **Encryption:** age, sops, sealed-secrets (K8s)
- **Scanning:** GitLeaks, SecretScanner

### Further Reading

- [OWASP Secrets Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)
- [12-Factor App: Config](https://12factor.net/config)
- [NIST SP 800-57: Key Management](https://csrc.nist.gov/publications/detail/sp/800-57-part-1/rev-5/final)

## Implementation Checklist

For agent_bus specifically:

- [x] Document secrets strategy (this file)
- [ ] Add .env.example template
- [ ] Implement secret loading from environment
- [ ] Add pre-commit hooks for secret detection
- [ ] Set up CI/CD secret scanning
- [ ] Create Kubernetes secret manifests
- [ ] Document rotation procedures
- [ ] Implement secret rotation automation
- [ ] Add secret access audit logging
- [ ] Create incident response runbook
