"""Experimento Real 01 — MEC Lab: Memória longitudinal do Projeto Atlas.

Orquestrador que executa as 4 fases progressivamente, consulta após cada fase,
e produz avaliação final, snapshots e resultados brutos.

Regras:
- Não altera motor, pesos ou thresholds
- Preserva os 116 testes existentes
- Produz artefatos reproduzíveis
- Usa os 8 tipos de memória substantivamente
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

# Ensure src is on path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from mec_lab.evaluation import Evaluator, EvalDataset, generate_report
from mec_lab.retrieval import HybridRetriever, RetrievalConfig
from mec_lab.storage import Storage

EXPERIMENT_DIR = Path(__file__).resolve().parent
RAW_DIR = EXPERIMENT_DIR / "RAW_RESULTS"
PROJECT_ID = "proj-atlas"

# Dynamically load populate modules from this directory
import importlib.util as _iu


def _load_module(name: str, path: Path):
    spec = _iu.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load {path}")
    mod = _iu.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_pop1 = _load_module("populate_phase_1", EXPERIMENT_DIR / "populate_phase_1.py")
_pop2 = _load_module("populate_phase_2", EXPERIMENT_DIR / "populate_phase_2.py")
_pop3 = _load_module("populate_phase_3", EXPERIMENT_DIR / "populate_phase_3.py")
_pop4 = _load_module("populate_phase_4", EXPERIMENT_DIR / "populate_phase_4.py")


def main() -> int:
    """Run complete experiment. Returns 0 on success."""
    print("=" * 70)
    print("EXPERIMENTO REAL 01 — MEC Lab")
    print("Memória longitudinal do Projeto Atlas")
    print(f"Início: {datetime.now(UTC).isoformat()}")
    print("=" * 70)

    RAW_DIR.mkdir(parents=True, exist_ok=True)

    # ---- Phase 1 ----
    print("\n--- FASE 1: Decisão Inicial ---")
    store = Storage(":memory:")
    store.init_schema()
    ids_1 = _pop1.populate(store, PROJECT_ID)
    print(f"  Criados: {ids_1}")
    _snapshot(store, "phase_1")
    _run_queries_phase(store, "phase_1", [q for q in _load_queries().queries
                                         if q.query_id in {"q01-decisao-vigente",
                                                            "q02-abordagem-anterior",
                                                            "q12-delta-checkpoints"}])

    # ---- Phase 2 ----
    print("\n--- FASE 2: Problema Observado ---")
    ids_2 = _pop2.populate(store, PROJECT_ID)
    print(f"  Criados: {ids_2}")
    _snapshot(store, "phase_2")
    _run_queries_phase(store, "phase_2", [q for q in _load_queries().queries
                                         if q.query_id in {"q04-evidencia-duplicacao",
                                                            "q05-hipotese-replay",
                                                            "q06-aprendizado-reinicializacao"}])

    # ---- Phase 3 ----
    print("\n--- FASE 3: Mudança de Decisão ---")
    ids_3 = _pop3.populate(store, PROJECT_ID)
    print(f"  Criados: {ids_3}")
    _snapshot(store, "phase_3")
    _run_queries_phase(store, "phase_3", [q for q in _load_queries().queries
                                         if q.query_id in {"q01-decisao-vigente",
                                                            "q03-motivo-abandono",
                                                            "q11-conflitos"}])

    # ---- Phase 4 ----
    print("\n--- FASE 4: Estado Atual ---")
    ids_4 = _pop4.populate(store, PROJECT_ID)
    print(f"  Criados: {ids_4}")
    _snapshot(store, "phase_4")

    # ---- Full Evaluation ----
    print("\n" + "=" * 70)
    print("AVALIAÇÃO FINAL (todas as fases)")
    print("=" * 70)

    dataset = _load_queries()
    retriever = HybridRetriever(store, config=RetrievalConfig())
    evaluator = Evaluator(store, retriever)
    metrics = evaluator.evaluate(dataset)

    # Print summary
    print(f"\nQueries: {metrics.num_queries}")
    print(f"Hit@1:   {metrics.hit_1_rate:.3f}")
    print(f"Hit@3:   {metrics.hit_3_rate:.3f}")
    print(f"MRR:     {metrics.mrr:.3f}")
    print(f"Prec@1:  {metrics.precision_1:.3f}")
    print(f"FakeSrc: {metrics.fake_source_rate:.4f}")
    print(f"ConfDet: {metrics.conflict_detection_rate:.3f}")

    # Save raw results
    _save_raw_results(store, dataset, retriever, evaluator, metrics)

    # Verify tests still pass
    print("\n--- Verificando 116 testes ---")
    import subprocess
    project_root = str(EXPERIMENT_DIR.parents[1].resolve())
    result = subprocess.run(
        [sys.executable, str(Path(project_root) / "tests" / "run_tests.py")],
        capture_output=True, text=True, cwd=project_root
    )
    tests_ok = "OK" in (result.stdout + result.stderr) and "FAILED" not in (result.stdout + result.stderr)
    combined = (result.stdout + result.stderr).strip()
    # Show last few relevant lines
    for line in combined.split("\n")[-4:]:
        if line.strip():
            print(line)
    print(f"Testes preservados: {tests_ok}")

    # Final verdict
    print("\n" + "=" * 70)
    verdict = _compute_verdict(metrics, tests_ok, store)
    print(f"VEREDITO: {verdict}")
    print("=" * 70)

    # Save verdict
    (RAW_DIR / "verdict.txt").write_text(f"{verdict}\n")

    # Generate REPORT placeholder
    _write_report(metrics, store, tests_ok)

    return 0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_queries() -> EvalDataset:
    return EvalDataset.from_json(EXPERIMENT_DIR / "queries.json")


def _snapshot(store: Storage, label: str) -> None:
    """Export DB snapshot to RAW_RESULTS/."""
    path = RAW_DIR / f"snapshot_{label}.json"
    data = store.export_all()
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"  Snapshot salvo: {path.name}")


def _run_queries_phase(store: Storage, label: str, queries) -> None:
    """Run a subset of queries after each phase and save results."""
    retriever = HybridRetriever(store, config=RetrievalConfig())
    results = []
    for qc in queries:
        result = retriever.search(qc.query, project_id=qc.expected_project_id)
        results.append({
            "query_id": qc.query_id,
            "query": qc.query,
            "top_ids": [cs.memory_id for cs in result.candidate_scores[:5]],
            "top_scores": [cs.total_score for cs in result.candidate_scores[:5]],
            "quality": result.quality,
            "conflicts": result.conflicts,
            "missing": result.missing_information,
        })
    out_path = RAW_DIR / f"phase_queries_{label}.json"
    out_path.write_text(json.dumps(results, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"  Resultados de consulta salvos: {out_path.name}")


def _save_raw_results(
    store: Storage,
    dataset: EvalDataset,
    retriever: HybridRetriever,
    evaluator: Evaluator,
    metrics,
) -> None:
    """Save detailed per-query results."""
    raw_queries = []
    for qc in dataset.queries:
        result = retriever.search(qc.query, project_id=qc.expected_project_id)
        raw_queries.append({
            "query_id": qc.query_id,
            "query": qc.query,
            "expected_ids": qc.expected_ids,
            "retrieved_ids": [cs.memory_id for cs in result.candidate_scores],
            "retrieved_scores": [
                {"id": cs.memory_id, "score": cs.total_score, "decomp": cs.explanation_decomposition}
                for cs in result.candidate_scores[:10]
            ],
            "quality": result.quality,
            "conflicts": result.conflicts,
            "missing": result.missing_information,
            "inferences": result.inferences,
            "explanation": result.explanation,
        })
    (RAW_DIR / "per_query_details.json").write_text(
        json.dumps(raw_queries, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )

    # Aggregate metrics
    agg = {
        "num_queries": metrics.num_queries,
        "precision_1": metrics.precision_1,
        "precision_3": metrics.precision_3,
        "hit_1_rate": metrics.hit_1_rate,
        "hit_3_rate": metrics.hit_3_rate,
        "mrr": metrics.mrr,
        "fake_source_count": metrics.fake_source_count,
        "fake_source_rate": metrics.fake_source_rate,
        "conflict_detection_rate": metrics.conflict_detection_rate,
        "per_query": [
            {
                "query_id": sr.query_id,
                "hit_1": sr.hit_1,
                "hit_3": sr.hit_3,
                "mrr": sr.mrr,
                "precision_1": sr.precision_1,
                "conflicts_detected": sr.conflicts_detected,
                "fake_sources": sr.fake_sources,
            }
            for sr in metrics.per_query
        ],
    }
    (RAW_DIR / "aggregate_metrics.json").write_text(
        json.dumps(agg, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # Final snapshot
    _snapshot(store, "final")


def _compute_verdict(metrics, tests_ok: bool, store: Storage) -> str:
    """Compute PASSED / FAILED / INCONCLUSIVE based on all experiment criteria."""
    failures: list[str] = []
    warnings: list[str] = []

    if not tests_ok:
        failures.append("116 tests did NOT all pass")

    # Check all 8 memory types used substantively (at least 1 each)
    type_counts = {
        "fact": store.count_memories(mtype="fact"),
        "decision": store.count_memories(mtype="decision"),
        "hypothesis": store.count_memories(mtype="hypothesis"),
        "evidence": store.count_memories(mtype="evidence"),
        "learning": store.count_memories(mtype="learning"),
        "episode": store.count_memories(mtype="episode"),
        "checkpoint": store.count_memories(mtype="checkpoint"),
        "document": store.count_memories(mtype="document"),
    }
    missing_types = [t for t, c in type_counts.items() if c == 0]
    if missing_types:
        failures.append(f"Missing memory types: {missing_types}")

    # Fake source rate must be 0
    if metrics.fake_source_rate > 0:
        failures.append(f"Fake source rate {metrics.fake_source_rate:.4f} > 0")

    # --- Behavioral criteria from per-query analysis ---
    per_query = {sr.query_id: sr for sr in metrics.per_query}

    # Criterion: decisao vigente supera a obsoleta (q01, p01)
    q01 = per_query.get("q01-decisao-vigente")
    p01 = per_query.get("p01-parafrase-vigente")
    if q01 and not q01.hit_1:
        failures.append("q01: decisao vigente (dec-atlas-queue) nao foi hit@1; "
                       "a decisao obsoleta (dec-atlas-batch) teve score maior")
    if p01 and not p01.hit_1:
        failures.append("p01: parafrase — decisao vigente nao foi hit@1")

    # Criterion: decisao obsoleta recuperavel em consultas historicas (q02, p02)
    q02 = per_query.get("q02-abordagem-anterior")
    p02 = per_query.get("p02-parafrase-antigo")
    if q02 and not q02.hit_3:
        failures.append("q02: decisao obsoleta nao recuperavel em top-3")
    if p02 and not p02.hit_3:
        warnings.append("p02: decisao obsoleta nao foi hit@3")

    # Criterion: SUPERSEDES produz conflito detectavel (q11)
    q11 = per_query.get("q11-conflitos")
    if q11 and q11.conflicts_detected == 0:
        failures.append("q11: SUPERSEDES nao produziu conflito detectavel")

    # Criterion: proxima acao recuperada (q07, p05)
    q07 = per_query.get("q07-proximo-trabalho")
    p05 = per_query.get("p05-parafrase-proxima")
    if q07 and not q07.hit_3:
        failures.append("q07: proxima acao nao recuperada em top-3")
    if p05 and not p05.hit_3:
        warnings.append("p05: parafrase — proxima acao nao foi hit@3")

    # Criterion: consulta sem evidencia nao produz resposta inventada (q10, p07)
    q10 = per_query.get("q10-criptografia-ausente")
    p07 = per_query.get("p07-parafrase-seguranca")
    if q10 and q10.num_retrieved > 2:
        failures.append("q10: consulta de ausencia retornou memorias irrelevantes "
                       f"(num_retrieved={q10.num_retrieved}); "
                       "o sistema deveria indicar ausencia, nao retornar resultados")
    if p07 and p07.num_retrieved > 2:
        failures.append("p07: parafrase — consulta de ausencia retornou memorias "
                       f"(num_retrieved={p07.num_retrieved})")

    # Criterion: risco pendente recuperado (q08, p06)
    q08 = per_query.get("q08-risco-pendente")
    p06 = per_query.get("p06-parafrase-bloqueio")
    if q08 and not q08.hit_1:
        failures.append("q08: risco pendente nao foi hit@1")
    if p06 and not p06.hit_1:
        warnings.append("p06: risco pendente nao foi hit@1 na parafrase")

    # Criterion: documento de arquitetura recuperado (q09)
    q09 = per_query.get("q09-documento-arquitetura")
    if q09 and not q09.hit_1:
        failures.append("q09: documento de arquitetura nao foi hit@1")

    if failures:
        return f"EXPERIMENT_01_FAILED — {'; '.join(failures)}"

    if warnings:
        return f"EXPERIMENT_01_INCONCLUSIVE — warnings: {'; '.join(warnings)}"

    return "EXPERIMENT_01_PASSED"


def _write_report(metrics, store: Storage, tests_ok: bool) -> None:
    """Write initial REPORT.md. To be completed with human analysis."""
    lines = [
        "# Experimento Real 01 — Relatório",
        "",
        f"**Data**: {datetime.now(UTC).isoformat()}",
        "**Projeto**: Projeto Atlas",
        "**Branch**: experiment/mec-live-memory-01",
        "",
        "## Sumário Executivo",
        "",
        f"- Queries avaliadas: {metrics.num_queries}",
        f"- Hit@1: {metrics.hit_1_rate:.3f}",
        f"- Hit@3: {metrics.hit_3_rate:.3f}",
        f"- MRR: {metrics.mrr:.3f}",
        f"- Precision@1: {metrics.precision_1:.3f}",
        f"- Fake source rate: {metrics.fake_source_rate:.4f}",
        f"- Conflict detection rate: {metrics.conflict_detection_rate:.3f}",
        f"- Testes preservados: {tests_ok}",
        "",
        "## Memórias por Tipo",
        "",
        "| Tipo | Quantidade |",
        "|------|-----------|",
    ]
    for mtype in ["fact", "decision", "hypothesis", "evidence", "learning", "episode", "checkpoint", "document"]:
        count = store.count_memories(mtype=mtype)
        lines.append(f"| {mtype} | {count} |")

    lines += [
        "",
        "## Per-Query Results",
        "",
        "| Query ID | Hit@1 | Hit@3 | MRR | Conflicts |",
        "|----------|-------|-------|-----|-----------|",
    ]
    for sr in metrics.per_query:
        lines.append(f"| {sr.query_id} | {sr.hit_1} | {sr.hit_3} | {sr.mrr:.3f} | {sr.conflicts_detected} |")

    lines += [
        "",
        "## Fatos Observados",
        "",
        "(preenchido após análise dos resultados brutos)",
        "",
        "## Métricas Calculadas",
        "",
        f"Ver RAW_RESULTS/aggregate_metrics.json e RAW_RESULTS/per_query_details.json",
        "",
        "## Limitações",
        "",
        "- Baseline usa apenas busca lexical + TF-IDF determinístico",
        "- Sem re-ranqueamento por LLM",
        "- Cenário sintético com 18 memórias",
        "",
        "## Inferências",
        "",
        "(preenchido após análise)",
        "",
        "## Recomendação para o Próximo Experimento",
        "",
        "(preenchido após análise)",
    ]
    (EXPERIMENT_DIR / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
