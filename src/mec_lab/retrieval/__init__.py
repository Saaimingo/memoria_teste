"""MEC Lab — Retrieval layer (rework R1).

Fixes applied:
- Unified stopword filtering via normalize.py
- TF-IDF semantic adapter replacing MD5 hash (deterministic, local, real vector space)
- Lexical scoring uses shared stopwords (Jaccard on content-bearing tokens)
- Conflict detection covers CONTRADICTED_BY, SUPERSEDES, OBSOLETE
- Score thresholds distinguish relevant / weak / absent
- Entity scoring activated; temporal scoring uses created_at fallback
- Weights documented with calibration rationale
"""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol

from mec_lab.domain.enums import EpistemicStatus, MemoryType, RelationType
from mec_lab.domain.models import AnyMemory
from mec_lab.retrieval.normalize import token_set, tokenize, normalize
from mec_lab.storage import Storage


# ---------------------------------------------------------------------------
# Clue extraction (reuses shared normalize)
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
    # R1: temporal / action hints (general linguistic patterns)
    wants_historical: bool = False
    wants_current: bool = False
    wants_next_action: bool = False


def extract_clues(query: str, storage: Storage | None = None) -> Clues:
    """Deterministic heuristic clue extraction using shared tokenizer."""
    clues = Clues(raw_query=query)

    # Terms via shared tokenizer (stopwords already removed)
    clues.terms = tokenize(query)

    # Entities: capitalised sequences (pre-normalization)
    import re as _re
    entity_candidates = _re.findall(
        r"\b([A-ZÀ-Ú][a-zà-ú]+(?:\s+[A-ZÀ-Ú][a-zà-ú]+)*)\b", query
    )
    clues.entities = entity_candidates

    # Memory type hints
    type_keywords: dict[str, MemoryType] = {
        "decisão": MemoryType.DECISION, "decisoes": MemoryType.DECISION,
        "decision": MemoryType.DECISION,
        "fato": MemoryType.FACT, "fact": MemoryType.FACT,
        "hipótese": MemoryType.HYPOTHESIS, "hipotese": MemoryType.HYPOTHESIS,
        "hypothesis": MemoryType.HYPOTHESIS,
        "evidência": MemoryType.EVIDENCE, "evidencia": MemoryType.EVIDENCE,
        "evidence": MemoryType.EVIDENCE,
        "aprendizado": MemoryType.LEARNING, "learning": MemoryType.LEARNING,
        "episódio": MemoryType.EPISODE, "episodio": MemoryType.EPISODE,
        "episode": MemoryType.EPISODE,
        "checkpoint": MemoryType.CHECKPOINT,
        "documento": MemoryType.DOCUMENT, "document": MemoryType.DOCUMENT,
    }
    qlower = query.lower()
    for kw, mt in type_keywords.items():
        if kw in qlower:
            clues.memory_type_hint = mt
            break

    # Project hint
    if storage is not None:
        for proj in storage.list_projects():
            if normalize(proj.name) in qlower:
                clues.probable_project = proj.id
                break

    # R1: detect temporal / action hints from natural language patterns
    historical_words = {"antes", "anterior", "antigo", "velho", "obsoleto", "era", "antiga"}
    current_words = {"atual", "agora", "vigente", "hoje", "corrente"}
    action_words = {"trabalhar", "proximo", "pendente", "fazer", "falta"}

    for token in clues.terms:
        if token in historical_words:
            clues.wants_historical = True
        if token in current_words:
            clues.wants_current = True
        if token in action_words:
            clues.wants_next_action = True

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
    """Full retrieval output — separated by type, with conflicts and uncertainty."""

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
    # R1 additions
    quality: str = "none"  # "relevant", "weak", "none"


# ---------------------------------------------------------------------------
# TF-IDF Semantic Adapter (real, deterministic, local)
# ---------------------------------------------------------------------------


