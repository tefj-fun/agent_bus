"""ML Workload Detection Module.

Analyzes project requirements to determine if ML/CV workloads are needed
and what resources they require.
"""
import re
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum


class WorkloadType(str, Enum):
    """Type of workload detected."""
    CPU_ONLY = "cpu_only"
    GPU_REQUIRED = "gpu_required"
    GPU_OPTIONAL = "gpu_optional"


@dataclass
class MLWorkloadAnalysis:
    """Result of ML workload analysis."""
    is_ml_workload: bool
    confidence: float  # 0.0 to 1.0
    workload_type: WorkloadType
    detected_keywords: List[str]
    required_gpu_count: int
    estimated_memory_gb: int
    estimated_cpu_cores: int
    reasoning: str


class MLWorkloadDetector:
    """Detects ML/CV workloads from project requirements."""
    
    # Keywords that indicate ML/CV workload
    ML_KEYWORDS = {
        # Core ML terms
        "machine learning": 0.9,
        "deep learning": 0.95,
        "neural network": 0.95,
        "artificial intelligence": 0.7,
        "ai model": 0.85,
        "model training": 0.95,
        "model inference": 0.8,
        
        # Computer vision
        "computer vision": 0.95,
        "image recognition": 0.9,
        "object detection": 0.95,
        "image classification": 0.9,
        "semantic segmentation": 0.95,
        "face recognition": 0.9,
        "ocr": 0.8,
        "optical character recognition": 0.8,
        
        # NLP
        "natural language processing": 0.9,
        "nlp": 0.85,
        "text classification": 0.8,
        "sentiment analysis": 0.8,
        "language model": 0.9,
        "llm": 0.85,
        "transformer": 0.9,
        "bert": 0.95,
        "gpt": 0.95,
        
        # ML frameworks
        "tensorflow": 0.85,
        "pytorch": 0.85,
        "keras": 0.85,
        "scikit-learn": 0.7,
        "xgboost": 0.75,
        "lightgbm": 0.75,
        
        # Common ML tasks
        "recommendation system": 0.8,
        "anomaly detection": 0.75,
        "time series forecasting": 0.7,
        "clustering": 0.6,
        "regression": 0.5,
        "classification": 0.6,
        "prediction": 0.5,
    }
    
    # GPU-required keywords
    GPU_REQUIRED_KEYWORDS = {
        "gpu", "cuda", "training", "fine-tuning", "deep learning",
        "neural network", "cnn", "rnn", "lstm", "transformer",
        "large model", "llm training", "stable diffusion",
    }
    
    # Resource estimation rules
    RESOURCE_PROFILES = {
        "small": {"gpu": 0, "memory_gb": 4, "cpu_cores": 2},
        "medium": {"gpu": 1, "memory_gb": 16, "cpu_cores": 4},
        "large": {"gpu": 1, "memory_gb": 32, "cpu_cores": 8},
        "xlarge": {"gpu": 2, "memory_gb": 64, "cpu_cores": 16},
    }
    
    def __init__(self):
        """Initialize the detector."""
        pass
    
    def analyze(self, requirements: str, prd: Optional[str] = None) -> MLWorkloadAnalysis:
        """
        Analyze requirements to detect ML workload.
        
        Args:
            requirements: User requirements text
            prd: Product requirements document (optional, for additional context)
            
        Returns:
            MLWorkloadAnalysis with detection results
        """
        # Combine text for analysis
        text = requirements.lower()
        if prd:
            text += " " + prd.lower()
        
        # Detect keywords
        detected_keywords = []
        confidence_scores = []
        
        for keyword, score in self.ML_KEYWORDS.items():
            if keyword in text:
                detected_keywords.append(keyword)
                confidence_scores.append(score)
        
        # Calculate overall confidence
        if not confidence_scores:
            confidence = 0.0
        else:
            # Use maximum score with some smoothing
            confidence = max(confidence_scores)
            if len(confidence_scores) > 1:
                confidence = min(1.0, confidence + 0.05 * (len(confidence_scores) - 1))
        
        is_ml_workload = confidence >= 0.5
        
        # Determine workload type
        workload_type = self._determine_workload_type(text, detected_keywords)
        
        # Estimate resources
        resource_profile = self._estimate_resources(text, workload_type, detected_keywords)
        
        # Generate reasoning
        reasoning = self._generate_reasoning(
            is_ml_workload, confidence, detected_keywords, workload_type
        )
        
        return MLWorkloadAnalysis(
            is_ml_workload=is_ml_workload,
            confidence=confidence,
            workload_type=workload_type,
            detected_keywords=detected_keywords,
            required_gpu_count=resource_profile["gpu"],
            estimated_memory_gb=resource_profile["memory_gb"],
            estimated_cpu_cores=resource_profile["cpu_cores"],
            reasoning=reasoning,
        )
    
    def _determine_workload_type(
        self, text: str, detected_keywords: List[str]
    ) -> WorkloadType:
        """Determine if GPU is required, optional, or not needed."""
        # Check for GPU-required keywords
        gpu_required = any(kw in text for kw in self.GPU_REQUIRED_KEYWORDS)
        
        # Check for inference-only keywords
        inference_only = any(
            kw in text for kw in ["inference", "prediction", "deploy model"]
        ) and not any(kw in text for kw in ["training", "fine-tuning"])
        
        # Check for small ML tasks
        small_ml = any(
            kw in detected_keywords
            for kw in ["scikit-learn", "clustering", "regression", "classification"]
        ) and not any(
            kw in detected_keywords
            for kw in ["deep learning", "neural network", "transformer"]
        )
        
        if gpu_required:
            return WorkloadType.GPU_REQUIRED
        elif inference_only or small_ml:
            return WorkloadType.CPU_ONLY
        elif detected_keywords:
            return WorkloadType.GPU_OPTIONAL
        else:
            return WorkloadType.CPU_ONLY
    
    def _estimate_resources(
        self, text: str, workload_type: WorkloadType, detected_keywords: List[str]
    ) -> Dict[str, int]:
        """Estimate required computing resources."""
        # Default to small profile
        profile = "small"
        
        # Check for size indicators
        if any(kw in text for kw in ["large model", "llm", "stable diffusion", "gpt"]):
            profile = "xlarge"
        elif any(kw in text for kw in ["training", "fine-tuning", "deep learning"]):
            profile = "large"
        elif workload_type == WorkloadType.GPU_REQUIRED:
            profile = "medium"
        elif len(detected_keywords) > 5:
            profile = "medium"
        
        return self.RESOURCE_PROFILES[profile].copy()
    
    def _generate_reasoning(
        self,
        is_ml_workload: bool,
        confidence: float,
        detected_keywords: List[str],
        workload_type: WorkloadType,
    ) -> str:
        """Generate human-readable reasoning for the analysis."""
        if not is_ml_workload:
            return "No ML/CV workload detected. Project appears to be standard software development."
        
        reasoning_parts = [
            f"ML workload detected with {confidence:.1%} confidence.",
            f"Found {len(detected_keywords)} relevant keywords: {', '.join(detected_keywords[:5])}",
        ]
        
        if workload_type == WorkloadType.GPU_REQUIRED:
            reasoning_parts.append("GPU acceleration is required for this workload.")
        elif workload_type == WorkloadType.GPU_OPTIONAL:
            reasoning_parts.append("GPU acceleration is optional but recommended.")
        else:
            reasoning_parts.append("CPU-only execution should be sufficient.")
        
        return " ".join(reasoning_parts)
    
    def should_route_to_gpu(self, analysis: MLWorkloadAnalysis) -> bool:
        """
        Determine if work should be routed to GPU worker.
        
        Args:
            analysis: MLWorkloadAnalysis result
            
        Returns:
            True if should route to GPU worker
        """
        return (
            analysis.is_ml_workload
            and analysis.workload_type == WorkloadType.GPU_REQUIRED
            and analysis.required_gpu_count > 0
        )


# Singleton instance
_detector = MLWorkloadDetector()


def detect_ml_workload(requirements: str, prd: Optional[str] = None) -> MLWorkloadAnalysis:
    """
    Convenience function to detect ML workload.
    
    Args:
        requirements: User requirements text
        prd: Product requirements document (optional)
        
    Returns:
        MLWorkloadAnalysis result
    """
    return _detector.analyze(requirements, prd)
