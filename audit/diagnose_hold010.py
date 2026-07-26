"""Deep diagnostic for hold-010."""
import sys, json
sys.path.insert(0, "src")

from mec_lab.retrieval import HybridRetriever, extract_clues
from mec_lab.storage import Storage
from mec_lab.evaluation import Evaluator, EvalDataset

store = Storage("test_r2.db")
store.init_schema()
retriever = HybridRetriever(store)

# Load the holdout
from pathlib import Path
dataset = EvalDataset.from_json(Path("audit/holdout_queries_r2.json"))

# Find hold-010
for q in dataset.queries:
    if "hold-010" in q.query_id:
        print(f"Query: {q.query_id}")
        print(f"Text: '{q.query}'")
        print(f"Expected IDs: {q.expected_ids}")
        print(f"Expected project: {q.expected_project_id}")
        print()
        
        clues = extract_clues(q.query, store)
        print(f"Clues: terms={clues.terms}")
        print(f"  wants_historical={clues.wants_historical}")
        print(f"  wants_current={clues.wants_current}")
        print(f"  wants_next_action={clues.wants_next_action}")
        print()
        
        result = retriever.search(q.query)
        print(f"Top-10 results:")
        for i, cs in enumerate(result.candidate_scores[:10]):
            mem = store.get_memory(cs.memory_id)
            marker = " <-- EXPECTED" if cs.memory_id in q.expected_ids else ""
            print(f"  {i+1}. {cs.memory_id} score={cs.total_score:.4f} type={mem.type.value if mem else '?'} content='{mem.content[:60] if mem else '?'}...'{marker}")
        
        # Check if checkpoint-queue-001 is in candidates at all
        found = False
        for i, cs in enumerate(result.candidate_scores):
            if cs.memory_id == "checkpoint-queue-001":
                print(f"\n  checkpoint-queue-001 found at rank {i+1} with score {cs.total_score:.4f}")
                found = True
                break
        if not found:
            print(f"\n  checkpoint-queue-001 NOT in candidate pool (top {len(result.candidate_scores)})")
            # Check if it's in the full candidate pool
            all_mems = store.list_all_memories()
            checkpoint = next((m for m in all_mems if m.id == "checkpoint-queue-001"), None)
            if checkpoint:
                print(f"  checkpoint content: '{checkpoint.content}'")
                print(f"  checkpoint type: {checkpoint.type}")
                print(f"  checkpoint project: {checkpoint.project_id}")
        
        break
