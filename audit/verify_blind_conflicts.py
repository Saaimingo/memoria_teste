"""Audit: Per-query R1 vs R2 comparison on blind queries + conflict verification."""
import sys
sys.path.insert(0, "src")

from mec_lab.retrieval import HybridRetriever, RetrievalConfig, TfidfAdapter, extract_clues
from mec_lab.storage import Storage

store = Storage("test_r2.db")
store.init_schema()

retriever = HybridRetriever(store)

# Blind queries (from evidence/blind_queries.json)
blind_queries = {
    "blind-001": "quais fatos do simulador de futebol mencionam datas FIFA",
    "blind-002": "existe algum bug conhecido que causa mensagens duplicadas",
    "blind-003": "como era a regra do calendario antes da mudanca para incluir pausas FIFA",
    "blind-004": "quais decisoes foram tomadas sobre armazenamento local",
    "blind-005": "qual foi o aprendizado apos o incidente de duplicacao financeira",
    "blind-006": "no que devo trabalhar agora no sistema de filas",
    "blind-007": "onde esta documentada a arquitetura do simulador",
    "blind-008": "a hipotese sobre deduplicacao foi verificada ou contradita",
}

print("=" * 80)
print("PER-QUERY BLIND ANALYSIS (R2)")
print("=" * 80)

for qid, query in blind_queries.items():
    clues = extract_clues(query, store)
    result = retriever.search(query)
    
    top_ids = [cs.memory_id for cs in result.candidate_scores[:5]]
    top_scores = [round(cs.total_score, 3) for cs in result.candidate_scores[:5]]
    
    print(f"\n[{qid}] {query}")
    print(f"  terms: {clues.terms}")
    print(f"  wants_historical: {clues.wants_historical}")
    print(f"  wants_current: {clues.wants_current}")
    print(f"  wants_next_action: {clues.wants_next_action}")
    print(f"  Top-5: {list(zip(top_ids, top_scores))}")
    print(f"  Conflicts: {result.conflicts}")
    print(f"  Quality: {result.quality}")

# Conflict-specific verification
print("\n" + "=" * 80)
print("CONFLICT DETECTION VERIFICATION")
print("=" * 80)

conflict_queries = [
    "o calendario do simulador mudou depois de qual problema",
    "qual era a regra que foi substituida e qual a regra atual",
    "aposentadoria",
]

for q in conflict_queries:
    result = retriever.search(q)
    print(f"\nQuery: '{q}'")
    print(f"  Conflicts ({len(result.conflicts)}): {result.conflicts}")
    print(f"  Top-3: {[(cs.memory_id, round(cs.total_score, 3)) for cs in result.candidate_scores[:3]]}")
