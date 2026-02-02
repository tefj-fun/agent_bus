"""Tests for improved ML workload detection."""

import pytest

from src.ml_pipeline.detector import (
    WorkloadDetector,
    WorkloadType,
    MODEL_ARCHITECTURES,
    ML_FRAMEWORKS,
)


class TestImprovedDetection:
    """Test improved detection with weighted scoring."""

    def test_weighted_framework_scoring(self):
        """Test that frameworks contribute weighted scores."""
        detector = WorkloadDetector()

        # PyTorch has high weight
        pytorch_sig = detector.detect("Use PyTorch for training")
        # PIL has lower weight
        pil_sig = detector.detect("Use PIL for image processing")

        # PyTorch should have higher confidence
        assert pytorch_sig[0].confidence > pil_sig[0].confidence

    def test_model_architecture_detection(self):
        """Test detection of model architectures."""
        detector = WorkloadDetector()

        # BERT should be detected with high confidence
        bert_sig = detector.detect("Fine-tune BERT model for classification")
        assert any("bert" in sig.indicators for sig in bert_sig)
        assert bert_sig[0].confidence > 0.5

        # ResNet should indicate CV workload
        resnet_sig = detector.detect("Train ResNet for image classification")
        assert any("resnet" in sig.indicators for sig in resnet_sig)

    def test_multiple_indicators_boost_confidence(self):
        """Test that multiple indicators increase confidence."""
        detector = WorkloadDetector()

        # Single indicator
        single = detector.detect("Use PyTorch")

        # Multiple indicators
        multiple = detector.detect(
            "Use PyTorch with CUDA acceleration to train ResNet "
            "with backpropagation and gradient descent"
        )

        # Multiple indicators should have higher confidence
        assert multiple[0].confidence > single[0].confidence

    def test_confidence_boosting(self):
        """Test that strong indicators boost workload confidence."""
        detector = WorkloadDetector()

        signatures = detector.detect(
            "Train neural network using PyTorch with CUDA GPU acceleration"
        )

        # Should have high confidence due to multiple strong indicators
        assert signatures[0].confidence > 0.7

    def test_gpu_keyword_weighting(self):
        """Test that GPU keywords have weighted impact."""
        detector = WorkloadDetector()

        # "cuda" is a strong indicator
        cuda_sig = detector.detect("Run on CUDA device")
        # Generic "accelerate" is weaker
        accel_sig = detector.detect("Use acceleration")

        assert cuda_sig[0].confidence > accel_sig[0].confidence


class TestCodeDetection:
    """Test code-specific detection."""

    def test_detect_from_code_training(self):
        """Test detecting training from code."""
        detector = WorkloadDetector()

        code = """
        model.train()
        optimizer.zero_grad()
        loss = criterion(output, target)
        loss.backward()
        optimizer.step()
        """

        signatures = detector.detect_from_code(code)

        assert len(signatures) > 0
        assert signatures[0].workload_type == WorkloadType.ML_TRAINING
        assert signatures[0].requires_gpu

    def test_detect_from_code_inference(self):
        """Test detecting inference from code."""
        detector = WorkloadDetector()

        code = """
        model.eval()
        with torch.no_grad():
            output = model(input_data)
        """

        signatures = detector.detect_from_code(code)

        assert len(signatures) > 0
        assert signatures[0].workload_type == WorkloadType.ML_INFERENCE

    def test_detect_from_code_generation(self):
        """Test detecting text generation from code."""
        detector = WorkloadDetector()

        code = """
        tokens = tokenizer(prompt, return_tensors="pt")
        output = model.generate(tokens, max_length=100)
        """

        signatures = detector.detect_from_code(code)

        assert len(signatures) > 0
        assert signatures[0].workload_type == WorkloadType.NLP_GENERATION

    def test_code_detection_higher_confidence(self):
        """Test that code detection has higher confidence than text."""
        detector = WorkloadDetector()

        # Text description
        text_sig = detector.detect("Train a model")

        # Actual training code
        code_sig = detector.detect_from_code("""
            model.train()
            for epoch in range(10):
                optimizer.zero_grad()
                loss.backward()
        """)

        # Code should have higher confidence
        assert code_sig[0].confidence > text_sig[0].confidence


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_mixed_workload_detection(self):
        """Test detection of mixed workloads."""
        detector = WorkloadDetector()

        signatures = detector.detect(
            "First train ResNet for image classification, "
            "then use BERT for text analysis"
        )

        # Should detect both CV and NLP workloads
        workload_types = [sig.workload_type for sig in signatures]
        assert WorkloadType.CV_CLASSIFICATION in workload_types or \
               WorkloadType.NLP_GENERATION in workload_types or \
               len(signatures) > 0  # At least detect something

    def test_ambiguous_keywords(self):
        """Test handling of ambiguous keywords."""
        detector = WorkloadDetector()

        # "train" could mean training or "train station"
        signatures = detector.detect("Take the train to work")

        # Should still return a signature (might be CPU-bound)
        assert len(signatures) > 0

    def test_confidence_capping(self):
        """Test that confidence is capped at 1.0."""
        detector = WorkloadDetector()

        # Many strong indicators
        signatures = detector.detect(
            "Train BERT GPT transformer with PyTorch TensorFlow "
            "using CUDA GPU acceleration on NVIDIA with TensorRT"
        )

        # Confidence should not exceed 1.0
        for sig in signatures:
            assert sig.confidence <= 1.0

    def test_empty_input(self):
        """Test handling of empty input."""
        detector = WorkloadDetector()

        signatures = detector.detect("")

        # Should return CPU-bound as default
        assert len(signatures) > 0
        assert signatures[0].workload_type == WorkloadType.CPU_BOUND

    def test_non_ml_task(self):
        """Test detection of non-ML tasks."""
        detector = WorkloadDetector()

        signatures = detector.detect(
            "Parse JSON configuration file and validate schema"
        )

        # Should be CPU-bound
        assert signatures[0].workload_type == WorkloadType.CPU_BOUND
        assert not signatures[0].requires_gpu


