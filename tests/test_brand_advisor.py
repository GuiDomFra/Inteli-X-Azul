import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import anthropic

from brand_advisor import BrandAdvisorError, get_brand_parecer


def _fake_response(parecer_dict, stop_reason="end_turn", model="claude-opus-4-8"):
    block = MagicMock(type="text", text=json.dumps(parecer_dict))
    return MagicMock(content=[block], stop_reason=stop_reason, model=model)


def test_get_brand_parecer_happy_path():
    fake = {
        "veredito": "aprovado_com_ressalvas",
        "risco": "medio",
        "resumo": "Ok com ajustes.",
        "principais_riscos": ["Nome pode confundir com concorrente X"],
        "perguntas_antes_de_aprovar": ["Já checamos disponibilidade de domínio?"],
        "recomendacao": "Ajustar o nome antes de anunciar.",
    }
    with patch("brand_advisor.client.messages.create", return_value=_fake_response(fake)):
        result = get_brand_parecer("Renomear produto X para Y", "diretrizes de teste")
    assert result["veredito"] == "aprovado_com_ressalvas"
    assert result["principais_riscos"] == fake["principais_riscos"]
    assert result["_model_id"] == "claude-opus-4-8"


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
