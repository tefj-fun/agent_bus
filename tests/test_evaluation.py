"""Tests for memory evaluation harness."""

import pytest

from src.memory.evaluation import (
    MemoryEvaluator,
    QueryTestCase,
    RecallMetrics,
    run_basic_evaluation,
)
from src.memory.memory_store import InMemoryStore


@pytest.fixture
def memory_store():
    """Create an in-memory store for testing."""
    return InMemoryStore()


@pytest.fixture
def evaluator(memory_store):
    """Create an evaluator for testing."""
    return MemoryEvaluator(memory_store)


@pytest.fixture
async def seeded_store(memory_store):
    """Create a store seeded with test data."""
    await memory_store.store("doc1", "Python programming language tutorial")
    await memory_store.store("doc2", "JavaScript web development guide")
    await memory_store.store("doc3", "Python data science with pandas")
    await memory_store.store("doc4", "Machine learning in Python")
    await memory_store.store("doc5", "React JavaScript framework")
    return memory_store


class TestMetricsCalculation:
    """Test metrics calculation."""

    def test_calculate_metrics_perfect(self, evaluator):
        """Test perfect precision and recall."""
        expected = ["doc1", "doc2", "doc3"]
        retrieved = ["doc1", "doc2", "doc3"]

        precision, recall, f1, tp, fp, fn = evaluator.calculate_metrics(expected, retrieved)

        assert precision == 1.0
        assert recall == 1.0
        assert f1 == 1.0
        assert tp == 3
        assert fp == 0
        assert fn == 0

    def test_calculate_metrics_partial(self, evaluator):
        """Test partial precision and recall."""
        expected = ["doc1", "doc2", "doc3"]
        retrieved = ["doc1", "doc2", "doc4"]

        precision, recall, f1, tp, fp, fn = evaluator.calculate_metrics(expected, retrieved)

        # 2 out of 3 retrieved are correct
        assert precision == 2/3
        # 2 out of 3 expected were retrieved
        assert recall == 2/3
        # F1 should be same since precision == recall
        assert f1 == 2/3
        assert tp == 2
        assert fp == 1
        assert fn == 1

    def test_calculate_metrics_no_match(self, evaluator):
        """Test metrics when nothing matches."""
        expected = ["doc1", "doc2"]
        retrieved = ["doc3", "doc4"]

        precision, recall, f1, tp, fp, fn = evaluator.calculate_metrics(expected, retrieved)

        assert precision == 0.0
        assert recall == 0.0
        assert f1 == 0.0
        assert tp == 0
        assert fp == 2
        assert fn == 2

    def test_calculate_metrics_empty_retrieval(self, evaluator):
        """Test metrics when nothing is retrieved."""
        expected = ["doc1", "doc2"]
        retrieved = []

        precision, recall, f1, tp, fp, fn = evaluator.calculate_metrics(expected, retrieved)

        assert precision == 0.0
        assert recall == 0.0
        assert f1 == 0.0
        assert tp == 0
        assert fp == 0
        assert fn == 2

    def test_calculate_metrics_extra_results(self, evaluator):
        """Test metrics when extra results are returned."""
        expected = ["doc1"]
        retrieved = ["doc1", "doc2", "doc3"]

        precision, recall, f1, tp, fp, fn = evaluator.calculate_metrics(expected, retrieved)

        assert precision == 1/3  # Only 1 out of 3 is relevant
        assert recall == 1.0  # All expected docs were found
        assert tp == 1
        assert fp == 2
        assert fn == 0


class TestQueryEvaluation:
    """Test single query evaluation."""

    @pytest.mark.asyncio
    async def test_evaluate_query_perfect(self, evaluator, seeded_store):
        """Test evaluating a query with perfect results."""
        test_case = QueryTestCase(
            query="Python programming",
            expected_doc_ids=["doc1", "doc3", "doc4"],
            top_k=5,
        )

        metrics = await evaluator.evaluate_query(test_case)

        # Should find all Python-related docs
        assert metrics.precision >= 0.5  # At least some are correct
        assert metrics.recall >= 0.5  # At least some expected docs found
        assert metrics.latency_ms > 0
        assert "doc1" in metrics.retrieved_ids or "doc3" in metrics.retrieved_ids

    @pytest.mark.asyncio
    async def test_evaluate_query_latency(self, evaluator, seeded_store):
        """Test that latency is measured."""
        test_case = QueryTestCase(
            query="test query",
            expected_doc_ids=["doc1"],
        )

        metrics = await evaluator.evaluate_query(test_case)

        # Latency should be positive
        assert metrics.latency_ms > 0
        # Should be reasonably fast (less than 1 second for in-memory)
        assert metrics.latency_ms < 1000

    @pytest.mark.asyncio
    async def test_evaluate_query_with_filters(self, evaluator, memory_store):
        """Test evaluation with metadata filters."""
        # Seed with pattern types
        await memory_store.store("prd1", "Product PRD", {"pattern_type": "prd"})
        await memory_store.store("prd2", "Another PRD", {"pattern_type": "prd"})
        await memory_store.store("bug1", "Bug report", {"pattern_type": "bug_report"})

        test_case = QueryTestCase(
            query="PRD product",
            expected_doc_ids=["prd1", "prd2"],
            filters={"pattern_type": "prd"},
        )

        metrics = await evaluator.evaluate_query(test_case)

        # Should only retrieve PRDs
        assert all(
            doc_id.startswith("prd") or doc_id not in metrics.retrieved_ids
            for doc_id in metrics.retrieved_ids
        )


