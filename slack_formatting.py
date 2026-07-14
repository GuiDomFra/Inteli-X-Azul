import time

VERDICT_EMOJI = {
    "aprovado": "✅",
    "aprovado_com_ressalvas": "⚠️",
    "nao_aprovado": "🛑",
    "precisa_mais_info": "❓",
}

VERDICT_LABEL = {
    "aprovado": "Aprovado",
    "aprovado_com_ressalvas": "Aprovado com ressalvas",
    "nao_aprovado": "Não aprovado",
    "precisa_mais_info": "Precisa de mais informações",
}

RISK_EMOJI = {
    "baixo": "🟢",
    "medio": "🟡",
    "alto": "🔴",
}

# Cor de marca da Azul usada na barra lateral do attachment do Slack.
# Ajuste para o hex exato do guia de marca da Azul se ele for diferente.
AZUL_BLUE = "#003DA6"

BRAND_FOOTER = "✈️ Azul Linhas Aéreas · Parecer de Marca automático"


def format_slack_blocks(parecer: dict) -> list:
    emoji = VERDICT_EMOJI.get(parecer["veredito"], "")
    veredito_label = VERDICT_LABEL.get(parecer["veredito"], parecer["veredito"])
    risco_emoji = RISK_EMOJI.get(parecer["risco"], "")
    riscos = "\n".join(f"• {r}" for r in parecer["principais_riscos"]) or "—"
    perguntas = "\n".join(f"• {q}" for q in parecer["perguntas_antes_de_aprovar"]) or "—"
    return [
        {"type": "header", "text": {"type": "plain_text", "text": f"{emoji} Parecer de Marca"}},
        {
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": "✈️ *Azul Linhas Aéreas* · Parceria de Marca"}],
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Veredito*\n{emoji} {veredito_label}"},
                {"type": "mrkdwn", "text": f"*Risco*\n{risco_emoji} {parecer['risco'].capitalize()}"},
            ],
        },
        {"type": "section", "text": {"type": "mrkdwn", "text": parecer["resumo"]}},
        {"type": "divider"},
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Principais riscos de marca:*\n{riscos}"},
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Perguntas antes de aprovar:*\n{perguntas}"},
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Recomendação:*\n{parecer['recomendacao']}"},
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
    veredito_label = VERDICT_LABEL.get(parecer["veredito"], parecer["veredito"])
    return f"✈️ Parecer de Marca (Azul) — {veredito_label} (risco {parecer['risco']}): {parecer['resumo']}"
