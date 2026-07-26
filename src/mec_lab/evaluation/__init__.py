"""MEC Lab — Evaluation framework.

Implements all metrics from PLANO_DE_AVALIACAO.md:
- Precision@k, Recall@k, Hit@1, Hit@3, MRR, nDCG
- Hallucination rate, inference marking accuracy
- Capsule efficiency metrics
- Ablation test runner
- Report generation
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from mec_lab.context import Capsule, CapsuleBuilder
from mec_lab.retrieval import (
    DeterministicSemanticAdapter,
    HybridRetriever,
    LexicalRetriever,
    NullSemanticAdapter,
    RetrievalConfig,
    RetrievalResult,
)
from mec_lab.storage import Storage


# ---------------------------------------------------------------------------
# Evaluation dataset types
# ---------------------------------------------------------------------------


@dataclass
class QueryCase:
    """A single evaluation query with expected answers."""

    query_id: str
    query: str
    expected_ids: list[str]  # IDs that should be retrieved
    expected_project_id: str | None = None
    distractors: list[str] = field(default_factory=list)  # IDs that should NOT appear
    relevance_grades: dict[str, float] = field(default_factory=dict)  # id -> grade for nDCG
    required_clues: list[str] = field(default_factory=list)
    expected_conflicts: list[str] = field(default_factory=list)
    expected_missing: list[str] = field(default_factory=list)


@dataclass
class EvalDataset:
    """Wrapper for an evaluation dataset."""

    name: str
    queries: list[QueryCase]
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_json(cls, path: Path) -> EvalDataset:
        data = json.loads(path.read_text(encoding="utf-8"))
        queries = [QueryCase(**q) for q in data["queries"]]
        return cls(name=data.get("name", path.stem), queries=queries, metadata=data.get("metadata", {}))


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------


@dataclass
class SingleResult:
    """Metrics for a single query."""

    query_id: str
    precision_1: float = 0.0
    precision_3: float = 0.0
    precision_5: float = 0.0
    recall_1: float = 0.0
    recall_3: float = 0.0
    recall_5: float = 0.0
    hit_1: bool = False
    hit_3: bool = False
    hit_5: bool = False
    mrr: float = 0.0
    ndcg: float = 0.0
    num_retrieved: int = 0
    relevant_retrieved: int = 0
    fake_sources: int = 0
    inferences_marked: int = 0
    conflicts_detected: int = 0


@dataclass
class AggregatedMetrics:
    """Aggregated metrics across all queries."""

    num_queries: int = 0
    precision_1: float = 0.0
    precision_3: float = 0.0
    precision_5: float = 0.0
    recall_3: float = 0.0
    recall_5: float = 0.0
    hit_1_rate: float = 0.0
    hit_3_rate: float = 0.0
    hit_5_rate: float = 0.0
    mrr: float = 0.0
    ndcg: float = 0.0
    fake_source_count: int = 0
    fake_source_rate: float = 0.0
    inference_mark_rate: float = 0.0
    conflict_detection_rate: float = 0.0
    capsule_avg_chars: int = 0
    capsule_avg_tokens: int = 0
    reduction_vs_raw: float = 0.0
    per_query: list[SingleResult] = field(default_factory=list)
    latency_ms: float = 0.0
    config: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Evaluator
# ---------------------------------------------------------------------------


class Evaluator:
    """Runs evaluation queries and computes metrics."""

    def __init__(
        self,
        storage: Storage,
        retriever: HybridRetriever | None = None,
        capsule_builder: CapsuleBuilder | None = None,
    ) -> None:
        self.storage = storage
        self.retriever = retriever or HybridRetriever(storage)
        self.capsule_builder = capsule_builder or CapsuleBuilder(storage, self.retriever)

    def evaluate(self, dataset: EvalDataset, raw_history_chars: int = 0) -> AggregatedMetrics:
        """Run all queries and return aggregated metrics."""
        import time

        t0 = time.perf_counter()
        results: list[SingleResult] = []

        for qc in dataset.queries:
            sr = self._evaluate_one(qc)
            results.append(sr)

        elapsed = (time.perf_counter() - t0) * 1000

        agg = AggregatedMetrics(
            num_queries=len(dataset.queries),
            per_query=results,
            latency_ms=elapsed,
        )

        if results:
            agg.precision_1 = sum(r.precision_1 for r in results) / len(results)
            agg.precision_3 = sum(r.precision_3 for r in results) / len(results)
            agg.precision_5 = sum(r.precision_5 for r in results) / len(results)
            agg.recall_3 = sum(r.recall_3 for r in results) / len(results)
            agg.recall_5 = sum(r.recall_5 for r in results) / len(results)
            agg.hit_1_rate = sum(1 for r in results if r.hit_1) / len(results)
            agg.hit_3_rate = sum(1 for r in results if r.hit_3) / len(results)
            agg.hit_5_rate = sum(1 for r in results if r.hit_5) / len(results)
            agg.mrr = sum(r.mrr for r in results) / len(results)
            agg.ndcg = sum(r.ndcg for r in results) / len(results)
            agg.fake_source_count = sum(r.fake_sources for r in results)
            total_retrieved = sum(r.num_retrieved for r in results)
            agg.fake_source_rate = agg.fake_source_count / max(1, total_retrieved)
            total_inferences = sum(r.inferences_marked for r in results)
            agg.inference_mark_rate = total_inferences / max(1, len(results))
            total_expected_conflicts = sum(
                len(qc.expected_conflicts) for qc in dataset.queries
            )
            detected_conflicts = sum(r.conflicts_detected for r in results)
            agg.conflict_detection_rate = (
                detected_conflicts / max(1, total_expected_conflicts)
            )

        # Capsule stats
        chars_list: list[int] = []
        tokens_list: list[int] = []
        for qc in dataset.queries:
            capsule = self.capsule_builder.build(
                qc.query, project_id=qc.expected_project_id
            )
            chars_list.append(capsule.total_characters)
            tokens_list.append(capsule.estimated_tokens)
        agg.capsule_avg_chars = int(sum(chars_list) / max(1, len(chars_list)))
        agg.capsule_avg_tokens = int(sum(tokens_list) / max(1, len(tokens_list)))
        if raw_history_chars > 0:
            agg.reduction_vs_raw = 1.0 - (agg.capsule_avg_chars / raw_history_chars)

        return agg

    def _evaluate_one(self, qc: QueryCase) -> SingleResult:
        """Evaluate a single query."""
        result = self.retriever.search(qc.query, project_id=qc.expected_project_id)
        retrieved_ids = [cs.memory_id for cs in result.candidate_scores]
        expected_set = set(qc.expected_ids)

        sr = SingleResult(query_id=qc.query_id)
        sr.num_retrieved = len(retrieved_ids)

        # Precision@k
        def _prec(k: int) -> float:
            top = set(retrieved_ids[:k])
            if not top:
                return 0.0
            rel = top & expected_set
            return len(rel) / len(top)

        sr.precision_1 = _prec(1)
        sr.precision_3 = _prec(3)
        sr.precision_5 = _prec(5)

        # Recall@k
        def _rec(k: int) -> float:
            if not expected_set:
                return 1.0
            top = set(retrieved_ids[:k])
            rel = top & expected_set
            return len(rel) / len(expected_set)

        sr.recall_1 = _rec(1)
        sr.recall_3 = _rec(3)
        sr.recall_5 = _rec(5)

        # Hit@k
        sr.hit_1 = bool(set(retrieved_ids[:1]) & expected_set)
        sr.hit_3 = bool(set(retrieved_ids[:3]) & expected_set)
        sr.hit_5 = bool(set(retrieved_ids[:5]) & expected_set)

        # MRR
        for rank, rid in enumerate(retrieved_ids, start=1):
            if rid in expected_set:
                sr.mrr = 1.0 / rank
                break

        # nDCG
        if qc.relevance_grades:
            sr.ndcg = _compute_ndcg(retrieved_ids, qc.relevance_grades)

        # Fake sources: retrieved IDs not in the storage
        sr.fake_sources = sum(
            1 for rid in retrieved_ids if self.storage.get_memory(rid) is None
        )

        # Inference marking
        sr.inferences_marked = len(result.inferences)

        # Conflict detection
        sr.conflicts_detected = len(result.conflicts)

        sr.relevant_retrieved = len(set(retrieved_ids) & expected_set)

        return sr


def _compute_ndcg(retrieved_ids: list[str], relevance_grades: dict[str, float], k: int = 10) -> float:
    """Compute nDCG@k."""
    top_k = retrieved_ids[:k]
    dcg = 0.0
    for i, rid in enumerate(top_k, start=1):
        rel = relevance_grades.get(rid, 0.0)
        dcg += (2**rel - 1) / math.log2(i + 1)

    # Ideal DCG: sort all grades descending
    ideal_grades = sorted(relevance_grades.values(), reverse=True)[:k]
    idcg = 0.0
    for i, rel in enumerate(ideal_grades, start=1):
        idcg += (2**rel - 1) / math.log2(i + 1)

    return dcg / idcg if idcg > 0 else 0.0


# ---------------------------------------------------------------------------
# Ablation runner
# ---------------------------------------------------------------------------


@dataclass
class AblationVariant:
    """A specific ablation configuration."""

    name: str
    config: RetrievalConfig


ABLATION_VARIANTS: list[AblationVariant] = [
    AblationVariant("full_mec", RetrievalConfig()),
    AblationVariant("no_semantic", RetrievalConfig(enable_semantic=False, semantic_weight=0.0)),
    AblationVariant("no_graph", RetrievalConfig(enable_graph=False, relation_weight=0.0)),
    AblationVariant("no_temporal", RetrievalConfig(enable_temporal=False, temporal_weight=0.0)),
    AblationVariant("no_typing", RetrievalConfig(enable_typing=False, type_weight=0.0, entity_weight=0.0)),
    AblationVariant("no_state", RetrievalConfig(enable_state=False, state_weight=0.0)),
    AblationVariant("no_checkpoint_boost", RetrievalConfig(enable_checkpoint_boost=False)),
]


def run_ablation(
    storage: Storage, dataset: EvalDataset, semantic_adapter: Any = None,
) -> dict[str, AggregatedMetrics]:
    """Run all ablation variants and return comparative metrics."""
    results: dict[str, AggregatedMetrics] = {}

    for variant in ABLATION_VARIANTS:
        retriever = HybridRetriever(
            storage,
            config=variant.config,
            semantic=semantic_adapter or DeterministicSemanticAdapter(),
        )
        evaluator = Evaluator(storage, retriever)
        metrics = evaluator.evaluate(dataset)
        metrics.config = {"variant": variant.name, "config": variant.config.__dict__}
        results[variant.name] = metrics

    return results


# ---------------------------------------------------------------------------
# Report generator
# ---------------------------------------------------------------------------


def generate_report(
    metrics: AggregatedMetrics,
    ablation_results: dict[str, AggregatedMetrics] | None = None,
    dataset_name: str = "",
    version: str = "",
    commit_hash: str = "",
) -> str:
    """Generate a Markdown evaluation report."""

    lines: list[str] = []
    lines.append("# MEC Lab — Evaluation Report")
    lines.append("")
    lines.append(f"**Dataset**: {dataset_name}")
    lines.append(f"**Version**: {version}")
    lines.append(f"**Commit**: {commit_hash}")
    lines.append(f"**Generated**: {datetime.now(UTC).isoformat()}")
    lines.append("")

    lines.append("## Aggregate Metrics")
    lines.append("")
    lines.append(f"| Metric | Value |")
    lines.append(f"|--------|-------|")
    lines.append(f"| Queries | {metrics.num_queries} |")
    lines.append(f"| Precision@1 | {metrics.precision_1:.3f} |")
    lines.append(f"| Precision@3 | {metrics.precision_3:.3f} |")
    lines.append(f"| Precision@5 | {metrics.precision_5:.3f} |")
    lines.append(f"| Recall@3 | {metrics.recall_3:.3f} |")
    lines.append(f"| Recall@5 | {metrics.recall_5:.3f} |")
    lines.append(f"| Hit@1 | {metrics.hit_1_rate:.3f} |")
    lines.append(f"| Hit@3 | {metrics.hit_3_rate:.3f} |")
    lines.append(f"| Hit@5 | {metrics.hit_5_rate:.3f} |")
    lines.append(f"| MRR | {metrics.mrr:.3f} |")
    lines.append(f"| nDCG | {metrics.ndcg:.3f} |")
    lines.append(f"| Fake source rate | {metrics.fake_source_rate:.4f} |")
    lines.append(f"| Conflict detection rate | {metrics.conflict_detection_rate:.3f} |")
    lines.append(f"| Capsule avg chars | {metrics.capsule_avg_chars} |")
    lines.append(f"| Capsule avg tokens | {metrics.capsule_avg_tokens} |")
    lines.append(f"| Reduction vs raw | {metrics.reduction_vs_raw:.1%} |")
    lines.append(f"| Latency (ms) | {metrics.latency_ms:.0f} |")
    lines.append("")

    if ablation_results:
        lines.append("## Ablation Results")
        lines.append("")
        header = "| Variant | Hit@1 | Hit@3 | MRR | Precision@1 |"
        sep = "|---------|-------|-------|-----|-------------|"
        lines.append(header)
        lines.append(sep)
        for name, am in ablation_results.items():
            lines.append(
                f"| {name} | {am.hit_1_rate:.3f} | {am.hit_3_rate:.3f} | "
                f"{am.mrr:.3f} | {am.precision_1:.3f} |"
            )
        lines.append("")

    lines.append("## Per-Query Results")
    lines.append("")
    for sr in metrics.per_query:
        lines.append(f"### {sr.query_id}")
        lines.append(f"- Hit@1: {sr.hit_1}, Hit@3: {sr.hit_3}")
        lines.append(f"- MRR: {sr.mrr:.3f}, nDCG: {sr.ndcg:.3f}")
        lines.append(f"- Precision@1: {sr.precision_1:.3f}")
        lines.append(f"- Conflicts detected: {sr.conflicts_detected}")
        lines.append("")

    lines.append("## Limitations")
    lines.append("")
    lines.append("- Baseline semantic search uses deterministic hashing, not real embeddings.")
    lines.append("- No LLM-based re-ranking or inference generation.")
    lines.append("- Dataset is synthetic; real-world performance may differ.")
    lines.append("")

    return "\n".join(lines)
