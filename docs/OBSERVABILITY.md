# Observability & Monitoring

## Overview

Agent Bus includes comprehensive observability with Prometheus metrics, Grafana dashboards, and structured logging.

## Metrics

### Prometheus Integration

All application components expose Prometheus metrics on `/metrics` endpoint.

#### API Metrics

```python
from src.infrastructure.metrics import http_requests_total, http_request_duration_seconds

# Track request
http_requests_total.labels(method="POST", endpoint="/api/projects", status="200").inc()

# Track duration
with http_request_duration_seconds.labels(method="POST", endpoint="/api/projects").time():
    # Handle request
    pass
```

#### Job Metrics

- `agent_bus_jobs_created_total` - Total jobs created
- `agent_bus_jobs_completed_total` - Total jobs completed
- `agent_bus_jobs_active` - Currently active jobs
- `agent_bus_job_duration_seconds` - Job execution duration

#### Agent Metrics

- `agent_bus_agent_executions_total` - Total agent executions
- `agent_bus_agent_execution_duration_seconds` - Agent execution time
- `agent_bus_agent_llm_calls_total` - LLM API calls
- `agent_bus_agent_llm_tokens_total` - LLM tokens consumed

#### Worker Metrics

- `agent_bus_worker_tasks_processed_total` - Tasks processed
- `agent_bus_worker_queue_size` - Queue depth

### Installing Prometheus

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm install prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace \
  --values k8s/monitoring/prometheus-values.yaml
```

### Applying Custom Config

```bash
kubectl apply -f k8s/monitoring/prometheus-config.yaml
```

## Grafana Dashboards

### Installing Grafana

Grafana is included with kube-prometheus-stack.

Access Grafana:
```bash
kubectl port-forward -n monitoring svc/prometheus-grafana 3000:80
```

Default credentials:
- Username: `admin`
- Password: `prom-operator`

### Importing Dashboard

1. Open Grafana (http://localhost:3000)
2. Go to Dashboards → Import
3. Upload `k8s/monitoring/grafana-dashboard.json`

### Key Dashboards

**Agent Bus System Overview:**
- HTTP request rate and latency
- Active jobs and completion rate
- Agent execution metrics
- LLM API usage and costs
- Error rates
- Worker queue depth

**GPU Monitoring:**
- GPU utilization per node
- GPU memory usage
- GPU temperature
- Job distribution across GPUs

**Database Performance:**
- Query duration percentiles
- Active connections
- Slow queries

## Alerting

### Prometheus Alert Rules

```yaml
groups:
  - name: agent_bus_alerts
    rules:
      - alert: HighErrorRate
        expr: rate(agent_bus_errors_total[5m]) > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High error rate detected"
          
      - alert: JobsStuck
        expr: agent_bus_jobs_active > 100
        for: 30m
        labels:
          severity: critical
        annotations:
          summary: "Many jobs stuck in processing"
          
      - alert: HighLLMCost
        expr: rate(agent_bus_agent_llm_tokens_total[1h]) > 1000000
        for: 1h
        labels:
          severity: warning
        annotations:
          summary: "High LLM token usage - check for runaway jobs"
          
      - alert: WorkerQueueBacklog
        expr: agent_bus_worker_queue_size > 1000
        for: 15m
        labels:
          severity: warning
        annotations:
          summary: "Worker queue backing up - scale workers"
```

### AlertManager Configuration

```bash
kubectl apply -f k8s/monitoring/alertmanager-config.yaml
```

## Logging

### Structured Logging

All components use structured JSON logging:

```python
import logging
import json

logger = logging.getLogger(__name__)

# Configure JSON logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    handlers=[logging.StreamHandler()]
)

# Log structured data
logger.info(json.dumps({
    "event": "job_started",
    "job_id": "job_123",
    "project_id": "proj_456",
    "timestamp": time.time()
}))
```

### Log Aggregation

#### Using Loki

```bash
helm repo add grafana https://grafana.github.io/helm-charts
helm install loki grafana/loki-stack \
  --namespace monitoring \
  --set grafana.enabled=false \
  --set prometheus.enabled=false
