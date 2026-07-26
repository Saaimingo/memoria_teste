"""MEC Lab — Retrieval layer.

Implements lexical, semantic (adapter), and hybrid MEC retrieval with:
- clue extraction (deterministic)
- configurable scoring
- explanation decomposition
- ablation flags
- conflict/missing detection
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Protocol

from mec_lab.domain.enums import EpistemicStatus, MemoryType, RelationType
from mec_lab.domain.models import (
    AnyMemory,
    Checkpoint,
    Decision,
    MemoryRelation,
)
from mec_lab.storage import Storage


# ---------------------------------------------------------------------------
# Clue extraction
# ---------------------------------------------------------------------------


@dataclass
class Clues:
    """Structured clues extracted from a free-text query."""

    raw_query: str
    terms: list[str] = field(default_factory=list)
    entities: list[str] = field(default_factory=list)
    probable_project: str | None = None
    period_start: str | None = None
    period_end: str | None = None
    status_hint: str | None = None
    problem: str | None = None
    action: str | None = None
    result: str | None = None
    memory_type_hint: MemoryType | None = None


def extract_clues(query: str, storage: Storage | None = None) -> Clues:
    """Deterministic heuristic clue extraction from a free-text query."""
    clues = Clues(raw_query=query)

    # Terms: split on whitespace and punctuation, filter short
    words = re.findall(r"[a-zA-ZÀ-ÿ0-9_]{3,}", query.lower())
    stopwords = {
        "que", "com", "para", "dos", "das", "uma", "como", "mais", "mas",
        "the", "and", "for", "was", "that", "this", "with", "from", "have",
        "não", "ele", "ela", "são", "está", "por", "era", "tem", "seu",
    }
    clues.terms = [w for w in words if w not in stopwords]

    # Entities: capitalised sequences or well-known patterns
    entity_candidates = re.findall(r"\b([A-ZÀ-Ú][a-zà-ú]+(?:\s+[A-ZÀ-Ú][a-zà-ú]+)*)\b", query)
    clues.entities = entity_candidates

    # Memory type hints
    type_keywords: dict[str, MemoryType] = {
        "decisão": MemoryType.DECISION,
        "decisoes": MemoryType.DECISION,
        "decision": MemoryType.DECISION,
        "fato": MemoryType.FACT,
        "fact": MemoryType.FACT,
        "hipótese": MemoryType.HYPOTHESIS,
        "hipotese": MemoryType.HYPOTHESIS,
        "hypothesis": MemoryType.HYPOTHESIS,
        "evidência": MemoryType.EVIDENCE,
        "evidencia": MemoryType.EVIDENCE,
        "evidence": MemoryType.EVIDENCE,
        "aprendizado": MemoryType.LEARNING,
        "learning": MemoryType.LEARNING,
        "episódio": MemoryType.EPISODE,
        "episodio": MemoryType.EPISODE,
        "episode": MemoryType.EPISODE,
        "checkpoint": MemoryType.CHECKPOINT,
        "documento": MemoryType.DOCUMENT,
        "document": MemoryType.DOCUMENT,
    }
    for kw, mt in type_keywords.items():
        if kw in query.lower():
            clues.memory_type_hint = mt
            break

    # Project hint: try to match known project names if storage is provided
    if storage is not None:
        projects = storage.list_projects()
        for proj in projects:
            if proj.name.lower() in query.lower():
                clues.probable_project = proj.id
                break

    return clues


# ---------------------------------------------------------------------------
# Retrieval result structures
# ---------------------------------------------------------------------------


@dataclass
class CandidateScore:
    """Score breakdown for a single candidate."""

    memory_id: str
    total_score: float
    lexical_score: float = 0.0
    semantic_score: float = 0.0
    entity_score: float = 0.0
    type_score: float = 0.0
    relation_score: float = 0.0
    temporal_score: float = 0.0
    state_score: float = 0.0
    project_score: float = 0.0
    explanation_decomposition: dict[str, float] = field(default_factory=dict)


@dataclass
class RetrievalResult:
    """Full retrieval output as specified in ESPECIFICACAO_EXPERIMENTAL.md sec 10."""

    query: str
    retrieved_facts: list[AnyMemory] = field(default_factory=list)
    retrieved_decisions: list[AnyMemory] = field(default_factory=list)
    retrieved_hypotheses: list[AnyMemory] = field(default_factory=list)
    retrieved_evidence: list[AnyMemory] = field(default_factory=list)
    retrieved_learnings: list[AnyMemory] = field(default_factory=list)
    episodes: list[AnyMemory] = field(default_factory=list)
    checkpoints: list[AnyMemory] = field(default_factory=list)
    documents: list[AnyMemory] = field(default_factory=list)
    inferences: list[str] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)
    missing_information: list[str] = field(default_factory=list)
    candidate_scores: list[CandidateScore] = field(default_factory=list)
    explanation: str = ""
    source_ids: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Semantic adapter protocol
# ---------------------------------------------------------------------------


class SemanticAdapter(Protocol):
    """Protocol for semantic embedding providers."""

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Return embedding vectors for the given texts."""
        ...

    def is_available(self) -> bool:
        """Return whether the adapter can produce embeddings."""
        ...


