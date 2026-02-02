"""ML/CV workload detection for GPU routing."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional


class WorkloadType(str, Enum):
    """Type of computational workload."""

    # Machine Learning / AI
    ML_TRAINING = "ml_training"  # Model training
    ML_INFERENCE = "ml_inference"  # Model inference/prediction
    ML_FINE_TUNING = "ml_fine_tuning"  # Fine-tuning pre-trained models

    # Computer Vision
    CV_DETECTION = "cv_detection"  # Object detection
    CV_SEGMENTATION = "cv_segmentation"  # Image segmentation
    CV_CLASSIFICATION = "cv_classification"  # Image classification
    CV_GENERATION = "cv_generation"  # Image generation (DALL-E, Stable Diffusion)

    # Natural Language Processing
    NLP_GENERATION = "nlp_generation"  # Text generation (LLMs)
    NLP_EMBEDDING = "nlp_embedding"  # Text embeddings
    NLP_TRANSLATION = "nlp_translation"  # Translation

    # Scientific Computing
    SCIENTIFIC_COMPUTE = "scientific_compute"  # General scientific computation
    MATRIX_OPS = "matrix_ops"  # Large matrix operations

    # Generic
    GPU_ACCELERATED = "gpu_accelerated"  # Generic GPU-accelerated task
    CPU_BOUND = "cpu_bound"  # CPU-only task


@dataclass
class WorkloadSignature:
    """Signature indicating a specific workload type."""

    workload_type: WorkloadType
    confidence: float  # 0.0 to 1.0
    indicators: List[str]  # What triggered this detection
    requires_gpu: bool = True
    min_gpu_memory_gb: Optional[float] = None


# Keyword patterns for workload detection
WORKLOAD_PATTERNS = {
    WorkloadType.ML_TRAINING: [
        r"\btrain(?:ing)?\b",
        r"\bfit\b",
        r"\bbackprop",
        r"\bgradient\s+descent",
        r"\boptimize(?:r)?\b",
        r"\bloss\s+function",
        r"\bepoch",
        r"\bbatch\s+size",
    ],
    WorkloadType.ML_INFERENCE: [
        r"\bpredict(?:ion)?\b",
        r"\binference\b",
        r"\bforward\s+pass",
        r"\bmodel\.predict",
        r"\bclassify\b",
    ],
    WorkloadType.ML_FINE_TUNING: [
        r"\bfine[- ]tun",
        r"\btransfer\s+learning",
        r"\badapt\s+model",
    ],
    WorkloadType.CV_DETECTION: [
        r"\bobject\s+detection",
        r"\byolo",
        r"\brcnn",
        r"\bdetect\s+objects",
        r"\bbounding\s+box",
    ],
    WorkloadType.CV_SEGMENTATION: [
        r"\bsegmentation",
        r"\bmask\s+rcnn",
        r"\bunet",
        r"\bsemantic\s+segment",
    ],
    WorkloadType.CV_CLASSIFICATION: [
        r"\bimage\s+classification",
        r"\bresnet",
        r"\bvgg",
        r"\bconvnet",
        r"\bcnn",
    ],
    WorkloadType.CV_GENERATION: [
        r"\bstable\s+diffusion",
        r"\bdall[- ]?e",
        r"\bgan",
        r"\bimage\s+generation",
        r"\btext[- ]to[- ]image",
    ],
    WorkloadType.NLP_GENERATION: [
        r"\bllm",
        r"\bgpt",
        r"\btransformer",
        r"\btext\s+generation",
        r"\bcausal\s+lm",
    ],
    WorkloadType.NLP_EMBEDDING: [
        r"\bembedding",
        r"\bbert",
        r"\bsentence[- ]transformer",
        r"\bvector(?:ize)?",
    ],
    WorkloadType.NLP_TRANSLATION: [
        r"\btranslat(?:e|ion)",
        r"\bseq2seq",
    ],
    WorkloadType.MATRIX_OPS: [
        r"\bmatrix\s+multiplication",
        r"\btensor\s+operation",
        r"\bcuda",
        r"\bcublas",
    ],
}

# Library/framework indicators
ML_FRAMEWORKS = [
    "torch", "pytorch", "tensorflow", "tf", "keras",
    "jax", "sklearn", "scikit-learn", "xgboost", "lightgbm",
]

CV_LIBRARIES = [
    "opencv", "cv2", "pillow", "pil", "torchvision",
    "detectron2", "mmdetection", "albumentations",
]

NLP_LIBRARIES = [
    "transformers", "huggingface", "spacy", "nltk",
    "gensim", "sentence-transformers",
]

GPU_KEYWORDS = [
    "gpu", "cuda", "cudnn", "tensorrt", "nvidia",
    "accelerat", "device=cuda", "to(\"cuda\")",
]


class WorkloadDetector:
    """Detect ML/CV workload types from task descriptions."""

    def __init__(self):
        """Initialize workload detector."""
        self.compiled_patterns: Dict[WorkloadType, List[re.Pattern]] = {}

        # Compile regex patterns for efficiency
        for workload_type, patterns in WORKLOAD_PATTERNS.items():
            self.compiled_patterns[workload_type] = [
                re.compile(pattern, re.IGNORECASE) for pattern in patterns
            ]

    def detect(
        self,
        task_description: str,
        task_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[WorkloadSignature]:
        """Detect workload types from task description.

        Args:
            task_description: Description of the task
            task_metadata: Optional metadata (e.g., libraries, tags)

        Returns:
            List of detected workload signatures, sorted by confidence
        """
        text = task_description.lower()
        metadata = task_metadata or {}

        signatures: List[WorkloadSignature] = []

        # Check for explicit GPU requirement in metadata
        explicit_gpu = metadata.get("requires_gpu", False)

        # Detect specific workload patterns
        for workload_type, patterns in self.compiled_patterns.items():
            matches = []
            for pattern in patterns:
                if pattern.search(text):
                    matches.append(pattern.pattern)

            if matches:
                confidence = min(1.0, len(matches) * 0.3)  # More matches = higher confidence
                signatures.append(
                    WorkloadSignature(
                        workload_type=workload_type,
                        confidence=confidence,
                        indicators=matches,
                        requires_gpu=True,
                    )
                )

        # Check for framework/library indicators
        framework_score = 0.0
        framework_indicators = []

        for framework in ML_FRAMEWORKS + CV_LIBRARIES + NLP_LIBRARIES:
            if framework.lower() in text:
                framework_score += 0.2
                framework_indicators.append(framework)

        # Check for GPU keywords
        gpu_score = 0.0
        gpu_indicators = []

        for keyword in GPU_KEYWORDS:
            if keyword.lower() in text:
                gpu_score += 0.3
                gpu_indicators.append(keyword)

        # Add generic GPU-accelerated signature if indicators found but no specific workload
        if (framework_score > 0 or gpu_score > 0 or explicit_gpu) and not signatures:
            confidence = min(1.0, framework_score + gpu_score + (0.5 if explicit_gpu else 0))
            signatures.append(
                WorkloadSignature(
                    workload_type=WorkloadType.GPU_ACCELERATED,
                    confidence=confidence,
                    indicators=framework_indicators + gpu_indicators,
                    requires_gpu=True,
                )
            )

        # If no GPU indicators at all, mark as CPU-bound
        if not signatures:
            signatures.append(
                WorkloadSignature(
                    workload_type=WorkloadType.CPU_BOUND,
                    confidence=0.8,
                    indicators=["no_gpu_indicators"],
                    requires_gpu=False,
                )
            )

        # Sort by confidence (highest first)
        signatures.sort(key=lambda s: s.confidence, reverse=True)

        return signatures

    def requires_gpu(
        self,
        task_description: str,
        task_metadata: Optional[Dict[str, Any]] = None,
        threshold: float = 0.5,
    ) -> bool:
        """Determine if a task requires GPU acceleration.

        Args:
            task_description: Description of the task
            task_metadata: Optional metadata
            threshold: Confidence threshold for requiring GPU

        Returns:
            True if GPU is required
        """
        signatures = self.detect(task_description, task_metadata)

        if not signatures:
            return False

        # Check highest confidence signature
        top_signature = signatures[0]

        return (
            top_signature.requires_gpu
            and top_signature.confidence >= threshold
            and top_signature.workload_type != WorkloadType.CPU_BOUND
        )

    def estimate_gpu_memory(
        self,
        task_description: str,
        task_metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[float]:
        """Estimate GPU memory requirements in GB.

        Args:
            task_description: Description of the task
            task_metadata: Optional metadata

        Returns:
            Estimated GPU memory in GB, or None if not applicable
        """
        signatures = self.detect(task_description, task_metadata)

        if not signatures or not signatures[0].requires_gpu:
            return None

        workload = signatures[0].workload_type

        # Rough estimates based on workload type
        memory_estimates = {
            WorkloadType.ML_TRAINING: 8.0,
            WorkloadType.ML_FINE_TUNING: 12.0,
            WorkloadType.ML_INFERENCE: 4.0,
            WorkloadType.CV_DETECTION: 6.0,
            WorkloadType.CV_SEGMENTATION: 8.0,
            WorkloadType.CV_GENERATION: 10.0,
            WorkloadType.NLP_GENERATION: 16.0,
            WorkloadType.NLP_EMBEDDING: 4.0,
            WorkloadType.GPU_ACCELERATED: 4.0,
        }

        return memory_estimates.get(workload, 4.0)


def create_detector() -> WorkloadDetector:
    """Create a workload detector instance.

    Returns:
        Configured WorkloadDetector
    """
    return WorkloadDetector()
