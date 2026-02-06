"""Feature Tree Agent - Maps requirements to modular feature trees."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import BaseAgent, AgentTask, AgentResult
from ..config import settings
from ..memory import create_memory_store
from ..catalog.module_catalog import fetch_module_catalog, seed_module_catalog, catalog_is_empty


class FeatureTreeAgent(BaseAgent):
    """Agent specialized in mapping requirements to modular feature trees."""

    def get_agent_id(self) -> str:
        return "feature_tree_agent"

    def define_capabilities(self) -> Dict[str, Any]:
        return {
            "can_build_feature_tree": True,
            "can_map_to_modules": True,
            "can_enforce_modularization": True,
            "output_formats": ["json", "mermaid"],
        }

    async def execute(self, task: AgentTask) -> AgentResult:
        """Generate a modular feature tree from requirements and/or PRD."""
        try:
            self._set_active_task_id(task.task_id)
            await self.log_event("info", "Starting feature tree generation")

            requirements = (task.input_data.get("requirements") or "").strip()
            prd_content = (task.input_data.get("prd") or "").strip()

            if not requirements and not prd_content:
                return AgentResult(
                    task_id=task.task_id,
                    agent_id=self.agent_id,
                    success=False,
                    output={},
                    artifacts=[],
                    error="Missing requirements or PRD content for feature tree generation",
                )

            module_catalog = task.input_data.get("module_catalog") or await self._load_module_catalog()
            if isinstance(module_catalog, str):
                try:
                    module_catalog = json.loads(module_catalog)
                except json.JSONDecodeError:
                    module_catalog = await self._load_module_catalog()
            if not isinstance(module_catalog, dict):
                module_catalog = await self._load_module_catalog()

            similar_trees: List[Dict[str, Any]] = []
            try:
                memory_store = create_memory_store(
                    settings.memory_backend,
                    db_pool=self.context.db_pool,
                    pattern_type_default="feature_tree",
                    collection_name=settings.chroma_collection_name,
                    persist_directory=settings.chroma_persist_directory,
                    host=settings.chroma_host,
                    port=settings.chroma_port,
                )
                query_text = requirements or prd_content
                similar_trees = await memory_store.query_similar(
                    query=query_text,
                    top_k=3,
                    pattern_type="feature_tree",
                )
            except Exception:
                similar_trees = []

            system_prompt = self._build_system_prompt()
            user_prompt = self._build_user_prompt(
                requirements=requirements,
                prd_content=prd_content,
                module_catalog=module_catalog,
                similar_trees=similar_trees,
            )

            has_existing_context = self._has_existing_context(requirements, prd_content)

            if settings.llm_mode == "mock":
                payload = self._mock_feature_tree(module_catalog)
                payload = self._normalize_feature_tree_payload(
                    payload, module_catalog, has_existing_context=has_existing_context
                )
                feature_tree_content = json.dumps(payload, indent=2)
            else:
                response_text = await self.query_llm(
                    prompt=user_prompt,
                    system=system_prompt,
                    thinking_budget=2048,
                    max_tokens=settings.anthropic_max_tokens,
                )
                parsed = self._extract_json(response_text)
                if parsed is not None:
                    payload = parsed
                    if isinstance(payload, list):
                        payload = {"feature_tree": payload}
                    if isinstance(payload, dict) and "module_catalog" not in payload:
                        payload["module_catalog"] = module_catalog
                    if isinstance(payload, dict):
                        payload = self._normalize_feature_tree_payload(
                            payload, module_catalog, has_existing_context=has_existing_context
                        )
                    feature_tree_content = json.dumps(payload, indent=2)
                else:
                    payload = {"raw_feature_tree": response_text}
                    feature_tree_content = response_text

            mermaid = ""
            if isinstance(payload, dict):
                mermaid = str(payload.get("mermaid") or "").strip()
                if not mermaid:
                    mermaid = self._build_mermaid(payload.get("feature_tree"))
            mermaid = self._sanitize_mermaid(mermaid)
            if not mermaid:
                mermaid = self._build_mermaid(None)

            artifact_id = await self.save_artifact(
                artifact_type="feature_tree",
                content=feature_tree_content,
                metadata={
                    "task_id": task.task_id,
                    "requirements_length": len(requirements),
                    "prd_length": len(prd_content),
                    "parseable_json": "raw_feature_tree" not in payload,
                    "module_catalog_size": len(module_catalog.get("modules", [])),
                },
            )

            await self._store_feature_tree_in_memory(payload, artifact_id)

            result = AgentResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                success=True,
                output={
                    "feature_tree": payload,
                    "artifact_id": artifact_id,
                    "next_stage": "plan_generation",
                },
                artifacts=[artifact_id],
                metadata={
                    "parseable_json": "raw_feature_tree" not in payload,
                    "new_module_count": len(payload.get("new_modules", []))
                    if isinstance(payload, dict)
                    else 0,
                },
            )

            await self.notify_completion(result)
            return result

        except Exception as exc:
            await self.log_event(
                "error",
                f"Feature tree generation failed: {type(exc).__name__}: {str(exc) or repr(exc)}",
            )
            result = AgentResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                success=False,
                output={},
                artifacts=[],
                error=str(exc),
            )
            await self.notify_completion(result)
            return result

    async def _load_module_catalog(self) -> Dict[str, Any]:
        # Prefer database-backed catalog
        try:
            catalog = await fetch_module_catalog(self.context.db_pool)
            if catalog.get("modules"):
                return catalog

            if settings.module_catalog_seed_on_startup:
                seeded = await self._seed_catalog_from_file()
                if seeded:
                    return await fetch_module_catalog(self.context.db_pool)
        except Exception:
            pass

        # Fallback to file-based catalog
        return self._load_module_catalog_from_file()

    async def _seed_catalog_from_file(self) -> bool:
        path = Path(settings.module_catalog_path)
        if not path.exists():
            return False
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return False
        modules = payload.get("modules") if isinstance(payload, dict) else None
        if not isinstance(modules, list) or not modules:
            return False
        try:
            if await catalog_is_empty(self.context.db_pool):
                await seed_module_catalog(self.context.db_pool, modules)
                return True
        except Exception:
            return False
        return False

    def _load_module_catalog_from_file(self) -> Dict[str, Any]:
        path = Path(settings.module_catalog_path)
        try:
            if path.exists():
                return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
        return {"modules": []}

    def _build_system_prompt(self) -> str:
        return (
            f"{self._truth_system_guardrails()}\n"
            "You are an expert Platform Architect. Your job is to map product requirements "
            "into a modular feature tree aligned to a reusable platform. Every feature must "
            "map to an existing module OR explicitly justify a new module. Your priority is "
            "reuse and modularization to avoid reinventing new products.\n\n"
            "Output MUST be valid JSON with this shape:\n"
            "{\n"
            '  "module_catalog": {"modules": [...]},\n'
            '  "feature_tree": [\n'
            "    {\n"
            '      "id": "feat.core",\n'
            '      "name": "Feature name",\n'
            '      "description": "What it does",\n'
            '      "module_id": "mod.some-module",\n'
            '      "reuse_decision": "reuse_existing|extend_existing|new_module",\n'
            '      "requirements_refs": ["FR-1"],\n'
            '      "children": []\n'
            "    }\n"
            "  ],\n"
            '  "new_modules": [\n'
            "    {\n"
            '      "proposed_id": "mod.new-module",\n'
            '      "name": "Module name",\n'
            '      "justification": "Why existing modules do not fit",\n'
            '      "requirements_refs": ["FR-9"]\n'
            "    }\n"
            "  ],\n"
            '  "modularization_report": {\n'
            '    "reuse_count": 0,\n'
            '    "new_module_count": 0,\n'
            '    "violations": []\n'
            "  },\n"
            '  "mermaid": "graph TD; ..."\n'
            "}\n\n"
            "Rules:\n"
            "- Prefer existing modules from the catalog.\n"
            "- If proposing a new module, clearly justify why no existing module fits.\n"
            "- Identify overlaps and add them to modularization_report.violations.\n"
            "- Keep the tree modular and reusable."
        )

    def _build_user_prompt(
        self,
        requirements: str,
        prd_content: str,
        module_catalog: Dict[str, Any],
        similar_trees: List[Dict[str, Any]],
    ) -> str:
        memory_context = ""
        if similar_trees:
            snippets = []
            for item in similar_trees:
                snippet = (item.get("text") or "").strip()
                if snippet:
                    snippets.append(snippet[:800])
            if snippets:
                memory_context = (
                    "\n\nRelevant prior feature trees:\n"
                    + "\n\n".join(f"- {s}" for s in snippets)
                )

        req_block = (
            f"\n\nUser Requirements (source of truth):\n{requirements}"
            if requirements
            else ""
        )
        prd_block = f"\n\nPRD (source of truth):\n{prd_content}" if prd_content else ""

        return (
            "Create a modular feature tree for this request.\n"
            "Map features to existing modules whenever possible.\n"
            "Only propose new modules when you cannot reasonably extend existing ones.\n\n"
            "Use prior trees for inspiration only. Do not import features not present in the "
            "requirements or PRD.\n\n"
            f"Module Catalog:\n{json.dumps(module_catalog, indent=2)}"
            f"{memory_context}{req_block}{prd_block}\n\n"
            "Return JSON only."
        )

    def _mock_feature_tree(self, module_catalog: Dict[str, Any]) -> Dict[str, Any]:
        catalog = module_catalog if module_catalog.get("modules") else {
            "modules": [
                {
                    "module_id": "mod.identity",
                    "name": "Identity & Access",
                    "capabilities": ["login", "sso", "mfa"],
                },
                {
                    "module_id": "mod.workflow",
                    "name": "Workflow Orchestration",
                    "capabilities": ["pipelines", "approvals"],
                }
            ]
        }
        feature_tree = [
            {
                "id": "feat.core-platform",
                "name": "Core Platform",
                "description": "Reusable platform foundation",
                "module_id": "mod.workflow",
                "reuse_decision": "reuse_existing",
                "requirements_refs": ["REQ-1"],
                "children": [
                    {
                        "id": "feat.identity",
                        "name": "Identity & Access",
                        "description": "Login and access control",
                        "module_id": "mod.identity",
                        "reuse_decision": "reuse_existing",
                        "requirements_refs": ["REQ-2"],
                        "children": [],
                    }
                ],
            }
        ]
        payload = {
            "module_catalog": catalog,
            "feature_tree": feature_tree,
            "new_modules": [],
            "modularization_report": {
                "reuse_count": 1,
                "new_module_count": 0,
                "violations": [],
            },
            "mermaid": self._build_mermaid(feature_tree),
        }
        return payload

    def _normalize_feature_tree_payload(
        self,
        payload: Dict[str, Any],
        module_catalog: Dict[str, Any],
        has_existing_context: bool = False,
    ) -> Dict[str, Any]:
        if not isinstance(payload, dict):
            return payload

        feature_tree = payload.get("feature_tree")
        if not isinstance(feature_tree, list):
            return payload

        modules = module_catalog.get("modules") if isinstance(module_catalog, dict) else []
        module_ids = {
            m.get("module_id")
            for m in modules
            if isinstance(m, dict) and m.get("module_id")
        }
        catalog_empty = len(module_ids) == 0

        existing_new_modules = payload.get("new_modules")
        new_modules: List[Dict[str, Any]] = []
        if isinstance(existing_new_modules, list):
            for item in existing_new_modules:
                if isinstance(item, dict) and item.get("proposed_id"):
                    new_modules.append(item)

        def slugify(value: str) -> str:
            value = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower())
            return value.strip("-") or "feature"

        def signals_extension(node: Dict[str, Any]) -> bool:
            text = " ".join(
                [
                    str(node.get("name") or ""),
                    str(node.get("description") or ""),
                ]
            ).lower()
            return any(
                term in text
                for term in ("extend", "enhance", "upgrade", "augment", "expand")
            )

        reuse_count = 0
        new_module_count = 0

        def apply_rules(node: Dict[str, Any]) -> None:
            nonlocal reuse_count, new_module_count
            name = str(node.get("name") or node.get("id") or "feature")
            module_id = node.get("module_id")
            if not module_id:
                module_id = f"mod.{slugify(name)}"
                node["module_id"] = module_id

            if catalog_empty or module_id not in module_ids:
                node["reuse_decision"] = "new_module"
                new_module_count += 1
                if not any(m.get("proposed_id") == module_id for m in new_modules):
                    new_modules.append(
                        {
                            "proposed_id": module_id,
                            "name": name,
                            "justification": "No matching module found in catalog.",
                            "requirements_refs": node.get("requirements_refs", []),
                        }
                    )
            else:
                node["reuse_decision"] = "reuse_existing"
                reuse_count += 1

            children = node.get("children") or []
            if isinstance(children, list):
                for child in children:
                    if isinstance(child, dict):
                        apply_rules(child)

        for node in feature_tree:
            if isinstance(node, dict):
                apply_rules(node)

        payload["feature_tree"] = feature_tree
        payload["new_modules"] = new_modules
        payload["modularization_report"] = {
            "reuse_count": reuse_count,
            "new_module_count": new_module_count,
            "violations": [],
        }
        return payload

    def _has_existing_context(self, requirements: str, prd_content: str) -> bool:
        haystack = f"{requirements}\n{prd_content}".lower()
        return any(
            term in haystack
            for term in (
                "existing",
                "current",
                "legacy",
                "migrate",
                "migration",
                "upgrade",
                "extend",
                "enhance",
                "brownfield",
            )
        )

    def _build_mermaid(self, feature_tree: Optional[List[Dict[str, Any]]]) -> str:
        if not feature_tree:
            return "graph TD\n  A[Feature Tree] --> B[No data]"

        lines = ["graph TD"]
        root_id = "PlatformRoot"
        lines.append(f'{root_id}["Platform Feature Tree"]')
        seen = set()

        def add_node(node: Dict[str, Any], parent_id: str) -> None:
            node_id_raw = node.get("id") or node.get("name") or "feature"
            node_id = self._sanitize_node_id(node_id_raw)
            label = (node.get("name") or node_id_raw).replace('"', "'")
            module_id = node.get("module_id")
            if module_id:
                module_label = str(module_id).replace('"', "'")
                label = f"{label}\\n[{module_label}]"

            if node_id not in seen:
                lines.append(f'{node_id}["{label}"]')
                seen.add(node_id)
            lines.append(f"{parent_id} --> {node_id}")

            for child in node.get("children", []) or []:
                add_node(child, node_id)

        for top in feature_tree:
            add_node(top, root_id)

        return "\n".join(lines)

    def _sanitize_mermaid(self, text: str) -> str:
        if not text:
            return ""
        lines = [
            line for line in text.splitlines() if not line.strip().startswith("```")
        ]
        return "\n".join(lines).strip()

    def _extract_json(self, text: str) -> Optional[Any]:
        if not text:
            return None
        candidate = text.strip()
        if not candidate:
            return None
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

        fenced = re.search(r"```(?:json)?\s*(.*?)```", candidate, re.DOTALL | re.IGNORECASE)
        if fenced:
            fenced_text = fenced.group(1).strip()
            try:
                return json.loads(fenced_text)
            except json.JSONDecodeError:
                pass

        for start_char, end_char in (("{", "}"), ("[", "]")):
            start = candidate.find(start_char)
            end = candidate.rfind(end_char)
            if start != -1 and end != -1 and end > start:
                snippet = candidate[start : end + 1]
                try:
                    return json.loads(snippet)
                except json.JSONDecodeError:
                    continue

        return None

    def _sanitize_node_id(self, value: str) -> str:
        return re.sub(r"[^a-zA-Z0-9_]", "_", value)

    async def _store_feature_tree_in_memory(
        self, payload: Dict[str, Any], artifact_id: str
    ) -> None:
        if not isinstance(payload, dict):
            return

        try:
            memory_store = create_memory_store(
                settings.memory_backend,
                db_pool=self.context.db_pool,
                pattern_type_default="feature_tree",
                collection_name=settings.chroma_collection_name,
                persist_directory=settings.chroma_persist_directory,
                host=settings.chroma_host,
                port=settings.chroma_port,
            )
        except Exception:
            return

        summary = self._summarize_feature_tree(payload.get("feature_tree"))
        if not summary:
            return

        try:
            await memory_store.upsert_document(
                doc_id=artifact_id,
                text=summary,
                metadata={
                    "pattern_type": "feature_tree",
                    "project_id": self.context.project_id,
                    "job_id": self.context.job_id,
                    "artifact_id": artifact_id,
                },
            )
        except Exception:
            return

    def _summarize_feature_tree(self, feature_tree: Any) -> str:
        if not isinstance(feature_tree, list):
            return ""
        lines: List[str] = ["Feature Tree Summary:"]

        def walk(nodes: List[Dict[str, Any]], depth: int) -> None:
            for node in nodes:
                name = node.get("name") or node.get("id") or "feature"
                module_id = node.get("module_id") or "unmapped"
                prefix = "  " * depth
                lines.append(f"{prefix}- {name} ({module_id})")
                children = node.get("children", []) or []
                if isinstance(children, list):
                    walk(children, depth + 1)

        walk(feature_tree, 0)
        return "\n".join(lines)
