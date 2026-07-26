"""MEC Lab — Context capsule reconstruction.

Builds layered contextual capsules from retrieved memories, following
the priority order: checkpoint → atomic records → episodes → documents → raw sources.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from mec_lab.domain.enums import MemoryType
from mec_lab.domain.models import AnyMemory, Checkpoint, Decision, Episode, Fact
from mec_lab.retrieval import HybridRetriever, RetrievalResult
from mec_lab.storage import Storage


# ---------------------------------------------------------------------------
# Capsule
# ---------------------------------------------------------------------------


@dataclass
class Capsule:
    """Contextual capsule assembled from layered retrieval."""

    project_id: str
    query: str
    checkpoints: list[AnyMemory] = field(default_factory=list)
    active_decisions: list[AnyMemory] = field(default_factory=list)
    current_facts: list[AnyMemory] = field(default_factory=list)
    related_episodes: list[AnyMemory] = field(default_factory=list)
    applicable_learnings: list[AnyMemory] = field(default_factory=list)
    documents: list[AnyMemory] = field(default_factory=list)
    raw_sources: list[str] = field(default_factory=list)
    inclusion_reasons: dict[str, str] = field(default_factory=dict)
    gaps: list[str] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)
    total_characters: int = 0
    estimated_tokens: int = 0
    created_at: str = ""
    config_used: dict = field(default_factory=dict)

    def summary(self) -> dict:
        """Return a machine-readable summary of the capsule."""
        return {
            "project_id": self.project_id,
            "query": self.query,
            "num_checkpoints": len(self.checkpoints),
            "num_decisions": len(self.active_decisions),
            "num_facts": len(self.current_facts),
            "num_episodes": len(self.related_episodes),
            "num_learnings": len(self.applicable_learnings),
            "num_documents": len(self.documents),
            "num_raw_sources": len(self.raw_sources),
            "total_characters": self.total_characters,
            "estimated_tokens": self.estimated_tokens,
            "gaps": len(self.gaps),
            "conflicts": len(self.conflicts),
        }


# ---------------------------------------------------------------------------
# Capsule builder
# ---------------------------------------------------------------------------


class CapsuleBuilder:
    """Assembles a Capsule from a hybrid retrieval result."""

    def __init__(self, storage: Storage, retriever: HybridRetriever) -> None:
        self.storage = storage
        self.retriever = retriever

    def build(
        self,
        query: str,
        project_id: str | None = None,
        max_items_per_layer: int = 10,
    ) -> Capsule:
        """Build a layered capsule for the given query."""
        result = self.retriever.search(query, project_id=project_id)

        pid = project_id or "unknown"
        capsule = Capsule(project_id=pid, query=query)
        capsule.created_at = datetime.now(UTC).isoformat()
        capsule.config_used = {
            "max_items_per_layer": max_items_per_layer,
        }

        # Layer 1: Checkpoints
        capsule.checkpoints = result.checkpoints[:max_items_per_layer]
        for cp in capsule.checkpoints:
            capsule.inclusion_reasons[cp.id] = "checkpoint: most relevant snapshot"

        # Layer 2: Active decisions
        active = [
            d
            for d in result.retrieved_decisions
            if hasattr(d, "decision_status") and getattr(d, "decision_status", None) == "active"
        ]
        capsule.active_decisions = active[:max_items_per_layer]
        for d in capsule.active_decisions:
            capsule.inclusion_reasons[d.id] = "decision: currently active"

        # Layer 3: Current facts
        capsule.current_facts = result.retrieved_facts[:max_items_per_layer]
        for f in capsule.current_facts:
            capsule.inclusion_reasons[f.id] = "fact: relevant to query"

        # Layer 4: Related episodes
        capsule.related_episodes = result.episodes[:max_items_per_layer]
        for ep in capsule.related_episodes:
            capsule.inclusion_reasons[ep.id] = "episode: related experience"

        # Layer 5: Applicable learnings
        capsule.applicable_learnings = result.retrieved_learnings[:max_items_per_layer]
        for lr in capsule.applicable_learnings:
            capsule.inclusion_reasons[lr.id] = "learning: applicable to context"

        # Layer 6: Documents
        capsule.documents = result.documents[:max_items_per_layer]
        for doc in capsule.documents:
            capsule.inclusion_reasons[doc.id] = "document: needed for context"

        # Layer 7: Raw sources (only when explicitly justified)
        # In this baseline, raw sources are referenced by IDs; actual files are not auto-loaded
        capsule.raw_sources = result.source_ids[:max_items_per_layer]

        # Gaps and conflicts
        capsule.gaps = result.missing_information
        capsule.conflicts = result.conflicts

        # Size metrics
        all_contents = []
        for mem in (
            capsule.checkpoints
            + capsule.active_decisions
            + capsule.current_facts
            + capsule.related_episodes
            + capsule.applicable_learnings
            + capsule.documents
        ):
            all_contents.append(mem.content)
        full_text = "\n\n".join(all_contents)
        capsule.total_characters = len(full_text)
        # Rough token estimate: ~4 chars per token for English/Portuguese
        capsule.estimated_tokens = max(1, capsule.total_characters // 4)

        return capsule


def build_resumption_prompt(capsule: Capsule) -> str:
    """Build a resumption prompt an agent can use to re-enter a project."""

    lines: list[str] = []
    lines.append("=== MEC CONTEXT CAPSULE ===")
    lines.append(f"Project: {capsule.project_id}")
    lines.append(f"Generated: {capsule.created_at}")
    lines.append("")

    if capsule.checkpoints:
        cp = capsule.checkpoints[0]
        if hasattr(cp, "current_state"):
            lines.append(f"Current state: {getattr(cp, 'current_state', '')}")
        if hasattr(cp, "last_completed_action"):
            lines.append(f"Last action: {getattr(cp, 'last_completed_action', '')}")
        if hasattr(cp, "next_allowed_action"):
            lines.append(f"Next action: {getattr(cp, 'next_allowed_action', '')}")
        if hasattr(cp, "blockers"):
            blockers = getattr(cp, "blockers", [])
            if blockers:
                lines.append(f"Blockers: {', '.join(blockers)}")
        if hasattr(cp, "pending_items"):
            pending = getattr(cp, "pending_items", [])
            if pending:
                lines.append(f"Pending: {', '.join(pending)}")
        lines.append("")

    if capsule.active_decisions:
        lines.append("Active decisions:")
        for d in capsule.active_decisions:
            lines.append(f"  - {d.content[:200]}")
        lines.append("")

    if capsule.current_facts:
        lines.append("Relevant facts:")
        for f in capsule.current_facts:
            lines.append(f"  - {f.content[:200]}")
        lines.append("")

    if capsule.gaps:
        lines.append("Known gaps:")
        for g in capsule.gaps:
            lines.append(f"  - {g}")
        lines.append("")

    if capsule.conflicts:
        lines.append("⚠ Conflicts detected:")
        for c in capsule.conflicts:
            lines.append(f"  - {c}")
        lines.append("")

    lines.append(f"--- Capsule stats: {capsule.total_characters} chars, ~{capsule.estimated_tokens} tokens ---")

    return "\n".join(lines)
