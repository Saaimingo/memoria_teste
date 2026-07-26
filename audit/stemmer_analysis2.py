"""Stemmer analysis — corrected: normalize before stemming."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from mec_lab.retrieval.normalize import stem_pt, normalize as norm


def stem(word: str) -> str:
    return stem_pt(norm(word))


def analyze():
    should_match = [
        ("processar", "processamento"),
        ("notificar", "notificação"),
        ("implementar", "implementação"),
        ("migrar", "migração"),
        ("validar", "validação"),
        ("duplicar", "duplicação"),
        ("reiniciar", "reinicialização"),
        ("decisão", "decidir"),
        ("conclusão", "concluir"),
        ("execução", "executar"),
        ("processados", "processar"),
        ("enviadas", "enviar"),
        ("bloqueio", "bloquear"),
        ("risco", "arriscado"),
        ("alertas", "alerta"),
        ("notificações", "notificação"),
        ("eventos", "evento"),
        ("métricas", "métrica"),
    ]

    should_not_match = [
        ("medicamento", "médico"),
        ("paciente", "paciência"),
        ("ponta", "ponto"),
        ("consulta", "consultório"),
        ("prescrição", "prescrito"),
    ]

    print("=" * 70)
    print("STEM OVERLAP ANALYSIS (with normalize)")
    print("=" * 70)

    print("\n--- SHOULD MATCH ---")
    under = 0
    for w1, w2 in should_match:
        s1, s2 = stem(w1), stem(w2)
        match = s1 == s2
        if not match:
            under += 1
        status = "✓" if match else "✗ UNDER"
        print(f"  [{status}] {w1} → '{s1}'  |  {w2} → '{s2}'")

    print(f"\n  Under-stemming: {under}/{len(should_match)}")

    print("\n--- SHOULD NOT MATCH ---")
    over = 0
    for w1, w2 in should_not_match:
        s1, s2 = stem(w1), stem(w2)
        match = s1 == s2
        if match:
            over += 1
        status = "✗ OVER" if match else "✓"
        print(f"  [{status}] {w1} → '{s1}'  |  {w2} → '{s2}'")

    print(f"\n  Over-stemming: {over}/{len(should_not_match)}")

    # Detailed trace for known issues
    print("\n--- DETAILED TRACES ---")
    for w in ["notificacao", "implementacao", "reinicializacao", "medicamento", "medico", "ponta", "ponto"]:
        print(f"  {w}: normalize='{norm(w)}', stem='{stem_pt(norm(w))}'")

    print(f"\n=== SUMMARY ===")
    print(f"Under-stemming: {under}, Over-stemming: {over}")


if __name__ == "__main__":
    analyze()
