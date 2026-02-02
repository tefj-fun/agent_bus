#!/usr/bin/env python3
"""CLI for memory pattern management."""

import asyncio
import json
import sys
from typing import Optional

import click

from .memory.chroma_store import ChromaDBStore
from .config import settings


def get_store() -> ChromaDBStore:
    """Get ChromaDB store instance."""
    return ChromaDBStore(
        collection_name="agent_bus_patterns",
        persist_directory=settings.chroma_persist_directory,
        auto_embed=True,
    )


@click.group()
def cli():
    """Agent Bus memory management CLI."""
    pass


@cli.command()
@click.argument("query")
@click.option("--top-k", default=5, help="Number of results")
@click.option("--pattern-type", default=None, help="Filter by pattern type")
def query(query: str, top_k: int, pattern_type: Optional[str]):
    """Search for similar patterns."""

    async def _query():
        store = get_store()
        results = await store.query_similar(query, top_k, pattern_type)

        click.echo(f"\n🔍 Found {len(results)} similar patterns:\n")
        for i, result in enumerate(results, 1):
            click.echo(f"[{i}] {result.get('id')}")
            click.echo(f"    Score: {result.get('score', 0):.3f}")
            metadata = result.get("metadata", {})
            click.echo(f"    Type: {metadata.get('pattern_type', 'N/A')}")
            click.echo(f"    Success: {metadata.get('success_score', 'N/A')}")
            click.echo(f"    Usage: {metadata.get('usage_count', 0)}")
            preview = result.get("text", "")[:150]
            click.echo(f"    Preview: {preview}...")
            click.echo()

    asyncio.run(_query())


@cli.command()
@click.argument("pattern_id")
def get(pattern_id: str):
    """Get a specific pattern by ID."""

    async def _get():
        store = get_store()
        doc = await store.get_document(pattern_id)

        if not doc:
            click.echo(f"❌ Pattern {pattern_id} not found", err=True)
            sys.exit(1)

        click.echo(f"\n📄 Pattern: {doc.get('id')}\n")
        metadata = doc.get("metadata", {})
        click.echo(f"Type: {metadata.get('pattern_type', 'N/A')}")
        click.echo(f"Success Score: {metadata.get('success_score', 'N/A')}")
        click.echo(f"Usage Count: {metadata.get('usage_count', 0)}")
        click.echo(f"\nContent:\n{doc.get('text', '')}\n")

    asyncio.run(_get())


@cli.command()
def list():
    """List all pattern types and counts."""

    async def _list():
        store = get_store()
        health = await store.health()

        click.echo("\n📊 Memory Store Status:\n")
        click.echo(f"Backend: {health.get('backend')}")
        click.echo(f"Mode: {health.get('mode')}")
        click.echo(f"Collection: {health.get('collection')}")
        click.echo(f"Total Patterns: {health.get('count', 0)}")

        if health.get("embedding_info"):
            emb_info = health["embedding_info"]
            click.echo(f"\nEmbedding Model: {emb_info.get('model_name')}")
            click.echo(f"Embedding Dimension: {emb_info.get('embedding_dim')}")
            click.echo(f"Cache Size: {emb_info.get('cache_size', 0)}")

    asyncio.run(_list())


@cli.command()
@click.argument("pattern_id")
@click.argument("content")
@click.option("--pattern-type", default="general", help="Pattern type")
@click.option("--success-score", default=0.0, type=float, help="Success score (0-1)")
def add(pattern_id: str, content: str, pattern_type: str, success_score: float):
    """Add a new pattern."""

    async def _add():
        store = get_store()

        metadata = {
            "pattern_type": pattern_type,
            "success_score": str(success_score),
            "usage_count": "0",
        }

        await store.upsert_document(pattern_id, content, metadata)
        click.echo(f"✓ Added pattern: {pattern_id}")

    asyncio.run(_add())


@cli.command()
@click.argument("pattern_id")
@click.confirmation_option(prompt="Are you sure you want to delete this pattern?")
def delete(pattern_id: str):
    """Delete a pattern."""

    async def _delete():
        store = get_store()
        success = await store.delete_document(pattern_id)

        if success:
            click.echo(f"✓ Deleted pattern: {pattern_id}")
        else:
            click.echo(f"❌ Pattern {pattern_id} not found", err=True)
            sys.exit(1)

    asyncio.run(_delete())


@cli.command()
def health():
    """Check memory store health."""

    async def _health():
        store = get_store()
        health_info = await store.health()

        click.echo(json.dumps(health_info, indent=2))

    asyncio.run(_health())


@cli.command()
@click.argument("requirements")
@click.option("--top-k", default=3, help="Number of suggestions")
@click.option("--min-score", default=0.5, type=float, help="Minimum combined score")
def suggest(requirements: str, top_k: int, min_score: float):
    """Suggest templates based on requirements."""

    async def _suggest():
        store = get_store()

        # Query for templates
        candidates = await store.query_similar(
            requirements, top_k=top_k * 2, pattern_type="template"
        )

        # Rank by combined score
        suggestions = []
        for candidate in candidates:
            similarity_score = candidate.get("score", 0.0)
            metadata = candidate.get("metadata", {})
            success_score = float(metadata.get("success_score", 0.5))
            usage_count = int(metadata.get("usage_count", 0))

            combined_score = similarity_score * 0.7 + success_score * 0.3

            if combined_score >= min_score:
                suggestions.append(
                    {
                        "id": candidate.get("id"),
                        "similarity": similarity_score,
                        "success": success_score,
                        "usage": usage_count,
                        "combined": combined_score,
                        "text": candidate.get("text", "")[:200],
                    }
                )

        suggestions.sort(key=lambda x: x["combined"], reverse=True)
        suggestions = suggestions[:top_k]

        click.echo(f"\n💡 Template Suggestions for: '{requirements}'\n")
        for i, suggestion in enumerate(suggestions, 1):
            click.echo(f"[{i}] {suggestion['id']}")
            click.echo(f"    Combined Score: {suggestion['combined']:.3f}")
            click.echo(f"    Similarity: {suggestion['similarity']:.3f}")
            click.echo(f"    Success: {suggestion['success']:.3f}")
            click.echo(f"    Usage: {suggestion['usage']}")
            click.echo(f"    Preview: {suggestion['text']}...")
            click.echo()

    asyncio.run(_suggest())


def main():
    """Entry point."""
    cli()


if __name__ == "__main__":
    main()
