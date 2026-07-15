import json
import logging
import time

import anthropic
import yaml

from config import ANTHROPIC_API_KEY, BRAND_GUIDELINES_PATH, CLAUDE_MODEL

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
logger = logging.getLogger(__name__)

MAX_REPORT_WORDS = 300
NO_GUIDELINE_SENTINEL = "não há diretriz sobre isso"

BRAND_PARECER_SCHEMA = {
    "type": "object",
    "properties": {
        "semaforo": {
            "type": "string",
            "enum": ["verde", "amarelo", "vermelho"],
            "description": "verde=alinhado, amarelo=atenção, vermelho=conflito com o brandbook.",
        },
        "riscos": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "diretriz": {
                        "type": "string",
                        "description": (
                            "A diretriz específica do brandbook que embasa este risco "
                            f"(título/id da diretriz), ou '{NO_GUIDELINE_SENTINEL}' se o "
                            "brandbook não cobrir o assunto."
                        ),
                    },
                    "risco": {"type": "string", "description": "O risco em si, 1 frase curta."},
                },
                "required": ["diretriz", "risco"],
                "additionalProperties": False,
            },
            "description": "No máximo 3 pontos de risco, cada um citando a diretriz afetada.",
        },
        "sugestoes": {
            "type": "array",
            "items": {"type": "string"},
            "description": "No máximo 3 sugestões de ajuste para resolver os conflitos.",
        },
    },
    "required": ["semaforo", "riscos", "sugestoes"],
    "additionalProperties": False,
}

SYSTEM_PROMPT_TEMPLATE = """\
Você é um(a) estrategista de marca sênior da Azul Linhas Aéreas, consultado(a)
ANTES que uma proposta (campanha de destino, promoção TudoAzul, parceria da
Azul Viagens) seja finalizada — para que a visão de marca chegue à mesa de
aprovação com argumentos concretos, e não depois que já é caro mudar.

Você receberá o brandbook da Azul (fonte de verdade) e o texto de um
briefing ou proposta em estágio inicial. Pode também receber, opcionalmente,
público-alvo e canal da campanha.

Regras invioláveis:

1. Você NUNCA aprova nem reprova uma proposta. Você apenas informa riscos de
   marca através do semáforo e das listas abaixo. A decisão final é sempre
   humana — isso é estrutural, não opcional.

2. Baseie-se exclusivamente nas diretrizes de marca fornecidas em
   <brand_guidelines> abaixo. Não traga boas práticas genéricas de marketing
   que não estejam ali.

3. Nunca invente diretrizes. Se um aspecto da proposta tocar em um assunto que
   o brandbook não cobre, o campo "diretriz" desse item deve ser exatamente
   "não há diretriz sobre isso" — não fabrique uma regra para justificar uma
   opinião. Só inclua um item assim quando for relevante ser transparente
   sobre a ausência de diretriz; não force um item para cada detalhe não
   coberto.

4. Todo risco real deve citar a diretriz específica (pelo título/id em
   `diretrizes_proibidas`, ou o ponto relevante de `tom_de_voz`/`posicionamento`)
   que o embasa. Nunca diga apenas "isso não parece muito Azul" sem apontar a
   fonte.

5. No máximo 3 itens em "riscos" e no máximo 3 itens em "sugestoes". Se
   houver mais conflitos genuínos, mantenha só os 3 mais graves/claros. Se
   nada conflita, "riscos" pode ser uma lista vazia e o semáforo deve ser
   "verde".

6. Calibre o semáforo assim: "vermelho" = conflito direto com uma diretriz
   proibida explícita (ex.: tom low-cost, promessa de pontualidade absoluta,
   citar concorrente nominalmente); "amarelo" = desvio de tom/posicionamento
   ou risco menor, sem violar uma proibição explícita; "verde" = alinhado ou
   sem risco relevante o suficiente para sinalizar.

7. As SUAS PRÓPRIAS sugestões nunca podem: usar tom de empresa barata/low
   cost, prometer pontualidade absoluta/100%, ou citar/atacar concorrentes
   nominalmente. É fácil apontar uma violação no texto avaliado e reproduzir
   a mesma violação na sua sugestão de correção — preste atenção especial a
   isso.

8. O relatório completo (soma de todos os textos em "riscos" + "sugestoes")
   deve ter no máximo {max_words} palavras. Seja direto: uma a duas frases
   por item, sem preâmbulos repetidos.

9. Onde não comprometer precisão nem o limite de palavras, reflita o tom de
   voz da Azul (caloroso, brasileiro, acessível) no texto do parecer — isso é
   secundário a ser conciso e sempre citar a fonte.

10. Se público-alvo e/ou canal forem fornecidos no contexto adicional, use-os
    para calibrar a severidade do risco (a mesma frase pode ser um risco menor
    em um e-mail para o programa TudoAzul e um risco maior em mídia paga em
    redes sociais).

11. Se as diretrizes abaixo tiverem uma chave "verticais_ativas", ela lista
    qual(is) vertical(is) da Azul estão sendo avaliadas nesta proposta (ex.:
    Azul Cargo, Azul Viagens, TudoAzul, Azul Linhas Aéreas) — use o campo
    "foco" de cada uma para contextualizar a análise. As diretrizes_proibidas
    já vêm combinadas (núcleo + todas as verticais ativas) e devem ser usadas
    exatamente como estão. Se houver mais de uma vertical ativa (proposta
    conjunta entre verticais, ex. promoção TudoAzul + pacote Azul Viagens),
    considere as diretrizes de todas elas ao apontar riscos e garanta que
    cada sugestão funcione para todas as verticais envolvidas, não só para
    uma.

Diretrizes de marca (fonte de verdade):
<brand_guidelines>
{brand_guidelines_text}
</brand_guidelines>
"""


