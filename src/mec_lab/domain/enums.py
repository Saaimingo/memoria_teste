"""MEC Lab — Domain enums and constants."""

from enum import Enum


class MemoryType(str, Enum):
    """Top-level memory type discriminator."""

    FACT = "fact"
    DECISION = "decision"
    HYPOTHESIS = "hypothesis"
    EVIDENCE = "evidence"
    LEARNING = "learning"
    EPISODE = "episode"
    CHECKPOINT = "checkpoint"
    DOCUMENT = "document"


class EpistemicStatus(str, Enum):
    """Epistemic state of a memory record."""

    REGISTERED = "registered"
    UNVERIFIED = "unverified"
    PARTIALLY_SUPPORTED = "partially_supported"
    VERIFIED = "verified"
    CONTRADICTED = "contradicted"
    OBSOLETE = "obsolete"
    SUPERSEDED = "superseded"
    INCONCLUSIVE = "inconclusive"


class RelationType(str, Enum):
    """Typed relationships between memory records."""

    DERIVED_FROM = "derived_from"
    SUPPORTED_BY = "supported_by"
    CONTRADICTED_BY = "contradicted_by"
    CAUSED_BY = "caused_by"
    RESOLVED_BY = "resolved_by"
    PART_OF = "part_of"
    OCCURRED_DURING = "occurred_during"
    SUPERSEDES = "supersedes"
    SIMILAR_TO = "similar_to"
    FAILED_UNDER = "failed_under"
    WORKS_UNDER = "works_under"
    SUMMARIZES = "summarizes"
    REFERENCES = "references"


class EvidenceType(str, Enum):
    """Kind of evidence artefact."""

    LOG = "log"
    TEST_RESULT = "test_result"
    COMMIT = "commit"
    BENCHMARK = "benchmark"
    OBSERVATION = "observation"
    SCREENSHOT = "screenshot"
    METRIC = "metric"
    ARTIFACT = "artifact"


class LearningState(str, Enum):
    """Maturity of a learning."""

    OBSERVED = "observed"
    RECURRENT = "recurrent"
    PROMOTED = "promoted"
    NORMATIVE = "normative"


class DecisionStatus(str, Enum):
    """Validity lifecycle of a decision."""

    ACTIVE = "active"
    SUPERSEDED = "superseded"
    REVOKED = "revoked"
    EXPIRED = "expired"


class HypothesisState(str, Enum):
    """Experimental state of a hypothesis."""

    PROPOSED = "proposed"
    UNDER_TEST = "under_test"
    SUSTAINED = "sustained"
    REJECTED = "rejected"
    INCONCLUSIVE = "inconclusive"


class FactStatus(str, Enum):
    """Temporal and epistemic validity of a fact."""

    CURRENT = "current"
    OBSOLETE = "obsolete"
    CONTRADICTED = "contradicted"
    SUPERSEDED = "superseded"


class EpisodePhase(str, Enum):
    """Phase of a causal episode."""

    INITIAL_STATE = "initial_state"
    GOAL = "goal"
    PLAN = "plan"
    ACTIONS = "actions"
    OBSERVATIONS = "observations"
    DEVIATIONS = "deviations"
    CORRECTIONS = "corrections"
    RESULT = "result"
    CONSEQUENCES = "consequences"
    LEARNING = "learning"


class Confidence(str, Enum):
    """Ordinal confidence scale."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNCERTAIN = "uncertain"