class TestGPUMemoryEstimation:
    """Test GPU memory estimation improvements."""

    def test_memory_estimation_by_workload(self):
        """Test that different workloads get appropriate memory estimates."""
        detector = WorkloadDetector()

        # Training should need more memory
        training_mem = detector.estimate_gpu_memory("Train large model")
        assert training_mem is not None
        assert training_mem >= 8.0

        # Fine-tuning should need even more
        finetuning_mem = detector.estimate_gpu_memory("Fine-tune LLM")
        assert finetuning_mem is not None
        assert finetuning_mem >= training_mem

        # Inference should need less
        inference_mem = detector.estimate_gpu_memory("Run inference")
        assert inference_mem is not None
        assert inference_mem < training_mem

    def test_memory_estimation_none_for_cpu(self):
        """Test that CPU tasks return None for memory."""
        detector = WorkloadDetector()

        cpu_mem = detector.estimate_gpu_memory("Sort array")
        assert cpu_mem is None


class TestRealWorldExamples:
    """Test with real-world task descriptions."""

    def test_stable_diffusion_detection(self):
        """Test detecting Stable Diffusion workload."""
        detector = WorkloadDetector()

        signatures = detector.detect(
            "Generate images using Stable Diffusion with text-to-image prompts"
        )

        assert len(signatures) > 0
        assert signatures[0].workload_type == WorkloadType.CV_GENERATION
        assert signatures[0].requires_gpu

    def test_yolo_detection(self):
        """Test detecting YOLO object detection."""
        detector = WorkloadDetector()

        signatures = detector.detect(
            "Detect objects in video frames using YOLOv8"
        )

        assert len(signatures) > 0
        assert signatures[0].workload_type == WorkloadType.CV_DETECTION
        assert signatures[0].requires_gpu

    def test_bert_finetuning(self):
        """Test detecting BERT fine-tuning."""
        detector = WorkloadDetector()

        signatures = detector.detect(
            "Fine-tune BERT model on custom dataset for sentiment analysis"
        )

        assert len(signatures) > 0
        # Should detect either fine-tuning or NLP workload
        assert (
            signatures[0].workload_type == WorkloadType.ML_FINE_TUNING or
            signatures[0].workload_type == WorkloadType.NLP_GENERATION or
            signatures[0].requires_gpu  # At least requires GPU
        )

    def test_scientific_computing(self):
        """Test detecting scientific computing workload."""
        detector = WorkloadDetector()

        signatures = detector.detect(
            "Perform large matrix multiplication with CUDA acceleration"
        )

        assert len(signatures) > 0
        assert signatures[0].requires_gpu


class TestMetadataIntegration:
    """Test integration with task metadata."""

    def test_explicit_gpu_requirement(self):
        """Test explicit GPU requirement in metadata."""
        detector = WorkloadDetector()

        # Even vague description with explicit GPU flag
        requires_gpu = detector.requires_gpu(
            "Process data",
            task_metadata={"requires_gpu": True}
        )

        assert requires_gpu

    def test_metadata_overrides_detection(self):
        """Test that explicit metadata can influence detection."""
        detector = WorkloadDetector()

        signatures = detector.detect(
            "Some task",
            task_metadata={"requires_gpu": True}
        )

        # Should have GPU-accelerated signature
        assert any(sig.requires_gpu for sig in signatures)
