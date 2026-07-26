"""MEC Lab — CLI (Click).

Commands: init-db, load-dataset, add-memory, add-relation, create-episode,
create-checkpoint, search, explain, build-capsule, evaluate, export-report, show-lineage.
"""

from __future__ import annotations

import json
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
from mec_lab.retrieval import (
    DeterministicSemanticAdapter,
    HybridRetriever,
    LexicalRetriever,
    RetrievalConfig,
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


@cli.command()
@click.argument("query")
@click.option("--project", "project_id", default=None)
@click.option("--strategy", default="hybrid", type=click.Choice(["lexical", "semantic", "hybrid"]))
@click.option("--top-k", default=10)
@click.option("--explain/--no-explain", default=False, help="Show score decomposition")
@click.pass_context
def search(
    ctx: click.Context, query: str, project_id: str | None, strategy: str,
    top_k: int, explain: bool,
) -> None:
    """Search memories by clues."""
    store = _get_storage(ctx.obj["db"])

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


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
