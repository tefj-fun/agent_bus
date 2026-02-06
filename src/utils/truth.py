"""Utilities for canonical truth handling and alignment checks."""
from __future__ import annotations

import hashlib
import re
from collections import Counter
from typing import Dict, List


_STOPWORDS = {
    "the", "and", "for", "with", "this", "that", "from", "into", "will", "your", "you",
    "are", "can", "able", "able", "have", "has", "had", "use", "using", "used", "based",
    "should", "must", "may", "might", "would", "could", "also", "only", "not", "any",
    "all", "each", "per", "via", "within", "across", "between", "including", "include",
    "includes", "such", "than", "then", "when", "where", "what", "which", "while",
    "these", "those", "their", "them", "our", "ours", "its", "it's", "who", "whom",
    "user", "users", "system", "product", "project", "feature", "features", "requirements",
    "design", "plan", "architecture",
}


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def hash_text(text: str) -> str:
    normalized = normalize_text(text)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _extract_heading_terms(text: str) -> List[str]:
    for line in (text or "").splitlines():
        line = line.strip()
        if line.startswith("#"):
            cleaned = re.sub(r"[^a-zA-Z0-9\\s-]", " ", line)
            tokens = re.findall(r"[a-zA-Z][a-zA-Z0-9-]{2,}", cleaned.lower())
            return [t for t in tokens if t not in _STOPWORDS]
    return []


def extract_keywords(text: str, limit: int = 12) -> List[str]:
    heading_terms = _extract_heading_terms(text)
    tokens = re.findall(r"[a-zA-Z][a-zA-Z0-9-]{3,}", (text or "").lower())
    tokens = [t for t in tokens if t not in _STOPWORDS]
    freq = Counter(tokens)

    keywords = []
    for term in heading_terms:
        if term not in keywords:
            keywords.append(term)

    for term, _ in freq.most_common(limit * 2):
        if term not in keywords:
            keywords.append(term)
        if len(keywords) >= limit:
            break

    return keywords[:limit]


def alignment_check(
    truth_text: str,
    artifact_text: str,
    min_matches: int = 2,
    threshold: float = 0.15,
) -> Dict[str, object]:
    keywords = extract_keywords(truth_text)
    if not keywords:
        return {
            "status": "skipped",
            "reason": "no_keywords",
            "score": 1.0,
            "matches": [],
            "keywords": [],
        }

    haystack = (artifact_text or "").lower()
    matches = [term for term in keywords if term in haystack]
    score = len(matches) / max(1, len(keywords))
    status = "pass" if (len(matches) >= min_matches or score >= threshold) else "fail"

    return {
        "status": status,
        "score": round(score, 3),
        "matches": matches,
        "keywords": keywords,
    }

