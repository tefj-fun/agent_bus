"""Tests for ML pipeline GPU routing."""

import pytest

from src.ml_pipeline.detector import (
    WorkloadDetector,
    WorkloadType,
    create_detector,
)
from src.ml_pipeline.executor import (
    GPURouter,
    TaskExecutor,
    ExecutorType,
    create_executor,
)


class TestWorkloadDetector:
    """Test workload detection."""

    def test_detector_creation(self):
        """Test creating a detector."""
        detector = create_detector()
        assert detector is not None

    def test_detect_ml_training(self):
        """Test detecting ML training workload."""
        detector = WorkloadDetector()
        signatures = detector.detect(
            "Train a neural network with PyTorch on GPU using backpropagation"
        )

        assert len(signatures) > 0
        # Should detect ML training
        assert any(s.workload_type == WorkloadType.ML_TRAINING for s in signatures)
        assert signatures[0].requires_gpu

    def test_detect_cv_detection(self):
        """Test detecting computer vision workload."""
        detector = WorkloadDetector()
        signatures = detector.detect(
            "Perform object detection with YOLO on video frames"
        )

        assert len(signatures) > 0
        assert any(s.workload_type == WorkloadType.CV_DETECTION for s in signatures)

    def test_detect_nlp_generation(self):
        """Test detecting NLP generation workload."""
        detector = WorkloadDetector()
        signatures = detector.detect(
            "Generate text using GPT transformer model"
        )

        assert len(signatures) > 0
        assert any(s.workload_type == WorkloadType.NLP_GENERATION for s in signatures)

    def test_detect_cpu_bound(self):
        """Test detecting CPU-bound workload."""
        detector = WorkloadDetector()
        signatures = detector.detect(
            "Parse CSV file and perform basic statistics"
        )

        assert len(signatures) > 0
        # Should default to CPU-bound
        assert signatures[0].workload_type == WorkloadType.CPU_BOUND
        assert not signatures[0].requires_gpu

    def test_requires_gpu_true(self):
        """Test GPU requirement detection."""
        detector = WorkloadDetector()
        requires_gpu = detector.requires_gpu(
            "Train CNN with TensorFlow on CUDA GPU"
        )

        assert requires_gpu

    def test_requires_gpu_false(self):
        """Test no GPU requirement."""
        detector = WorkloadDetector()
        requires_gpu = detector.requires_gpu(
            "Sort list and calculate average"
        )

        assert not requires_gpu

    def test_estimate_gpu_memory(self):
        """Test GPU memory estimation."""
        detector = WorkloadDetector()

        # Training should need more memory
        training_mem = detector.estimate_gpu_memory(
            "Train large language model"
        )
        assert training_mem is not None
        assert training_mem > 8.0

        # Inference should need less
        inference_mem = detector.estimate_gpu_memory(
            "Run model inference on test data"
        )
        assert inference_mem is not None
        assert inference_mem < 8.0

        # CPU tasks should return None
        cpu_mem = detector.estimate_gpu_memory(
            "Parse text file"
        )
        assert cpu_mem is None

    def test_confidence_scores(self):
        """Test confidence scoring."""
        detector = WorkloadDetector()

        # Strong indicators should have high confidence
        strong_signatures = detector.detect(
            "Train neural network with PyTorch using GPU acceleration, "
            "backpropagation, and gradient descent optimizer"
        )
        assert strong_signatures[0].confidence > 0.7

        # Weak indicators should have lower confidence
        weak_signatures = detector.detect(
            "Process data"
        )
        assert weak_signatures[0].confidence < 0.9


