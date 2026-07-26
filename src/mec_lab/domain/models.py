"""MEC Lab — Domain models (Pydantic v2).

Each memory type preserves the fields defined in the MEC experimental specification.
The common envelope provides id, type, content, project_id, source_refs, timestamps,
status, confidence, entities, relations, version, and lineage tracking.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from mec_lab.domain.enums import (
    Confidence,
    DecisionStatus,
    EpistemicStatus,
    EpisodePhase,
    EvidenceType,
    FactStatus,
    HypothesisState,
    LearningState,
    MemoryType,
    RelationType,
)


# ---------------------------------------------------------------------------
# Common envelope
# ---------------------------------------------------------------------------


class SourceRef(BaseModel):
    """A reference to an external or internal source."""

    source_id: str
    source_type: str = "manual"
    description: str | None = None
    uri: str | None = None


class EntityRef(BaseModel):
    """Named entity extracted or tagged."""

    name: str
    entity_type: str | None = None  # e.g. "person", "tool", "concept"


class MemoryEnvelope(BaseModel):
    """Common fields for every memory record."""

    model_config = ConfigDict(frozen=False, use_enum_values=True)

    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    type: MemoryType
    content: str
    project_id: str
    source_refs: list[SourceRef] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    status: EpistemicStatus = EpistemicStatus.REGISTERED
    confidence: Confidence = Confidence.MEDIUM
    entities: list[EntityRef] = Field(default_factory=list)
    relations: list[str] = Field(default_factory=list)  # relation ids for quick lookup
    version: int = 1
    supersedes: str | None = None  # id of record this one supersedes
    superseded_by: str | None = None  # id of record that supersedes this one
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Specialised models
# ---------------------------------------------------------------------------


class Fact(MemoryEnvelope):
    """Affirmation valid within a scope and time, backed by source or observation."""

    type: Literal[MemoryType.FACT] = MemoryType.FACT  # type: ignore[assignment]
    fact_status: FactStatus = FactStatus.CURRENT
    assertion: str = ""
    scope: str = ""
    temporal_context: str = ""
    evidence_ids: list[str] = Field(default_factory=list)
    contradiction_ids: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _sync_content(self) -> Fact:
        if not self.content and self.assertion:
            self.content = self.assertion
        return self


class Decision(MemoryEnvelope):
    """Authorised choice among alternatives."""

    type: Literal[MemoryType.DECISION] = MemoryType.DECISION  # type: ignore[assignment]
    decision_status: DecisionStatus = DecisionStatus.ACTIVE
    authority: str = ""
    alternatives: list[str] = Field(default_factory=list)
    justification: str = ""
    expected_consequences: str = ""
    revocation_criteria: str = ""
    superseded_decision_id: str | None = None

    @model_validator(mode="after")
    def _sync_content(self) -> Decision:
        if not self.content and self.justification:
            self.content = self.justification
        return self


class Hypothesis(MemoryEnvelope):
    """Explanation or proposal not yet proven."""

    type: Literal[MemoryType.HYPOTHESIS] = MemoryType.HYPOTHESIS  # type: ignore[assignment]
    hypothesis_state: HypothesisState = HypothesisState.PROPOSED
    origin_observation: str = ""
    prediction: str = ""
    test_condition: str = ""
    confirmation_criterion: str = ""
    rejection_criterion: str = ""
    risk: str = ""

    @model_validator(mode="after")
    def _sync_content(self) -> Hypothesis:
        if not self.content and self.prediction:
            self.content = self.prediction
        return self


class Evidence(MemoryEnvelope):
    """Artefact or observation that supports or contradicts a claim."""

    type: Literal[MemoryType.EVIDENCE] = MemoryType.EVIDENCE  # type: ignore[assignment]
    evidence_type: EvidenceType = EvidenceType.OBSERVATION
    location: str = ""
    producer: str = ""
    environment: str = ""
    timestamp: datetime | None = None
    artifact_version: str = ""
    integrity_hash: str = ""
    supported_claims: list[str] = Field(default_factory=list)
    contradicted_claims: list[str] = Field(default_factory=list)
    limitations: str = ""

    @model_validator(mode="after")
    def _sync_content(self) -> Evidence:
        if not self.content:
            parts = [p for p in [self.location, self.limitations] if p]
            self.content = " | ".join(parts) if parts else ""
        return self


class Learning(MemoryEnvelope):
    """Operational conclusion derived from episodes and evidence."""

    type: Literal[MemoryType.LEARNING] = MemoryType.LEARNING  # type: ignore[assignment]
    learning_state: LearningState = LearningState.OBSERVED
    origin_episode_ids: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    works_under_conditions: str = ""
    fails_under_conditions: str = ""
    generalization_degree: str = ""


class Episode(MemoryEnvelope):
    """Causal container of a delimited operational experience."""

    type: Literal[MemoryType.EPISODE] = MemoryType.EPISODE  # type: ignore[assignment]
    initial_state: str = ""
    goal: str = ""
    plan: str = ""
    actions: list[str] = Field(default_factory=list)
    observations: list[str] = Field(default_factory=list)
    deviations: list[str] = Field(default_factory=list)
    corrections: list[str] = Field(default_factory=list)
    result: str = ""
    consequences: str = ""
    learning_summary: str = ""

    def causal_chain(self) -> list[tuple[EpisodePhase, str]]:
        """Return the causal chain as ordered (phase, text) pairs."""
        mapping: list[tuple[EpisodePhase, str]] = [
            (EpisodePhase.INITIAL_STATE, self.initial_state),
            (EpisodePhase.GOAL, self.goal),
            (EpisodePhase.PLAN, self.plan),
            (EpisodePhase.ACTIONS, "\n".join(self.actions)),
            (EpisodePhase.OBSERVATIONS, "\n".join(self.observations)),
            (EpisodePhase.DEVIATIONS, "\n".join(self.deviations)),
            (EpisodePhase.CORRECTIONS, "\n".join(self.corrections)),
            (EpisodePhase.RESULT, self.result),
            (EpisodePhase.CONSEQUENCES, self.consequences),
            (EpisodePhase.LEARNING, self.learning_summary),
        ]
        return [(phase, text) for phase, text in mapping if text.strip()]


class Checkpoint(MemoryEnvelope):
    """Verifiable snapshot of project state at a point in time."""

    type: Literal[MemoryType.CHECKPOINT] = MemoryType.CHECKPOINT  # type: ignore[assignment]
    current_state: str = ""
    last_completed_action: str = ""
    active_decisions: list[str] = Field(default_factory=list)
    pending_items: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    artifacts_and_versions: dict[str, str] = Field(default_factory=dict)
    next_allowed_action: str = ""
    known_risks: list[str] = Field(default_factory=list)
    deep_dive_refs: list[str] = Field(default_factory=list)


class DocumentRecord(MemoryEnvelope):
    """Composite artefact organising multiple records."""

    type: Literal[MemoryType.DOCUMENT] = MemoryType.DOCUMENT  # type: ignore[assignment]
    document_type: str = "specification"  # specification, report, log, code, conversation
    sections: list[str] = Field(default_factory=list)
    constituent_ids: list[str] = Field(default_factory=list)
    is_normative: bool = False


class MemoryRelation(BaseModel):
    """A typed, directed relation between two memory records."""

    model_config = ConfigDict(frozen=True, use_enum_values=True)

    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    source_id: str
    target_id: str
    relation_type: RelationType
    confidence: Confidence = Confidence.MEDIUM
    evidence_ids: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = Field(default_factory=dict)


class ProjectRecord(BaseModel):
    """Scope / project — groups memory records under a common namespace."""

    model_config = ConfigDict(frozen=False)

    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str
    description: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Union type for storage
# ---------------------------------------------------------------------------

AnyMemory = Fact | Decision | Hypothesis | Evidence | Learning | Episode | Checkpoint | DocumentRecord


_MEMORY_TYPE_MAP: dict[MemoryType, type[AnyMemory]] = {
    MemoryType.FACT: Fact,
    MemoryType.DECISION: Decision,
    MemoryType.HYPOTHESIS: Hypothesis,
    MemoryType.EVIDENCE: Evidence,
    MemoryType.LEARNING: Learning,
    MemoryType.EPISODE: Episode,
    MemoryType.CHECKPOINT: Checkpoint,
    MemoryType.DOCUMENT: DocumentRecord,
}


def memory_class_for(mtype: MemoryType) -> type[AnyMemory]:
    """Return the Pydantic model class for the given MemoryType."""
    return _MEMORY_TYPE_MAP[mtype]
