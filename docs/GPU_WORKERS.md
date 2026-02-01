# GPU Worker Configuration

## Overview

This document describes the GPU worker setup for agent_bus ML/CV workloads.

## GPU Node Requirements

### Hardware
- NVIDIA Tesla V100 or A100 GPUs
- 8+ cores CPU per GPU
- 32Gi+ RAM per GPU
- NVMe storage for fast model loading

### Software
- NVIDIA GPU drivers (535.x+)
- NVIDIA Container Toolkit
- Kubernetes 1.28+
- NVIDIA Device Plugin for Kubernetes

## Installation

### 1. Install NVIDIA Device Plugin

```bash
kubectl create -f https://raw.githubusercontent.com/NVIDIA/k8s-device-plugin/v0.14.0/nvidia-device-plugin.yml
```

### 2. Label GPU Nodes

```bash
# For V100 nodes
kubectl label nodes <node-name> accelerator=nvidia-tesla-v100

# For A100 nodes
kubectl label nodes <node-name> accelerator=nvidia-tesla-a100
```

### 3. Taint GPU Nodes (Optional but Recommended)

```bash
kubectl taint nodes <node-name> nvidia.com/gpu=true:NoSchedule
```

This ensures only GPU workloads run on expensive GPU nodes.

## GPU Job Template

### Basic Job

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: gpu-ml-task
spec:
  template:
    spec:
      containers:
      - name: worker
        image: agent_bus:latest
        resources:
          limits:
            nvidia.com/gpu: 1
      nodeSelector:
        accelerator: nvidia-tesla-v100
      tolerations:
      - key: nvidia.com/gpu
        operator: Equal
        value: "true"
        effect: NoSchedule
```

### Creating GPU Jobs from Code

```python
from src.infrastructure.k8s_manager import KubernetesJobManager

k8s = KubernetesJobManager()

# Create GPU job for ML workload
job_name = k8s.create_gpu_job(
    task_id="ml_task_123",
    image="agent_bus:latest",
    gpu_count=1,
    gpu_type="v100",  # or "a100"
    memory="16Gi",
    cpu="8000m",
    command=["python", "-m", "src.workers.worker"],
    env={"WORKER_TYPE": "gpu", "TASK_ID": "ml_task_123"}
)
```

## Resource Configuration

### V100 Configuration

```yaml
resources:
  requests:
    memory: "8Gi"
    cpu: "4000m"
    nvidia.com/gpu: "1"
  limits:
    memory: "16Gi"
    cpu: "8000m"
    nvidia.com/gpu: "1"
```

### A100 Configuration (Higher Memory)

```yaml
resources:
  requests:
    memory: "16Gi"
    cpu: "8000m"
    nvidia.com/gpu: "1"
  limits:
    memory: "32Gi"
    cpu: "16000m"
    nvidia.com/gpu: "1"
```

### Multi-GPU Configuration

```yaml
resources:
  limits:
    nvidia.com/gpu: "2"  # or "4", "8"
env:
- name: CUDA_VISIBLE_DEVICES
  value: "0,1"  # Explicitly set visible GPUs
```

## Node Selectors and Affinity

### V100 Node Selector

```yaml
nodeSelector:
  accelerator: nvidia-tesla-v100
  node.kubernetes.io/instance-type: p3.2xlarge  # AWS example
```

### A100 Node Selector

```yaml
nodeSelector:
  accelerator: nvidia-tesla-a100
  node.kubernetes.io/instance-type: p4d.24xlarge  # AWS example
```

### GPU Affinity (Prefer Specific GPUs)

```yaml
affinity:
  nodeAffinity:
    preferredDuringSchedulingIgnoredDuringExecution:
    - weight: 100
      preference:
        matchExpressions:
        - key: accelerator
          operator: In
          values:
          - nvidia-tesla-a100
    - weight: 50
      preference:
        matchExpressions:
        - key: accelerator
          operator: In
          values:
          - nvidia-tesla-v100
```

## ML Workload Detection

The system automatically detects ML/CV workloads from requirements:

```python
# src/ml_pipeline/detector.py

def detect_ml_workload(requirements: str) -> bool:
    """Detect if requirements need GPU."""
    ml_keywords = [
        "machine learning", "deep learning", "neural network",
        "pytorch", "tensorflow", "computer vision", "cv",
        "object detection", "image classification", "nlp",
        "model training", "inference", "gpu", "cuda"
    ]
    
    requirements_lower = requirements.lower()
    return any(keyword in requirements_lower for keyword in ml_keywords)

