import time

from brand_advisor import NO_GUIDELINE_SENTINEL

ESTADO_EMOJI = {"verde": "🟢", "amarelo": "🟡", "vermelho": "🔴"}
ESTADO_LABEL = {"verde": "Alinhado", "amarelo": "Atenção", "vermelho": "Conflito"}

# Cor de marca da Azul usada na barra lateral do attachment do Slack.
# TODO: valor ainda não confirmado com o time de marca da Azul — ajustar
# para o hex exato do guia de identidade visual assim que disponível.
AZUL_BLUE = "#003DA6"

BRAND_FOOTER = "✈️ Azul Linhas Aéreas · Tucano (parecer de marca automático)"

DISCLAIMER = "Este parecer é informativo — a decisão final é sempre da equipe de marca."


def _format_risco(risco: dict) -> str:
    diretriz = risco["diretriz"]
    if diretriz == NO_GUIDELINE_SENTINEL:
        return f"• _Sem diretriz aplicável_: {risco['risco']}"
    return f"• *{diretriz}*: {risco['risco']}"


def format_slack_blocks(parecer: dict) -> list:
    emoji = ESTADO_EMOJI.get(parecer["estado"], "")
    label = ESTADO_LABEL.get(parecer["estado"], parecer["estado"])
    riscos = "\n".join(_format_risco(r) for r in parecer["riscos"]) or "Nenhum risco de marca identificado."
    sugestoes = "\n".join(f"• {s}" for s in parecer["sugestoes"]) or "—"

    return [
        {"type": "header", "text": {"type": "plain_text", "text": f"{emoji} Tucano · Parecer de Marca"}},
        {
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": "✈️ *Azul Linhas Aéreas* · Tucano"}],
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Semáforo*\n{emoji} {label}"},
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Pontos de risco:*\n{riscos}"},
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Sugestões de ajuste:*\n{sugestoes}"},
        },
        {
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": DISCLAIMER}],
        },
    ]


def format_slack_attachment(parecer: dict) -> dict:
    return {
        "color": AZUL_BLUE,
        "blocks": format_slack_blocks(parecer),
        "footer": BRAND_FOOTER,
        "ts": int(time.time()),
    }


def format_fallback_text(parecer: dict) -> str:
    label = ESTADO_LABEL.get(parecer["estado"], parecer["estado"])
    n = len(parecer["riscos"])
    return f"✈️ Tucano (Azul) — {label} ({n} risco(s) identificado(s))."
