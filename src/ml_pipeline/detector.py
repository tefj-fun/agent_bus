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

# Library/framework indicators with weights
ML_FRAMEWORKS = {
    "torch": 0.8, "pytorch": 0.8, "tensorflow": 0.8, "tf": 0.5,
    "keras": 0.7, "jax": 0.8, "sklearn": 0.6, "scikit-learn": 0.6,
    "xgboost": 0.7, "lightgbm": 0.7, "catboost": 0.7,
    "mxnet": 0.7, "paddle": 0.7, "onnx": 0.6,
}

CV_LIBRARIES = {
    "opencv": 0.7, "cv2": 0.7, "pillow": 0.4, "pil": 0.4,
    "torchvision": 0.8, "detectron2": 0.9, "mmdetection": 0.9,
    "albumentations": 0.6, "imgaug": 0.5, "kornia": 0.7,
}

NLP_LIBRARIES = {
    "transformers": 0.9, "huggingface": 0.9, "spacy": 0.6,
    "nltk": 0.4, "gensim": 0.5, "sentence-transformers": 0.8,
    "langchain": 0.7, "llama": 0.9, "openai": 0.6,
}

GPU_KEYWORDS = {
    "gpu": 0.8, "cuda": 0.9, "cudnn": 0.9, "tensorrt": 0.9,
    "nvidia": 0.7, "accelerat": 0.6, "device=cuda": 0.9,
    "to(\"cuda\")": 0.9, "to('cuda')": 0.9, "cupy": 0.8,
    "numba.cuda": 0.8, "rapids": 0.8,
}

# Model architecture keywords (strong GPU indicators)
MODEL_ARCHITECTURES = {
    "resnet": 0.8, "vgg": 0.8, "efficientnet": 0.8, "mobilenet": 0.7,
    "bert": 0.9, "gpt": 0.9, "t5": 0.9, "llama": 0.9, "mistral": 0.9,
    "yolo": 0.9, "rcnn": 0.9, "mask-rcnn": 0.9, "retinanet": 0.8,
    "unet": 0.8, "vae": 0.8, "gan": 0.8, "diffusion": 0.9,
    "transformer": 0.8, "attention": 0.7, "lstm": 0.6, "gru": 0.6,
}


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

        # Check for framework/library indicators with weighted scoring
        framework_score = 0.0
        framework_indicators = []

        all_frameworks = {**ML_FRAMEWORKS, **CV_LIBRARIES, **NLP_LIBRARIES}
        for framework, weight in all_frameworks.items():
            if framework.lower() in text:
                framework_score += weight * 0.25
                framework_indicators.append(framework)

        # Check for model architecture keywords
        architecture_score = 0.0
        architecture_indicators = []

        for arch, weight in MODEL_ARCHITECTURES.items():
            if arch.lower() in text:
                architecture_score += weight * 0.3
                architecture_indicators.append(arch)

        # Check for GPU keywords with weighted scoring
        gpu_score = 0.0
        gpu_indicators = []

        for keyword, weight in GPU_KEYWORDS.items():
            if keyword.lower() in text:
                gpu_score += weight * 0.3
                gpu_indicators.append(keyword)

        # Add generic GPU-accelerated signature if indicators found but no specific workload
        total_score = framework_score + architecture_score + gpu_score
        all_indicators = framework_indicators + architecture_indicators + gpu_indicators

        if (total_score > 0 or explicit_gpu) and not signatures:
            confidence = min(1.0, total_score + (0.5 if explicit_gpu else 0))
            signatures.append(
                WorkloadSignature(
                    workload_type=WorkloadType.GPU_ACCELERATED,
                    confidence=confidence,
                    indicators=all_indicators,
                    requires_gpu=True,
                )
            )
        elif signatures and all_indicators:
            # Boost confidence of existing signatures if strong framework/GPU indicators present
            for sig in signatures:
                boost = min(0.3, total_score * 0.2)
                sig.confidence = min(1.0, sig.confidence + boost)
                sig.indicators.extend(all_indicators)

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

    def detect_from_code(self, code_snippet: str) -> List[WorkloadSignature]:
        """Detect workload from code snippet with enhanced heuristics.

        Args:
            code_snippet: Python code to analyze

        Returns:
            List of detected workload signatures
        """
        signatures = []
        text = code_snippet.lower()

        # Code-specific patterns
        code_patterns = {
            WorkloadType.ML_TRAINING: [
                r"\.train\(\)", r"\.fit\(", r"optimizer\.", r"loss\.backward",
                r"model\.zero_grad", r"scheduler\.",
            ],
            WorkloadType.ML_INFERENCE: [
                r"\.eval\(\)", r"torch\.no_grad", r"model\.predict",
                r"@torch\.inference_mode", r"with\s+torch\.no_grad",
            ],
            WorkloadType.CV_DETECTION: [
                r"cv2\.detect", r"\.detect\(", r"nms\(", r"iou\(",
            ],
            WorkloadType.NLP_GENERATION: [
                r"\.generate\(", r"tokenizer\(", r"model\.forward",
            ],
        }

        # Check code-specific patterns
        for workload_type, patterns in code_patterns.items():
            matches = []
            for pattern_str in patterns:
                pattern = re.compile(pattern_str, re.IGNORECASE)
                if pattern.search(text):
                    matches.append(pattern_str)

            if matches:
                confidence = min(1.0, len(matches) * 0.4)
                signatures.append(
                    WorkloadSignature(
                        workload_type=workload_type,
                        confidence=confidence,
                        indicators=matches,
                        requires_gpu=True,
                    )
                )

        # If no code-specific patterns, fall back to regular detection
        if not signatures:
            signatures = self.detect(code_snippet)

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