class NullSemanticAdapter:
    """Fallback adapter that returns zero vectors when semantic is unavailable."""

    def __init__(self, dimension: int = 384) -> None:
        self.dimension = dimension

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[0.0] * self.dimension for _ in texts]

    def is_available(self) -> bool:
        return False


class DeterministicSemanticAdapter:
    """Deterministic vector representation using TF-IDF-like hashing.

    Not a real semantic model, but provides a stable, reproducible
    vector for testing and baseline without external dependencies.
    """

    def __init__(self, dimension: int = 64) -> None:
        self.dimension = dimension

    def _hash_vector(self, text: str) -> list[float]:
        """Produce a deterministic pseudo-embedding from text."""
        tokens = re.findall(r"\w+", text.lower())
        vec = [0.0] * self.dimension
        for token in tokens:
            h = int(hashlib.md5(token.encode()).hexdigest(), 16)
            for i in range(self.dimension):
                # Pseudo-random sign based on hash and position
                bit = (h >> (i % 32)) & 1
                vec[i] += 1.0 if bit else -1.0
        # Normalise
        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0:
            vec = [v / norm for v in vec]
        return vec

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._hash_vector(t) for t in texts]

    def is_available(self) -> bool:
        return True


# ---------------------------------------------------------------------------
# Retrieval engines
# ---------------------------------------------------------------------------


@dataclass
class RetrievalConfig:
    """Configuration for the hybrid MEC retriever."""

    lexical_weight: float = 1.0
    semantic_weight: float = 0.3
    entity_weight: float = 0.5
    type_weight: float = 0.5
    relation_weight: float = 0.4
    temporal_weight: float = 0.3
    state_weight: float = 0.4
    project_weight: float = 0.6

    # Ablation flags
    enable_semantic: bool = True
    enable_graph: bool = True
    enable_temporal: bool = True
    enable_typing: bool = True
    enable_state: bool = True
    enable_checkpoint_boost: bool = True

    top_k: int = 20


