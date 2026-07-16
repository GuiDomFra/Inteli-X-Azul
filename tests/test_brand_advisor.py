import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import anthropic

from brand_advisor import (
    BrandAdvisorError,
    compute_report_word_count,
    get_brand_parecer,
    load_brand_guidelines_text,
)


def _fake_response(parecer_dict, stop_reason="end_turn", model="claude-opus-4-8"):
    block = MagicMock(type="text", text=json.dumps(parecer_dict))
    return MagicMock(content=[block], stop_reason=stop_reason, model=model)


def test_get_brand_parecer_happy_path():
    fake = {
        "estado": "amarelo",
        "riscos": [{"diretriz": "tom_low_cost", "risco": "Menção a preço baixo."}],
        "sugestoes": ["Focar na experiência em vez do preço."],
    }
    with patch("brand_advisor.client.messages.create", return_value=_fake_response(fake)):
        result = get_brand_parecer("Renomear produto X para Y", "diretrizes de teste")
    assert result["estado"] == "amarelo"
    assert result["riscos"] == fake["riscos"]
    assert result["sugestoes"] == fake["sugestoes"]
    assert result["_model_id"] == "claude-opus-4-8"
    assert result["_word_count"] == compute_report_word_count(fake)


def test_get_brand_parecer_raises_on_refusal():
    with patch(
        "brand_advisor.client.messages.create",
        return_value=_fake_response({}, stop_reason="refusal"),
    ):
        try:
            get_brand_parecer("decisão qualquer", "diretrizes")
            assert False, "esperava BrandAdvisorError"
        except BrandAdvisorError as exc:
            assert exc.code == "refusal"


def test_get_brand_parecer_wraps_connection_errors():
    with patch(
        "brand_advisor.client.messages.create",
        side_effect=anthropic.APIConnectionError(request=MagicMock()),
    ):
        try:
            get_brand_parecer("decisão qualquer", "diretrizes")
            assert False, "esperava BrandAdvisorError"
        except BrandAdvisorError as exc:
            assert exc.code == "connection_error"


def test_get_brand_parecer_truncates_to_three_items():
    fake = {
        "estado": "vermelho",
        "riscos": [{"diretriz": f"d{i}", "risco": f"r{i}"} for i in range(5)],
        "sugestoes": [f"s{i}" for i in range(5)],
    }
    with patch("brand_advisor.client.messages.create", return_value=_fake_response(fake)):
        result = get_brand_parecer("decisão com muitos riscos", "diretrizes")
    assert len(result["riscos"]) == 3
    assert len(result["sugestoes"]) == 3


def test_get_brand_parecer_annotates_word_count():
    fake = {
        "estado": "verde",
        "riscos": [],
        "sugestoes": ["uma sugestão " * 50],
    }
    with patch("brand_advisor.client.messages.create", return_value=_fake_response(fake)):
        result = get_brand_parecer("decisão qualquer", "diretrizes")
    assert result["_word_count"] == compute_report_word_count(fake)
    assert result["_word_count"] > 0


def test_load_brand_guidelines_text_missing_file(tmp_path):
    try:
        load_brand_guidelines_text(path=tmp_path / "nao_existe.yaml")
        assert False, "esperava BrandAdvisorError"
    except BrandAdvisorError as exc:
        assert exc.code == "brandbook_missing"


def test_load_brand_guidelines_text_not_configured(tmp_path):
    path = tmp_path / "brand.yaml"
    path.write_text("brand_name: Teste\n", encoding="utf-8")
    try:
        load_brand_guidelines_text(path=path)
        assert False, "esperava BrandAdvisorError"
    except BrandAdvisorError as exc:
        assert exc.code == "brandbook_not_configured"


def test_load_brand_guidelines_text_invalid_yaml(tmp_path):
    path = tmp_path / "brand.yaml"
    path.write_text("chave: [nao fechado\n", encoding="utf-8")
    try:
        load_brand_guidelines_text(path=path)
        assert False, "esperava BrandAdvisorError"
    except BrandAdvisorError as exc:
        assert exc.code == "brandbook_invalid"


def test_load_brand_guidelines_text_configured(tmp_path):
    path = tmp_path / "brand.yaml"
    path.write_text("brand_name: Teste\nmetadata:\n  status: configured\n", encoding="utf-8")
    text = load_brand_guidelines_text(path=path)
    assert "Teste" in text


def test_load_brand_guidelines_text_without_vertical_has_no_vertical_specific_rule():
    text = load_brand_guidelines_text()
    assert "prazo_entrega_absoluto" not in text
    assert "verticais_ativas" not in text


def test_load_brand_guidelines_text_with_vertical_merges_additional_rules():
    text = load_brand_guidelines_text(vertical="cargo")
    assert "prazo_entrega_absoluto" in text
    assert "verticais_ativas" in text
    assert "Azul Cargo" in text
    # diretrizes do núcleo continuam presentes junto das da vertical
    assert "tom_low_cost" in text


def test_load_brand_guidelines_text_unknown_vertical_falls_back_to_core():
    text = load_brand_guidelines_text(vertical="vertical_que_nao_existe")
    assert "verticais_ativas" not in text


def test_load_brand_guidelines_text_with_multiple_verticals_merges_all():
    text = load_brand_guidelines_text(vertical=["cargo", "viagens"])
    # diretriz adicional de cada vertical selecionada presente
    assert "prazo_entrega_absoluto" in text
    assert "preco_pacote_final" in text
    # diretriz de uma vertical NÃO selecionada não deve aparecer
    assert "valor_ponto_implicito" not in text
    assert "Azul Cargo" in text
    assert "Azul Viagens" in text
    assert "tom_low_cost" in text
