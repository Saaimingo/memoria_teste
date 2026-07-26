"""Audit verification script — checks critical issues without modifying source."""
import sys
sys.path.insert(0, "src")

from mec_lab.retrieval.normalize import STOPWORDS, tokenize, token_set
from mec_lab.retrieval import extract_clues, HybridRetriever, TfidfAdapter
from mec_lab.storage import Storage
from mec_lab.domain.models import Fact, MemoryRelation
from mec_lab.domain.enums import EpistemicStatus, RelationType, MemoryType

print("=" * 60)
print("AUDIT CHECK 1: Stopword vs temporal hint overlap")
print("=" * 60)

historical_words = {"antes", "anterior", "antigo", "velho", "obsoleto", "era", "antiga"}
current_words = {"atual", "agora", "vigente", "hoje", "corrente"}
action_words = {"trabalhar", "proximo", "pendente", "fazer", "falta"}

overlap_hist = historical_words & STOPWORDS
overlap_curr = current_words & STOPWORDS
overlap_act = action_words & STOPWORDS

print(f"Historical words ALSO in stopwords: {overlap_hist}")
print(f"Current words ALSO in stopwords: {overlap_curr}")
print(f"Action words ALSO in stopwords: {overlap_act}")

if overlap_hist:
    print(f"\n*** BUG: {overlap_hist} are in STOPWORDS but also used as temporal hints.")
    print("    These words will be removed from terms before hint check → hints never fire.")

# Test temporal hint with 'antes' removed
clues = extract_clues("como era o calendario antes da mudanca")
print(f"\nQuery: 'como era o calendario antes da mudanca'")
print(f"Terms (stopwords removed): {clues.terms}")
print(f"wants_historical: {clues.wants_historical}")
print(f"wants_current: {clues.wants_current}")
if "antes" in STOPWORDS and not clues.wants_historical:
    print("*** CONFIRMED: 'antes' in stopwords breaks temporal hint detection")

print()
print("=" * 60)
print("AUDIT CHECK 2: Conflict detection for SUPERSEDES")
print("=" * 60)

store = Storage(":memory:")
store.init_schema()

old = Fact(id="old", content="Old rule", project_id="p1",
           status=EpistemicStatus.OBSOLETE)
new = Fact(id="new", content="New rule", project_id="p1",
           status=EpistemicStatus.VERIFIED, supersedes="old")
old.superseded_by = "new"
store.save_memory(old)
store.save_memory(new)
store.save_relation(MemoryRelation(
    source_id="new", target_id="old", relation_type=RelationType.SUPERSEDES,
))

retriever = HybridRetriever(store)
result = retriever.search("rule", project_id="p1")
print(f"Conflicts found: {result.conflicts}")
print(f"Conflict count: {len(result.conflicts)}")
if len(result.conflicts) > 0:
    print("PASS: SUPERSEDES conflict detection works")
else:
    print("FAIL: SUPERSEDES conflict detection broken")

print()
print("=" * 60)
print("AUDIT CHECK 3: TF-IDF adapter behavior")
print("=" * 60)

store2 = Storage(":memory:")
store2.init_schema()
store2.save_memory(Fact(id="f1", content="Football simulator calendar FIFA dates.",
                         project_id="p1", status=EpistemicStatus.VERIFIED))
store2.save_memory(Fact(id="f2", content="Financial alerts duplication restart.",
                         project_id="p2", status=EpistemicStatus.VERIFIED))
store2.save_memory(Fact(id="f3", content="Queue inventory items duplication after restart.",
                         project_id="p3", status=EpistemicStatus.VERIFIED))

adapter = TfidfAdapter(store2)
print(f"Vocab size: {len(adapter._vocab)}")
print(f"Available: {adapter.is_available()}")

# Test similarity between related phrases
v_finance = adapter.embed(["financial alerts duplicate"])[0]
v_queue = adapter.embed(["queue items duplicate"])[0]
v_football = adapter.embed(["football calendar"])[0]

# cosine
import math
def cosine(a, b):
    dot = sum(x*y for x,y in zip(a,b))
    na = math.sqrt(sum(x*x for x in a))
    nb = math.sqrt(sum(y*y for y in b))
    return dot/(na*nb) if na*nb > 0 else 0

sim_fin_queue = cosine(v_finance, v_queue)
sim_fin_fb = cosine(v_finance, v_football)
print(f"Similarity(finance, queue): {sim_fin_queue:.4f}")
print(f"Similarity(finance, football): {sim_fin_fb:.4f}")
# Queue should be more similar to finance (both about duplication) than to football
print(f"Finance-queue more similar than finance-football: {sim_fin_queue >= sim_fin_fb}")

print()
print("=" * 60)
print("AUDIT CHECK 4: Stopwords filter quality")
print("=" * 60)

# Check what tokens are produced for various queries
test_queries = [
    "o que foi feito no projeto de futebol",
    "por que o Redis foi escolhido",
    "aquele sistema que tinha bug de repetição quando ligava de novo",
    "no que devo trabalhar agora no projeto de estoque",
]
for q in test_queries:
    tokens = tokenize(q)
    tokens_all = tokenize(q, remove_stopwords=False)
    print(f"Query: '{q}'")
    print(f"  All tokens: {tokens_all}")
    print(f"  Content tokens: {tokens}")
    print()

print("=" * 60)
print("AUDIT CHECK 5: Token sets for blind queries")
print("=" * 60)

# Check overlap between blind query tokens and target content
blind_queries = [
    ("blind-001", "aquele sistema que tinha bug de repetição quando ligava de novo",
     ["Sistema enviava alertas duplicados sempre que o serviço reiniciava.",
      "Sistema perdia confirmação de itens processados ao reiniciar."]),
    ("blind-007", "por que o Redis foi escolhido",
     ["Usar Redis para cache de idempotência com TTL de 24h; não usar banco relacional para deduplicação em tempo real."]),
]

for qid, query, targets in blind_queries:
    q_tokens = token_set(query)
    print(f"{qid}: {query}")
    print(f"  Query tokens: {q_tokens}")
    for ti, target in enumerate(targets):
        t_tokens = token_set(target)
        overlap = q_tokens & t_tokens
        union = q_tokens | t_tokens
        jaccard = len(overlap) / len(union) if union else 0
        print(f"  Target {ti}: overlap={overlap}, jaccard={jaccard:.4f}")
    print()

print("=" * 60)
print("AUDIT COMPLETE")
print("=" * 60)
