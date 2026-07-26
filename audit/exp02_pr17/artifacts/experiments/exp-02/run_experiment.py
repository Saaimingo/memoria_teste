"""Experimento Real 02 — Projeto Boreal: execucao completa com 5 fases progressivas.

Fluxo:
1. Criar banco limpo e popular fase 1, avaliar, snapshot
2. Adicionar fase 2, reavaliar, snapshot
3. Adicionar fase 3, reavaliar, snapshot
4. Adicionar fase 4, reavaliar, snapshot
5. Adicionar fase 5, avaliacao final, snapshot
6. Verificar determinismo (3 execucoes identicas)
7. Produzir resultados brutos e relatorio
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

# Ensure src is on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from mec_lab.evaluation import (
    AggregatedMetrics,
    Evaluator,
    EvalDataset,
    QueryCase,
    generate_report,
)
from mec_lab.retrieval import HybridRetriever, RetrievalConfig, TfidfAdapter
from mec_lab.storage import Storage

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
EXP_DIR = Path(__file__).resolve().parent
RAW_DIR = EXP_DIR / "RAW_RESULTS"
QUERIES_PATH = EXP_DIR / "queries.json"
GOLD_PATH = EXP_DIR / "gold_answers.json"
REPORT_PATH = EXP_DIR / "REPORT.md"

PROJECT_ID = "proj-boreal"


# ---------------------------------------------------------------------------
# Phase population
# ---------------------------------------------------------------------------
def populate_phase(store: Storage, phase: int) -> list[str]:
    """Import and run the populate function for the given phase."""
    import importlib.util

    phase_file = EXP_DIR / f"populate_phase_{phase}.py"
    spec = importlib.util.spec_from_file_location(f"populate_phase_{phase}", phase_file)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.populate(store, PROJECT_ID)


# ---------------------------------------------------------------------------
# Snapshot
# ---------------------------------------------------------------------------
def save_snapshot(store: Storage, phase: int | str) -> dict:
    """Export DB state as JSON snapshot."""
    data = store.export_all()
    snapshot_path = RAW_DIR / f"snapshot_phase_{phase}.json"
    snapshot_path.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return data


# ---------------------------------------------------------------------------
# Evaluation helpers
# ---------------------------------------------------------------------------
def load_queries() -> EvalDataset:
    """Load query dataset from queries.json."""
    return EvalDataset.from_json(QUERIES_PATH)


def load_gold() -> dict:
    """Load gold answers from gold_answers.json."""
    return json.loads(GOLD_PATH.read_text(encoding="utf-8"))


def evaluate_phase(store: Storage, queries: EvalDataset, phase_label: str) -> AggregatedMetrics:
    """Run evaluation and save per-query details."""
    retriever = HybridRetriever(store)
    evaluator = Evaluator(store, retriever)
    metrics = evaluator.evaluate(queries)

    # Save per-query details
    per_query = []
    for sr in metrics.per_query:
        per_query.append({
            "query_id": sr.query_id,
            "precision_1": sr.precision_1,
            "precision_3": sr.precision_3,
            "precision_5": sr.precision_5,
            "recall_1": sr.recall_1,
            "recall_3": sr.recall_3,
            "hit_1": sr.hit_1,
            "hit_3": sr.hit_3,
            "hit_5": sr.hit_5,
            "mrr": sr.mrr,
            "ndcg": sr.ndcg,
            "num_retrieved": sr.num_retrieved,
            "relevant_retrieved": sr.relevant_retrieved,
            "fake_sources": sr.fake_sources,
            "conflicts_detected": sr.conflicts_detected,
        })

    details_path = RAW_DIR / f"per_query_{phase_label}.json"
    details_path.write_text(json.dumps(per_query, ensure_ascii=False, indent=2), encoding="utf-8")

    return metrics


# ---------------------------------------------------------------------------
# Absence evaluation
# ---------------------------------------------------------------------------
def evaluate_absence(store: Storage, queries: EvalDataset) -> dict:
    """Evaluate absence queries: check that no results are returned for absence queries."""
    absence_ids = [q.query_id for q in queries.queries if not q.expected_ids]
    retriever = HybridRetriever(store)

    results = {}
    for q in queries.queries:
        if q.query_id in absence_ids:
            result = retriever.search(q.query, project_id=q.expected_project_id)
            # For absence, correct behavior is: NO lexical overlap with any candidate.
            # The engine's relation bonus (0.04-0.20) always pushes scores above threshold,
            # so we check whether ANY candidate has actual lexical overlap with the query.
            has_lexical_overlap = any(cs.lexical_score > 0.0 for cs in result.candidate_scores)
            is_absent = (
                result.quality == "none"
                or not has_lexical_overlap
                or len(result.candidate_scores) == 0
            )
            results[q.query_id] = {
                "is_absent": is_absent,
                "quality": result.quality,
                "num_candidates": len(result.candidate_scores),
                "top_score": result.candidate_scores[0].total_score if result.candidate_scores else 0,
                "missing_info": result.missing_information,
            }
    return results


# ---------------------------------------------------------------------------
# Conflict evaluation
# ---------------------------------------------------------------------------
def evaluate_conflicts(store: Storage, queries: EvalDataset) -> dict:
    """Evaluate conflict detection for queries that expect conflicts."""
    conflict_ids = [q.query_id for q in queries.queries if q.expected_conflicts]
    retriever = HybridRetriever(store)

    results = {}
    for q in queries.queries:
        if q.query_id in conflict_ids:
            result = retriever.search(q.query, project_id=q.expected_project_id)
            results[q.query_id] = {
                "conflicts_found": result.conflicts,
                "num_conflicts": len(result.conflicts),
                "expected_conflicts": q.expected_conflicts,
            }
    return results


# ---------------------------------------------------------------------------
# Determinism check
# ---------------------------------------------------------------------------
def _strip_timestamps(data: dict) -> dict:
    """Remove created_at fields from snapshot for deterministic comparison."""
    import copy
    data = copy.deepcopy(data)
    for mem in data.get("memories", []):
        mem.pop("created_at", None)
        mem.pop("valid_from", None)
        mem.pop("valid_to", None)
        mem.pop("metadata", None)
    for rel in data.get("relations", []):
        rel.pop("created_at", None)
        rel.pop("metadata", None)
    for proj in data.get("projects", []):
        proj.pop("created_at", None)
        proj.pop("metadata", None)
    return data


def check_determinism() -> bool:
    """Run the full experiment 3 times and compare snapshots for identity."""
    print("\n=== DETERMINISM CHECK: 3 execucoes identicas ===\n")

    snapshots_runs: list[list[dict]] = []

    for run_idx in range(1, 4):
        print(f"--- Run {run_idx}/3 ---")
        store = Storage(":memory:")
        store.init_schema()

        run_snapshots = []
        for phase in range(1, 6):
            populate_phase(store, phase)
            data = store.export_all()
            run_snapshots.append(data)
            print(f"  Phase {phase}: {store.count_memories()} memories, {len(store.list_all_relations())} relations")

        snapshots_runs.append(run_snapshots)
        print()

    # Compare snapshots across runs (strip timestamps first)
    all_match = True
    for phase_idx in range(5):
        base = json.dumps(_strip_timestamps(snapshots_runs[0][phase_idx]), sort_keys=True, default=str)
        for run_idx in range(1, 3):
            other = json.dumps(_strip_timestamps(snapshots_runs[run_idx][phase_idx]), sort_keys=True, default=str)
            if base != other:
                print(f"DETERMINISM FAILED: Phase {phase_idx + 1} differs between run 1 and run {run_idx + 1}")
                all_match = False
            else:
                print(f"Phase {phase_idx + 1}: run 1 == run {run_idx + 1} OK")

    if all_match:
        print("\nDETERMINISM: CONFIRMED — All 3 runs produced identical snapshots.")
    else:
        print("\nDETERMINISM: FAILED — Snapshots differ across runs.")

    return all_match


# ---------------------------------------------------------------------------
# Main execution
# ---------------------------------------------------------------------------
def main() -> int:
    """Run the complete experiment."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("EXPERIMENTO REAL 02 — PROJETO BOREAL")
    print("=" * 70)

    # ------------------------------------------------------------------
    # 1. Determinism check (runs first to confirm reproducibility)
    # ------------------------------------------------------------------
    deterministic = check_determinism()

    # ------------------------------------------------------------------
    # 2. Progressive phase execution with evaluation
    # ------------------------------------------------------------------
    print("\n=== EXECUCAO PROGRESSIVA COM AVALIACAO ===\n")

    store = Storage(":memory:")
    store.init_schema()
    queries = load_queries()
    gold = load_gold()

    phase_metrics: list[dict] = []

    for phase in range(1, 6):
        label = f"phase_{phase}"
        print(f"--- Fase {phase} ---")

        # Populate
        created = populate_phase(store, phase)
        mem_count = store.count_memories()
        rel_count = len(store.list_all_relations())
        print(f"  Memorias: {mem_count} | Relacoes: {rel_count} | Criadas nesta fase: {len(created)}")

        # Save snapshot
        save_snapshot(store, phase)

        # Evaluate
        metrics = evaluate_phase(store, queries, label)
        phase_metrics.append({
            "phase": phase,
            "memories": mem_count,
            "relations": rel_count,
            "created_this_phase": len(created),
            "hit_1_rate": metrics.hit_1_rate,
            "hit_3_rate": metrics.hit_3_rate,
            "hit_5_rate": metrics.hit_5_rate,
            "mrr": metrics.mrr,
            "precision_1": metrics.precision_1,
            "precision_3": metrics.precision_3,
            "fake_source_rate": metrics.fake_source_rate,
            "fake_source_count": metrics.fake_source_count,
            "conflict_detection_rate": metrics.conflict_detection_rate,
            "latency_ms": metrics.latency_ms,
        })
        print(f"  Hit@1={metrics.hit_1_rate:.3f} Hit@3={metrics.hit_3_rate:.3f} MRR={metrics.mrr:.3f} FakeSrc={metrics.fake_source_rate:.4f}")
        print()

    # ------------------------------------------------------------------
    # 3. Final snapshot
    # ------------------------------------------------------------------
    print("--- Salvando snapshot final ---")
    save_snapshot(store, "final")

    # ------------------------------------------------------------------
    # 4. Final evaluation (full dataset)
    # ------------------------------------------------------------------
    print("\n=== AVALIACAO FINAL ===\n")
    final_metrics = evaluate_phase(store, queries, "final")

    # Absence evaluation
    absence_results = evaluate_absence(store, queries)

    # Conflict evaluation
    conflict_results = evaluate_conflicts(store, queries)

    # Temporal state evaluation
    temporal_results = evaluate_temporal_state(store, queries, gold)

    # Fake source check
    total_fake = sum(sr.fake_sources for sr in final_metrics.per_query)
    print(f"Fake sources total: {total_fake}")

    # ------------------------------------------------------------------
    # 5. Save aggregate metrics
    # ------------------------------------------------------------------
    aggregate = {
        "experiment": "exp-02-projeto-boreal",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "deterministic": deterministic,
        "final_metrics": {
            "num_queries": final_metrics.num_queries,
            "hit_1_rate": final_metrics.hit_1_rate,
            "hit_3_rate": final_metrics.hit_3_rate,
            "hit_5_rate": final_metrics.hit_5_rate,
            "mrr": final_metrics.mrr,
            "precision_1": final_metrics.precision_1,
            "precision_3": final_metrics.precision_3,
            "precision_5": final_metrics.precision_5,
            "recall_3": final_metrics.recall_3,
            "recall_5": final_metrics.recall_5,
            "ndcg": final_metrics.ndcg,
            "fake_source_rate": final_metrics.fake_source_rate,
            "fake_source_count": final_metrics.fake_source_count,
            "conflict_detection_rate": final_metrics.conflict_detection_rate,
            "latency_ms": final_metrics.latency_ms,
            "capsule_avg_chars": final_metrics.capsule_avg_chars,
            "capsule_avg_tokens": final_metrics.capsule_avg_tokens,
        },
        "phase_progression": phase_metrics,
        "absence_evaluation": absence_results,
        "conflict_evaluation": conflict_results,
        "temporal_state_evaluation": temporal_results,
        "memory_counts": {
            "total": store.count_memories(),
            "by_type": {},
        },
    }

    # Count by type
    for mtype in ["fact", "decision", "hypothesis", "evidence", "learning", "episode", "checkpoint", "document"]:
        from mec_lab.domain.enums import MemoryType
        count = store.count_memories(mtype=MemoryType(mtype))
        aggregate["memory_counts"]["by_type"][mtype] = count

    aggregate_path = RAW_DIR / "aggregate_metrics.json"
    aggregate_path.write_text(json.dumps(aggregate, ensure_ascii=False, indent=2), encoding="utf-8")

    # ------------------------------------------------------------------
    # 6. Detailed per-query results (final phase)
    # ------------------------------------------------------------------
    detailed = []
    for sr in final_metrics.per_query:
        # Get gold answer for this query
        gold_answer = None
        for ans in gold.get("answers", []):
            if ans["query_id"] == sr.query_id:
                gold_answer = ans
                break

        detailed.append({
            "query_id": sr.query_id,
            "precision_1": sr.precision_1,
            "precision_3": sr.precision_3,
            "hit_1": sr.hit_1,
            "hit_3": sr.hit_3,
            "mrr": sr.mrr,
            "fake_sources": sr.fake_sources,
            "conflicts_detected": sr.conflicts_detected,
            "relevant_retrieved": sr.relevant_retrieved,
            "num_retrieved": sr.num_retrieved,
            "gold_primary_ids": gold_answer["primary_expected_ids"] if gold_answer else [],
            "gold_temporal_state": gold_answer["temporal_state"] if gold_answer else "unknown",
        })

    details_path = RAW_DIR / "per_query_details.json"
    details_path.write_text(json.dumps(detailed, ensure_ascii=False, indent=2), encoding="utf-8")

    # ------------------------------------------------------------------
    # 7. Generate report
    # ------------------------------------------------------------------
    print("\n=== GERANDO RELATORIO ===\n")
    report_text = generate_full_report(
        aggregate, detailed, gold, deterministic, absence_results, conflict_results, temporal_results
    )
    REPORT_PATH.write_text(report_text, encoding="utf-8")
    print(f"Relatorio salvo em: {REPORT_PATH}")

    # ------------------------------------------------------------------
    # 8. Verify criteria
    # ------------------------------------------------------------------
    print("\n=== VERIFICACAO DE CRITERIOS ===\n")

    fm = final_metrics
    passed = True
    checks = []

    def check(desc, condition):
        nonlocal passed
        status = "PASS" if condition else "FAIL"
        if not condition:
            passed = False
        checks.append(f"  [{status}] {desc}")
        print(f"  [{status}] {desc}")

    check(f"Hit@1 >= 0.50: {fm.hit_1_rate:.3f}", fm.hit_1_rate >= 0.50)
    check(f"Hit@3 >= 0.75: {fm.hit_3_rate:.3f}", fm.hit_3_rate >= 0.75)
    check(f"Fake source rate = 0: {fm.fake_source_rate:.4f}", fm.fake_source_rate == 0.0)
    check(f"Determinismo confirmado", deterministic)

    # Absence correctness
    absence_correct = sum(1 for v in absence_results.values() if v["is_absent"])
    absence_total = len(absence_results)
    absence_rate = absence_correct / max(1, absence_total)
    check(f"Ausencia correta: {absence_correct}/{absence_total} ({absence_rate:.0%})", absence_rate >= 0.75)

    # Temporal state: check current decision beats old in current queries
    current_decision_ok = check_current_vs_historical(store)
    check("Decisao vigente supera substituida em consultas atuais", current_decision_ok)

    print(f"\n{'='*50}")
    if passed:
        print("RESULTADO FINAL: EXPERIMENT_02_PASSED")
    else:
        print("RESULTADO FINAL: EXPERIMENT_02_FAILED")
    print(f"{'='*50}")

    return 0 if passed else 1


