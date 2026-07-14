import json
import time

import anthropic
import yaml

from config import ANTHROPIC_API_KEY, BRAND_GUIDELINES_PATH, CLAUDE_MODEL

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

BRAND_PARECER_SCHEMA = {
    "type": "object",
    "properties": {
        "veredito": {
            "type": "string",
            "enum": ["aprovado", "aprovado_com_ressalvas", "nao_aprovado", "precisa_mais_info"],
        },
        "risco": {"type": "string", "enum": ["baixo", "medio", "alto"]},
        "resumo": {"type": "string", "description": "Resumo do parecer em 1-2 frases."},
        "principais_riscos": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Riscos de marca identificados, cada um citando a diretriz relevante.",
        },
        "perguntas_antes_de_aprovar": {"type": "array", "items": {"type": "string"}},
        "recomendacao": {"type": "string"},
    },
    "required": [
        "veredito",
        "risco",
        "resumo",
        "principais_riscos",
        "perguntas_antes_de_aprovar",
        "recomendacao",
    ],
    "additionalProperties": False,
}

SYSTEM_PROMPT_TEMPLATE = """\
Você é um(a) estrategista de marca sênior atuando como consultor(a) proativo(a)
dentro da empresa. Seu papel é dar um "parecer de marca" rápido e acionável
ANTES que uma decisão (copy de marketing, nome de produto, direção de
campanha, posicionamento) seja finalizada — para que a marca tenha voz na
mesa antes que seja tarde demais.

Você receberá as diretrizes de marca da empresa e a descrição de uma decisão
que está prestes a ser tomada.

Regras:
- Avalie a decisão à luz das diretrizes de marca fornecidas abaixo.
- Seja específico: cite a diretriz concreta (tom de voz, valor, posicionamento
  ou item de "coisas a evitar") que embasa cada risco apontado — não seja
  genérico.
- Se a descrição da decisão for vaga ou faltar contexto crítico, não invente
  informação: registre isso em "perguntas_antes_de_aprovar" e ajuste o
  veredito para "precisa_mais_info" em vez de arriscar um parecer sem base.
- Seu tom é o de um colega experiente e pragmático — o objetivo é ajudar o
  time a decidir melhor e mais rápido, não bloquear por bloquear. Reserve
  "nao_aprovado" para riscos de marca claros e diretamente embasados nas
  diretrizes abaixo.

Diretrizes de marca (fonte de verdade):
<brand_guidelines>
{brand_guidelines_text}
</brand_guidelines>
"""


class BrandAdvisorError(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def load_brand_guidelines_text(path=BRAND_GUIDELINES_PATH) -> str:
    with open(path, "r", encoding="utf-8") as f:
        guidelines = yaml.safe_load(f)
    return yaml.dump(guidelines, allow_unicode=True, sort_keys=False)


def get_brand_parecer(decision_text: str, brand_guidelines_text: str) -> dict:
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(brand_guidelines_text=brand_guidelines_text)
    start = time.monotonic()
    try:
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=2048,
            system=system_prompt,
            output_config={"format": {"type": "json_schema", "schema": BRAND_PARECER_SCHEMA}},
            messages=[{"role": "user", "content": f"Decisão a avaliar:\n\n{decision_text}"}],
        )
    except anthropic.RateLimitError as e:
        raise BrandAdvisorError("rate_limited", str(e)) from e
    except anthropic.APIConnectionError as e:
        raise BrandAdvisorError("connection_error", str(e)) from e
    except anthropic.APIStatusError as e:
        raise BrandAdvisorError(f"api_error_{e.status_code}", e.message) from e

    latency_ms = int((time.monotonic() - start) * 1000)

    if response.stop_reason == "refusal":
        raise BrandAdvisorError("refusal", "O modelo recusou a solicitação.")
    if response.stop_reason == "max_tokens":
        raise BrandAdvisorError("truncated", "Resposta truncada por max_tokens.")

    text = next(b.text for b in response.content if b.type == "text")
    parecer = json.loads(text)
    parecer["_latency_ms"] = latency_ms
    parecer["_model_id"] = response.model
    parecer["_raw"] = text
    return parecer
