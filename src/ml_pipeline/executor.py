"""GPU-aware task executor for ML/CV workloads."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from .detector import WorkloadDetector, WorkloadType

logger = logging.getLogger(__name__)


class ExecutorType(str, Enum):
    """Type of executor for task execution."""

    GPU_WORKER = "gpu_worker"  # Dedicated GPU worker
    CPU_WORKER = "cpu_worker"  # CPU-only worker
    AUTO = "auto"  # Automatically select based on workload


@dataclass
class ExecutionContext:
    """Context for task execution."""

    task_id: str
    executor_type: ExecutorType
    workload_type: WorkloadType
    gpu_device_id: Optional[int] = None
    gpu_memory_allocated_gb: Optional[float] = None
    cpu_cores: Optional[int] = None


@dataclass
class ExecutionResult:
    """Result of task execution."""

    task_id: str
    success: bool
    result: Any = None
    error: Optional[str] = None
    execution_time_ms: float = 0.0
    executor_type: Optional[ExecutorType] = None
    gpu_used: bool = False


class GPURouter:
    """Route tasks to appropriate executors based on GPU requirements."""

    def __init__(
        self,
        gpu_workers: Optional[List[str]] = None,
        cpu_workers: Optional[List[str]] = None,
    ):
        """Initialize GPU router.

        Args:
            gpu_workers: List of GPU worker IDs/addresses
            cpu_workers: List of CPU worker IDs/addresses
        """
        self.detector = WorkloadDetector()
        self.gpu_workers = gpu_workers or []
        self.cpu_workers = cpu_workers or []

        # Track worker availability
        self.gpu_worker_availability: Dict[str, bool] = {
            worker: True for worker in self.gpu_workers
        }
        self.cpu_worker_availability: Dict[str, bool] = {
            worker: True for worker in self.cpu_workers
        }

        logger.info(
            f"Initialized GPURouter with {len(self.gpu_workers)} GPU workers "
            f"and {len(self.cpu_workers)} CPU workers"
        )

    def route_task(
        self,
        task_id: str,
        task_description: str,
        task_metadata: Optional[Dict[str, Any]] = None,
    ) -> ExecutionContext:
        """Route a task to the appropriate executor.

        Args:
            task_id: Unique task identifier
            task_description: Description of the task
            task_metadata: Optional task metadata

        Returns:
            ExecutionContext with routing decision
        """
        # Detect workload type
        signatures = self.detector.detect(task_description, task_metadata)
        workload_type = signatures[0].workload_type if signatures else WorkloadType.CPU_BOUND
        requires_gpu = signatures[0].requires_gpu if signatures else False

        logger.info(
            f"Task {task_id}: detected workload={workload_type.value}, "
            f"requires_gpu={requires_gpu}"
        )

        # Determine executor type
        if requires_gpu and self.gpu_workers:
            executor_type = ExecutorType.GPU_WORKER
            gpu_memory = self.detector.estimate_gpu_memory(task_description, task_metadata)
            return ExecutionContext(
                task_id=task_id,
                executor_type=executor_type,
                workload_type=workload_type,
                gpu_memory_allocated_gb=gpu_memory,
            )
        else:
            executor_type = ExecutorType.CPU_WORKER
            return ExecutionContext(
                task_id=task_id,
                executor_type=executor_type,
                workload_type=workload_type,
            )

    def get_available_worker(self, executor_type: ExecutorType) -> Optional[str]:
        """Get an available worker of the specified type.

        Args:
            executor_type: Type of executor needed

        Returns:
            Worker ID/address, or None if none available
        """
        if executor_type == ExecutorType.GPU_WORKER:
            for worker, available in self.gpu_worker_availability.items():
                if available:
                    return worker
        elif executor_type == ExecutorType.CPU_WORKER:
            for worker, available in self.cpu_worker_availability.items():
                if available:
                    return worker

        return None

    def mark_worker_busy(self, worker_id: str, is_gpu: bool = False) -> None:
        """Mark a worker as busy.

        Args:
            worker_id: Worker identifier
            is_gpu: True if GPU worker
        """
        if is_gpu:
            if worker_id in self.gpu_worker_availability:
                self.gpu_worker_availability[worker_id] = False
        else:
            if worker_id in self.cpu_worker_availability:
                self.cpu_worker_availability[worker_id] = False

    def mark_worker_available(self, worker_id: str, is_gpu: bool = False) -> None:
        """Mark a worker as available.

        Args:
            worker_id: Worker identifier
            is_gpu: True if GPU worker
        """
        if is_gpu:
            if worker_id in self.gpu_worker_availability:
                self.gpu_worker_availability[worker_id] = True
        else:
            if worker_id in self.cpu_worker_availability:
                self.cpu_worker_availability[worker_id] = True

    def get_stats(self) -> Dict[str, Any]:
        """Get router statistics.

        Returns:
            Dictionary with routing statistics
        """
        gpu_available = sum(1 for v in self.gpu_worker_availability.values() if v)
        cpu_available = sum(1 for v in self.cpu_worker_availability.values() if v)

        return {
            "total_gpu_workers": len(self.gpu_workers),
            "available_gpu_workers": gpu_available,
            "total_cpu_workers": len(self.cpu_workers),
            "available_cpu_workers": cpu_available,
        }


class TaskExecutor:
    """Execute tasks with GPU routing support."""

    def __init__(self, router: Optional[GPURouter] = None):
        """Initialize task executor.

        Args:
            router: GPU router for task routing
        """
        self.router = router or GPURouter()
        self.execution_handlers: Dict[ExecutorType, Callable] = {}

    def register_handler(
        self,
        executor_type: ExecutorType,
        handler: Callable,
    ) -> None:
        """Register a handler for an executor type.

        Args:
            executor_type: Type of executor
            handler: Async callable to handle execution
        """
        self.execution_handlers[executor_type] = handler
        logger.info(f"Registered handler for {executor_type.value}")

    async def execute(
        self,
        task_id: str,
        task_description: str,
        task_payload: Any,
        task_metadata: Optional[Dict[str, Any]] = None,
    ) -> ExecutionResult:
        """Execute a task with appropriate routing.

        Args:
            task_id: Unique task identifier
            task_description: Description of the task
            task_payload: Task data/code to execute
            task_metadata: Optional task metadata

        Returns:
            ExecutionResult with outcome
        """
        import time

        start_time = time.time()

        try:
            # Route the task
            context = self.router.route_task(task_id, task_description, task_metadata)

            # Get handler for executor type
            handler = self.execution_handlers.get(context.executor_type)

            if not handler:
                return ExecutionResult(
                    task_id=task_id,
                    success=False,
                    error=f"No handler registered for {context.executor_type.value}",
                    execution_time_ms=(time.time() - start_time) * 1000,
                )

            # Get available worker
            worker_id = self.router.get_available_worker(context.executor_type)

            if not worker_id:
                return ExecutionResult(
                    task_id=task_id,
                    success=False,
                    error=f"No available {context.executor_type.value} workers",
                    execution_time_ms=(time.time() - start_time) * 1000,
                )

            # Mark worker busy
            is_gpu = context.executor_type == ExecutorType.GPU_WORKER
            self.router.mark_worker_busy(worker_id, is_gpu)

            try:
                # Execute task
                result = await handler(task_payload, context, worker_id)

                execution_time_ms = (time.time() - start_time) * 1000

                return ExecutionResult(
                    task_id=task_id,
                    success=True,
                    result=result,
                    execution_time_ms=execution_time_ms,
                    executor_type=context.executor_type,
                    gpu_used=is_gpu,
                )

            finally:
                # Mark worker available again
                self.router.mark_worker_available(worker_id, is_gpu)

        except Exception as e:
            logger.exception(f"Error executing task {task_id}")
            execution_time_ms = (time.time() - start_time) * 1000

            return ExecutionResult(
                task_id=task_id,
                success=False,
                error=str(e),
                execution_time_ms=execution_time_ms,
            )


# Example handler functions (placeholder implementations)

async def gpu_worker_handler(
    task_payload: Any,
    context: ExecutionContext,
    worker_id: str,
) -> Any:
    """Handle GPU worker execution (placeholder).

    Args:
        task_payload: Task data
        context: Execution context
        worker_id: GPU worker ID

    Returns:
        Task result
    """
    logger.info(
        f"Executing task {context.task_id} on GPU worker {worker_id} "
        f"(workload={context.workload_type.value})"
    )

    # Placeholder: simulate GPU execution
    await asyncio.sleep(0.1)

    return {
        "status": "completed",
        "worker_id": worker_id,
        "executor_type": "gpu",
        "workload_type": context.workload_type.value,
    }


async def cpu_worker_handler(
    task_payload: Any,
    context: ExecutionContext,
    worker_id: str,
) -> Any:
    """Handle CPU worker execution (placeholder).

    Args:
        task_payload: Task data
        context: Execution context
        worker_id: CPU worker ID

    Returns:
        Task result
    """
    logger.info(
        f"Executing task {context.task_id} on CPU worker {worker_id} "
        f"(workload={context.workload_type.value})"
    )

    # Placeholder: simulate CPU execution
    await asyncio.sleep(0.05)

    return {
        "status": "completed",
        "worker_id": worker_id,
        "executor_type": "cpu",
        "workload_type": context.workload_type.value,
    }


def create_executor(
    gpu_workers: Optional[List[str]] = None,
    cpu_workers: Optional[List[str]] = None,
) -> TaskExecutor:
    """Create a task executor with GPU routing.

    Args:
        gpu_workers: List of GPU worker IDs
        cpu_workers: List of CPU worker IDs

    Returns:
        Configured TaskExecutor
    """
    router = GPURouter(gpu_workers, cpu_workers)
    executor = TaskExecutor(router)

    # Register default handlers
    executor.register_handler(ExecutorType.GPU_WORKER, gpu_worker_handler)
    executor.register_handler(ExecutorType.CPU_WORKER, cpu_worker_handler)

    return executor
