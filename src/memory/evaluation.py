"""Memory evaluation harness for testing recall quality."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .base import MemoryStoreBase


@dataclass
class QueryTestCase:
    """A test case for evaluating memory recall."""

    query: str
    expected_doc_ids: List[str]
    filters: Optional[Dict[str, Any]] = None
    top_k: int = 5
    description: str = ""


@dataclass
class RecallMetrics:
    """Metrics for a single query evaluation."""

    query: str
    precision: float
    recall: float
    f1_score: float
    latency_ms: float
    num_results: int
    expected_count: int
    retrieved_ids: List[str] = field(default_factory=list)
    expected_ids: List[str] = field(default_factory=list)
    true_positives: int = 0
    false_positives: int = 0
    false_negatives: int = 0


@dataclass
class EvaluationReport:
    """Complete evaluation report for a test suite."""

    test_name: str
    total_queries: int
    avg_precision: float
    avg_recall: float
    avg_f1_score: float
    avg_latency_ms: float
    individual_results: List[RecallMetrics]
    timestamp: float = field(default_factory=time.time)


class MemoryEvaluator:
    """Evaluate memory store recall quality using test cases."""

    def __init__(self, store: MemoryStoreBase):
        """Initialize evaluator with a memory store.

        Args:
            store: Memory store to evaluate
        """
        self.store = store

    def calculate_metrics(
        self,
        expected_ids: List[str],
        retrieved_ids: List[str],
    ) -> Tuple[float, float, float, int, int, int]:
        """Calculate precision, recall, and F1 score.

        Args:
            expected_ids: List of expected document IDs
            retrieved_ids: List of retrieved document IDs

        Returns:
            Tuple of (precision, recall, f1, true_positives, false_positives, false_negatives)
        """
        expected_set = set(expected_ids)
        retrieved_set = set(retrieved_ids)

        true_positives = len(expected_set & retrieved_set)
        false_positives = len(retrieved_set - expected_set)
        false_negatives = len(expected_set - retrieved_set)

        # Precision: what fraction of retrieved docs are relevant
        precision = (
            true_positives / len(retrieved_set) if len(retrieved_set) > 0 else 0.0
        )

        # Recall: what fraction of relevant docs were retrieved
        recall = (
            true_positives / len(expected_set) if len(expected_set) > 0 else 0.0
        )

        # F1: harmonic mean of precision and recall
        f1_score = (
            2 * (precision * recall) / (precision + recall)
            if (precision + recall) > 0
            else 0.0
        )

        return precision, recall, f1_score, true_positives, false_positives, false_negatives

    async def evaluate_query(self, test_case: QueryTestCase) -> RecallMetrics:
        """Evaluate a single query test case.

        Args:
            test_case: Test case to evaluate

        Returns:
            RecallMetrics with evaluation results
        """
        start_time = time.time()

        # Execute query
        results = await self.store.search(
            query=test_case.query,
            top_k=test_case.top_k,
            filters=test_case.filters,
        )

        latency_ms = (time.time() - start_time) * 1000

        # Extract retrieved document IDs
        retrieved_ids = [result["id"] for result in results]

        # Calculate metrics
        precision, recall, f1, tp, fp, fn = self.calculate_metrics(
            test_case.expected_doc_ids, retrieved_ids
        )

        return RecallMetrics(
            query=test_case.query,
            precision=precision,
            recall=recall,
            f1_score=f1,
            latency_ms=latency_ms,
            num_results=len(retrieved_ids),
            expected_count=len(test_case.expected_doc_ids),
            retrieved_ids=retrieved_ids,
            expected_ids=test_case.expected_doc_ids,
            true_positives=tp,
            false_positives=fp,
            false_negatives=fn,
        )

    async def evaluate_suite(
        self,
        test_cases: List[QueryTestCase],
        test_name: str = "Memory Evaluation",
    ) -> EvaluationReport:
        """Evaluate a suite of test cases.

        Args:
            test_cases: List of test cases to evaluate
            test_name: Name for this evaluation run

        Returns:
            EvaluationReport with aggregated results
        """
        individual_results: List[RecallMetrics] = []

        for test_case in test_cases:
            metrics = await self.evaluate_query(test_case)
            individual_results.append(metrics)

        # Calculate averages
        total = len(individual_results)
        avg_precision = sum(m.precision for m in individual_results) / total if total > 0 else 0.0
        avg_recall = sum(m.recall for m in individual_results) / total if total > 0 else 0.0
        avg_f1 = sum(m.f1_score for m in individual_results) / total if total > 0 else 0.0
        avg_latency = sum(m.latency_ms for m in individual_results) / total if total > 0 else 0.0

        return EvaluationReport(
            test_name=test_name,
            total_queries=total,
            avg_precision=avg_precision,
            avg_recall=avg_recall,
            avg_f1_score=avg_f1,
            avg_latency_ms=avg_latency,
            individual_results=individual_results,
        )

    def format_report(self, report: EvaluationReport, verbose: bool = False) -> str:
        """Format evaluation report as human-readable text.

        Args:
            report: Evaluation report to format
            verbose: If True, include individual query results

        Returns:
            Formatted report string
        """
        lines = [
            f"=== {report.test_name} ===",
            f"Total queries: {report.total_queries}",
            f"Average Precision: {report.avg_precision:.3f}",
            f"Average Recall: {report.avg_recall:.3f}",
            f"Average F1 Score: {report.avg_f1_score:.3f}",
            f"Average Latency: {report.avg_latency_ms:.2f}ms",
            "",
        ]

        if verbose:
            lines.append("=== Individual Query Results ===")
            for i, metrics in enumerate(report.individual_results, 1):
                lines.extend([
                    f"\nQuery {i}: {metrics.query}",
                    f"  Precision: {metrics.precision:.3f}",
                    f"  Recall: {metrics.recall:.3f}",
                    f"  F1: {metrics.f1_score:.3f}",
                    f"  Latency: {metrics.latency_ms:.2f}ms",
                    f"  Results: {metrics.num_results}/{metrics.expected_count}",
                    f"  TP: {metrics.true_positives}, FP: {metrics.false_positives}, FN: {metrics.false_negatives}",
                ])

                if metrics.false_positives > 0:
                    unexpected = set(metrics.retrieved_ids) - set(metrics.expected_ids)
                    lines.append(f"  Unexpected: {list(unexpected)}")

                if metrics.false_negatives > 0:
                    missing = set(metrics.expected_ids) - set(metrics.retrieved_ids)
                    lines.append(f"  Missing: {list(missing)}")

        return "\n".join(lines)


async def run_basic_evaluation(store: MemoryStoreBase) -> EvaluationReport:
    """Run a basic evaluation with standard test cases.

    This is a convenience function that seeds some test data and runs
    a basic evaluation. Useful for quick sanity checks.

    Args:
        store: Memory store to evaluate

    Returns:
        Evaluation report
    """
    # Seed test data
    test_docs = [
        ("prd-auth", "User authentication PRD: OAuth2, SSO, MFA support", {"pattern_type": "prd"}),
        ("prd-billing", "Billing system PRD: Stripe integration, subscriptions", {"pattern_type": "prd"}),
        ("spec-api", "API specification: REST endpoints, authentication", {"pattern_type": "spec"}),
        ("bug-login", "Bug: Login fails with SSO", {"pattern_type": "bug_report"}),
        ("meeting-sprint", "Sprint planning meeting notes", {"pattern_type": "meeting_notes"}),
    ]

    for doc_id, text, metadata in test_docs:
        await store.store(doc_id, text, metadata)

    # Define test cases
    test_cases = [
        QueryTestCase(
            query="authentication OAuth SSO",
            expected_doc_ids=["prd-auth", "spec-api"],
            description="Should find auth-related docs",
        ),
        QueryTestCase(
            query="billing payment subscription",
            expected_doc_ids=["prd-billing"],
            description="Should find billing PRD",
        ),
        QueryTestCase(
            query="login SSO bug",
            expected_doc_ids=["bug-login", "prd-auth"],
            description="Should find SSO-related items",
        ),
        QueryTestCase(
            query="PRD product requirements",
            expected_doc_ids=["prd-auth", "prd-billing"],
            filters={"pattern_type": "prd"},
            description="Should find PRDs only",
        ),
    ]

    evaluator = MemoryEvaluator(store)
    return await evaluator.evaluate_suite(test_cases, "Basic Memory Evaluation")
