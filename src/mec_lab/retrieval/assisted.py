"""MEC R4 — Structured assisted retrieval pipeline.

Deterministic multi-stage retrieval that combines:

1. exact identifier matching (serial, MAC, protocol, commit, path, ticket);
2. safe partial identifier matching (suffix/prefix forms);
3. structured metadata filtering (project, environment, responsible, etc.);
4. textual / TF-IDF semantic matching (reuses the existing TfidfAdapter);
5. graph relations and temporal validity (SUPERSEDES / valid_from / valid_until);
6. a final normalized ranking with per-component diagnostic breakdown;
7. four canonical retrieval states (MEMORY_CONFIRMED, AMBIGUOUS_CANDIDATES,
   CLARIFICATION_REQUIRED, MEMORY_NOT_FOUND);
8. a deterministic clarification cycle limited to three questions.

No LLM is involved; every state transition and every clarification question
is produced by explicit rules and templates.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Callable

from mec_lab.domain.enums import EpistemicStatus, MemoryType, RelationType
from mec_lab.domain.models import AnyMemory, MemoryRelation
from mec_lab.retrieval.normalize import token_set
from mec_lab.retrieval.identifiers import (
    IDENTIFIER_FIELDS,
    extract_identifier_hints,
    normalize_identifier,
)
from mec_lab.storage import Storage


# ---------------------------------------------------------------------------
# Retrieval states
# ---------------------------------------------------------------------------


class RetrievalState(str, Enum):
    """Exactly one of these is returned by every assisted retrieval call."""

    MEMORY_CONFIRMED = "MEMORY_CONFIRMED"
    AMBIGUOUS_CANDIDATES = "AMBIGUOUS_CANDIDATES"
    CLARIFICATION_REQUIRED = "CLARIFICATION_REQUIRED"
    MEMORY_NOT_FOUND = "MEMORY_NOT_FOUND"


# ---------------------------------------------------------------------------
# Score breakdown (mirrors the spec field names)
# ---------------------------------------------------------------------------


@dataclass
class StructuredScore:
    """Per-component score breakdown for a single candidate."""

    memory_id: str
    identifier_score: float = 0.0
    metadata_score: float = 0.0
    text_score: float = 0.0
    relation_score: float = 0.0
    temporal_score: float = 0.0
    final_score: float = 0.0
    match_reasons: list[str] = field(default_factory=list)
    is_exact_identifier: bool = False
    # R4.1: new score channels
    path_score: float = 0.0
    symbol_score: float = 0.0
    cli_score: float = 0.0
    commit_score: float = 0.0
    entity_group_score: float = 0.0
    group_id: str = ""

    def components(self) -> dict[str, float]:
        return {
            "identifier_score": round(self.identifier_score, 4),
            "metadata_score": round(self.metadata_score, 4),
            "text_score": round(self.text_score, 4),
            "relation_score": round(self.relation_score, 4),
            "temporal_score": round(self.temporal_score, 4),
            "path_score": round(self.path_score, 4),
            "symbol_score": round(self.symbol_score, 4),
            "cli_score": round(self.cli_score, 4),
            "commit_score": round(self.commit_score, 4),
            "entity_group_score": round(self.entity_group_score, 4),
            "final_score": round(self.final_score, 4),
        }


# ---------------------------------------------------------------------------
# Configuration (weights + thresholds, all documented and mutable)
# ---------------------------------------------------------------------------


@dataclass
class AssistedRetrievalConfig:
    """Weights and thresholds for the assisted retrieval pipeline.

    Identifier matches dominate by design: an exact identifier hit carries
    more weight than any purely textual match, so a semantic look-alike cannot
    silently outrank a real technical anchor.
    """

    # Component weights (the final score is a weighted sum normalized to [0,1]).
    identifier_weight: float = 2.0
    metadata_weight: float = 0.6
    text_weight: float = 0.5
    relation_weight: float = 0.25
    temporal_weight: float = 0.3

    # Identifier scoring
    exact_identifier_score: float = 1.0
    partial_identifier_score: float = 0.55
    min_partial_len: int = 4  # minimum length for a partial match to be safe

    # Metadata scoring: each matching structured field contributes this amount
    per_metadata_field_score: float = 0.25
    metadata_cap: float = 0.9

    # Temporal scoring
    temporal_valid_bonus: float = 0.15
    temporal_expired_penalty: float = 0.15
    temporal_supersedes_bonus: float = 0.20  # active decision that supersedes

    # Relation scoring
    per_relation_score: float = 0.1
    relation_cap: float = 0.4

    # State classification thresholds (applied to final_score)
    confirmed_min_score: float = 0.35
    confirmed_margin: float = 0.15        # best must beat 2nd by at least this
    ambiguous_min_score: float = 0.22      # two or three candidates above this => ambiguous
    clarification_min_score: float = 0.10  # below this => not_found unless hints
    not_found_floor: float = 0.06           # below this => not_found even with hints

    # Clarification cycle
    max_clarifications: int = 3
    clarification_question_score_floor: float = 0.12

    # Stale-memory penalty
    superseded_penalty: float = 0.25
    obsolete_penalty: float = 0.20
    hypothesis_penalty: float = 0.10  # not approved -> cannot be a confirmed decision

    # R4.1: Symbolic and structural score channels
    path_weight: float = 1.5          # exact path match dominates
    symbol_weight: float = 1.2        # exact symbol match dominates
    cli_weight: float = 0.8           # CLI command/option match
    commit_weight: float = 1.0         # commit SHA match
    entity_group_weight: float = 0.15  # entity grouping bonus

    path_exact_score: float = 1.0
    path_partial_score: float = 0.5
    symbol_exact_score: float = 1.0
    symbol_partial_score: float = 0.4
    cli_exact_score: float = 1.0
    cli_partial_score: float = 0.4
    commit_exact_score: float = 1.0
    commit_prefix_score: float = 0.6

    # Top-k pool considered for ranking
    pool_size: int = 50


# ---------------------------------------------------------------------------
# Per-candidate metadata extraction (backwards compatible)
# ---------------------------------------------------------------------------


def candidate_metadata(mem: AnyMemory) -> dict[str, Any]:
    """Return the effective structured metadata of a memory.

    Structured fields may live on the typed model directly (e.g. environment on
    Evidence) or inside the free-form ``metadata`` dict of ``MemoryEnvelope``.
    Both sources are merged; the free-form dict never overrides a typed value.
    """
    data: dict[str, Any] = {}
    # Typed model attributes first
    for attr in (
        "project_id", "environment", "responsible", "manufacturer", "device_model",
        "version", "serial_number", "mac_address", "protocol_number", "ticket_number",
        "issue_id", "repository", "branch", "folder_path", "file_path",
        "class_name", "function_name", "commit_sha", "status",
    ):
        val = getattr(mem, attr, None)
        if val not in (None, "", []):
            data[attr] = val
    # Plus the record-level valid window
    if getattr(mem, "valid_from", None):
        data["valid_from"] = mem.valid_from
    if getattr(mem, "valid_to", None):
        data["valid_to"] = mem.valid_to
    # Free-form metadata dict augments but does not overwrite typed attrs
    meta = getattr(mem, "metadata", None) or {}
    if isinstance(meta, dict):
        for k, v in meta.items():
            if v not in (None, "", []) and k not in data:
                data[k] = v
    return data


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------


@dataclass
class AssistedRetrievalResult:
    """Full output of an assisted retrieval call."""

    state: RetrievalState
    query: str
    scores: list[StructuredScore] = field(default_factory=list)
    memories: list[AnyMemory] = field(default_factory=list)
    explanation: str = ""
    related: list[AnyMemory] = field(default_factory=list)
    clarification_dimension: str | None = None
    clarification_question: str | None = None
    clarifications_used: int = 0
    session_filters: dict[str, Any] = field(default_factory=dict)

    def top_memory(self) -> AnyMemory | None:
        return self.memories[0] if self.memories else None

    def top_scores(self, k: int = 3) -> list[StructuredScore]:
        return self.scores[:k]


class AssistedRetriever:
    """Deterministic structured-assisted retriever built on top of Storage.

    The retriever is stateless across calls except for the explicit
    ``session_filters`` parameter that callers may pass to accumulate
    clarification answers. No filter is persisted automatically.
    """

    def __init__(
        self,
        storage: Storage,
        config: AssistedRetrievalConfig | None = None,
        semantic: TfidfAdapter | None = None,
        clarifications_used: int = 0,
    ) -> None:
        self.storage = storage
        self.config = config or AssistedRetrievalConfig()
        if semantic is not None:
            self.semantic = semantic
        else:
            from mec_lab.retrieval import TfidfAdapter  # lazy — avoids circular import
            self.semantic = TfidfAdapter(storage)
        if not self.semantic.is_available():
            self.semantic.build(storage)
        self.clarifications_used = clarifications_used

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def retrieve(
        self,
        query: str,
        project_id: str | None = None,
        session_filters: dict[str, Any] | None = None,
    ) -> AssistedRetrievalResult:
        """Run the full pipeline and return an :class:`AssistedRetrievalResult`."""
        session_filters = dict(session_filters or {})
        hints = extract_identifier_hints(query)
        candidates = self._candidate_pool(project_id, session_filters)
        query_tokens = token_set(query, stem=True)
        query_vec = self.semantic.embed([query])[0] if self.semantic.is_available() else []

        scored: list[StructuredScore] = []
        for mem in candidates:
            s = self._score(mem, hints, query_tokens, query_vec, query, session_filters)
            scored.append(s)

        # Sort by final score (desc), then identifier_score as tiebreaker
        scored.sort(key=lambda s: (s.final_score, s.identifier_score), reverse=True)
        scored = [s for s in scored if s.final_score > 0.0][: self.config.pool_size]

        # Apply session/structural filters that came from clarifications
        if session_filters:
            scored = self._apply_session_filters(scored, session_filters)

        # R4.1: Entity grouping — merge segments from the same file
        scored = self._group_entities(scored)

        state = self._classify_state(scored, session_filters)

        result = AssistedRetrievalResult(
            state=state, query=query, scores=scored, session_filters=session_filters,
            clarifications_used=self.clarifications_used,
        )
        result.memories = [self.storage.get_memory(s.memory_id) for s in scored]  # type: ignore[assignment]
        result.memories = [m for m in result.memories if m is not None]  # type: ignore[list-item]

        # Related memories (up to 2) for confirmed results
        if state == RetrievalState.MEMORY_CONFIRMED and result.memories:
            result.related = self._related_for(result.memories[0], limit=2)

        # Ambiguous: cap to 3 candidates per spec
        if state == RetrievalState.AMBIGUOUS_CANDIDATES and len(result.memories) > 3:
            result.memories = result.memories[:3]
            result.scores = result.scores[:3]

        if state == RetrievalState.CLARIFICATION_REQUIRED:
            dim, q = self._build_clarification(query, scored, session_filters)
            result.clarification_dimension = dim
            result.clarification_question = q

        result.explanation = self._explain(result)
        return result

    # ------------------------------------------------------------------
    # Candidate pool + session filters
    # ------------------------------------------------------------------

    def _candidate_pool(
        self, project_id: str | None, session_filters: dict[str, Any]
    ) -> list[AnyMemory]:
        memories = self.storage.list_all_memories()
        if project_id:
            memories = [m for m in memories if m.project_id == project_id]
        # Session filters act as hard constraints on metadata
        if not session_filters:
            return memories
        filtered: list[AnyMemory] = []
        for m in memories:
            md = candidate_metadata(m)
            keep = True
            for k, v in session_filters.items():
                if v is None or v == "":
                    continue
                mv = md.get(k)
                if mv is None:
                    keep = False
                    break
                if normalize_identifier(k, str(mv)) != normalize_identifier(k, str(v)) \
                        and str(mv).lower() != str(v).lower():
                    keep = False
                    break
            if keep:
                filtered.append(m)
        return filtered

    def _apply_session_filters(
        self, scored: list[StructuredScore], session_filters: dict[str, Any]
    ) -> list[StructuredScore]:
        if not session_filters:
            return scored
        kept: list[StructuredScore] = []
        for s in scored:
            mem = self.storage.get_memory(s.memory_id)
            if mem is None:
                continue
            md = candidate_metadata(mem)
            ok = True
            for k, v in session_filters.items():
                if v is None or v == "":
                    continue
                mv = md.get(k)
                if mv is None:
                    ok = False
                    break
                if normalize_identifier(k, str(mv)) != normalize_identifier(k, str(v)) \
                        and str(mv).lower() != str(v).lower():
                    ok = False
                    break
            if ok:
                kept.append(s)
        return kept

    # ------------------------------------------------------------------
    # Scoring
    # ------------------------------------------------------------------

    def _score(
        self,
        mem: AnyMemory,
        hints: dict[str, list[str]],
        query_tokens: set[str],
        query_vec: list[float],
        query: str,
        session_filters: dict[str, Any],
    ) -> StructuredScore:
        cfg = self.config
        md = candidate_metadata(mem)
        s = StructuredScore(memory_id=mem.id)

        # 1. Identifier matching
        s.identifier_score, exact_hit, id_reasons = self._identifier_score(md, hints)
        s.is_exact_identifier = exact_hit
        s.match_reasons.extend(id_reasons)

        # 2. Partial identifier matching (only counted if no exact hit)
        if not exact_hit:
            ps, p_reasons = self._partial_identifier_score(md, hints)
            s.identifier_score = max(s.identifier_score, ps)
            s.match_reasons.extend(p_reasons)

        # R4.1: Symbolic scoring (path, symbol, CLI, commit)
        s.path_score, path_reasons = self._path_score(md, query)
        s.match_reasons.extend(path_reasons)

        s.symbol_score, sym_reasons = self._symbol_score(md, query)
        s.match_reasons.extend(sym_reasons)

        s.cli_score, cli_reasons = self._cli_score(md, query)
        s.match_reasons.extend(cli_reasons)

        s.commit_score, commit_reasons = self._commit_score(md, query)
        s.match_reasons.extend(commit_reasons)

        s.group_id = md.get("source_path", "")

        # 3. Structured metadata match (filters + query tokens over metadata)
        s.metadata_score, md_reasons = self._metadata_score(md, hints, query, session_filters)
        s.match_reasons.extend(md_reasons)

        # 4. Textual / semantic match
        s.text_score, txt_reasons = self._text_score(mem, query_tokens, query_vec)
        s.match_reasons.extend(txt_reasons)

        # 5. Relations
        s.relation_score, rel_reasons = self._relation_score(mem)
        s.match_reasons.extend(rel_reasons)

        # 6. Temporal / validity
        s.temporal_score, t_reasons = self._temporal_score(mem, md)
        s.match_reasons.extend(t_reasons)

        # 7. Final weighted sum (R4.1: includes symbolic channels)
        s.final_score = (
            s.identifier_score * cfg.identifier_weight
            + s.metadata_score * cfg.metadata_weight
            + s.text_score * cfg.text_weight
            + s.relation_score * cfg.relation_weight
            + s.temporal_score * cfg.temporal_weight
            + s.path_score * cfg.path_weight
            + s.symbol_score * cfg.symbol_weight
            + s.cli_score * cfg.cli_weight
            + s.commit_score * cfg.commit_weight
        )

        # Non-textual signal floor: if there is no signal at all, drop it.
        if (s.identifier_score == 0.0 and s.metadata_score == 0.0
                and s.text_score == 0.0 and s.path_score == 0.0
                and s.symbol_score == 0.0 and s.cli_score == 0.0
                and s.commit_score == 0.0):
            s.final_score = 0.0

        # Stale penalties (applied to final_score so they can drop a candidate)
        status_val = mem.status.value if hasattr(mem.status, "value") else str(mem.status)
        if status_val in (EpistemicStatus.OBSOLETE.value, EpistemicStatus.SUPERSEDED.value):
            s.final_score -= cfg.obsolete_penalty if status_val == EpistemicStatus.OBSOLETE.value else cfg.superseded_penalty
            s.match_reasons.append(f"penalty: status={status_val}")

        # Hypotheses are never treated as approved decisions
        if mem.type == MemoryType.HYPOTHESIS:
            hs = getattr(mem, "hypothesis_state", None)
            if hs not in ("sustained",):
                s.final_score -= cfg.hypothesis_penalty
                s.match_reasons.append("penalty: hypothesis not sustained")

        # Temporal / active-superseded bonuses from query intent
        qlower = query.lower()
        if "atual" in qlower or "vigente" in qlower or "atualmente" in qlower:
            if hasattr(mem, "decision_status") and getattr(mem, "decision_status", None) == "active":
                s.final_score += 0.25
                s.match_reasons.append("bonus: active decision + current intent")
            elif mem.status == EpistemicStatus.SUPERSEDED:
                s.final_score -= 0.15
                s.match_reasons.append("penalty: superseded + current intent")
        if "antiga" in qlower or "antigo" in qlower or "anterior" in qlower or "antes" in qlower or "substituida" in qlower:
            if mem.status == EpistemicStatus.SUPERSEDED:
                s.final_score += 0.15
                s.match_reasons.append("bonus: superseded + historical intent")
            elif hasattr(mem, "decision_status") and getattr(mem, "decision_status", None) == "active":
                s.final_score -= 0.10
                s.match_reasons.append("penalty: active + historical intent")

        # Normalize to [0, 1]
        s.final_score = max(0.0, min(1.0, s.final_score))
        return s

    def _identifier_score(
        self, md: dict[str, Any], hints: dict[str, list[str]]
    ) -> tuple[float, bool, list[str]]:
        cfg = self.config
        reasons: list[str] = []
        best = 0.0
        exact = False
        for field in IDENTIFIER_FIELDS:
            stored = md.get(field)
            if not stored:
                continue
            norm_stored = normalize_identifier(field, str(stored))
            for raw_hint in hints.get(field, []):
                norm_hint = normalize_identifier(field, raw_hint)
                if not norm_hint:
                    continue
                if norm_stored == norm_hint:
                    best = max(best, cfg.exact_identifier_score)
                    exact = True
                    reasons.append(f"exact match: {field}={raw_hint}")
        return best, exact, reasons

    def _partial_identifier_score(
        self, md: dict[str, Any], hints: dict[str, list[str]]
    ) -> tuple[float, list[str]]:
        cfg = self.config
        reasons: list[str] = []
        best = 0.0
        for field in IDENTIFIER_FIELDS:
            stored = md.get(field)
            if not stored:
                continue
            norm_stored = normalize_identifier(field, str(stored))
            for raw_hint in hints.get(field, []):
                norm_hint = normalize_identifier(field, raw_hint)
                if not norm_hint or len(norm_hint) < cfg.min_partial_len:
                    continue
                # Safe partial: hint is a prefix or suffix of stored, or vice versa.
                if norm_stored.startswith(norm_hint) or norm_hint.startswith(norm_stored) \
                        or norm_stored.endswith(norm_hint) or norm_hint.endswith(norm_stored):
                    # Scale by overlap ratio to avoid trivial 4-char hits matching everything.
                    overlap = min(len(norm_hint), len(norm_stored))
                    ratio = overlap / max(len(norm_hint), len(norm_stored))
                    score = cfg.partial_identifier_score * ratio
                    if score > best:
                        best = score
                        reasons.append(f"partial match: {field} (hint={raw_hint}, stored={stored})")
        return best, reasons

    # ------------------------------------------------------------------
    # R4.1: Symbolic scoring methods
    # ------------------------------------------------------------------

    def _path_score(
        self, md: dict[str, Any], query: str
    ) -> tuple[float, list[str]]:
        """Score based on file path matching (exact, partial, basename)."""
        from mec_lab.ingestion.symbol_normalize import normalize_path_symbol, paths_symbol_match
        cfg = self.config
        reasons: list[str] = []
        best = 0.0

        stored_path = md.get("source_path", "")
        if not stored_path:
            return 0.0, []

        # Extract path-like tokens from the query
        import re
        path_patterns = [
            re.compile(r'([A-Za-z]:[\\/][^ \t]+|/[A-Za-z][^ \t]+|[\w\-./]+\.[a-z]{1,6})'),
        ]
        for pat in path_patterns:
            for match in pat.findall(query):
                if paths_symbol_match(match, stored_path):
                    # Check if it's an exact match
                    norm_q = normalize_path_symbol(match)
                    norm_s = normalize_path_symbol(stored_path)
                    if norm_q == norm_s:
                        best = max(best, cfg.path_exact_score)
                        reasons.append(f"exact path match: {match}")
                    else:
                        best = max(best, cfg.path_partial_score)
                        reasons.append(f"partial path match: {match} ~ {stored_path}")

        return best, reasons

    def _symbol_score(
        self, md: dict[str, Any], query: str
    ) -> tuple[float, list[str]]:
        """Score based on software symbol matching (class, function, module name)."""
        from mec_lab.ingestion.symbol_normalize import normalize_symbol
        cfg = self.config
        reasons: list[str] = []
        best = 0.0

        # Get the stored symbol name
        stored_name = md.get("qualified_name", "") or md.get("source_heading", "")
        if not stored_name:
            return 0.0, []

        # Simple name: last component of qualified name
        simple_name = stored_name.rsplit(".", 1)[-1] if "." in stored_name else stored_name
        symbol_kind = md.get("symbol_kind", "") or md.get("entity_type", "")

        # Extract candidate symbols from query using regex
        import re
        # Match PascalCase, camelCase, snake_case identifiers of 3+ chars
        candidates = set()
        # PascalCase / camelCase
        for m in re.findall(r'\b([A-Z][a-zA-Z0-9]{2,})\b', query):
            candidates.add(m)
        # snake_case
        for m in re.findall(r'\b([a-z][a-z0-9_]{2,})\b', query):
            candidates.add(m)
        # Dotted module paths
        for m in re.findall(r'\b([a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+)\b', query):
            candidates.add(m)

        # Get normalized forms of the stored symbol
        stored_forms = set(normalize_symbol(stored_name))
        simple_forms = set(normalize_symbol(simple_name))

        for candidate in candidates:
            cand_forms = set(normalize_symbol(candidate))
            # Check exact match against simple name
            if cand_forms & simple_forms:
                # Only boost if it looks like a real symbol match (not a stopword)
                if len(candidate) >= 3 and candidate.lower() not in {
                    "the", "for", "and", "but", "not", "all", "any", "can",
                    "has", "her", "his", "its", "may", "our", "she", "the",
                }:
                    best = max(best, cfg.symbol_exact_score)
                    reasons.append(f"exact symbol match: {candidate} ~ {simple_name} ({symbol_kind})")
            elif cand_forms & stored_forms:
                best = max(best, cfg.symbol_partial_score)
                reasons.append(f"partial symbol match: {candidate} ~ {stored_name}")

        return best, reasons

    def _cli_score(
        self, md: dict[str, Any], query: str
    ) -> tuple[float, list[str]]:
        """Score based on CLI command and option matching."""
        from mec_lab.ingestion.symbol_normalize import normalize_cli_option, cli_options_match
        cfg = self.config
        reasons: list[str] = []
        best = 0.0

        cli_command = md.get("cli_command", "")
        cli_option = md.get("cli_option", "")

        if not cli_command and not cli_option:
            return 0.0, []

        import re
        # Extract CLI-looking tokens from query: --option, command-name
        cli_tokens = re.findall(r'--?[a-z][\w-]+', query, re.IGNORECASE)
        # Also extract bare words that could be command names
        words = re.findall(r'\b([a-z][a-z-]{2,})\b', query, re.IGNORECASE)

        for token in cli_tokens:
            token_clean = token.lstrip("-")
            if cli_option:
                if cli_options_match(token, cli_option):
                    best = max(best, cfg.cli_exact_score)
                    reasons.append(f"exact CLI option match: {token} ~ {cli_option}")
            if cli_command:
                norm_token = token_clean.replace("-", "_").lower()
                norm_cmd = cli_command.replace("-", "_").lower()
                if norm_token == norm_cmd:
                    best = max(best, cfg.cli_exact_score)
                    reasons.append(f"exact CLI command match: {token} ~ {cli_command}")

        for word in words:
            norm_word = word.lower().replace("-", "_")
            if cli_command:
                norm_cmd = cli_command.lower().replace("-", "_")
                if norm_word == norm_cmd:
                    best = max(best, cfg.cli_exact_score)
                    reasons.append(f"CLI command match: {word} ~ {cli_command}")
                elif norm_word in norm_cmd or norm_cmd in norm_word:
                    best = max(best, cfg.cli_partial_score)
                    reasons.append(f"partial CLI command match: {word} ~ {cli_command}")

        return best, reasons

    def _commit_score(
        self, md: dict[str, Any], query: str
    ) -> tuple[float, list[str]]:
        """Score based on commit SHA matching."""
        from mec_lab.ingestion.symbol_normalize import extract_commit_prefix, commit_prefix_matches
        cfg = self.config
        reasons: list[str] = []
        best = 0.0

        stored_sha = md.get("commit_sha", "")
        if not stored_sha or len(stored_sha) < 7:
            return 0.0, []

        # Extract commit prefix from query
        prefix = extract_commit_prefix(query)
        if not prefix:
            return 0.0, []

        if commit_prefix_matches(prefix, stored_sha):
            if len(prefix) >= len(stored_sha):
                best = cfg.commit_exact_score
                reasons.append(f"exact commit SHA match: {prefix}")
            else:
                best = cfg.commit_prefix_score
                reasons.append(f"commit prefix match: {prefix} ~ {stored_sha[:7]}")

        return best, reasons

    def _metadata_score(
        self,
        md: dict[str, Any],
        hints: dict[str, list[str]],
        query: str,
        session_filters: dict[str, Any],
    ) -> tuple[float, list[str]]:
        cfg = self.config
        reasons: list[str] = []
        score = 0.0
        matched_fields: set[str] = set()

        # Metadata fields we consider for structural matching. project_id is
        # handled by the explicit project filter, so we skip it here.
        meta_fields = (
            "environment", "responsible", "manufacturer", "device_model",
            "version", "status", "repository", "branch", "class_name",
            "function_name", "organization_id", "client_id", "entity_id",
        )
        qlower = query.lower()

        for f in meta_fields:
            stored = md.get(f)
            if stored is None or stored == "":
                continue
            stored_s = str(stored).lower()
            # Avoid matching trivial substrings (single digits, 2-letter codes)
            if len(stored_s) < 3:
                continue
            # Whole-word-ish containment to avoid substring false positives.
            if f" {stored_s} " in f" {qlower} " or stored_s in qlower.split():
                if f not in matched_fields:
                    score += cfg.per_metadata_field_score
                    matched_fields.add(f)
                    reasons.append(f"metadata match: {f}={stored}")
            # Match against session clarification filters (exact or normalized)
            sv = session_filters.get(f)
            if sv is not None and sv != "":
                if normalize_identifier(f, str(sv)) == normalize_identifier(f, str(stored)) \
                        or str(sv).lower() == stored_s:
                    if f not in matched_fields:
                        score += cfg.per_metadata_field_score
                        matched_fields.add(f)
                        reasons.append(f"session filter match: {f}={stored}")

        # Project name text match (when no explicit project_id was supplied)
        if "project_id" not in session_filters:
            pid = md.get("project_id")
            if pid:
                proj = self.storage.get_project(str(pid))
                if proj and proj.name and proj.name.lower() in qlower:
                    if "project_id" not in matched_fields:
                        score += cfg.per_metadata_field_score
                        matched_fields.add("project_id")
                        reasons.append(f"metadata match: project={proj.name}")

        score = min(score, cfg.metadata_cap)
        return score, reasons

    def _text_score(
        self,
        mem: AnyMemory,
        query_tokens: set[str],
        query_vec: list[float],
    ) -> tuple[float, list[str]]:
        reasons: list[str] = []
        content_tokens = token_set(mem.content, stem=True)
        lex = 0.0
        if query_tokens and content_tokens:
            overlap = query_tokens & content_tokens
            union = query_tokens | content_tokens
            lex = len(overlap) / len(union) if union else 0.0
            if overlap:
                reasons.append(f"lexical overlap: {len(overlap)} tokens")

        sem = 0.0
        if query_vec and self.semantic.is_available():
            mem_vecs = self.semantic.embed([mem.content])
            if mem_vecs and mem_vecs[0]:
                sem = _cosine(query_vec, mem_vecs[0])
                if sem > 0.15:
                    reasons.append(f"semantic similarity: {sem:.3f}")

        score = max(lex, sem)
        return score, reasons

    def _relation_score(self, mem: AnyMemory) -> tuple[float, list[str]]:
        cfg = self.config
        rels = self.storage.get_relations_for(mem.id)
        if not rels:
            return 0.0, []
        # SUPERSEDES relations are especially informative
        supersedes_count = sum(
            1 for r in rels if r.relation_type == RelationType.SUPERSEDES
        )
        score = min(len(rels) * cfg.per_relation_score, cfg.relation_cap)
        reasons = [f"relations: {len(rels)}"]
        if supersedes_count:
            reasons.append(f"supersedes relation: {supersedes_count}")
        return score, reasons

    def _temporal_score(
        self, mem: AnyMemory, md: dict[str, Any]
    ) -> tuple[float, list[str]]:
        cfg = self.config
        reasons: list[str] = []
        now = datetime.now(UTC)
        vf = md.get("valid_from")
        vu = md.get("valid_to")
        score = 0.0
        if vf and vu:
            if vf <= now <= vu:
                score += cfg.temporal_valid_bonus
                reasons.append("temporal: currently valid")
            elif vu < now:
                score -= cfg.temporal_expired_penalty
                reasons.append("temporal: expired")
        elif vf and vf <= now:
            score += cfg.temporal_valid_bonus * 0.5
            reasons.append("temporal: valid_from set, no end")
        return score, reasons

    # ------------------------------------------------------------------
    # R4.1: Entity grouping
    # ------------------------------------------------------------------

    def _group_entities(self, scored: list[StructuredScore]) -> list[StructuredScore]:
        """Group candidates from the same source file into a single representative.

        Multiple segments of the same file (e.g. module, its classes, its functions)
        should not cause false ambiguity. The highest-scoring segment represents
        the group, and others are absorbed.

        Only groups by ``source_path`` metadata — truly different files remain
        separate candidates.
        """
        if not scored:
            return scored

        groups: dict[str, list[StructuredScore]] = {}
        standalone: list[StructuredScore] = []

        for s in scored:
            mem = self.storage.get_memory(s.memory_id)
            if mem is None:
                standalone.append(s)
                continue
            md = candidate_metadata(mem)
            source_path = md.get("source_path", "")
            if source_path:
                groups.setdefault(source_path, []).append(s)
            else:
                standalone.append(s)

        result: list[StructuredScore] = []
        for path, segs in groups.items():
            if len(segs) == 1:
                result.extend(segs)
            else:
                # Keep the highest-scoring segment as representative
                segs.sort(key=lambda s: s.final_score, reverse=True)
                rep = segs[0]
                rep.entity_group_score = self.config.entity_group_weight
                if not any("entity group representative" in r for r in rep.match_reasons):
                    rep.match_reasons.append(
                        f"entity group representative: {path} ({len(segs)} segments)"
                    )
                result.append(rep)

        result.extend(standalone)
        # Re-sort by final score (entity_group_score may have changed order)
        result.sort(key=lambda s: (s.final_score, s.identifier_score), reverse=True)
        return result

    # ------------------------------------------------------------------
    # State classification
    # ------------------------------------------------------------------

    def _classify_state(
        self, scored: list[StructuredScore], session_filters: dict[str, Any]
    ) -> RetrievalState:
        cfg = self.config
        if not scored:
            if self.clarifications_used >= cfg.max_clarifications:
                return RetrievalState.MEMORY_NOT_FOUND
            return RetrievalState.MEMORY_NOT_FOUND

        best = scored[0]
        second = scored[1] if len(scored) > 1 else None

        # Exact identifier hits always confirm (they are by definition unambiguous)
        if best.is_exact_identifier and best.final_score >= cfg.confirmed_min_score:
            # Unless another exact identifier candidate ties — that's ambiguous
            if second and second.is_exact_identifier and second.final_score >= cfg.confirmed_min_score:
                # Two different exact hits -> genuinely ambiguous
                return RetrievalState.AMBIGUOUS_CANDIDATES
            return RetrievalState.MEMORY_CONFIRMED

        # Strong single candidate, clearly above the rest
        if best.final_score >= cfg.confirmed_min_score:
            if second is None or (best.final_score - second.final_score) >= cfg.confirmed_margin:
                return RetrievalState.MEMORY_CONFIRMED
            # Close contenders => ambiguous
            if second.final_score >= cfg.ambiguous_min_score:
                return RetrievalState.AMBIGUOUS_CANDIDATES
            # Best is strong, second is weak — confirm
            return RetrievalState.MEMORY_CONFIRMED

        # Ambiguous band: two or three candidates close together
        if best.final_score >= cfg.ambiguous_min_score and second is not None \
                and second.final_score >= cfg.ambiguous_min_score:
            return RetrievalState.AMBIGUOUS_CANDIDATES

        # Below the not-found floor: nothing
        if best.final_score < cfg.not_found_floor:
            return RetrievalState.MEMORY_NOT_FOUND

        # Between not_found_floor and confirmed_min: try clarification if budget allows
        if self.clarifications_used >= cfg.max_clarifications:
            return RetrievalState.MEMORY_NOT_FOUND

        if best.final_score >= cfg.clarification_min_score:
            # Can we find a discriminatory dimension?
            dim, _ = self._build_clarification("", scored, session_filters)
            if dim is not None:
                return RetrievalState.CLARIFICATION_REQUIRED
        return RetrievalState.MEMORY_NOT_FOUND

    # ------------------------------------------------------------------
    # Clarification generation
    # ------------------------------------------------------------------

    # Priority order of discriminatory dimensions. Templates use {hint} for any
    # value the user previously gave. Deterministic — no LLM involved.
    _CLARIFICATION_TEMPLATES: dict[str, str] = {
        "project_id": "Você lembra em qual projeto isso aconteceu?",
        "organization_id": "Você lembra a qual empresa ou organização isso se refere?",
        "client_id": "Você lembra de qual cliente se trata?",
        "entity_id": "Você lembra de qual entidade ou equipamento se trata?",
        "environment": "Era no ambiente de testes ou produção?",
        "responsible": "Você lembra quem era o responsável?",
        "manufacturer": "Você lembra o fabricante do equipamento?",
        "device_model": "Você lembra o modelo do equipamento?",
        "serial_number": "Você tem parte do número de série?",
        "mac_address": "Você lembra do endereço MAC do equipamento?",
        "protocol_number": "Você lembra do número do protocolo?",
        "ticket_number": "Você lembra do número do chamado?",
        "file_path": "Você lembra do caminho da pasta ou arquivo?",
        "file_name": "Você lembra do nome do arquivo?",
        "repository": "Você lembra do repositório onde isso estava?",
        "branch": "Você lembra do nome da branch?",
        "commit_sha": "Você lembra do commit SHA?",
        "valid_from": "Você lembra aproximadamente de quando isso aconteceu?",
        "memory_type": "Era uma decisão aprovada, um fato verificado ou uma hipótese?",
        "status": "Era uma decisão vigente ou já substituída?",
    }

    _DIMENSION_PRIORITY: tuple[str, ...] = (
        "project_id", "manufacturer", "device_model", "serial_number",
        "mac_address", "protocol_number", "ticket_number", "file_path",
        "file_name", "environment", "responsible", "repository", "branch",
        "commit_sha", "valid_from", "memory_type", "status",
        "organization_id", "client_id", "entity_id",
    )

    def _build_clarification(
        self,
        query: str,
        scored: list[StructuredScore],
        session_filters: dict[str, Any],
    ) -> tuple[str | None, str | None]:
        """Pick the best discriminatory dimension and render its template.

        The dimension is the first one (by priority) where the top candidates
        actually differ in value and the user has not already supplied it.
        """
        if not scored:
            return None, None
        top = scored[:3]
        mems: list[AnyMemory] = []
        for s in top:
            m = self.storage.get_memory(s.memory_id)
            if m is not None:
                mems.append(m)
        if len(mems) < 2:
            return None, None
        mds = [candidate_metadata(m) for m in mems]

        for dim in self._DIMENSION_PRIORITY:
            if dim in session_filters:
                continue
            values = []
            for md in mds:
                v = md.get(dim)
                if dim == "memory_type":
                    v = md.get("type") or self.storage.get_memory(top[0].memory_id).type  # type: ignore[union-attr]
                if v is None or v == "":
                    values.append(None)
                else:
                    values.append(str(v).lower())
            non_null = [v for v in values if v is not None]
            if len(non_null) >= 2 and len(set(non_null)) >= 2:
                template = self._CLARIFICATION_TEMPLATES.get(dim)
                if template:
                    return dim, template

        # Fall through — no discriminatory dimension available
        return None, None

    # ------------------------------------------------------------------
    # Related memories
    # ------------------------------------------------------------------

    def _related_for(self, mem: AnyMemory, limit: int = 2) -> list[AnyMemory]:
        rels = self.storage.get_relations_for(mem.id)
        related: list[AnyMemory] = []
        seen = {mem.id}
        for r in rels:
            other_id = r.target_id if r.source_id == mem.id else r.source_id
            if other_id in seen:
                continue
            other = self.storage.get_memory(other_id)
            if other is not None:
                related.append(other)
                seen.add(other_id)
            if len(related) >= limit:
                break
        return related

    # ------------------------------------------------------------------
    # Explanation
    # ------------------------------------------------------------------

    def _explain(self, result: AssistedRetrievalResult) -> str:
        lines: list[str] = []
        lines.append(f"State: {result.state.value}")
        lines.append(f"Query: {result.query}")
        lines.append(f"Clarifications used: {result.clarifications_used}/{self.config.max_clarifications}")
        for s in result.scores[:5]:
            mem = self.storage.get_memory(s.memory_id)
            snippet = (mem.content[:80] if mem else "(missing)")
            lines.append(
                f"  [{s.final_score:.3f}] {s.memory_id} "
                f"({mem.type if mem else '?'}): {snippet}"
            )
            lines.append(f"     components: {s.components()}")
            if s.match_reasons:
                lines.append(f"     reasons: {'; '.join(s.match_reasons[:5])}")
        if result.state == RetrievalState.CLARIFICATION_REQUIRED and result.clarification_question:
            lines.append(f"Clarification ({result.clarification_dimension}): {result.clarification_question}")
        if result.state == RetrievalState.MEMORY_NOT_FOUND:
            lines.append(
                "Nenhuma lembrança confiável foi localizada com os parâmetros e "
                "esclarecimentos fornecidos. Resultados aproximados não devem "
                "ser usados como memória confirmada."
            )
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Clarification cycle driver
# ---------------------------------------------------------------------------


@dataclass
class ClarificationTurn:
    """One turn in a clarification cycle."""

    query: str
    answer: str | None
    dimension: str | None
    question: str | None
    result: AssistedRetrievalResult


class ClarificationCycle:
    """Drives the up-to-three-question clarification cycle.

    Usage::

        cycle = ClarificationCycle(storage, config, semantic)
        turn = cycle.start(query)
        while turn.result.state == RetrievalState.CLARIFICATION_REQUIRED:
            answer = ask_user(turn.result.clarification_question)
            turn = cycle.answer(answer)
        final = turn.result

    Answers are never persisted; they only become session filters. Only the
    caller can, after confirmation, persist a derived association via
    :func:`save_confirmed_association`.
    """

    def __init__(
        self,
        storage: Storage,
        config: AssistedRetrievalConfig | None = None,
        semantic: TfidfAdapter | None = None,
    ) -> None:
        self.storage = storage
        self.config = config or AssistedRetrievalConfig()
        if semantic is not None:
            self.semantic = semantic
        else:
            from mec_lab.retrieval import TfidfAdapter  # lazy — avoids circular import
            self.semantic = TfidfAdapter(storage)
        if not self.semantic.is_available():
            self.semantic.build(storage)
        self._session_filters: dict[str, Any] = {}
        self._query: str = ""
        self._project_id: str | None = None
        self._used = 0
        self._history: list[ClarificationTurn] = []
        self._user_gave_up = False

    def start(
        self, query: str, project_id: str | None = None
    ) -> ClarificationTurn:
        self._query = query
        self._project_id = project_id
        self._session_filters = {}
        self._used = 0
        self._history = []
        return self._run_turn(None)

    def answer(self, answer: str | None) -> ClarificationTurn:
        """Process a clarification answer and re-run retrieval."""
        if not self._history:
            raise RuntimeError("answer() called before start()")
        last = self._history[-1]
        dim = last.result.clarification_dimension
        if answer is None or answer.strip().lower() in ("nao", "não", "no", "n", "nao sei", "não sei", ""):
            self._user_gave_up = True
            # Re-run without new filter -> classify as NOT_FOUND
            return self._run_turn(answer, dim=dim)
        # Record filter
        if dim is not None:
            existing = self._session_filters.get(dim)
            if existing is None:
                self._session_filters[dim] = answer.strip()
            else:
                # Combine: keep only the latest answer (clarification overwrites)
                self._session_filters[dim] = answer.strip()
        return self._run_turn(answer, dim=dim)

    def history(self) -> list[ClarificationTurn]:
        return list(self._history)

    def session_filters(self) -> dict[str, Any]:
        return dict(self._session_filters)

    def _run_turn(
        self, answer: str | None, dim: str | None = None
    ) -> ClarificationTurn:
        retriever = AssistedRetriever(
            self.storage, self.config, self.semantic, clarifications_used=self._used
        )
        # If the user gave up, force NOT_FOUND by exhausting the budget
        if self._user_gave_up:
            retriever.clarifications_used = self.config.max_clarifications
        result = retriever.retrieve(
            self._query, project_id=self._project_id,
            session_filters=self._session_filters,
        )
        turn = ClarificationTurn(
            query=self._query, answer=answer, dimension=dim,
            question=result.clarification_question, result=result,
        )
        self._history.append(turn)
        # Only count a clarification that was actually asked and answered
        if answer is not None and dim is not None:
            self._used += 1
        elif result.state == RetrievalState.CLARIFICATION_REQUIRED and self._used == 0:
            # The initial CLARIFICATION_REQUIRED counts toward the budget only
            # when we actually answer it; this is tracked in answer().
            pass
        return turn


# ---------------------------------------------------------------------------
# Confirmed association persistence (opt-in, explicit)
# ---------------------------------------------------------------------------


def save_confirmed_association(
    storage: Storage,
    user_id: str,
    query: str,
    confirmed_memory_id: str,
    session_filters: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> MemoryRelation:
    """Persist an explicit user-confirmed association.

    This is the only path through which a clarification outcome can become a
    permanent record. It is always tagged as user-confirmed and never created
    automatically by the retrieval pipeline.

    To satisfy the FK constraint on the relations table, a lightweight anchor
    memory is first created for the user id if one does not already exist.
    """
    from mec_lab.domain.models import Fact
    if storage.get_memory(user_id) is None:
        storage.save_memory(
            Fact(id=user_id, content=f"user_confirmed_association:{user_id}", project_id="")
        )
    rel = MemoryRelation(
        source_id=user_id,
        target_id=confirmed_memory_id,
        relation_type=RelationType.REFERENCES,
        metadata={
            "kind": "user_confirmed_association",
            "query": query,
            "session_filters": dict(session_filters or {}),
            **(metadata or {}),
        },
    )
    storage.save_relation(rel)
    return rel


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)