class TestSuiteEvaluation:
    """Test evaluation suite."""

    @pytest.mark.asyncio
    async def test_evaluate_suite(self, evaluator, seeded_store):
        """Test evaluating multiple test cases."""
        test_cases = [
            QueryTestCase(
                query="Python",
                expected_doc_ids=["doc1", "doc3", "doc4"],
            ),
            QueryTestCase(
                query="JavaScript",
                expected_doc_ids=["doc2", "doc5"],
            ),
        ]

        report = await evaluator.evaluate_suite(test_cases, "Test Suite")

        assert report.test_name == "Test Suite"
        assert report.total_queries == 2
        assert 0.0 <= report.avg_precision <= 1.0
        assert 0.0 <= report.avg_recall <= 1.0
        assert 0.0 <= report.avg_f1_score <= 1.0
        assert report.avg_latency_ms > 0
        assert len(report.individual_results) == 2

    @pytest.mark.asyncio
    async def test_evaluate_suite_empty(self, evaluator, memory_store):
        """Test evaluating empty suite."""
        report = await evaluator.evaluate_suite([], "Empty Suite")

        assert report.total_queries == 0
        assert report.avg_precision == 0.0
        assert report.avg_recall == 0.0
        assert report.avg_f1_score == 0.0
        assert report.avg_latency_ms == 0.0
        assert len(report.individual_results) == 0


class TestReportFormatting:
    """Test report formatting."""

    @pytest.mark.asyncio
    async def test_format_report_basic(self, evaluator, seeded_store):
        """Test basic report formatting."""
        test_cases = [
            QueryTestCase(query="Python", expected_doc_ids=["doc1"]),
        ]

        report = await evaluator.evaluate_suite(test_cases)
        formatted = evaluator.format_report(report, verbose=False)

        assert "Average Precision" in formatted
        assert "Average Recall" in formatted
        assert "Average F1 Score" in formatted
        assert "Average Latency" in formatted

    @pytest.mark.asyncio
    async def test_format_report_verbose(self, evaluator, seeded_store):
        """Test verbose report formatting."""
        test_cases = [
            QueryTestCase(query="Python", expected_doc_ids=["doc1"]),
        ]

        report = await evaluator.evaluate_suite(test_cases)
        formatted = evaluator.format_report(report, verbose=True)

        assert "Individual Query Results" in formatted
        assert "Query 1:" in formatted
        assert "Precision:" in formatted
        assert "Recall:" in formatted

    @pytest.mark.asyncio
    async def test_format_report_with_errors(self, evaluator, memory_store):
        """Test report formatting with false positives/negatives."""
        # Seed specific docs
        await memory_store.store("doc1", "Expected document")
        await memory_store.store("doc2", "Unexpected document")

        test_cases = [
            QueryTestCase(
                query="document",
                expected_doc_ids=["doc1"],
                top_k=2,
            ),
        ]

        report = await evaluator.evaluate_suite(test_cases)
        formatted = evaluator.format_report(report, verbose=True)

        # If there are false positives or negatives, they should be shown
        if report.individual_results[0].false_positives > 0:
            assert "Unexpected:" in formatted
        if report.individual_results[0].false_negatives > 0:
            assert "Missing:" in formatted


class TestBasicEvaluation:
    """Test the convenience evaluation function."""

    @pytest.mark.asyncio
    async def test_run_basic_evaluation(self, memory_store):
        """Test running basic evaluation."""
        report = await run_basic_evaluation(memory_store)

        assert report.test_name == "Basic Memory Evaluation"
        assert report.total_queries > 0
        assert len(report.individual_results) > 0

        # Should have seeded some documents
        doc_count = await memory_store.count()
        assert doc_count > 0


class TestRecallMetrics:
    """Test RecallMetrics dataclass."""

    def test_recall_metrics_creation(self):
        """Test creating RecallMetrics."""
        metrics = RecallMetrics(
            query="test query",
            precision=0.8,
            recall=0.9,
            f1_score=0.85,
            latency_ms=50.0,
            num_results=5,
            expected_count=4,
        )

        assert metrics.query == "test query"
        assert metrics.precision == 0.8
        assert metrics.recall == 0.9
        assert metrics.f1_score == 0.85
        assert metrics.latency_ms == 50.0
        assert metrics.num_results == 5
        assert metrics.expected_count == 4
