"""MEC Lab — CLI (Click).

Commands: init-db, load-dataset, add-memory, add-relation, create-episode,
create-checkpoint, search, explain, build-capsule, evaluate, export-report, show-lineage.

R4 integration: --retrieval-mode assisted enables the structured assisted
retrieval pipeline with the four canonical states and interactive clarification.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from mec_lab.context import CapsuleBuilder, build_resumption_prompt
from mec_lab.domain.enums import (
    Confidence,
    EpistemicStatus,
    MemoryType,
    RelationType,
)
from mec_lab.domain.models import (
    Checkpoint,
    Decision,
    DocumentRecord,
    Episode,
    Evidence,
    Fact,
    Hypothesis,
    Learning,
    MemoryRelation,
    ProjectRecord,
    memory_class_for,
)
from mec_lab.evaluation import (
    EvalDataset,
    Evaluator,
    generate_report,
    run_ablation,
)
from mec_lab.ingestion import IngestionManifest, IngestionPipeline
from mec_lab.retrieval import (
    AssistedRetrievalConfig,
    AssistedRetrievalResult,
    AssistedRetriever,
    ClarificationCycle,
    DeterministicSemanticAdapter,
    HybridRetriever,
    LexicalRetriever,
    RetrievalConfig,
    RetrievalState,
    TfidfAdapter,
)
from mec_lab.storage import Storage

console = Console()


@click.group()
@click.option("--db", default="mec_lab.db", help="SQLite database path", show_default=True)
@click.pass_context
def cli(ctx: click.Context, db: str) -> None:
    """MEC Lab — Memoria Estruturada e Causal experimental CLI."""
    ctx.ensure_object(dict)
    ctx.obj["db"] = db


def _get_storage(db: str) -> Storage:
    store = Storage(db)
    store.init_schema()
    return store


# ---------------------------------------------------------------------------
# init-db
# ---------------------------------------------------------------------------


@cli.command()
@click.pass_context
def init_db(ctx: click.Context) -> None:
    """Initialize the SQLite database schema."""
    db = ctx.obj["db"]
    store = _get_storage(db)
    console.print(f"[green]Database initialized at {db}[/green]")


# ---------------------------------------------------------------------------
# load-dataset
# ---------------------------------------------------------------------------


@cli.command()
@click.argument("path", type=click.Path(exists=True))
@click.pass_context
def load_dataset(ctx: click.Context, path: str) -> None:
    """Load a JSON dataset into the database."""
    db = ctx.obj["db"]
    store = _get_storage(db)
    data = json.loads(Path(path).read_text(encoding="utf-8"))

    for proj in data.get("projects", []):
        store.save_project(ProjectRecord(**proj))
        console.print(f"  Project: {proj['name']}")

    for mem_data in data.get("memories", []):
        mtype = MemoryType(mem_data["type"])
        cls = memory_class_for(mtype)
        mem = cls(**mem_data)
        store.save_memory(mem)
        console.print(f"  Memory [{mem.type}]: {mem.id}")

    for rel_data in data.get("relations", []):
        store.save_relation(MemoryRelation(**rel_data))
        console.print(f"  Relation: {rel_data['source_id']} -> {rel_data['target_id']}")

    console.print(
        f"[green]Loaded {len(data.get('memories', []))} memories "
        f"and {len(data.get('relations', []))} relations.[/green]"
    )


# ---------------------------------------------------------------------------
# add-memory
# ---------------------------------------------------------------------------


@cli.command()
@click.option("--type", "mtype", required=True, help="Memory type")
@click.option("--project", "project_id", required=True, help="Project ID")
@click.option("--content", default="", help="Memory content")
@click.option("--status", default="registered", help="Epistemic status")
@click.option("--confidence", default="medium", help="Confidence level")
@click.option("--extra", default="{}", help="JSON with type-specific fields")
@click.pass_context
def add_memory(
    ctx: click.Context, mtype: str, project_id: str, content: str, status: str,
    confidence: str, extra: str,
) -> None:
    """Add a single memory record."""
    store = _get_storage(ctx.obj["db"])
    mem_type = MemoryType(mtype)
    cls = memory_class_for(mem_type)
    extra_data = json.loads(extra) if extra else {}
    base = {
        "type": mem_type,
        "content": content,
        "project_id": project_id,
        "status": EpistemicStatus(status),
        "confidence": Confidence(confidence),
    }
    base.update(extra_data)
    mem = cls(**base)
    store.save_memory(mem)
    console.print(f"[green]Created {mem_type}: {mem.id}[/green]")


# ---------------------------------------------------------------------------
# add-relation
# ---------------------------------------------------------------------------


@cli.command()
@click.option("--source", "source_id", required=True)
@click.option("--target", "target_id", required=True)
@click.option("--type", "relation_type", required=True, help="Relation type")
@click.option("--confidence", default="medium")
@click.pass_context
def add_relation(
    ctx: click.Context, source_id: str, target_id: str, relation_type: str,
    confidence: str,
) -> None:
    """Create a typed relation between two memory records."""
    store = _get_storage(ctx.obj["db"])
    rel = MemoryRelation(
        source_id=source_id,
        target_id=target_id,
        relation_type=RelationType(relation_type),
        confidence=Confidence(confidence),
    )
    store.save_relation(rel)
    console.print(f"[green]Relation {rel.id}: {source_id} --[{relation_type}]--> {target_id}[/green]")


# ---------------------------------------------------------------------------
# create-episode
# ---------------------------------------------------------------------------


@cli.command()
@click.option("--project", "project_id", required=True)
@click.option("--initial-state", default="")
@click.option("--goal", default="")
@click.option("--plan", default="")
@click.option("--result", default="")
@click.option("--content", default="")
@click.pass_context
def create_episode(
    ctx: click.Context, project_id: str, initial_state: str, goal: str,
    plan: str, result: str, content: str,
) -> None:
    """Create an episode record."""
    store = _get_storage(ctx.obj["db"])
    ep = Episode(
        project_id=project_id,
        content=content or f"Goal: {goal}\nResult: {result}",
        initial_state=initial_state,
        goal=goal,
        plan=plan,
        result=result,
    )
    store.save_memory(ep)
    console.print(f"[green]Episode created: {ep.id}[/green]")


# ---------------------------------------------------------------------------
# create-checkpoint
# ---------------------------------------------------------------------------


@cli.command()
@click.option("--project", "project_id", required=True)
@click.option("--state", "current_state", default="")
@click.option("--last-action", default="")
@click.option("--next-action", default="")
@click.option("--content", default="")
@click.pass_context
def create_checkpoint(
    ctx: click.Context, project_id: str, current_state: str,
    last_action: str, next_action: str, content: str,
) -> None:
    """Create a checkpoint for a project."""
    store = _get_storage(ctx.obj["db"])
    cp = Checkpoint(
        project_id=project_id,
        content=content or current_state,
        current_state=current_state,
        last_completed_action=last_action,
        next_allowed_action=next_action,
    )
    store.save_memory(cp)
    console.print(f"[green]Checkpoint created: {cp.id}[/green]")


# ---------------------------------------------------------------------------
# search
# ---------------------------------------------------------------------------


def _format_assisted_result_json(result: AssistedRetrievalResult) -> str:
    """Serialize an AssistedRetrievalResult to JSON for machine consumption."""
    scores_out = []
    for s in result.scores:
        scores_out.append({
            "memory_id": s.memory_id,
            **s.components(),
            "is_exact_identifier": s.is_exact_identifier,
            "match_reasons": s.match_reasons,
        })
    memories_out = []
    for m in result.memories:
        memories_out.append({
            "id": m.id,
            "type": str(m.type) if hasattr(m.type, "value") else str(m.type),
            "content": m.content[:200],
            "project_id": m.project_id,
            "status": str(m.status) if hasattr(m.status, "value") else str(m.status),
        })
    related_out = []
    for m in result.related:
        related_out.append({
            "id": m.id,
            "type": str(m.type) if hasattr(m.type, "value") else str(m.type),
            "content": m.content[:200],
        })
    return json.dumps({
        "state": result.state.value,
        "query": result.query,
        "candidates": scores_out,
        "memories": memories_out,
        "related": related_out,
        "explanation": result.explanation,
        "clarification_dimension": result.clarification_dimension,
        "clarification_question": result.clarification_question,
        "clarifications_used": result.clarifications_used,
        "session_filters": result.session_filters,
        "identifier_constraint_applied": result.identifier_constraint_applied,
        "identifier_constraint_status": result.identifier_constraint_status,
        "identifier_matches": result.identifier_matches,
        "identifier_failure_reason": result.identifier_failure_reason,
    }, ensure_ascii=False, indent=2)


_STATE_ICONS = {
    RetrievalState.MEMORY_CONFIRMED: "[green]MEMORY_CONFIRMED[/green]",
    RetrievalState.AMBIGUOUS_CANDIDATES: "[yellow]AMBIGUOUS_CANDIDATES[/yellow]",
    RetrievalState.CLARIFICATION_REQUIRED: "[cyan]CLARIFICATION_REQUIRED[/cyan]",
    RetrievalState.MEMORY_NOT_FOUND: "[red]MEMORY_NOT_FOUND[/red]",
}

_STATE_HUMAN = {
    RetrievalState.MEMORY_CONFIRMED: "Lembrança confirmada — a memória foi localizada com confiança.",
    RetrievalState.AMBIGUOUS_CANDIDATES: "Ambiguidade — há múltiplas lembranças possíveis. Refine a consulta.",
    RetrievalState.CLARIFICATION_REQUIRED: "Esclarecimento necessário — uma informação adicional resolve a busca.",
    RetrievalState.MEMORY_NOT_FOUND: "Nenhuma lembrança localizada com os parâmetros fornecidos.",
}


def _print_assisted_result(result: AssistedRetrievalResult) -> None:
    """Pretty-print an assisted retrieval result for human consumption."""
    state = result.state
    console.print(f"\n[bold]Estado:[/bold] {_STATE_ICONS.get(state, state.value)}")
    console.print(f"[bold]Significado:[/bold] {_STATE_HUMAN.get(state, '')}")
    console.print(f"[bold]Consulta:[/bold] {result.query}")
    console.print(f"[bold]Esclarecimentos usados:[/bold] {result.clarifications_used}/3")

    if result.session_filters:
        console.print(f"[bold]Filtros de sessão:[/bold] {result.session_filters}")

    if result.identifier_constraint_applied:
        console.print(
            f"[bold]Restrição de identificador:[/bold] "
            f"{result.identifier_constraint_status}"
        )
        if result.identifier_failure_reason:
            console.print(f"[bold]Motivo:[/bold] {result.identifier_failure_reason}")

    if result.scores:
        table = Table(title="Candidatos")
        table.add_column("Rank", style="dim")
        table.add_column("ID")
        table.add_column("Tipo")
        table.add_column("Score", justify="right")
        table.add_column("ID Exacto", justify="center")
        table.add_column("Trecho")
        for i, s in enumerate(result.scores[:10], 1):
            mem = next((m for m in result.memories if m.id == s.memory_id), None)
            snippet = (mem.content[:80] + "..." if mem and len(mem.content) > 80 else mem.content) if mem else "(ausente)"
            mtype = str(mem.type) if mem and hasattr(mem.type, "value") else (str(mem.type) if mem else "?")
            exact = "S" if s.is_exact_identifier else ""
            table.add_row(str(i), s.memory_id, mtype, f"{s.final_score:.4f}", exact, snippet)
        console.print(table)

        # Score breakdown
        console.print("\n[bold]Decomposição dos scores:[/bold]")
        for s in result.scores[:5]:
            comp = s.components()
            console.print(
                f"  {s.memory_id}: id={comp['identifier_score']:.3f} "
                f"meta={comp['metadata_score']:.3f} text={comp['text_score']:.3f} "
                f"rel={comp['relation_score']:.3f} temp={comp['temporal_score']:.3f} "
                f"→ final={comp['final_score']:.3f}"
            )
            if s.match_reasons:
                console.print(f"    motivos: {'; '.join(s.match_reasons[:5])}")

    if state == RetrievalState.MEMORY_CONFIRMED and result.related:
        console.print(f"\n[bold]Memórias relacionadas ({len(result.related)}):[/bold]")
        for m in result.related:
            console.print(f"  {m.id} ({m.type}): {m.content[:100]}")

    if state == RetrievalState.CLARIFICATION_REQUIRED and result.clarification_question:
        console.print(f"\n[bold cyan]Pergunta de esclarecimento:[/bold cyan] {result.clarification_question}")
        console.print(f"[dim]Dimensão: {result.clarification_dimension}[/dim]")

    if state == RetrievalState.MEMORY_NOT_FOUND:
        console.print(
            "\n[dim]Nenhuma lembrança confiável foi localizada com os parâmetros "
            "e esclarecimentos fornecidos. Resultados aproximados não devem "
            "ser usados como memória confirmada.[/dim]"
        )


def _run_assisted_search(
    store: Storage,
    query: str,
    project_id: str | None,
    json_output: bool,
) -> None:
    """Run the R4 assisted retrieval pipeline with interactive clarification."""
    cycle = ClarificationCycle(store)
    turn = cycle.start(query, project_id=project_id)

    while True:
        result = turn.result

        if json_output:
            sys.stdout.write(_format_assisted_result_json(result))
            sys.stdout.write("\n")
            sys.stdout.flush()
        else:
            _print_assisted_result(result)

        if result.state != RetrievalState.CLARIFICATION_REQUIRED:
            break

        # Interactive clarification
        question = result.clarification_question or "Pode fornecer mais detalhes?"
        dim = result.clarification_dimension or ""

        if json_output:
            # In JSON mode, the question is already in the JSON output.
            # Exit so the caller can inspect and re-invoke with the answer.
            break

        # Human-interactive mode: prompt for answer
        console.print(f"\n[bold cyan]⚠ {question}[/bold cyan]")
        try:
            answer = click.prompt(
                f"  Resposta ({dim})",
                default="",
                show_default=False,
            )
        except (EOFError, KeyboardInterrupt):
            console.print("\n[yellow]Esclarecimento cancelado.[/yellow]")
            break

        if not answer or answer.strip() == "":
            answer = "não sei"

        turn = cycle.answer(answer)


@cli.command()
@click.argument("query")
@click.option("--project", "project_id", default=None)
@click.option("--strategy", default="hybrid",
              type=click.Choice(["lexical", "semantic", "hybrid"]),
              help="Estratégia de busca (modo R3)")
@click.option("--retrieval-mode", "retrieval_mode", default="hybrid",
              type=click.Choice(["hybrid", "assisted"]),
              help="Pipeline de recuperação: hybrid (R3, padrão) ou assisted (R4)")
@click.option("--top-k", default=10)
@click.option("--explain/--no-explain", default=False, help="Show score decomposition")
@click.option("--json", "json_output", is_flag=True, default=False,
              help="Saída estruturada em JSON (para integração com Harness)")
@click.option("--clarify-dimension", default=None,
              help="Dimensão do esclarecimento (usado com --clarify-answer)")
@click.option("--clarify-answer", default=None,
              help="Resposta ao esclarecimento anterior")
@click.pass_context
def search(
    ctx: click.Context,
    query: str,
    project_id: str | None,
    strategy: str,
    retrieval_mode: str,
    top_k: int,
    explain: bool,
    json_output: bool,
    clarify_dimension: str | None,
    clarify_answer: str | None,
) -> None:
    """Search memories by clues.

    Modos de recuperação:

    \b
    --retrieval-mode hybrid  : pipeline R3 (padrão, HybridRetriever)
    --retrieval-mode assisted: pipeline R4 (AssistedRetriever com 4 estados)

    No modo assisted, se o estado for CLARIFICATION_REQUIRED, o CLI
    perguntará interativamente por até 3 esclarecimentos.
    """
    store = _get_storage(ctx.obj["db"])

    if retrieval_mode == "assisted":
        _run_assisted_search(store, query, project_id, json_output)
        return

    # --- R3 / hybrid mode (existing behaviour, preserved) ---
    if strategy == "lexical":
        retriever = LexicalRetriever(store)
        results = retriever.search(query, project_id=project_id, top_k=top_k)
        table = Table(title=f"Lexical search: {query}")
        table.add_column("Rank", style="dim")
        table.add_column("ID")
        table.add_column("Type")
        table.add_column("Score")
        table.add_column("Snippet")
        for i, (mem, score) in enumerate(results, 1):
            table.add_row(str(i), mem.id, mem.type, f"{score:.3f}", mem.content[:80])
        console.print(table)
    else:
        cfg = RetrievalConfig(top_k=top_k)
        semantic = DeterministicSemanticAdapter()
        retriever = HybridRetriever(store, config=cfg, semantic=semantic)
        result = retriever.search(query, project_id=project_id, top_k=top_k)

        if json_output:
            scores_out = []
            for cs in result.candidate_scores:
                mem = store.get_memory(cs.memory_id)
                scores_out.append({
                    "memory_id": cs.memory_id,
                    "total_score": cs.total_score,
                    "type": str(mem.type) if mem and hasattr(mem.type, "value") else "?",
                    "snippet": mem.content[:200] if mem else "",
                    "decomposition": cs.explanation_decomposition,
                })
            sys.stdout.write(json.dumps({
                "quality": result.quality,
                "query": result.query,
                "candidates": scores_out,
                "conflicts": result.conflicts,
                "missing_information": result.missing_information,
            }, ensure_ascii=False, indent=2))
            sys.stdout.write("\n")
            sys.stdout.flush()
            return

        table = Table(title=f"Hybrid search: {query}")
        table.add_column("Rank", style="dim")
        table.add_column("ID")
        table.add_column("Type")
        table.add_column("Score")
        table.add_column("Snippet")
        for i, cs in enumerate(result.candidate_scores, 1):
            mem = store.get_memory(cs.memory_id)
            snippet = mem.content[:80] if mem else "(missing)"
            table.add_row(str(i), cs.memory_id, mem.type if mem else "?", f"{cs.total_score:.3f}", snippet)
        console.print(table)

        if explain:
            console.print("\n[bold]Score decomposition:[/bold]")
            for cs in result.candidate_scores[:5]:
                console.print(f"  {cs.memory_id}: {cs.explanation_decomposition}")

        if result.conflicts:
            console.print(f"\n[yellow]Conflicts: {result.conflicts}[/yellow]")
        if result.missing_information:
            console.print(f"\n[dim]Missing: {result.missing_information}[/dim]")


# ---------------------------------------------------------------------------
# explain
# ---------------------------------------------------------------------------


@cli.command()
@click.argument("query")
@click.option("--project", "project_id", default=None)
@click.pass_context
def explain(ctx: click.Context, query: str, project_id: str | None) -> None:
    """Show detailed explanation of retrieval for a query."""
    store = _get_storage(ctx.obj["db"])
    retriever = HybridRetriever(store, semantic=DeterministicSemanticAdapter())
    result = retriever.search(query, project_id=project_id)
    console.print(result.explanation)


# ---------------------------------------------------------------------------
# build-capsule
# ---------------------------------------------------------------------------


@cli.command()
@click.argument("query")
@click.option("--project", "project_id", default=None)
@click.option("--output", default=None, help="Save capsule to file")
@click.pass_context
def build_capsule(
    ctx: click.Context, query: str, project_id: str | None, output: str | None,
) -> None:
    """Build a contextual capsule."""
    store = _get_storage(ctx.obj["db"])
    retriever = HybridRetriever(store, semantic=DeterministicSemanticAdapter())
    builder = CapsuleBuilder(store, retriever)
    capsule = builder.build(query, project_id=project_id)
    prompt = build_resumption_prompt(capsule)
    console.print(prompt)
    if output:
        Path(output).write_text(prompt, encoding="utf-8")
        console.print(f"\n[green]Capsule saved to {output}[/green]")
    console.print(f"\n[dim]Capsule summary: {capsule.summary()}[/dim]")


# ---------------------------------------------------------------------------
# evaluate
# ---------------------------------------------------------------------------


@cli.command()
@click.argument("dataset_path", type=click.Path(exists=True))
@click.option("--raw-chars", default=0, type=int, help="Raw history size for reduction calc")
@click.option("--ablation/--no-ablation", default=False, help="Run all ablation variants")
@click.pass_context
def evaluate(
    ctx: click.Context, dataset_path: str, raw_chars: int, ablation: bool,
) -> None:
    """Run evaluation suite on a dataset."""
    store = _get_storage(ctx.obj["db"])
    dataset = EvalDataset.from_json(Path(dataset_path))
    console.print(f"Evaluating dataset: {dataset.name} ({len(dataset.queries)} queries)")

    if ablation:
        results = run_ablation(store, dataset, DeterministicSemanticAdapter())
        table = Table(title="Ablation Results")
        table.add_column("Variant")
        table.add_column("Hit@1")
        table.add_column("Hit@3")
        table.add_column("MRR")
        table.add_column("Precision@1")
        for name, am in results.items():
            table.add_row(
                name, f"{am.hit_1_rate:.3f}", f"{am.hit_3_rate:.3f}",
                f"{am.mrr:.3f}", f"{am.precision_1:.3f}",
            )
        console.print(table)
    else:
        retriever = HybridRetriever(store, semantic=DeterministicSemanticAdapter())
        evaluator = Evaluator(store, retriever)
        metrics = evaluator.evaluate(dataset, raw_history_chars=raw_chars)
        console.print(f"\n[bold]Results:[/bold]")
        console.print(f"  Hit@1: {metrics.hit_1_rate:.3f}")
        console.print(f"  Hit@3: {metrics.hit_3_rate:.3f}")
        console.print(f"  MRR:   {metrics.mrr:.3f}")
        console.print(f"  Precision@1: {metrics.precision_1:.3f}")
        console.print(f"  Fake source rate: {metrics.fake_source_rate:.4f}")
        console.print(f"  Capsule avg chars: {metrics.capsule_avg_chars}")
        console.print(f"  Reduction vs raw: {metrics.reduction_vs_raw:.1%}")


# ---------------------------------------------------------------------------
# export-report
# ---------------------------------------------------------------------------


@cli.command()
@click.argument("dataset_path", type=click.Path(exists=True))
@click.option("--output", default="report.md", help="Output report path")
@click.option("--version", default="0.1.0")
@click.option("--commit", default="")
@click.pass_context
def export_report(
    ctx: click.Context, dataset_path: str, output: str, version: str, commit: str,
) -> None:
    """Export evaluation report as Markdown."""
    store = _get_storage(ctx.obj["db"])
    dataset = EvalDataset.from_json(Path(dataset_path))
    retriever = HybridRetriever(store, semantic=DeterministicSemanticAdapter())
    evaluator = Evaluator(store, retriever)
    metrics = evaluator.evaluate(dataset)
    ablation_results = run_ablation(store, dataset, DeterministicSemanticAdapter())
    report = generate_report(metrics, ablation_results, dataset.name, version, commit)
    Path(output).write_text(report, encoding="utf-8")
    console.print(f"[green]Report written to {output}[/green]")


# ---------------------------------------------------------------------------
# show-lineage
# ---------------------------------------------------------------------------


@cli.command()
@click.argument("memory_id")
@click.pass_context
def show_lineage(ctx: click.Context, memory_id: str) -> None:
    """Show provenance chain for a memory record."""
    store = _get_storage(ctx.obj["db"])
    mem = store.get_memory(memory_id)
    if mem is None:
        console.print(f"[red]Memory {memory_id} not found[/red]")
        raise click.Abort()

    console.print(f"[bold]Lineage for {memory_id}[/bold]")
    console.print(f"  Type: {mem.type}")
    console.print(f"  Version: {mem.version}")
    console.print(f"  Supersedes: {mem.supersedes or 'none'}")
    console.print(f"  Superseded by: {mem.superseded_by or 'none'}")

    current = mem
    console.print("\n[bold]Forward chain:[/bold]")
    while current.superseded_by:
        nxt = store.get_memory(current.superseded_by)
        if nxt:
            console.print(f"  -> {nxt.id} (v{nxt.version})")
            current = nxt
        else:
            break

    current = mem
    console.print("\n[bold]Backward chain:[/bold]")
    while current.supersedes:
        prev = store.get_memory(current.supersedes)
        if prev:
            console.print(f"  <- {prev.id} (v{prev.version})")
            current = prev
        else:
            break

    rels = store.get_relations_for(memory_id)
    if rels:
        console.print(f"\n[bold]Relations ({len(rels)}):[/bold]")
        for r in rels:
            console.print(f"  {r.relation_type}: {r.source_id} -> {r.target_id}")


# ---------------------------------------------------------------------------
# ingest-project
# ---------------------------------------------------------------------------


@cli.command()
@click.option("--source", required=True, type=click.Path(exists=True),
              help="Project source root directory")
@click.option("--db", "db_override", default=None,
              help="SQLite database path (overrides global --db)")
@click.option("--project-id", default="mec-lab", help="Project identifier")
@click.option("--manifest", "manifest_path", default=None,
              help="Path to write the ingestion manifest JSON")
@click.option("--report", "report_path", default=None,
              help="Path to write the ingestion report JSON")
@click.option("--dry-run", is_flag=True, default=False,
              help="Generate manifest without writing memories")
@click.option("--include", "include_patterns", multiple=True, default=None,
              help="File patterns to include (repeatable)")
@click.option("--exclude", "exclude_patterns", multiple=True, default=None,
              help="File patterns to exclude (repeatable)")
@click.option("--json", "json_output", is_flag=True, default=False,
              help="Output report as JSON to stdout")
@click.option("--force-reindex", is_flag=True, default=False,
              help="Re-create memories even if they already exist")
@click.option("--include-git-history", is_flag=True, default=False,
              help="Ingest git commit history as evidence memories")
@click.option("--git-history-since", default=None,
              help="Git ref to start history from (e.g. 8501da0)")
@click.pass_context
def ingest_project(
    ctx: click.Context,
    source: str,
    db_override: str | None,
    project_id: str,
    manifest_path: str | None,
    report_path: str | None,
    dry_run: bool,
    include_patterns: tuple[str, ...],
    exclude_patterns: tuple[str, ...],
    json_output: bool,
    force_reindex: bool,
    include_git_history: bool,
    git_history_since: str | None,
) -> None:
    """Ingest a project's files into MEC structured memories.

    Reads git-tracked files, segments them, and creates deterministic
    memory records with full provenance metadata.

    Examples:

    \b
    # Dry run — generate manifest only
    python -m mec_lab ingest-project --source . --dry-run --manifest manifest.json

    \b
    # Full ingestion
    python -m mec_lab ingest-project --source . --db pilot.db --project-id mec-lab
    """
    db = db_override or ctx.obj["db"]
    store = _get_storage(db)

    inc = list(include_patterns) if include_patterns else None
    exc = list(exclude_patterns) if exclude_patterns else None

    pipeline = IngestionPipeline(
        source_root=source,
        project_id=project_id,
        storage=store,
        dry_run=dry_run,
        include_patterns=inc,
        exclude_patterns=exc,
        force_reindex=force_reindex,
        include_git_history=include_git_history,
        git_history_since=git_history_since,
    )

    report = pipeline.run()

    if json_output:
        sys.stdout.write(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
        sys.stdout.write("\n")
        sys.stdout.flush()
        return

    console.print(f"[bold]Ingestion Pipeline[/bold]")
    console.print(f"  Source: {source}")
    console.print(f"  Project: {project_id}")
    console.print(f"  Database: {db}")
    console.print(f"  Mode: {'DRY RUN' if dry_run else 'LIVE'}")

    console.print(f"\n[bold green]Ingestion complete.[/bold green]")
    console.print(f"  Files analyzed:  {report.files_analyzed}")
    console.print(f"  Files included:  {report.files_included}")
    console.print(f"  Files excluded:  {report.files_excluded}")
    console.print(f"  Memories created: {report.memories_created}")
    console.print(f"  Duplicates skipped: {report.memories_skipped}")
    console.print(f"  Relations created: {report.relations_created}")
    console.print(f"  Secrets blocked: {report.secrets_blocked}")
    console.print(f"  Errors:          {report.errors}")
    console.print(f"  Elapsed:         {report.elapsed_seconds}s")

    if report.errors:
        console.print(f"\n[yellow]Errors:[/yellow]")
        for e in report.error_details[:10]:
            console.print(f"  - {e}")

    if report.secrets_blocked:
        console.print(f"\n[cyan]Secrets blocked:[/cyan]")
        for s in report.secret_details:
            console.print(f"  - {s['path']}: {', '.join(s['reasons'])}")

    # Save manifest and report if paths provided
    if manifest_path:
        # Rebuild manifest for saving (pipeline builds it internally)
        manifest = IngestionManifest(
            pipeline_version="1.1.0",
            project_id=project_id,
            source_root=source,
            generated_at=report.start_time,
            total_files=report.files_analyzed,
            included_files=report.files_included,
            excluded_files=report.files_excluded,
            total_expected_memories=report.memories_created,
        )
        manifest.save(manifest_path)
        console.print(f"\n[dim]Manifest saved to {manifest_path}[/dim]")

    if report_path:
        report.save(report_path)
        console.print(f"[dim]Report saved to {report_path}[/dim]")


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
