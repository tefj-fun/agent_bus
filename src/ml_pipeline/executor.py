"""GPU Job Orchestration Module.

Creates and manages Kubernetes GPU jobs for ML workloads.
"""
import asyncio
import logging
import os
from datetime import datetime
from typing import Dict, Optional, Any
from enum import Enum

from ..database.connection import get_session
from ..database.models import JobStatus
from ..ml_pipeline.detector import MLWorkloadAnalysis

logger = logging.getLogger(__name__)


class GPUJobStatus(str, Enum):
    """Status of GPU job."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class GPUJobExecutor:
    """Orchestrates GPU jobs on Kubernetes."""
    
    def __init__(self):
        """Initialize the executor."""
        self.k8s_available = self._check_k8s_available()
        if not self.k8s_available:
            logger.warning("Kubernetes client not available. GPU jobs will run in simulation mode.")
    
    def _check_k8s_available(self) -> bool:
        """Check if Kubernetes client is available."""
        try:
            from kubernetes import client, config
            # Try to load config
            try:
                config.load_incluster_config()
            except:
                config.load_kube_config()
            return True
        except Exception as e:
            logger.debug(f"Kubernetes not available: {e}")
            return False
    
    async def create_gpu_job(
        self,
        job_id: str,
        workload_analysis: MLWorkloadAnalysis,
        task_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Create a Kubernetes GPU job.
        
        Args:
            job_id: Project job ID
            workload_analysis: ML workload analysis result
            task_data: Task-specific data
            
        Returns:
            Job creation result with k8s job name and status
        """
        if not self.k8s_available:
            return await self._simulate_gpu_job(job_id, workload_analysis, task_data)
        
        try:
            from kubernetes import client
            
            batch_v1 = client.BatchV1Api()
            
            # Generate job name
            timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
            k8s_job_name = f"agent-bus-gpu-{job_id[:8]}-{timestamp}"
            
            # Build job spec
            job_spec = self._build_job_spec(
                k8s_job_name, job_id, workload_analysis, task_data
            )
            
            # Create job
            namespace = os.getenv("K8S_NAMESPACE", "agent-bus")
            response = batch_v1.create_namespaced_job(
                namespace=namespace,
                body=job_spec,
            )
            
            logger.info(f"Created GPU job: {k8s_job_name} for project {job_id}")
            
            return {
                "k8s_job_name": k8s_job_name,
                "namespace": namespace,
                "status": GPUJobStatus.PENDING,
                "created_at": datetime.utcnow().isoformat(),
                "gpu_count": workload_analysis.required_gpu_count,
            }
            
        except Exception as e:
            logger.error(f"Failed to create GPU job for {job_id}: {e}")
            raise
    
    def _build_job_spec(
        self,
        job_name: str,
        job_id: str,
        workload_analysis: MLWorkloadAnalysis,
        task_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Build Kubernetes job specification."""
        from kubernetes import client
        
        # Container spec
        container = client.V1Container(
            name="gpu-worker",
            image=os.getenv("WORKER_IMAGE", "ghcr.io/tefj-fun/agent-bus:latest"),
            command=["python", "-m", "src.worker.worker"],
            env=[
                client.V1EnvVar(name="WORKER_TYPE", value="gpu"),
                client.V1EnvVar(name="JOB_ID", value=job_id),
                client.V1EnvVar(
                    name="ANTHROPIC_API_KEY",
                    value_from=client.V1EnvVarSource(
                        secret_key_ref=client.V1SecretKeySelector(
                            name="agent-bus-secrets",
                            key="ANTHROPIC_API_KEY",
                        )
                    ),
                ),
            ],
            env_from=[
                client.V1EnvFromSource(
                    config_map_ref=client.V1ConfigMapEnvSource(
                        name="agent-bus-config"
                    )
                ),
            ],
            resources=client.V1ResourceRequirements(
                requests={
                    "nvidia.com/gpu": str(workload_analysis.required_gpu_count),
                    "memory": f"{workload_analysis.estimated_memory_gb}Gi",
                    "cpu": str(workload_analysis.estimated_cpu_cores),
                },
                limits={
                    "nvidia.com/gpu": str(workload_analysis.required_gpu_count),
                    "memory": f"{workload_analysis.estimated_memory_gb * 2}Gi",
                    "cpu": str(workload_analysis.estimated_cpu_cores * 2),
                },
            ),
        )
        
        # Pod template
        template = client.V1PodTemplateSpec(
            metadata=client.V1ObjectMeta(
                labels={
                    "app": "agent-bus",
                    "component": "gpu-worker",
                    "job-id": job_id[:8],
                }
            ),
            spec=client.V1PodSpec(
                restart_policy="OnFailure",
                containers=[container],
                node_selector={"nvidia.com/gpu": "true"},
                tolerations=[
                    client.V1Toleration(
                        key="nvidia.com/gpu",
                        operator="Exists",
                        effect="NoSchedule",
                    )
                ],
            ),
        )
        
        # Job spec
        job = client.V1Job(
            api_version="batch/v1",
            kind="Job",
            metadata=client.V1ObjectMeta(
                name=job_name,
                labels={
                    "app": "agent-bus",
                    "component": "gpu-worker",
                    "job-id": job_id[:8],
                },
            ),
            spec=client.V1JobSpec(
                template=template,
                backoff_limit=3,
                ttl_seconds_after_finished=3600,  # Clean up after 1 hour
            ),
        )
        
        return job
    
    async def _simulate_gpu_job(
        self,
        job_id: str,
        workload_analysis: MLWorkloadAnalysis,
        task_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Simulate GPU job when K8s is not available."""
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        k8s_job_name = f"simulated-gpu-{job_id[:8]}-{timestamp}"
        
        logger.info(
            f"Simulating GPU job for {job_id}: {workload_analysis.required_gpu_count} GPUs, "
            f"{workload_analysis.estimated_memory_gb}GB memory"
        )
        
        return {
            "k8s_job_name": k8s_job_name,
            "namespace": "simulated",
            "status": GPUJobStatus.PENDING,
            "created_at": datetime.utcnow().isoformat(),
            "gpu_count": workload_analysis.required_gpu_count,
            "simulated": True,
        }
    
    async def monitor_job(self, k8s_job_name: str, namespace: str) -> GPUJobStatus:
        """
        Monitor GPU job status.
        
        Args:
            k8s_job_name: Kubernetes job name
            namespace: Kubernetes namespace
            
        Returns:
            Current job status
        """
        if not self.k8s_available:
            # Simulate completion after a short delay
            await asyncio.sleep(2)
            return GPUJobStatus.COMPLETED
        
        try:
            from kubernetes import client
            
            batch_v1 = client.BatchV1Api()
            job = batch_v1.read_namespaced_job_status(k8s_job_name, namespace)
            
            if job.status.succeeded:
                return GPUJobStatus.COMPLETED
            elif job.status.failed:
                return GPUJobStatus.FAILED
            elif job.status.active:
                return GPUJobStatus.RUNNING
            else:
                return GPUJobStatus.PENDING
                
        except Exception as e:
            logger.error(f"Failed to monitor GPU job {k8s_job_name}: {e}")
            return GPUJobStatus.FAILED
    
    async def wait_for_completion(
        self,
        k8s_job_name: str,
        namespace: str,
        timeout: int = 3600,
        poll_interval: int = 10,
    ) -> GPUJobStatus:
        """
        Wait for GPU job to complete.
        
        Args:
            k8s_job_name: Kubernetes job name
            namespace: Kubernetes namespace
            timeout: Maximum wait time in seconds
            poll_interval: Polling interval in seconds
            
        Returns:
            Final job status
        """
        elapsed = 0
        
        while elapsed < timeout:
            status = await self.monitor_job(k8s_job_name, namespace)
            
            if status in (GPUJobStatus.COMPLETED, GPUJobStatus.FAILED):
                return status
            
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval
        
        logger.warning(f"GPU job {k8s_job_name} timed out after {timeout}s")
        return GPUJobStatus.FAILED
    
    async def collect_results(
        self, k8s_job_name: str, namespace: str
    ) -> Optional[Dict[str, Any]]:
        """
        Collect results from completed GPU job.
        
        Args:
            k8s_job_name: Kubernetes job name
            namespace: Kubernetes namespace
            
        Returns:
            Job results or None if failed
        """
        if not self.k8s_available:
            return {
                "status": "completed",
                "message": "Simulated GPU job completed successfully",
                "simulated": True,
            }
        
        try:
            from kubernetes import client
            
            core_v1 = client.CoreV1Api()
            
            # Get pods for this job
            pods = core_v1.list_namespaced_pod(
                namespace=namespace,
                label_selector=f"job-name={k8s_job_name}",
            )
            
            if not pods.items:
                logger.warning(f"No pods found for job {k8s_job_name}")
                return None
            
            # Get logs from first pod
            pod_name = pods.items[0].metadata.name
            logs = core_v1.read_namespaced_pod_log(pod_name, namespace)
            
            return {
                "status": "completed",
                "pod_name": pod_name,
                "logs": logs,
            }
            
        except Exception as e:
            logger.error(f"Failed to collect results for {k8s_job_name}: {e}")
            return None
    
    async def cleanup_job(self, k8s_job_name: str, namespace: str) -> bool:
        """
        Clean up completed GPU job.
        
        Args:
            k8s_job_name: Kubernetes job name
            namespace: Kubernetes namespace
            
        Returns:
            True if cleanup successful
        """
        if not self.k8s_available:
            logger.info(f"Simulated cleanup for {k8s_job_name}")
            return True
        
        try:
            from kubernetes import client
            
            batch_v1 = client.BatchV1Api()
            batch_v1.delete_namespaced_job(
                k8s_job_name,
                namespace,
                propagation_policy="Background",
            )
            
            logger.info(f"Cleaned up GPU job: {k8s_job_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cleanup GPU job {k8s_job_name}: {e}")
            return False


# Singleton instance
_executor = GPUJobExecutor()


async def execute_gpu_job(
    job_id: str,
    workload_analysis: MLWorkloadAnalysis,
    task_data: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Execute a GPU job and wait for completion.
    
    Args:
        job_id: Project job ID
        workload_analysis: ML workload analysis
        task_data: Task data
        
    Returns:
        Job results
    """
    # Create job
    job_info = await _executor.create_gpu_job(job_id, workload_analysis, task_data)
    
    # Wait for completion
    status = await _executor.wait_for_completion(
        job_info["k8s_job_name"],
        job_info["namespace"],
    )
    
    # Collect results
    if status == GPUJobStatus.COMPLETED:
        results = await _executor.collect_results(
            job_info["k8s_job_name"],
            job_info["namespace"],
        )
    else:
        results = {"status": "failed", "error": "Job failed or timed out"}
    
    # Cleanup (optional, jobs have TTL)
    await _executor.cleanup_job(
        job_info["k8s_job_name"],
        job_info["namespace"],
    )
    
    return {**job_info, "results": results}