class LexicalRetriever:
    """Baseline A: pure lexical / textual search."""

    def __init__(self, storage: Storage) -> None:
        self.storage = storage

    def search(self, query: str, project_id: str | None = None, top_k: int = 20) -> list[tuple[AnyMemory, float]]:
        """Return memories scored by lexical similarity."""
        clues = extract_clues(query)
        candidates = self.storage.list_all_memories()

        scored: list[tuple[AnyMemory, float]] = []
        query_lower = query.lower()
        query_terms = set(clues.terms)

        for mem in candidates:
            if project_id and mem.project_id != project_id:
                continue
            score = self._lexical_score(mem, query_lower, query_terms)
            if score > 0:
                scored.append((mem, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    @staticmethod
    def _lexical_score(mem: AnyMemory, query_lower: str, _terms: set[str]) -> float:
        """Simple TF-based lexical score."""
        content_lower = mem.content.lower()
        # Count word overlap
        query_words = set(query_lower.split())
        content_words = set(content_lower.split())
        overlap = query_words & content_words
        if not overlap:
            return 0.0
        # Jaccard-like
        union = query_words | content_words
        return len(overlap) / len(union) if union else 0.0


class HybridRetriever:
    """Candidate C: hybrid MEC retrieval combining multiple signals."""

    def __init__(
        self,
        storage: Storage,
        config: RetrievalConfig | None = None,
        semantic: SemanticAdapter | None = None,
    ) -> None:
        self.storage = storage
        self.config = config or RetrievalConfig()
        self.semantic = semantic or NullSemanticAdapter()
        self._embedding_cache: dict[str, list[float]] = {}

    def search(
        self,
        query: str,
        project_id: str | None = None,
        top_k: int | None = None,
    ) -> RetrievalResult:
        """Execute hybrid search and return full RetrievalResult."""
        top_k = top_k or self.config.top_k
        clues = extract_clues(query, self.storage)
        query_lower = query.lower()

        # Candidate pool
        candidates = self.storage.list_all_memories()
        if project_id:
            candidates = [m for m in candidates if m.project_id == project_id]
        if clues.memory_type_hint:
            candidates = [m for m in candidates if m.type == clues.memory_type_hint]

        # Pre-compute semantic embeddings if enabled
        query_vec: list[float] = []
        if self.config.enable_semantic:
            query_vec = self._get_embedding(query)

        scored: list[CandidateScore] = []
        for mem in candidates:
            cs = self._score_candidate(mem, clues, query_lower, query_vec)
            if cs.total_score > 0:
                scored.append(cs)

        scored.sort(key=lambda x: x.total_score, reverse=True)
        top = scored[:top_k]

        # Build result
        result = RetrievalResult(query=query)
        result.candidate_scores = top

        for cs in top:
            mem = self.storage.get_memory(cs.memory_id)
            if mem is None:
                continue
            result.source_ids.append(mem.id)
            match mem.type:
                case MemoryType.FACT:
                    result.retrieved_facts.append(mem)
                case MemoryType.DECISION:
                    result.retrieved_decisions.append(mem)
                case MemoryType.HYPOTHESIS:
                    result.retrieved_hypotheses.append(mem)
                case MemoryType.EVIDENCE:
                    result.retrieved_evidence.append(mem)
                case MemoryType.LEARNING:
                    result.retrieved_learnings.append(mem)
                case MemoryType.EPISODE:
                    result.episodes.append(mem)
                case MemoryType.CHECKPOINT:
                    result.checkpoints.append(mem)
                case MemoryType.DOCUMENT:
                    result.documents.append(mem)

        # Detect conflicts
        result.conflicts = self._detect_conflicts(result)
        result.missing_information = self._detect_missing(clues, result)
        result.explanation = self._build_explanation(result)
        result.inferences = self._generate_inferences(clues, result)

        return result

    def _score_candidate(
        self, mem: AnyMemory, clues: Clues, query_lower: str, query_vec: list[float]
    ) -> CandidateScore:
        """Compute all score components, respecting ablation flags."""
        cfg = self.config
        cs = CandidateScore(memory_id=mem.id, total_score=0.0)
        decomp: dict[str, float] = {}

        # Lexical
        content_lower = mem.content.lower()
        query_words = set(query_lower.split())
        content_words = set(content_lower.split())
        overlap = query_words & content_words
        if overlap:
            union = query_words | content_words
            cs.lexical_score = len(overlap) / len(union) if union else 0.0
        decomp["lexical"] = cs.lexical_score

        # Semantic
        if cfg.enable_semantic and self.semantic.is_available():
            mem_vec = self._get_embedding(mem.content)
            if query_vec and mem_vec:
                cs.semantic_score = _cosine(query_vec, mem_vec)
        decomp["semantic"] = cs.semantic_score

        # Entity
        if cfg.enable_typing:
            mem_entity_names = {e["name"].lower() for e in mem.entities if isinstance(e, dict)}
            for ent in mem_entity_names:
                if any(term in ent for term in clues.terms):
                    cs.entity_score += 0.3
            cs.entity_score = min(cs.entity_score, 1.0)
        decomp["entity"] = cs.entity_score

        # Type bonus
        if cfg.enable_typing and clues.memory_type_hint and mem.type == clues.memory_type_hint:
            cs.type_score = 0.5
        decomp["type"] = cs.type_score

        # Relations (graph)
        if cfg.enable_graph:
            rels = self.storage.get_relations_for(mem.id)
            if rels:
                cs.relation_score = min(len(rels) * 0.1, 1.0)
        decomp["relation"] = cs.relation_score

        # Temporal
        if cfg.enable_temporal:
            from datetime import UTC
            now = datetime.now(UTC)
            if mem.valid_to and mem.valid_to < now:
                cs.temporal_score = -0.1  # expired
            elif mem.valid_from and mem.valid_from <= now:
                cs.temporal_score = 0.2  # currently valid
        decomp["temporal"] = cs.temporal_score

        # State
        if cfg.enable_state:
            active_states = {EpistemicStatus.VERIFIED, EpistemicStatus.PARTIALLY_SUPPORTED}
            if mem.status in active_states:
                cs.state_score = 0.2
            elif mem.status == EpistemicStatus.SUPERSEDED:
                cs.state_score = -0.2
        decomp["state"] = cs.state_score

        # Project bonus
        if clues.probable_project and mem.project_id == clues.probable_project:
            cs.project_score = 0.4
        decomp["project"] = cs.project_score

        # Checkpoint boost
        if cfg.enable_checkpoint_boost and mem.type == MemoryType.CHECKPOINT:
            cs.total_score += 0.2  # extra boost for checkpoints

        # Weighted sum
        weights = {
            "lexical": cfg.lexical_weight,
            "semantic": cfg.semantic_weight,
            "entity": cfg.entity_weight,
            "type": cfg.type_weight,
            "relation": cfg.relation_weight,
            "temporal": cfg.temporal_weight,
            "state": cfg.state_weight,
            "project": cfg.project_weight,
        }
        cs.total_score = sum(
            decomp.get(k, 0.0) * weights.get(k, 0.0) for k in decomp
        )
        cs.explanation_decomposition = decomp

        return cs

    def _get_embedding(self, text: str) -> list[float]:
        """Retrieve or compute embedding, with caching."""
        h = hashlib.md5(text.encode()).hexdigest()
        if h not in self._embedding_cache:
            vecs = self.semantic.embed([text])
            self._embedding_cache[h] = vecs[0] if vecs else []
        return self._embedding_cache[h]

    def _detect_conflicts(self, result: RetrievalResult) -> list[str]:
        """Detect conflicts among retrieved items."""
        conflicts: list[str] = []
        mems = (
            list(result.retrieved_facts)
            + list(result.retrieved_decisions)
            + list(result.retrieved_hypotheses)
        )
        for i in range(len(mems)):
            for j in range(i + 1, len(mems)):
                rels = self.storage.search_relations(
                    source_id=mems[i].id, target_id=mems[j].id,
                    relation_type=RelationType.CONTRADICTED_BY,
                )
                if rels:
                    conflicts.append(
                        f"CONFLICT: {mems[i].id} CONTRADICTED_BY {mems[j].id}"
                    )
                # Also check reverse
                rels2 = self.storage.search_relations(
                    source_id=mems[j].id, target_id=mems[i].id,
                    relation_type=RelationType.CONTRADICTED_BY,
                )
                if rels2:
                    conflicts.append(
                        f"CONFLICT: {mems[j].id} CONTRADICTED_BY {mems[i].id}"
                    )
        return conflicts

    def _detect_missing(self, clues: Clues, result: RetrievalResult) -> list[str]:
        """Detect what information is missing from the retrieval."""
        missing: list[str] = []
        if clues.memory_type_hint:
            found_of_type = (
                len(result.retrieved_facts)
                + len(result.retrieved_decisions)
                + len(result.retrieved_hypotheses)
                + len(result.retrieved_evidence)
                + len(result.retrieved_learnings)
            )
            if found_of_type == 0:
                missing.append(f"No memories of hinted type {clues.memory_type_hint} found")
        if not result.source_ids:
            missing.append("No memories matched the query at all")
        return missing

    def _build_explanation(self, result: RetrievalResult) -> str:
        """Build human-readable explanation from candidate scores and sources."""
        lines: list[str] = []
        lines.append(f"Query: {result.query}")
        lines.append(f"Retrieved {len(result.source_ids)} items.")
        for cs in result.candidate_scores[:5]:
            mem = self.storage.get_memory(cs.memory_id)
            snippet = mem.content[:80] if mem else "(not found)"
            lines.append(
                f"  [{cs.total_score:.3f}] {cs.memory_id} ({mem.type if mem else '?'}): {snippet}"
            )
            lines.append(f"       decomposition: {cs.explanation_decomposition}")
        if result.conflicts:
            lines.append(f"Conflicts detected: {len(result.conflicts)}")
            for c in result.conflicts[:5]:
                lines.append(f"  {c}")
        if result.missing_information:
            lines.append("Missing information:")
            for m in result.missing_information:
                lines.append(f"  - {m}")
        if result.inferences:
            lines.append("[INFERENCE] " + "; ".join(result.inferences))
        return "\n".join(lines)

    def _generate_inferences(self, clues: Clues, result: RetrievalResult) -> list[str]:
        """Generate explicitly marked inferences (heuristic)."""
        inferences: list[str] = []
        if not result.source_ids:
            inferences.append(
                "No direct matches; any answer would be speculative."
            )
        return inferences


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _cosine(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two vectors."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)