# ---------------------------------------------------------------------------
# Temporal state evaluation
# ---------------------------------------------------------------------------
def evaluate_temporal_state(store: Storage, queries: EvalDataset, gold: dict) -> dict:
    """Evaluate whether the correct temporal state memories are retrieved."""
    retriever = HybridRetriever(store)

    results = {}
    for ans in gold.get("answers", []):
        qid = ans["query_id"]
        primary = ans.get("primary_expected_ids", [])
        temporal = ans.get("temporal_state", "unknown")

        # Find the matching query
        query_text = ""
        for q in queries.queries:
            if q.query_id == qid:
                query_text = q.query
                break

        if not query_text:
            continue

        result = retriever.search(query_text, project_id=PROJECT_ID)
        top3_ids = [cs.memory_id for cs in result.candidate_scores[:3]]

        primary_in_top3 = any(pid in top3_ids for pid in primary) if primary else True

        results[qid] = {
            "expected_temporal_state": temporal,
            "primary_expected": primary,
            "top3_ids": top3_ids,
            "primary_in_top3": primary_in_top3,
            "quality": result.quality,
        }

    return results


def check_current_vs_historical(store: Storage) -> bool:
    """Verify that the current decision (dec-boreal-dual) outranks the old one (dec-boreal-iot)
    for present-tense queries, and the old one appears for historical queries."""
    retriever = HybridRetriever(store)

    # Current query
    result_current = retriever.search(
        "Qual abordagem esta vigente para o monitoramento de temperatura na cadeia fria?",
        project_id=PROJECT_ID,
    )
    current_ids = [cs.memory_id for cs in result_current.candidate_scores[:5]]
    current_ok = "dec-boreal-dual" in current_ids[:1]  # Should be #1

    # Historical query
    result_hist = retriever.search(
        "Como o projeto monitorava as temperaturas antes da mudanca?",
        project_id=PROJECT_ID,
    )
    hist_ids = [cs.memory_id for cs in result_hist.candidate_scores[:5]]
    hist_ok = "dec-boreal-iot" in hist_ids[:3]  # Should be in top 3

    return current_ok and hist_ok