def calculate_gpu_requirements(requirements: str) -> dict:
    """Calculate GPU resource requirements."""
    # Analyze requirements complexity
    if "large model" in requirements.lower() or "billion" in requirements.lower():
        return {"gpu_count": 4, "gpu_type": "a100", "memory": "64Gi"}
    elif "training" in requirements.lower():
        return {"gpu_count": 1, "gpu_type": "a100", "memory": "32Gi"}
    else:
        return {"gpu_count": 1, "gpu_type": "v100", "memory": "16Gi"}
```

## Shared Memory (SHM)

GPU workloads often need large shared memory for data loading:

```yaml
volumes:
- name: shm
  emptyDir:
    medium: Memory
    sizeLimit: 2Gi  # Adjust based on dataset size

volumeMounts:
- name: shm
  mountPath: /dev/shm
```

## Monitoring GPU Usage

### NVIDIA DCGM Exporter

```bash
helm repo add gpu-helm-charts https://nvidia.github.io/dcgm-exporter/helm-charts
helm install dcgm-exporter gpu-helm-charts/dcgm-exporter
```

### Prometheus Queries

```promql
# GPU utilization
DCGM_FI_DEV_GPU_UTIL{kubernetes_node="gpu-node-1"}

# GPU memory usage
DCGM_FI_DEV_FB_USED{kubernetes_node="gpu-node-1"}

# GPU temperature
DCGM_FI_DEV_GPU_TEMP{kubernetes_node="gpu-node-1"}
```

### Grafana Dashboard

Import NVIDIA DCGM dashboard: https://grafana.com/grafana/dashboards/12239

## Cost Optimization

### Spot Instances

```yaml
nodeSelector:
  node.kubernetes.io/lifecycle: spot
tolerations:
- key: spot
  operator: Equal
  value: "true"
  effect: NoSchedule
```

### Time-based Scaling

```yaml
# CronJob to scale GPU node pool
apiVersion: batch/v1
kind: CronJob
metadata:
  name: scale-gpu-nodes
spec:
  schedule: "0 9 * * 1-5"  # 9 AM weekdays
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: scaler
            image: bitnami/kubectl
            command:
            - kubectl
            - scale
            - nodepool
            - gpu-pool
            - --replicas=5
```

## Troubleshooting

### GPU Not Visible

```bash
# Check NVIDIA device plugin
kubectl get pods -n kube-system | grep nvidia

# Check GPU resources
kubectl describe node <gpu-node> | grep nvidia.com/gpu

# Test GPU in pod
kubectl run gpu-test --rm -it --image=nvidia/cuda:12.0-base --limits=nvidia.com/gpu=1 -- nvidia-smi
```

### Out of Memory

- Increase memory limits
- Use gradient checkpointing
- Reduce batch size
- Enable mixed precision training

### Job Stuck Pending

```bash
# Check events
kubectl describe job <job-name>

# Common issues:
# - No GPU nodes available
# - Resource limits too high
# - Node selectors don't match
# - Taints not tolerated
```

## Best Practices

1. **Always set resource limits** - Prevents runaway GPU usage
2. **Use node selectors** - Ensure correct GPU type
3. **Implement timeouts** - Kill stuck jobs automatically
4. **Monitor GPU utilization** - Optimize batch sizes
5. **Use spot instances** - Save 60-90% on costs
6. **Clean up completed jobs** - Set ttlSecondsAfterFinished
7. **Shared memory** - Allocate sufficient SHM for data loaders
8. **Model caching** - Use persistent volumes to cache models

## Example: Complete GPU Job

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: ml-training-job
spec:
  backoffLimit: 3
  ttlSecondsAfterFinished: 3600
  template:
    spec:
      restartPolicy: OnFailure
      containers:
      - name: trainer
        image: agent_bus:latest
        resources:
          requests:
            memory: "16Gi"
            cpu: "8000m"
            nvidia.com/gpu: "1"
          limits:
            memory: "32Gi"
            cpu: "16000m"
            nvidia.com/gpu: "1"
        env:
        - name: WORKER_TYPE
          value: "gpu"
        - name: CUDA_VISIBLE_DEVICES
          value: "0"
        volumeMounts:
        - name: workspace
          mountPath: /workspace
        - name: shm
          mountPath: /dev/shm
      volumes:
      - name: workspace
        persistentVolumeClaim:
          claimName: ml-workspace
      - name: shm
        emptyDir:
          medium: Memory
          sizeLimit: 4Gi
      nodeSelector:
        accelerator: nvidia-tesla-a100
        node.kubernetes.io/instance-type: p4d.24xlarge
      tolerations:
      - key: nvidia.com/gpu
        operator: Equal
        value: "true"
        effect: NoSchedule
```

## Next Steps

- Set up NVIDIA DCGM for monitoring
- Configure auto-scaling for GPU node pools
- Implement job queuing for GPU resource management
- Add cost tracking for GPU usage
