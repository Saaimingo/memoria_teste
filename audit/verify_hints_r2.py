"""Audit verification: R1 vs R2 temporal hint comparison."""
import sys
sys.path.insert(0, "src")

from mec_lab.retrieval import extract_clues

# Test queries that should trigger temporal hints in R2 but were broken in R1
test_queries = [
    # (query, expected_wants_historical, expected_wants_current, expected_wants_next_action, description)
    ("com o era o calendario antes da mudanca", True, False, False, "antes -> wants_historical"),
    ("o que era aquilo", True, False, False, "era -> wants_historical (ambiguous but fires)"),
    ("o que fazer agora", False, True, True, "fazer+agora -> wants_next_action+wants_current"),
    ("qual a regra atual", False, True, False, "atual -> wants_current"),
    ("o que devo fazer", False, False, True, "fazer -> wants_next_action"),
    ("o que esta pendente", False, False, True, "pendente -> wants_next_action"),
    ("futebol calendario simulador", False, False, False, "neutral -> all false"),
    ("antes de fazer o trabalho atual", True, True, True, "multiple hints simultaneously"),
    ("como era o calendario antes da mudanca atual", True, True, False, "stopwords not in terms"),
]

print("=" * 80)
print("R2 TEMPORAL HINT VERIFICATION")
print("=" * 80)

all_passed = True

for query, exp_hist, exp_curr, exp_action, desc in test_queries:
    clues = extract_clues(query)
    hist_ok = clues.wants_historical == exp_hist
    curr_ok = clues.wants_current == exp_curr
    action_ok = clues.wants_next_action == exp_action
    
    # Verify stopwords not in terms
    stopwords_in_terms = [t for t in ["como", "era", "o", "antes", "da", "de", "que", "fazer", "agora"] 
                          if t in clues.terms]
    terms_clean = len(stopwords_in_terms) == 0
    
    status = "PASS" if (hist_ok and curr_ok and action_ok and terms_clean) else "FAIL"
    if status == "FAIL":
        all_passed = False
    
    print(f"\n[{status}] {desc}")
    print(f"  Query: '{query}'")
    print(f"  terms: {clues.terms}")
    print(f"  wants_historical: {clues.wants_historical} (expected {exp_hist}) {'OK' if hist_ok else 'MISMATCH'}")
    print(f"  wants_current:    {clues.wants_current} (expected {exp_curr}) {'OK' if curr_ok else 'MISMATCH'}")
    print(f"  wants_next_action: {clues.wants_next_action} (expected {exp_action}) {'OK' if action_ok else 'MISMATCH'}")
    if stopwords_in_terms:
        print(f"  STOPWORD LEAKAGE: {stopwords_in_terms}")

print("\n" + "=" * 80)
if all_passed:
    print("ALL VERIFICATIONS PASSED")
else:
    print("SOME VERIFICATIONS FAILED")
print("=" * 80)