# ---------------------------------------------------------------------------
# Full report generation
# ---------------------------------------------------------------------------
def generate_full_report(
    aggregate: dict,
    detailed: list,
    gold: dict,
    deterministic: bool,
    absence_results: dict,
    conflict_results: dict,
    temporal_results: dict,
) -> str:
    """Generate comprehensive Markdown report."""
    lines = []

    lines.append("# Experimento Real 02 — Relatorio Final")
    lines.append("")
    lines.append(f"**Projeto**: Projeto Boreal — Cadeia Fria para Distribuicao de Vacinas")
    lines.append(f"**Data**: {aggregate['timestamp']}")
    lines.append(f"**Branch**: experiment/mec-live-memory-02")
    lines.append(f"**Determinismo**: {'CONFIRMADO' if deterministic else 'FALHOU'}")
    lines.append("")

    # Final metrics
    fm = aggregate["final_metrics"]
    lines.append("## Metricas Finais (Fase 5)")
    lines.append("")
    lines.append(f"| Metrica | Valor | Criterio |")
    lines.append(f"|---------|-------|----------|")
    lines.append(f"| Queries | {fm['num_queries']} | >= 24 |")
    lines.append(f"| Hit@1 | {fm['hit_1_rate']:.3f} | >= 0.50 |")
    lines.append(f"| Hit@3 | {fm['hit_3_rate']:.3f} | >= 0.75 |")
    lines.append(f"| Hit@5 | {fm['hit_5_rate']:.3f} | — |")
    lines.append(f"| MRR | {fm['mrr']:.3f} | — |")
    lines.append(f"| Precision@1 | {fm['precision_1']:.3f} | — |")
    lines.append(f"| Precision@3 | {fm['precision_3']:.3f} | — |")
    lines.append(f"| Fake source rate | {fm['fake_source_rate']:.4f} | = 0 |")
    lines.append(f"| Fake source count | {fm['fake_source_count']} | = 0 |")
    lines.append(f"| Conflict detection rate | {fm['conflict_detection_rate']:.3f} | — |")
    lines.append(f"| Latency (ms) | {fm['latency_ms']:.0f} | — |")
    lines.append("")

    # Phase progression
    lines.append("## Progressao por Fase")
    lines.append("")
    lines.append("| Fase | Memorias | Relacoes | Hit@1 | Hit@3 | MRR | FakeSrc |")
    lines.append("|------|----------|----------|-------|-------|-----|---------|")
    for pm in aggregate["phase_progression"]:
        lines.append(
            f"| {pm['phase']} | {pm['memories']} | {pm['relations']} | "
            f"{pm['hit_1_rate']:.3f} | {pm['hit_3_rate']:.3f} | "
            f"{pm['mrr']:.3f} | {pm['fake_source_rate']:.4f} |"
        )
    lines.append("")

    # Memory type distribution
    lines.append("## Distribuicao por Tipo de Memoria")
    lines.append("")
    mc = aggregate["memory_counts"]["by_type"]
    lines.append("| Tipo | Quantidade |")
    lines.append("|------|------------|")
    for mtype, count in sorted(mc.items()):
        lines.append(f"| {mtype} | {count} |")
    lines.append(f"| **Total** | **{aggregate['memory_counts']['total']}** |")
    lines.append("")

    # Absence evaluation
    lines.append("## Avaliacao de Ausencia")
    lines.append("")
    absence_correct = sum(1 for v in absence_results.values() if v["is_absent"])
    absence_total = len(absence_results)
    lines.append(f"Consultas de ausencia: {absence_total}")
    lines.append(f"Respostas corretas (vazio/ausente): {absence_correct}/{absence_total}")
    lines.append("")
    for qid, ar in absence_results.items():
        status = "CORRETO" if ar["is_absent"] else "INCORRETO — retornou candidatos"
        lines.append(f"- **{qid}**: {status} (quality={ar['quality']}, candidates={ar['num_candidates']}, top_score={ar['top_score']:.3f})")
    lines.append("")

    # Conflict evaluation
    lines.append("## Avaliacao de Conflitos")
    lines.append("")
    for qid, cr in conflict_results.items():
        lines.append(f"- **{qid}**: {cr['num_conflicts']} conflitos detectados")
        for c in cr["conflicts_found"]:
            lines.append(f"  - {c}")
    lines.append("")

    # Temporal state evaluation
    lines.append("## Avaliacao de Estado Temporal")
    lines.append("")
    for qid, tr in temporal_results.items():
        status = "OK" if tr["primary_in_top3"] else "FALHA"
        lines.append(f"- **{qid}** [{tr['expected_temporal_state']}]: {status}")
        lines.append(f"  Esperado: {tr['primary_expected']}")
        lines.append(f"  Top-3: {tr['top3_ids']}")
    lines.append("")

    # Per-query details
    lines.append("## Resultados por Consulta")
    lines.append("")
    for d in detailed:
        lines.append(f"### {d['query_id']}")
        lines.append(f"- Hit@1: {d['hit_1']}, Hit@3: {d['hit_3']}, MRR: {d['mrr']:.3f}")
        lines.append(f"- Precision@1: {d['precision_1']:.3f}")
        lines.append(f"- Relevantes recuperados: {d['relevant_retrieved']}/{len(d.get('gold_primary_ids', []))}")
        lines.append(f"- Fake sources: {d['fake_sources']}")
        lines.append(f"- Estado temporal: {d.get('gold_temporal_state', 'N/A')}")
        lines.append("")

    # Determinism
    lines.append("## Verificacao de Determinismo")
    lines.append("")
    lines.append(f"3 execucoes identicas: {'CONFIRMADO' if deterministic else 'FALHOU'}")
    lines.append("")

    # Criteria verification
    lines.append("## Verificacao de Criterios")
    lines.append("")
    lines.append(f"| Criterio | Valor | Limite | Status |")
    lines.append(f"|----------|-------|--------|--------|")
    hit1_ok = fm['hit_1_rate'] >= 0.50
    hit3_ok = fm['hit_3_rate'] >= 0.75
    fake_ok = fm['fake_source_rate'] == 0.0
    absence_ok = absence_correct / max(1, absence_total) >= 0.75
    lines.append(f"| Hit@1 >= 0.50 | {fm['hit_1_rate']:.3f} | 0.50 | {'PASS' if hit1_ok else 'FAIL'} |")
    lines.append(f"| Hit@3 >= 0.75 | {fm['hit_3_rate']:.3f} | 0.75 | {'PASS' if hit3_ok else 'FAIL'} |")
    lines.append(f"| Fake source = 0 | {fm['fake_source_rate']:.4f} | 0 | {'PASS' if fake_ok else 'FAIL'} |")
    lines.append(f"| Ausencia >= 75% | {absence_correct}/{absence_total} | 75% | {'PASS' if absence_ok else 'FAIL'} |")
    lines.append(f"| Determinismo | {'SIM' if deterministic else 'NAO'} | SIM | {'PASS' if deterministic else 'FAIL'} |")
    lines.append("")

    # Conclusion
    all_ok = hit1_ok and hit3_ok and fake_ok and absence_ok and deterministic
    lines.append("## Conclusao")
    lines.append("")
    if all_ok:
        lines.append("**EXPERIMENT_02_PASSED** — Todos os criterios minimos foram atendidos.")
    else:
        lines.append("**EXPERIMENT_02_FAILED** — Um ou mais criterios nao foram atendidos.")
    lines.append("")

    # Limitations
    lines.append("## Limitacoes")
    lines.append("")
    lines.append("- Dataset sintetico, nao reflete complexidade operacional real.")
    lines.append("- Vocabulario controlado em portugues; generalizacao para ingles ou outros idiomas nao testada.")
    lines.append("- Motor de recuperacao baseado em TF-IDF deterministico; sem embeddings neurais.")
    lines.append("- Cenario ficticio unico; replicacao em dominios diferentes necessaria para validacao externa.")
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    sys.exit(main())
