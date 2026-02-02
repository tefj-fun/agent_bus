"""Tests for ML workload detector."""
import pytest
from src.ml_pipeline.detector import (
    MLWorkloadDetector,
    detect_ml_workload,
    WorkloadType,
)


class TestMLWorkloadDetector:
    """Test ML workload detection."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.detector = MLWorkloadDetector()
    
    def test_detect_no_ml_workload(self):
        """Test detection of non-ML project."""
        requirements = """
        Build a simple CRUD web application for managing contacts.
        Users should be able to create, read, update, and delete contacts.
        Include authentication and authorization.
        """
        
        analysis = self.detector.analyze(requirements)
        
        assert not analysis.is_ml_workload
        assert analysis.confidence < 0.5
        assert analysis.workload_type == WorkloadType.CPU_ONLY
        assert analysis.required_gpu_count == 0
    
    def test_detect_ml_workload_image_recognition(self):
        """Test detection of image recognition ML workload."""
        requirements = """
        Build an image recognition system that can classify images into categories.
        Use a pre-trained neural network for inference.
        The system should handle 100 images per second.
        """
        
        analysis = self.detector.analyze(requirements)
        
        assert analysis.is_ml_workload
        assert analysis.confidence >= 0.5
        assert "image recognition" in analysis.detected_keywords
        assert "neural network" in analysis.detected_keywords
    
    def test_detect_gpu_required_training(self):
        """Test detection of GPU-required training workload."""
        requirements = """
        Develop a deep learning model for object detection.
        Train the model on a custom dataset using GPU acceleration.
        The training should use PyTorch and CUDA.
        """
        
        analysis = self.detector.analyze(requirements)
        
        assert analysis.is_ml_workload
        assert analysis.workload_type == WorkloadType.GPU_REQUIRED
        assert analysis.required_gpu_count >= 1
        assert analysis.confidence >= 0.8
    
    def test_detect_cpu_only_ml(self):
        """Test detection of CPU-only ML workload."""
        requirements = """
        Create a simple classification model using scikit-learn.
        The model should predict customer churn based on historical data.
        Use logistic regression or random forest.
        """
        
        analysis = self.detector.analyze(requirements)
        
        assert analysis.is_ml_workload
        assert analysis.workload_type == WorkloadType.CPU_ONLY
        assert analysis.required_gpu_count == 0
        assert "scikit-learn" in analysis.detected_keywords
    
    def test_detect_llm_workload(self):
        """Test detection of LLM workload."""
        requirements = """
        Build a chatbot using a large language model.
        Fine-tune GPT on company-specific data.
        Deploy for customer service automation.
        """
        
        analysis = self.detector.analyze(requirements)
        
        assert analysis.is_ml_workload
        assert analysis.workload_type == WorkloadType.GPU_REQUIRED
        assert analysis.required_gpu_count >= 1
        assert "gpt" in analysis.detected_keywords
        assert "language model" in analysis.detected_keywords
    
    def test_detect_computer_vision(self):
        """Test detection of computer vision workload."""
        requirements = """
        Implement a computer vision system for quality control.
        Detect defects in manufactured parts using image processing.
        Use OpenCV and TensorFlow for the implementation.
        """
        
        analysis = self.detector.analyze(requirements)
        
        assert analysis.is_ml_workload
        assert analysis.confidence >= 0.8
        assert "computer vision" in analysis.detected_keywords
        assert analysis.estimated_memory_gb > 0
    
    def test_detect_inference_only(self):
        """Test detection of inference-only workload."""
        requirements = """
        Deploy a trained model for inference.
        The model should predict customer lifetime value.
        Use model inference endpoint with REST API.
        """
        
        analysis = self.detector.analyze(requirements)
        
        assert analysis.is_ml_workload
        # Inference can be CPU or GPU optional
        assert analysis.workload_type in (
            WorkloadType.CPU_ONLY,
            WorkloadType.GPU_OPTIONAL
        )
    
    def test_resource_estimation_small(self):
        """Test resource estimation for small ML task."""
        requirements = "Simple classification with scikit-learn"
        
        analysis = self.detector.analyze(requirements)
        
        assert analysis.estimated_cpu_cores >= 2
        assert analysis.estimated_memory_gb >= 4
    
    def test_resource_estimation_large(self):
        """Test resource estimation for large ML task."""
        requirements = """
        Train a large language model on company data.
        Use GPT-3 architecture with custom fine-tuning.
        Process millions of documents.
        """
        
        analysis = self.detector.analyze(requirements)
        
        assert analysis.required_gpu_count >= 1
        assert analysis.estimated_memory_gb >= 32
        assert analysis.estimated_cpu_cores >= 8
    
    def test_should_route_to_gpu(self):
        """Test GPU routing decision."""
        # GPU required
        requirements = "Train deep learning model with GPU acceleration"
        analysis = self.detector.analyze(requirements)
        assert self.detector.should_route_to_gpu(analysis)
        
        # CPU only
        requirements = "Simple linear regression"
        analysis = self.detector.analyze(requirements)
        assert not self.detector.should_route_to_gpu(analysis)
    
    def test_confidence_calculation(self):
        """Test confidence score calculation."""
        # High confidence - multiple strong keywords
        requirements = """
        Deep learning neural network for image classification
        using TensorFlow and GPU training.
        """
        analysis = self.detector.analyze(requirements)
        assert analysis.confidence >= 0.9
        
        # Low confidence - weak indicators
        requirements = "Data analysis and prediction"
        analysis = self.detector.analyze(requirements)
        assert analysis.confidence < 0.7
    
    def test_reasoning_generation(self):
        """Test reasoning message generation."""
        requirements = "Build a computer vision system"
        analysis = self.detector.analyze(requirements)
        
        assert len(analysis.reasoning) > 0
        assert "computer vision" in analysis.reasoning.lower()
        assert "confidence" in analysis.reasoning.lower()
    
    def test_convenience_function(self):
        """Test convenience function."""
        requirements = "Machine learning classification"
        analysis = detect_ml_workload(requirements)
        
        assert isinstance(analysis.is_ml_workload, bool)
        assert isinstance(analysis.confidence, float)
        assert 0 <= analysis.confidence <= 1
    
    def test_with_prd_context(self):
        """Test detection with additional PRD context."""
        requirements = "Build a system for users"
        prd = """
        Product Requirements:
        - Implement neural network for recommendations
        - Use deep learning for personalization
        - GPU acceleration required
        """
        
        analysis = detect_ml_workload(requirements, prd)
        
        assert analysis.is_ml_workload
        assert analysis.workload_type == WorkloadType.GPU_REQUIRED
    
    def test_multiple_ml_keywords(self):
        """Test detection with multiple ML keywords."""
        requirements = """
        Create a comprehensive AI system:
        - NLP for text analysis
        - Computer vision for image processing
        - Recommendation system for users
        - Deep learning models throughout
        """
        
        analysis = self.detector.analyze(requirements)
        
        assert analysis.is_ml_workload
        assert len(analysis.detected_keywords) >= 4
        assert analysis.confidence >= 0.9
