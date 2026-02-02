"""Memory retention policies and lifecycle management."""

from __future__ import annotations

from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

from .base import MemoryStoreBase


class RetentionPolicy(str, Enum):
    """Predefined retention policies for memory patterns."""

    # Never delete - for critical references and documentation
    PERMANENT = "permanent"

    # 90 days - for important project decisions and PRDs
    LONG_TERM = "long_term"

    # 30 days - for recent work context and feature specs
    MEDIUM_TERM = "medium_term"

    # 7 days - for temporary notes and experiments
    SHORT_TERM = "short_term"

    # 24 hours - for ephemeral data and test content
    EPHEMERAL = "ephemeral"


class PatternType(str, Enum):
    """Standard pattern types for categorizing memories."""

    # Product and planning
    PRD = "prd"  # Product requirement documents
    SPEC = "spec"  # Technical specifications
    DESIGN = "design"  # Design documents and diagrams

    # Code and implementation
    CODE_REVIEW = "code_review"  # Code review notes and feedback
    BUG_REPORT = "bug_report"  # Bug reports and issues
    SOLUTION = "solution"  # Solution patterns and fixes

    # Communication and meetings
    MEETING_NOTES = "meeting_notes"  # Meeting summaries
    DECISION = "decision"  # Important decisions and rationale
    DISCUSSION = "discussion"  # Discussion threads

    # Documentation
    DOCUMENT = "document"  # General documentation
    API_DOC = "api_doc"  # API documentation
    TUTORIAL = "tutorial"  # How-to guides and tutorials

    # Testing and validation
    TEST_CASE = "test_case"  # Test cases and scenarios
    VALIDATION = "validation"  # Validation results

    # Temporary
    EXPERIMENT = "experiment"  # Experimental ideas
    SCRATCH = "scratch"  # Temporary notes
    ARCHIVE = "archive"  # Archived content


# Default retention policies for each pattern type
DEFAULT_RETENTION_POLICIES: Dict[PatternType, RetentionPolicy] = {
    PatternType.PRD: RetentionPolicy.LONG_TERM,
    PatternType.SPEC: RetentionPolicy.LONG_TERM,
    PatternType.DESIGN: RetentionPolicy.LONG_TERM,
    PatternType.CODE_REVIEW: RetentionPolicy.MEDIUM_TERM,
    PatternType.BUG_REPORT: RetentionPolicy.MEDIUM_TERM,
    PatternType.SOLUTION: RetentionPolicy.PERMANENT,
    PatternType.MEETING_NOTES: RetentionPolicy.MEDIUM_TERM,
    PatternType.DECISION: RetentionPolicy.PERMANENT,
    PatternType.DISCUSSION: RetentionPolicy.SHORT_TERM,
    PatternType.DOCUMENT: RetentionPolicy.LONG_TERM,
    PatternType.API_DOC: RetentionPolicy.PERMANENT,
    PatternType.TUTORIAL: RetentionPolicy.LONG_TERM,
    PatternType.TEST_CASE: RetentionPolicy.MEDIUM_TERM,
    PatternType.VALIDATION: RetentionPolicy.SHORT_TERM,
    PatternType.EXPERIMENT: RetentionPolicy.SHORT_TERM,
    PatternType.SCRATCH: RetentionPolicy.EPHEMERAL,
    PatternType.ARCHIVE: RetentionPolicy.PERMANENT,
}


# Retention period in days for each policy
RETENTION_PERIODS: Dict[RetentionPolicy, Optional[int]] = {
    RetentionPolicy.PERMANENT: None,  # Never delete
    RetentionPolicy.LONG_TERM: 90,
    RetentionPolicy.MEDIUM_TERM: 30,
    RetentionPolicy.SHORT_TERM: 7,
    RetentionPolicy.EPHEMERAL: 1,
}


