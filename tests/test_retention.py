"""Tests for memory retention policies and pattern types."""

import pytest
from datetime import datetime, timedelta

from src.memory.retention import (
    RetentionPolicy,
    PatternType,
    RetentionManager,
    apply_retention_metadata,
    get_pattern_type_description,
    DEFAULT_RETENTION_POLICIES,
    RETENTION_PERIODS,
)
from src.memory.memory_store import InMemoryStore


@pytest.fixture
def memory_store():
    """Create an in-memory store for testing."""
    return InMemoryStore()


@pytest.fixture
def retention_manager(memory_store):
    """Create a retention manager for testing."""
    return RetentionManager(memory_store)


class TestRetentionPolicy:
    """Test retention policy enums and constants."""

    def test_retention_policies_exist(self):
        """Test that all retention policies are defined."""
        assert RetentionPolicy.PERMANENT == "permanent"
        assert RetentionPolicy.LONG_TERM == "long_term"
        assert RetentionPolicy.MEDIUM_TERM == "medium_term"
        assert RetentionPolicy.SHORT_TERM == "short_term"
        assert RetentionPolicy.EPHEMERAL == "ephemeral"

    def test_pattern_types_exist(self):
        """Test that all pattern types are defined."""
        assert PatternType.PRD == "prd"
        assert PatternType.SPEC == "spec"
        assert PatternType.CODE_REVIEW == "code_review"
        assert PatternType.MEETING_NOTES == "meeting_notes"
        assert PatternType.SCRATCH == "scratch"

    def test_default_retention_policies(self):
        """Test that default retention policies are defined for all pattern types."""
        for pattern_type in PatternType:
            assert pattern_type in DEFAULT_RETENTION_POLICIES
            policy = DEFAULT_RETENTION_POLICIES[pattern_type]
            assert isinstance(policy, RetentionPolicy)

    def test_retention_periods(self):
        """Test that retention periods are defined correctly."""
        assert RETENTION_PERIODS[RetentionPolicy.PERMANENT] is None
        assert RETENTION_PERIODS[RetentionPolicy.LONG_TERM] == 90
        assert RETENTION_PERIODS[RetentionPolicy.MEDIUM_TERM] == 30
        assert RETENTION_PERIODS[RetentionPolicy.SHORT_TERM] == 7
        assert RETENTION_PERIODS[RetentionPolicy.EPHEMERAL] == 1


class TestRetentionManager:
    """Test retention manager functionality."""

    def test_get_retention_policy_default(self, retention_manager):
        """Test getting default retention policy for a pattern type."""
        policy = retention_manager.get_retention_policy("prd")
        assert policy == RetentionPolicy.LONG_TERM

    def test_get_retention_policy_custom(self, retention_manager):
        """Test custom retention policy override."""
        policy = retention_manager.get_retention_policy("prd", "permanent")
        assert policy == RetentionPolicy.PERMANENT

    def test_get_retention_policy_unknown(self, retention_manager):
        """Test unknown pattern type defaults to medium term."""
        policy = retention_manager.get_retention_policy("unknown_type")
        assert policy == RetentionPolicy.MEDIUM_TERM

    def test_get_retention_days(self, retention_manager):
        """Test getting retention days for a policy."""
        assert retention_manager.get_retention_days(RetentionPolicy.PERMANENT) is None
        assert retention_manager.get_retention_days(RetentionPolicy.LONG_TERM) == 90
        assert retention_manager.get_retention_days(RetentionPolicy.EPHEMERAL) == 1

    def test_is_expired_permanent(self, retention_manager):
        """Test that permanent documents never expire."""
        created = datetime.utcnow() - timedelta(days=1000)
        last_used = datetime.utcnow() - timedelta(days=500)

        expired = retention_manager.is_expired(
            created, last_used, RetentionPolicy.PERMANENT
        )
        assert not expired

    def test_is_expired_recent(self, retention_manager):
        """Test that recent documents are not expired."""
        created = datetime.utcnow() - timedelta(days=5)
        last_used = datetime.utcnow() - timedelta(days=1)

        expired = retention_manager.is_expired(
            created, last_used, RetentionPolicy.SHORT_TERM
        )
        assert not expired

    def test_is_expired_old(self, retention_manager):
        """Test that old documents are expired."""
        created = datetime.utcnow() - timedelta(days=100)
        last_used = datetime.utcnow() - timedelta(days=50)

        expired = retention_manager.is_expired(
            created, last_used, RetentionPolicy.SHORT_TERM
        )
        assert expired

    def test_is_expired_uses_last_used(self, retention_manager):
        """Test that expiration uses the most recent timestamp."""
        created = datetime.utcnow() - timedelta(days=100)
        last_used = datetime.utcnow() - timedelta(days=5)

        # Should not be expired because last_used is recent
        expired = retention_manager.is_expired(
            created, last_used, RetentionPolicy.SHORT_TERM
        )
        assert not expired

    @pytest.mark.asyncio
    async def test_update_retention_policy(self, retention_manager, memory_store):
        """Test updating retention policy for a document."""
        # Store a document
        doc_id = "test-doc"
        await memory_store.store(doc_id, "Test content")

        # Update retention policy
        success = await retention_manager.update_retention_policy(
            doc_id, RetentionPolicy.PERMANENT
        )
        assert success

        # Verify it was updated
        doc = await memory_store.retrieve(doc_id)
        assert doc["metadata"]["retention_policy"] == "permanent"

    @pytest.mark.asyncio
    async def test_update_retention_policy_nonexistent(self, retention_manager):
        """Test updating retention policy for nonexistent document."""
        success = await retention_manager.update_retention_policy(
            "nonexistent", RetentionPolicy.PERMANENT
        )
        assert not success

    @pytest.mark.asyncio
    async def test_cleanup_expired(self, retention_manager):
        """Test cleanup of expired documents (placeholder)."""
        result = await retention_manager.cleanup_expired(dry_run=True)

        # Should return a status dict
        assert "expired_count" in result
        assert "deleted_count" in result
        assert "message" in result

    @pytest.mark.asyncio
    async def test_get_retention_stats(self, retention_manager):
        """Test getting retention statistics."""
        stats = await retention_manager.get_retention_stats()

        assert "total_documents" in stats
        assert "by_policy" in stats
        assert "by_pattern_type" in stats