class TestGPURouter:
    """Test GPU routing."""

    def test_router_creation(self):
        """Test creating a router."""
        router = GPURouter(
            gpu_workers=["gpu-0", "gpu-1"],
            cpu_workers=["cpu-0", "cpu-1"],
        )

        assert len(router.gpu_workers) == 2
        assert len(router.cpu_workers) == 2

    def test_route_to_gpu(self):
        """Test routing GPU workload."""
        router = GPURouter(
            gpu_workers=["gpu-0"],
            cpu_workers=["cpu-0"],
        )

        context = router.route_task(
            "task-1",
            "Train PyTorch model on GPU",
        )

        assert context.executor_type == ExecutorType.GPU_WORKER
        assert context.task_id == "task-1"

    def test_route_to_cpu(self):
        """Test routing CPU workload."""
        router = GPURouter(
            gpu_workers=["gpu-0"],
            cpu_workers=["cpu-0"],
        )

        context = router.route_task(
            "task-2",
            "Parse JSON file",
        )

        assert context.executor_type == ExecutorType.CPU_WORKER

    def test_fallback_to_cpu_when_no_gpu(self):
        """Test fallback to CPU when no GPU workers."""
        router = GPURouter(
            gpu_workers=[],
            cpu_workers=["cpu-0"],
        )

        context = router.route_task(
            "task-3",
            "Train neural network",  # Normally requires GPU
        )

        # Should fall back to CPU
        assert context.executor_type == ExecutorType.CPU_WORKER

    def test_get_available_worker(self):
        """Test getting available workers."""
        router = GPURouter(
            gpu_workers=["gpu-0", "gpu-1"],
            cpu_workers=["cpu-0"],
        )

        # Should get a GPU worker
        worker = router.get_available_worker(ExecutorType.GPU_WORKER)
        assert worker in ["gpu-0", "gpu-1"]

        # Should get CPU worker
        worker = router.get_available_worker(ExecutorType.CPU_WORKER)
        assert worker == "cpu-0"

    def test_worker_availability_tracking(self):
        """Test tracking worker availability."""
        router = GPURouter(
            gpu_workers=["gpu-0"],
            cpu_workers=[],
        )

        # Initially available
        worker = router.get_available_worker(ExecutorType.GPU_WORKER)
        assert worker == "gpu-0"

        # Mark busy
        router.mark_worker_busy("gpu-0", is_gpu=True)
        worker = router.get_available_worker(ExecutorType.GPU_WORKER)
        assert worker is None

        # Mark available again
        router.mark_worker_available("gpu-0", is_gpu=True)
        worker = router.get_available_worker(ExecutorType.GPU_WORKER)
        assert worker == "gpu-0"

    def test_get_stats(self):
        """Test getting router statistics."""
        router = GPURouter(
            gpu_workers=["gpu-0", "gpu-1"],
            cpu_workers=["cpu-0"],
        )

        stats = router.get_stats()

        assert stats["total_gpu_workers"] == 2
        assert stats["available_gpu_workers"] == 2
        assert stats["total_cpu_workers"] == 1
        assert stats["available_cpu_workers"] == 1

        # Mark one GPU busy
        router.mark_worker_busy("gpu-0", is_gpu=True)
        stats = router.get_stats()
        assert stats["available_gpu_workers"] == 1


class TestTaskExecutor:
    """Test task executor."""

    def test_executor_creation(self):
        """Test creating an executor."""
        executor = create_executor(
            gpu_workers=["gpu-0"],
            cpu_workers=["cpu-0"],
        )

        assert executor is not None
        assert executor.router is not None

    @pytest.mark.asyncio
    async def test_execute_gpu_task(self):
        """Test executing GPU task."""
        executor = create_executor(
            gpu_workers=["gpu-0"],
            cpu_workers=["cpu-0"],
        )

        result = await executor.execute(
            task_id="test-gpu",
            task_description="Train PyTorch model",
            task_payload={"model": "resnet"},
        )

        assert result.success
        assert result.task_id == "test-gpu"
        assert result.gpu_used

    @pytest.mark.asyncio
    async def test_execute_cpu_task(self):
        """Test executing CPU task."""
        executor = create_executor(
            gpu_workers=["gpu-0"],
            cpu_workers=["cpu-0"],
        )

        result = await executor.execute(
            task_id="test-cpu",
            task_description="Parse data file",
            task_payload={"file": "data.json"},
        )

        assert result.success
        assert result.task_id == "test-cpu"
        assert not result.gpu_used

    @pytest.mark.asyncio
    async def test_execute_no_available_workers(self):
        """Test execution when no workers available."""
        executor = create_executor(
            gpu_workers=[],
            cpu_workers=[],
        )

        result = await executor.execute(
            task_id="test-fail",
            task_description="Some task",
            task_payload={},
        )

        assert not result.success
        assert "No available" in result.error

    @pytest.mark.asyncio
    async def test_worker_released_after_execution(self):
        """Test that workers are released after execution."""
        executor = create_executor(
            gpu_workers=["gpu-0"],
            cpu_workers=[],
        )

        # Execute first task
        result1 = await executor.execute(
            task_id="task-1",
            task_description="Train model",
            task_payload={},
        )
        assert result1.success

        # Execute second task - should succeed because worker was released
        result2 = await executor.execute(
            task_id="task-2",
            task_description="Train another model",
            task_payload={},
        )
        assert result2.success


class TestIntegration:
    """Integration tests for ML pipeline."""

    @pytest.mark.asyncio
    async def test_end_to_end_gpu_routing(self):
        """Test end-to-end GPU routing workflow."""
        executor = create_executor(
            gpu_workers=["gpu-0", "gpu-1"],
            cpu_workers=["cpu-0"],
        )

        # Submit ML training task
        result = await executor.execute(
            task_id="ml-train-1",
            task_description="Train ResNet model with PyTorch on GPU",
            task_payload={"model": "resnet50", "epochs": 10},
        )

        assert result.success
        assert result.gpu_used
        assert result.executor_type == ExecutorType.GPU_WORKER

    @pytest.mark.asyncio
    async def test_mixed_workload_routing(self):
        """Test routing mixed CPU and GPU workloads."""
        executor = create_executor(
            gpu_workers=["gpu-0"],
            cpu_workers=["cpu-0"],
        )

        # GPU task
        gpu_result = await executor.execute(
            task_id="gpu-task",
            task_description="Image classification with CNN",
            task_payload={},
        )

        # CPU task
        cpu_result = await executor.execute(
            task_id="cpu-task",
            task_description="Parse configuration file",
            task_payload={},
        )

        assert gpu_result.success and gpu_result.gpu_used
        assert cpu_result.success and not cpu_result.gpu_used
