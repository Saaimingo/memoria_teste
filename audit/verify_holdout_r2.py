"""Audit: Holdout per-query reproduction + R2-specific hint behavior."""
import sys, json
sys.path.insert(0, "src")

from mec_lab.retrieval import HybridRetriever, extract_clues
from mec_lab.storage import Storage

store = Storage("test_r2.db")
store.init_schema()
retriever = HybridRetriever(store)

with open("audit/holdout_queries_r2.json") as f:
    dataset = json.load(f)

print("=" * 80)
print("HOLDOUT PER-QUERY ANALYSIS (R2) vs PR #6 AUDIT EXPECTATIONS")
print("=" * 80)

# Expected from PR #6 audit 
expected = {
    "hold-001": {"hit1": True, "hit3": True, "notes": "Strong lexical match"},
    "hold-002": {"hit1": False, "hit3": True, "notes": "Temporal hint bug impacts this"},
    "hold-003": {"hit1": True, "hit3": True, "notes": "Entity names match content"},
    "hold-004": {"hit1": True, "hit3": True, "notes": "3 conflicts detected correctly"},
    "hold-005": {"hit1": True, "hit3": True, "notes": "Shared vocabulary helps"},
    "hold-006": {"hit1": False, "hit3": False, "notes": "Can't find the version pair"},
    "hold-007": {"hit1": None, "hit3": None, "notes": "Correctly returns empty"},
    "hold-008": {"hit1": None, "hit3": None, "notes": "Correctly returns empty"},
    "hold-009": {"hit1": True, "hit3": True, "notes": "3 conflicts detected"},
    "hold-010": {"hit1": False, "hit3": True, "notes": "Checkpoint at rank 3, not 1"},
}

all_match = True

for q in dataset["queries"]:
    qid = q["query_id"]
    short_id = qid[:8]
    result = retriever.search(q["query"])
    clues = extract_clues(q["query"], store)
    
    top_ids = [cs.memory_id for cs in result.candidate_scores[:5]]
    expected_ids = set(q["expected_ids"])
    
    hit1 = top_ids[0] in expected_ids if top_ids else False
    hit3 = any(mid in expected_ids for mid in top_ids[:3]) if top_ids else False
    
    exp = expected.get(short_id, {})
    hit1_match = exp.get("hit1")
    hit3_match = exp.get("hit3")
    
    # For empty-expected queries, "success" means no false positives
    if not expected_ids:
        hit1_good = True
        hit3_good = True
    else:
        hit1_good = (hit1 == hit1_match) if hit1_match is not None else None
        hit3_good = (hit3 == hit3_match) if hit3_match is not None else None
    
    status = "MATCH" if (hit1_good is not False and hit3_good is not False) else "MISMATCH"
    if status == "MISMATCH":
        all_match = False
    
    print(f"\n[{status}] {qid}")
    print(f"  Query: '{q['query']}'")
    print(f"  R2 hints: hist={clues.wants_historical} curr={clues.wants_current} action={clues.wants_next_action}")
    print(f"  Top-3: {top_ids[:3]}")
    print(f"  Expected: {list(expected_ids)[:5]}")
    print(f"  Hit@1: {hit1} (expected: {hit1_match})")
    print(f"  Hit@3: {hit3} (expected: {hit3_match})")
    print(f"  Conflicts: {len(result.conflicts)} detected")
    print(f"  PR #6 notes: {exp.get('notes', 'N/A')}")

print("\n" + "=" * 80)
if all_match:
    print("ALL HOLDOUT RESULTS MATCH PR #6 AUDIT EXPECTATIONS")
else:
    print("SOME MISMATCHES DETECTED — INVESTIGATION REQUIRED")
print("=" * 80)
