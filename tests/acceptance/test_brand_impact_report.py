"""Teste de aceite (spec item 6) — chama a API real da Anthropic.

Não roda no `pytest` padrão (veja pytest.ini: `addopts = -m "not live"`).
Rodar explicitamente com:

    pytest -m live

Requer ANTHROPIC_API_KEY válida no ambiente; consome tokens reais.
"""

import os
import sys
import unicodedata
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from brand_advisor import compute_report_word_count, get_brand_parecer, load_brand_guidelines_text

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(
        not os.environ.get("ANTHROPIC_API_KEY"), reason="requer ANTHROPIC_API_KEY real"
    ),
]

TEST_BRIEFING = (
    "Vamos lançar a campanha 'Voe pagando menos com a Azul' — a passagem mais "
    "barata do Brasil, muito mais em conta que Gol e LATAM. E prometemos: com "
    "a Azul, seu voo NUNCA atrasa, pontualidade 100% garantida."
)

# Conjuntos de palavras-chave frouxos (case/acento-insensíveis) — casar
# string exata em citações de texto livre do modelo é frágil demais;
# keyword matching no texto diretriz+risco combinado é o meio-termo prático.
EXPECTED_VIOLATION_KEYWORDS = [
    ["barato", "baixo", "preco", "low cost", "low-cost", "pagando menos"],
    ["pontualidade", "atrasa", "atraso"],
    ["concorrente", "gol", "latam"],
]


def _normalize(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s.lower()) if unicodedata.category(c) != "Mn")


def test_three_known_violations_are_identified_as_red():
    guidelines_text = load_brand_guidelines_text()
    parecer = get_brand_parecer(TEST_BRIEFING, guidelines_text)

    assert parecer["semaforo"] == "vermelho"
    assert len(parecer["riscos"]) == 3

    combined_per_risk = [_normalize(r["diretriz"] + " " + r["risco"]) for r in parecer["riscos"]]
    for keywords in EXPECTED_VIOLATION_KEYWORDS:
        assert any(
            any(_normalize(kw) in text for kw in keywords) for text in combined_per_risk
        ), f"Nenhum risco cita palavras-chave de {keywords}. Riscos retornados: {parecer['riscos']}"

    assert 1 <= len(parecer["sugestoes"]) <= 3
    assert compute_report_word_count(parecer) <= 300

    suggestions_text = _normalize(" ".join(parecer["sugestoes"]))
    for banned in ("gol", "latam", "100%"):
        assert banned not in suggestions_text