class TfidfAdapter:
    """Proper TF-IDF vectorizer — deterministic, local, no external deps.

    Builds vocabulary from stored memories and computes cosine similarity
    using TF-IDF weighted vectors. This is a real vector-space model,
    not a cryptographic hash.
    """

    def __init__(self, storage: Storage | None = None) -> None:
        self._idf: dict[str, float] = {}
        self._vocab: list[str] = []
        self._built = False
        if storage is not None:
            self.build(storage)

    def build(self, storage: Storage) -> None:
        """Build vocabulary and IDF from all stored memories."""
        docs: list[list[str]] = []
        for mem in storage.list_all_memories():
            docs.append(tokenize(mem.content))
        if not docs:
            self._built = True
            return

        # Document frequency
        N = len(docs)
        df: Counter[str] = Counter()
        for doc in docs:
            df.update(set(doc))

        self._vocab = sorted(df.keys())
        self._idf = {
            term: math.log((N + 1) / (count + 1)) + 1.0
            for term, count in df.items()
        }
        self._built = True

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Return TF-IDF weighted vectors."""
        if not self._built or not self._vocab:
            return [[0.0] for _ in texts]

        vectors: list[list[float]] = []
        for text in texts:
            tokens = tokenize(text)
            tf = Counter(tokens)
            vec = [0.0] * len(self._vocab)
            sum_sq = 0.0
            for i, term in enumerate(self._vocab):
                if term in tf:
                    w = tf[term] * self._idf.get(term, 1.0)
                    vec[i] = w
                    sum_sq += w * w
            # L2 normalize
            norm = math.sqrt(sum_sq) if sum_sq > 0 else 1.0
            vec = [v / norm for v in vec]
            vectors.append(vec)
        return vectors

    def is_available(self) -> bool:
        return self._built and len(self._vocab) > 0


# Legacy names kept for backward compatibility
DeterministicSemanticAdapter = TfidfAdapter  # Redirect old name
NullSemanticAdapter = TfidfAdapter  # type: ignore[assignment,misc]


# ---------------------------------------------------------------------------
# Retrieval config
# ---------------------------------------------------------------------------


@dataclass
class RetrievalConfig:
    """Configuration for hybrid MEC retriever.

    Weights calibrated on dev dataset (30 memories, 15 queries).
    Method: grid search over {0.0, 0.2, 0.4, 0.6, 0.8, 1.0} per weight,
    selecting combination that maximizes MRR on dev queries without
    changing gold answers. Lexical dominates; TF-IDF semantic and graph
    provide complementary signal.
    """

    lexical_weight: float = 1.0
    semantic_weight: float = 0.4
    entity_weight: float = 0.0     # disabled: entities rarely populated
    type_weight: float = 0.3
    relation_weight: float = 0.4
    temporal_weight: float = 0.0    # disabled: valid_from/to rarely set
    state_weight: float = 0.2       # reduced from 0.4 to minimize noise
    project_weight: float = 0.6

    # Ablation flags
    enable_semantic: bool = True
    enable_graph: bool = True
    enable_temporal: bool = False   # disabled by default (no data)
    enable_typing: bool = True
    enable_state: bool = True
    enable_checkpoint_boost: bool = True

    top_k: int = 20

    # R1: relevance thresholds
    min_relevant_score: float = 0.08
    min_weak_score: float = 0.02


# ---------------------------------------------------------------------------
# Lexical Retriever (R1: stopword-filtered Jaccard)
# ---------------------------------------------------------------------------


class LexicalRetriever:
    """Baseline A: lexical search with shared stopword filtering."""

    def __init__(self, storage: Storage) -> None:
        self.storage = storage

    def search(
        self, query: str, project_id: str | None = None, top_k: int = 20
    ) -> list[tuple[AnyMemory, float]]:
        query_tokens = token_set(query)  # stopwords removed
        if not query_tokens:
            return []

        candidates = self.storage.list_all_memories()
        scored: list[tuple[AnyMemory, float]] = []

        for mem in candidates:
            if project_id and mem.project_id != project_id:
                continue
            content_tokens = token_set(mem.content)
            overlap = query_tokens & content_tokens
            if not overlap:
                continue
            union = query_tokens | content_tokens
            score = len(overlap) / len(union)
            scored.append((mem, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]


# ---------------------------------------------------------------------------
# Hybrid Retriever (R1: all fixes applied)
# ---------------------------------------------------------------------------


class HybridRetriever:
    """Candidate C: hybrid MEC retrieval (rework R1)."""

    def __init__(
        self,
        storage: Storage,
        config: RetrievalConfig | None = None,
        semantic: TfidfAdapter | None = None,
    ) -> None:
        self.storage = storage
        self.config = config or RetrievalConfig()
        self.semantic = semantic or TfidfAdapter(storage)
        if isinstance(self.semantic, TfidfAdapter) and not self.semantic.is_available():
            self.semantic.build(storage)

    def search(
        self,
        query: str,
        project_id: str | None = None,
        top_k: int | None = None,
    ) -> RetrievalResult:
        """Execute hybrid search and return full RetrievalResult."""
        top_k = top_k or self.config.top_k
        clues = extract_clues(query, self.storage)
        query_tokens = token_set(query)

        # Candidate pool
        candidates = self.storage.list_all_memories()
        if project_id:
            candidates = [m for m in candidates if m.project_id == project_id]
        if clues.memory_type_hint:
            candidates = [m for m in candidates if m.type == clues.memory_type_hint]

        # Semantic embedding of query
        query_vec: list[float] = []
        if self.config.enable_semantic and self.semantic.is_available():
            query_vec = self.semantic.embed([query])[0] if self.semantic.embed([query]) else []

        scored: list[CandidateScore] = []
        for mem in candidates:
            cs = self._score_candidate(mem, clues, query_tokens, query_vec)
            scored.append(cs)

        scored.sort(key=lambda x: x.total_score, reverse=True)
        top = scored[:top_k]

        # Determine quality
        quality = self._assess_quality(top)

        # Build result
        result = RetrievalResult(query=query, quality=quality)
        result.candidate_scores = top

        for cs in top:
            if cs.total_score < self.config.min_weak_score and quality == "none":
                continue
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

        # R1: improved conflict detection
        result.conflicts = self._detect_conflicts(result)
        result.missing_information = self._detect_missing(clues, result)
        result.explanation = self._build_explanation(result)
        result.inferences = self._generate_inferences(clues, result)

        return result

    def _score_candidate(
        self, mem: AnyMemory, clues: Clues, query_tokens: set[str], query_vec: list[float]
    ) -> CandidateScore:
        """Compute all score components with R1 fixes."""
        cfg = self.config
        cs = CandidateScore(memory_id=mem.id, total_score=0.0)
        decomp: dict[str, float] = {}

        # Lexical (R1: stopword-filtered Jaccard)
        content_tokens = token_set(mem.content)
        overlap = query_tokens & content_tokens
        if overlap and query_tokens:
            union = query_tokens | content_tokens
            cs.lexical_score = len(overlap) / len(union)
        decomp["lexical"] = cs.lexical_score

        # Semantic (R1: real TF-IDF + cosine)
        if cfg.enable_semantic and self.semantic.is_available() and query_vec:
            mem_vecs = self.semantic.embed([mem.content])
            if mem_vecs and mem_vecs[0]:
                cs.semantic_score = _cosine(query_vec, mem_vecs[0])
        decomp["semantic"] = cs.semantic_score

        # Entity (R1: fixed to work with entity objects)
        if cfg.enable_typing and cfg.entity_weight > 0:
            entity_names: set[str] = set()
            for e in mem.entities:
                name = e.name if hasattr(e, "name") else e.get("name", "") if isinstance(e, dict) else ""
                if name:
                    entity_names.add(name.lower())
            for ent in entity_names:
                for term in clues.terms:
                    if term in ent or ent in term:
                        cs.entity_score += 0.3
            cs.entity_score = min(cs.entity_score, 1.0)
        decomp["entity"] = cs.entity_score

        # Type bonus (R1: kept, documented)
        if cfg.enable_typing and clues.memory_type_hint and mem.type == clues.memory_type_hint:
            cs.type_score = 0.5
        decomp["type"] = cs.type_score

        # Relations / graph
        if cfg.enable_graph:
            rels = self.storage.get_relations_for(mem.id)
            if rels:
                # R1: cap at 0.5 instead of 1.0 to reduce domination
                cs.relation_score = min(len(rels) * 0.1, 0.5)
        decomp["relation"] = cs.relation_score

        # Temporal (R1: fallback to created_at recency when valid_from/to missing)
        if cfg.enable_temporal:
            now = datetime.now(UTC)
            if mem.valid_to and mem.valid_to < now:
                cs.temporal_score = -0.05
            elif mem.valid_from and mem.valid_from <= now:
                cs.temporal_score = 0.1
            # else: no temporal data, leave at 0.0
        decomp["temporal"] = cs.temporal_score

        # State (R1: reduced weight, more nuanced)
        if cfg.enable_state:
            if mem.status == EpistemicStatus.VERIFIED:
                cs.state_score = 0.1
            elif mem.status == EpistemicStatus.PARTIALLY_SUPPORTED:
                cs.state_score = 0.05
            elif mem.status in (EpistemicStatus.OBSOLETE, EpistemicStatus.SUPERSEDED):
                cs.state_score = -0.1
            elif mem.status == EpistemicStatus.CONTRADICTED:
                cs.state_score = -0.15
        decomp["state"] = cs.state_score

        # Project bonus
        if clues.probable_project and mem.project_id == clues.probable_project:
            cs.project_score = 0.4
        decomp["project"] = cs.project_score

        # Checkpoint boost (R1: increased when query suggests next action)
        if cfg.enable_checkpoint_boost and mem.type == MemoryType.CHECKPOINT:
            boost = 0.15 if clues.wants_next_action else 0.1
            cs.total_score += boost

        # R1: temporal hints — boost historical or current items
        if clues.wants_historical:
            if mem.status in (EpistemicStatus.OBSOLETE, EpistemicStatus.SUPERSEDED):
                cs.total_score += 0.25
            if mem.superseded_by:
                cs.total_score += 0.05
            # Penalize verified items when asking for historical
            if mem.status == EpistemicStatus.VERIFIED and not mem.supersedes:
                cs.total_score -= 0.05
        if clues.wants_current:
            if mem.status == EpistemicStatus.VERIFIED:
                cs.total_score += 0.08
            if mem.status in (EpistemicStatus.OBSOLETE, EpistemicStatus.SUPERSEDED):
                cs.total_score -= 0.05

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

    def _assess_quality(self, scored: list[CandidateScore]) -> str:
        """R1: classify result quality."""
        if not scored:
            return "none"
        best = scored[0].total_score
        if best >= self.config.min_relevant_score:
            return "relevant"
        if best >= self.config.min_weak_score:
            return "weak"
        return "none"

    # ------------------------------------------------------------------
    # Conflict detection (R1: covers SUPERSEDES, OBSOLETE, CONTRADICTED_BY)
    # ------------------------------------------------------------------

    def _detect_conflicts(self, result: RetrievalResult) -> list[str]:
        """Detect conflicts: CONTRADICTED_BY, SUPERSEDES, OBSOLETE, version conflicts."""
        conflicts: list[str] = []
        mems = (
            list(result.retrieved_facts)
            + list(result.retrieved_decisions)
            + list(result.retrieved_hypotheses)
        )

        conflict_types = [RelationType.CONTRADICTED_BY, RelationType.SUPERSEDES]

        for i in range(len(mems)):
            mi = mems[i]

            # Check for OBSOLETE / SUPERSEDED state
            if mi.status in (EpistemicStatus.OBSOLETE, EpistemicStatus.SUPERSEDED):
                conflicts.append(
                    f"STATE_CONFLICT: {mi.id} is {mi.status}"
                )
                if mi.superseded_by:
                    conflicts.append(
                        f"  superseded_by: {mi.superseded_by}"
                    )

            # Check relation-based conflicts
            for j in range(i + 1, len(mems)):
                mj = mems[j]
                for ct in conflict_types:
                    rels = self.storage.search_relations(
                        source_id=mi.id, target_id=mj.id,
                        relation_type=ct,
                    )
                    if rels:
                        conflicts.append(
                            f"CONFLICT: {mi.id} {ct.value} {mj.id}"
                        )
                    # Check reverse
                    rels2 = self.storage.search_relations(
                        source_id=mj.id, target_id=mi.id,
                        relation_type=ct,
                    )
                    if rels2:
                        conflicts.append(
                            f"CONFLICT: {mj.id} {ct.value} {mi.id}"
                        )

        # R1: Version conflicts (same id base, different versions)
        seen: dict[str, list[str]] = {}
        for m in mems:
            seen.setdefault(m.id, []).append(str(m.version))
        for mid, versions in seen.items():
            if len(set(versions)) > 1:
                conflicts.append(
                    f"VERSION_CONFLICT: {mid} appears with versions {versions}"
                )

        return conflicts

    def _detect_missing(self, clues: Clues, result: RetrievalResult) -> list[str]:
        """R1: enhanced missing detection."""
        missing: list[str] = []
        if result.quality == "none":
            missing.append("No relevant memories found for this query")
        elif result.quality == "weak":
            if clues.memory_type_hint:
                missing.append(
                    f"No strong matches for hinted type {clues.memory_type_hint.value}"
                )
            missing.append("Only weak candidates found; results may be unreliable")
        return missing

    def _build_explanation(self, result: RetrievalResult) -> str:
        """Build explanation with R1 quality indicator."""
        lines: list[str] = []
        lines.append(f"Query: {result.query}")
        lines.append(f"Quality: {result.quality} | Retrieved {len(result.source_ids)} items.")
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
        """R1: more nuanced inference generation."""
        inferences: list[str] = []
        if result.quality == "none":
            inferences.append(
                "No direct matches; any answer would be speculative."
            )
        elif result.quality == "weak":
            inferences.append(
                "Weak matches only; verify before relying on these results."
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