class RetentionManager:
    """Manages memory retention policies and cleanup."""

    def __init__(self, store: MemoryStoreBase):
        """Initialize retention manager with a memory store.

        Args:
            store: Memory store backend to manage
        """
        self.store = store

    def get_retention_policy(
        self,
        pattern_type: str,
        custom_policy: Optional[str] = None,
    ) -> RetentionPolicy:
        """Get the retention policy for a pattern type.

        Args:
            pattern_type: Pattern type to look up
            custom_policy: Optional custom policy override

        Returns:
            RetentionPolicy enum value
        """
        if custom_policy:
            try:
                return RetentionPolicy(custom_policy)
            except ValueError:
                pass

        # Try to match pattern type to enum
        try:
            pt = PatternType(pattern_type)
            return DEFAULT_RETENTION_POLICIES.get(pt, RetentionPolicy.MEDIUM_TERM)
        except ValueError:
            # Unknown pattern type, use medium term as default
            return RetentionPolicy.MEDIUM_TERM

    def get_retention_days(self, policy: RetentionPolicy) -> Optional[int]:
        """Get the number of days for a retention policy.

        Args:
            policy: Retention policy

        Returns:
            Number of days, or None for permanent retention
        """
        return RETENTION_PERIODS.get(policy)

    def is_expired(
        self,
        created_at: datetime,
        last_used_at: datetime,
        policy: RetentionPolicy,
    ) -> bool:
        """Check if a document has expired based on its retention policy.

        Documents are considered expired if they haven't been used within
        their retention period. The retention period starts from the most
        recent of created_at or last_used_at.

        Args:
            created_at: Document creation timestamp
            last_used_at: Last access timestamp
            policy: Retention policy

        Returns:
            True if the document is expired and should be deleted
        """
        if policy == RetentionPolicy.PERMANENT:
            return False

        retention_days = self.get_retention_days(policy)
        if retention_days is None:
            return False

        # Use the most recent timestamp
        most_recent = max(created_at, last_used_at)
        age = datetime.utcnow() - most_recent
        return age > timedelta(days=retention_days)

    async def cleanup_expired(
        self,
        dry_run: bool = True,
        pattern_type_filter: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Clean up expired documents based on retention policies.

        Args:
            dry_run: If True, only report what would be deleted
            pattern_type_filter: Optional filter to only clean specific pattern types

        Returns:
            Dictionary with cleanup statistics:
            - expired_count: Number of expired documents found
            - deleted_count: Number of documents actually deleted
            - skipped_count: Number of documents skipped
            - expired_ids: List of expired document IDs (if dry_run)
        """
        # Note: This is a placeholder implementation
        # Real implementation would need to:
        # 1. Query all documents (with optional pattern_type filter)
        # 2. Check each document against its retention policy
        # 3. Delete expired documents (if not dry_run)

        # For now, return a status report
        return {
            "expired_count": 0,
            "deleted_count": 0,
            "skipped_count": 0,
            "expired_ids": [],
            "message": "Cleanup not yet implemented - store backend needs created_at/last_used_at fields",
        }

    async def update_retention_policy(
        self,
        doc_id: str,
        policy: RetentionPolicy,
    ) -> bool:
        """Update the retention policy for a specific document.

        Args:
            doc_id: Document ID
            policy: New retention policy

        Returns:
            True if updated successfully, False otherwise
        """
        doc = await self.store.retrieve(doc_id)
        if not doc:
            return False

        metadata = doc.get("metadata", {})
        metadata["retention_policy"] = policy.value

        return await self.store.update(doc_id, metadata=metadata)

    async def get_retention_stats(self) -> Dict[str, Any]:
        """Get statistics about retention policies in the store.

        Returns:
            Dictionary with:
            - total_documents: Total number of documents
            - by_policy: Count of documents per retention policy
            - by_pattern_type: Count of documents per pattern type
        """
        # This would need full document enumeration
        # For now, return basic stats from store health
        health = await self.store.health()
        return {
            "total_documents": health.get("count", 0),
            "by_policy": {},
            "by_pattern_type": {},
            "message": "Detailed stats not yet implemented",
        }


def apply_retention_metadata(
    metadata: Dict[str, Any],
    pattern_type: Optional[str] = None,
) -> Dict[str, Any]:
    """Apply retention policy metadata to a document.

    Args:
        metadata: Existing metadata dictionary
        pattern_type: Optional pattern type to set

    Returns:
        Updated metadata with retention policy and pattern type
    """
    # Set pattern type if provided
    if pattern_type:
        metadata["pattern_type"] = pattern_type

    # Get or set retention policy
    if "retention_policy" not in metadata:
        pt = metadata.get("pattern_type", "document")
        manager = RetentionManager(None)  # type: ignore
        policy = manager.get_retention_policy(pt)
        metadata["retention_policy"] = policy.value

    return metadata


def get_pattern_type_description(pattern_type: str) -> str:
    """Get a human-readable description of a pattern type.

    Args:
        pattern_type: Pattern type string

    Returns:
        Description of the pattern type
    """
    descriptions = {
        "prd": "Product Requirement Document",
        "spec": "Technical Specification",
        "design": "Design Document",
        "code_review": "Code Review Notes",
        "bug_report": "Bug Report",
        "solution": "Solution Pattern",
        "meeting_notes": "Meeting Notes",
        "decision": "Decision Record",
        "discussion": "Discussion Thread",
        "document": "General Documentation",
        "api_doc": "API Documentation",
        "tutorial": "Tutorial or Guide",
        "test_case": "Test Case",
        "validation": "Validation Result",
        "experiment": "Experimental Note",
        "scratch": "Temporary Scratch Note",
        "archive": "Archived Content",
    }
    return descriptions.get(pattern_type, f"Custom: {pattern_type}")