class TestRetentionHelpers:
    """Test helper functions."""

    def test_apply_retention_metadata_with_pattern(self):
        """Test applying retention metadata with pattern type."""
        metadata = {}
        result = apply_retention_metadata(metadata, pattern_type="prd")

        assert result["pattern_type"] == "prd"
        assert result["retention_policy"] == "long_term"

    def test_apply_retention_metadata_existing(self):
        """Test that existing retention policy is preserved."""
        metadata = {"retention_policy": "permanent"}
        result = apply_retention_metadata(metadata, pattern_type="scratch")

        # Pattern type should be set, but retention policy preserved
        assert result["pattern_type"] == "scratch"
        assert result["retention_policy"] == "permanent"

    def test_apply_retention_metadata_default(self):
        """Test default retention policy for unknown pattern."""
        metadata = {"pattern_type": "custom_type"}
        result = apply_retention_metadata(metadata)

        # Should get medium term for unknown pattern type
        assert result["retention_policy"] == "medium_term"

    def test_get_pattern_type_description(self):
        """Test getting human-readable pattern type descriptions."""
        assert "Product" in get_pattern_type_description("prd")
        assert "Code Review" in get_pattern_type_description("code_review")
        assert "Custom" in get_pattern_type_description("unknown_type")


class TestIntegration:
    """Integration tests for retention system."""

    @pytest.mark.asyncio
    async def test_store_with_retention_metadata(self, memory_store):
        """Test storing documents with retention metadata."""
        metadata = apply_retention_metadata({}, pattern_type="prd")

        doc_id = await memory_store.store(
            "test-prd", "PRD content", metadata=metadata
        )

        doc = await memory_store.retrieve(doc_id)
        assert doc["metadata"]["pattern_type"] == "prd"
        assert doc["metadata"]["retention_policy"] == "long_term"

    @pytest.mark.asyncio
    async def test_search_by_pattern_type(self, memory_store):
        """Test searching documents by pattern type."""
        # Store documents with different pattern types
        await memory_store.store(
            "prd-1",
            "Product requirements",
            metadata=apply_retention_metadata({}, "prd"),
        )
        await memory_store.store(
            "bug-1",
            "Bug report",
            metadata=apply_retention_metadata({}, "bug_report"),
        )

        # Search for PRDs only
        results = await memory_store.search(
            "requirements", filters={"pattern_type": "prd"}
        )

        # Should only return the PRD
        assert len(results) == 1
        assert results[0]["id"] == "prd-1"

    @pytest.mark.asyncio
    async def test_count_by_pattern_type(self, memory_store):
        """Test counting documents by pattern type."""
        # Store multiple documents
        await memory_store.store(
            "prd-1", "PRD", metadata=apply_retention_metadata({}, "prd")
        )
        await memory_store.store(
            "prd-2", "PRD", metadata=apply_retention_metadata({}, "prd")
        )
        await memory_store.store(
            "bug-1", "Bug", metadata=apply_retention_metadata({}, "bug_report")
        )

        # Count PRDs
        prd_count = await memory_store.count(filters={"pattern_type": "prd"})
        assert prd_count == 2

        # Count bugs
        bug_count = await memory_store.count(filters={"pattern_type": "bug_report"})
        assert bug_count == 1

        # Count all
        total_count = await memory_store.count()
        assert total_count == 3