class BrandAdvisorError(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def load_brand_guidelines_text(
    path=BRAND_GUIDELINES_PATH, vertical: str | list[str] | None = None
) -> str:
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = f.read()
    except FileNotFoundError as e:
        raise BrandAdvisorError(
            "brandbook_missing", "Arquivo de brandbook não encontrado."
        ) from e

    try:
        guidelines = yaml.safe_load(raw)
    except yaml.YAMLError as e:
        raise BrandAdvisorError(
            "brandbook_invalid", "Brandbook malformado (YAML inválido)."
        ) from e

    if not guidelines or guidelines.get("metadata", {}).get("status") != "configured":
        raise BrandAdvisorError(
            "brandbook_not_configured",
            "Brandbook ainda não configurado (metadata.status != 'configured').",
        )

    guidelines = _apply_vertical(guidelines, vertical)

    return yaml.dump(guidelines, allow_unicode=True, sort_keys=False)


def _apply_vertical(guidelines: dict, vertical: str | list[str] | None) -> dict:
    """Combina o núcleo do brandbook com as diretrizes adicionais de uma ou
    mais verticais ativas (linhas_aereas/cargo/viagens/tudoazul) — útil para
    analisar de uma vez uma proposta que atravessa várias verticais (ex.:
    promoção conjunta TudoAzul + Azul Viagens), citando as diretrizes
    combinadas de todas as verticais envolvidas em um único parecer.

    Em qualquer caso, a chave "verticais" (metadados de todas as verticais)
    é removida do texto final — o modelo só deve ver as diretrizes que
    realmente se aplicam à análise em questão, nunca as das verticais não
    selecionadas, para não confundir a citação de fonte."""
    all_verticais = guidelines.get("verticais") or {}

    requested = [vertical] if isinstance(vertical, str) else list(vertical or [])
    selected_ids = [v for v in requested if v in all_verticais]

    guidelines = dict(guidelines)
    guidelines.pop("verticais", None)

    if not selected_ids:
        return guidelines

    extra_diretrizes = []
    verticais_ativas = []
    for vertical_id in selected_ids:
        vertical_info = all_verticais[vertical_id]
        verticais_ativas.append(
            {
                "id": vertical_id,
                "nome": vertical_info.get("nome", vertical_id),
                "foco": vertical_info.get("foco", ""),
            }
        )
        extra_diretrizes.extend(vertical_info.get("diretrizes_adicionais", []))

    guidelines["verticais_ativas"] = verticais_ativas
    guidelines["diretrizes_proibidas"] = (
        list(guidelines.get("diretrizes_proibidas", [])) + extra_diretrizes
    )
    return guidelines


def compute_report_word_count(parecer: dict) -> int:
    riscos_text = " ".join(f"{r['diretriz']} {r['risco']}" for r in parecer.get("riscos", []))
    sugestoes_text = " ".join(parecer.get("sugestoes", []))
    return len(f"{riscos_text} {sugestoes_text}".split())


def get_brand_parecer(
    decision_text: str,
    brand_guidelines_text: str,
    publico_alvo: str | None = None,
    canal: str | None = None,
) -> dict:
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
        brand_guidelines_text=brand_guidelines_text, max_words=MAX_REPORT_WORDS
    )

    user_content = f"Decisão a avaliar:\n\n{decision_text}"
    if publico_alvo or canal:
        user_content += "\n\nContexto adicional fornecido:"
        if publico_alvo:
            user_content += f"\n- Público-alvo: {publico_alvo}"
        if canal:
            user_content += f"\n- Canal: {canal}"

    start = time.monotonic()
    try:
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=4096,
            thinking={"type": "adaptive"},
            system=system_prompt,
            output_config={"format": {"type": "json_schema", "schema": BRAND_PARECER_SCHEMA}},
            messages=[{"role": "user", "content": user_content}],
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

    for key in ("riscos", "sugestoes"):
        items = parecer.get(key, [])
        if len(items) > 3:
            logger.warning("Modelo retornou %d itens em %r; truncando para 3.", len(items), key)
            parecer[key] = items[:3]

    word_count = compute_report_word_count(parecer)
    if word_count > MAX_REPORT_WORDS:
        logger.warning("Relatório excedeu %d palavras (%d).", MAX_REPORT_WORDS, word_count)

    parecer["_word_count"] = word_count
    parecer["_latency_ms"] = latency_ms
    parecer["_model_id"] = response.model
    parecer["_raw"] = text
    return parecer
