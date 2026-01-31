"""Memory store with optional ChromaDB backend."""

from __future__ import annotations

import hashlib
import math
import os
import re
from typing import Any, Dict, List, Optional


class MemoryStore:
    """Store and query project memory using ChromaDB when available."""

    def __init__(self, persist_directory: str, collection_name: str = "agent_bus"):
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        self.backend = "memory"
        self.last_error: Optional[str] = None
        self._client = None
        self._collection = None
        self._items: Dict[str, Dict[str, Any]] = {}
        self._init_backend()

    def _init_backend(self) -> None:
        try:
            import chromadb  # type: ignore

            os.makedirs(self.persist_directory, exist_ok=True)
            self._client = chromadb.PersistentClient(path=self.persist_directory)
            self._collection = self._client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"},
            )
            self.backend = "chromadb"
        except Exception as exc:  # ImportError or runtime errors
            self.backend = "memory"
            self.last_error = str(exc)

    def upsert_document(
        self,
        doc_id: str,
        text: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        record = {
            "id": doc_id,
            "text": text,
            "metadata": metadata or {},
        }

        if self.backend == "chromadb" and self._collection is not None:
            embedding = self._embed(text)
            self._collection.upsert(
                ids=[doc_id],
                documents=[text],
                metadatas=[record["metadata"]],
                embeddings=[embedding],
            )
        else:
            self._items[doc_id] = record

        return doc_id

    def query_similar(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        if self.backend == "chromadb" and self._collection is not None:
            if self._collection.count() == 0:
                return []
            embedding = self._embed(query)
            response = self._collection.query(
                query_embeddings=[embedding],
                n_results=top_k,
                include=["documents", "metadatas", "distances"],
            )
            ids = response.get("ids", [[]])[0]
            docs = response.get("documents", [[]])[0]
            metas = response.get("metadatas", [[]])[0]
            distances = response.get("distances", [[]])[0]
            results = []
            for idx, doc_id in enumerate(ids):
                distance = distances[idx] if idx < len(distances) else None
                score = None if distance is None else 1 - distance
                results.append(
                    {
                        "id": doc_id,
                        "text": docs[idx] if idx < len(docs) else "",
                        "metadata": metas[idx] if idx < len(metas) else {},
                        "score": score,
                    }
                )
            return results

        query_vec = self._embed(query)
        scored = []
        for record in self._items.values():
            score = self._cosine_similarity(query_vec, self._embed(record["text"]))
            scored.append({**record, "score": score})
        scored.sort(key=lambda item: item.get("score", 0.0), reverse=True)
        return scored[:top_k]

    def count(self) -> int:
        if self.backend == "chromadb" and self._collection is not None:
            return self._collection.count()
        return len(self._items)

    def health(self) -> Dict[str, Any]:
        return {
            "backend": self.backend,
            "count": self.count(),
            "persist_directory": self.persist_directory,
            "last_error": self.last_error,
        }

    def _embed(self, text: str, dim: int = 64) -> List[float]:
        tokens = re.findall(r"[a-z0-9]+", text.lower())
        vector = [0.0] * dim
        for token in tokens:
            token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
            bucket = int(token_hash[:8], 16) % dim
            vector[bucket] += 1.0

        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            return vector
        return [value / norm for value in vector]

    def _cosine_similarity(self, vec_a: List[float], vec_b: List[float]) -> float:
        if not vec_a or not vec_b:
            return 0.0
        return sum(a * b for a, b in zip(vec_a, vec_b))