```

#### Querying Logs in Grafana

```logql
{namespace="agent-bus", component="api"} |= "error"
{namespace="agent-bus"} | json | job_id="job_123"
rate({namespace="agent-bus"}[5m])
```

## Distributed Tracing

### OpenTelemetry Integration

```python
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

# Configure tracer
trace.set_tracer_provider(TracerProvider())
otlp_exporter = OTLPSpanExporter(endpoint="http://tempo:4317", insecure=True)
trace.get_tracer_provider().add_span_processor(BatchSpanProcessor(otlp_exporter))

# Use tracer
tracer = trace.get_tracer(__name__)

async def process_job(job_id: str):
    with tracer.start_as_current_span("process_job") as span:
        span.set_attribute("job.id", job_id)
        # Process job
        pass
```

## Health Checks

### Liveness Probe

```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 10
```

### Readiness Probe

```yaml
readinessProbe:
  httpGet:
    path: /health/ready
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 5
```

### Health Endpoint Implementation

```python
@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": time.time()}

@app.get("/health/ready")
async def readiness():
    # Check dependencies
    db_healthy = await check_postgres()
    redis_healthy = await check_redis()
    
    if db_healthy and redis_healthy:
        return {"status": "ready"}
    else:
        raise HTTPException(status_code=503, detail="Not ready")
```

## Cost Tracking

### LLM Cost Metrics

```python
from src.infrastructure.metrics import agent_llm_tokens_total

# Track token usage
agent_llm_tokens_total.labels(
    agent_type="prd_agent",
    provider="anthropic",
    type="input"
).inc(prompt_tokens)

agent_llm_tokens_total.labels(
    agent_type="prd_agent",
    provider="anthropic",
    type="output"
).inc(completion_tokens)
```

### Cost Dashboard

Create Grafana dashboard showing:
- Token usage per agent
- Estimated costs (tokens * price per token)
- Cost per project
- Daily/monthly burn rate

### Cost Alerts

```yaml
- alert: DailyCostExceeded
  expr: sum(increase(agent_bus_agent_llm_tokens_total[24h])) * 0.000015 > 100
  labels:
    severity: warning
  annotations:
    summary: "Daily LLM cost exceeded $100"
```

## Performance Profiling

### CPU Profiling

```bash
# Install py-spy
pip install py-spy

# Profile API process
kubectl exec -it <api-pod> -- py-spy record -o profile.svg --pid 1 --duration 60
```

### Memory Profiling

```bash
# Install memray
pip install memray

# Profile worker
kubectl exec -it <worker-pod> -- python -m memray run -o memory.bin src/workers/worker.py
```

## Monitoring Best Practices

1. **Set up alerts** - Don't just collect metrics, act on them
2. **Use SLOs** - Define service level objectives (e.g., 99% of requests < 200ms)
3. **Monitor costs** - Track LLM token usage to avoid surprises
4. **Regular reviews** - Weekly review of dashboards and alerts
5. **Capacity planning** - Use historical data to predict scaling needs

## Troubleshooting with Metrics

### High Response Times

```promql
# Check p95 latency
histogram_quantile(0.95, rate(agent_bus_http_request_duration_seconds_bucket[5m]))

# Slow endpoints
topk(5, rate(agent_bus_http_request_duration_seconds_sum[5m]))
```

### Memory Leaks

```promql
# Check memory growth
container_memory_usage_bytes{pod=~"agent-bus-.*"}
```

### Database Issues

```promql
# Connection pool saturation
agent_bus_db_connections_active / max_connections

# Slow queries
rate(agent_bus_db_query_duration_seconds_sum[5m])
```

## Next Steps

- Set up PagerDuty/Slack alerts
- Configure log rotation and retention
- Implement custom business metrics
- Set up cost anomaly detection
