import json

from slack_bolt import App

from brand_advisor import BrandAdvisorError, get_brand_parecer, load_brand_guidelines_text
from command_parsing import parse_parecer_command
from config import SLACK_BOT_TOKEN, SLACK_SIGNING_SECRET
from db import insert_decision
from slack_formatting import format_fallback_text, format_slack_attachment

bolt_app = App(token=SLACK_BOT_TOKEN, signing_secret=SLACK_SIGNING_SECRET)

_BRANDBOOK_ERROR_MESSAGES = {
    "brandbook_missing": (
        "Ainda não há um brandbook da Azul configurado para este agente. "
        "Peça ao time de marca para configurar `brand_guidelines.yaml` antes "
        "de gerar pareceres."
    ),
    "brandbook_invalid": (
        "O brandbook da Azul (`brand_guidelines.yaml`) está malformado e não "
        "pôde ser lido. Avise o time de marca."
    ),
    "brandbook_not_configured": (
        "O brandbook da Azul ainda não foi marcado como configurado "
        "(`metadata.status: configured`). Peça ao time de marca para revisar "
        "e confirmar `brand_guidelines.yaml`."
    ),
}


def ack_command(ack):
    ack()


def handle_parecer(body, client, logger):
    raw_text = body.get("text", "").strip()
    channel_id = body["channel_id"]
    user_id = body["user_id"]
    team_id = body.get("team_id")

    if not raw_text:
        client.chat_postEphemeral(
            channel=channel_id,
            user=user_id,
            text="Use assim: `/parecer-marca <descrição da decisão> | publico: ... | canal: ...`",
        )
        return

    decision_text, extra = parse_parecer_command(raw_text)
    if not decision_text:
        client.chat_postEphemeral(
            channel=channel_id,
            user=user_id,
            text="Descreva a decisão antes dos filtros `publico:`/`canal:`.",
        )
        return

    try:
        guidelines_text = load_brand_guidelines_text()
    except BrandAdvisorError as exc:
        logger.error("Brandbook indisponível: %s", exc)
        client.chat_postEphemeral(
            channel=channel_id,
            user=user_id,
            text=_BRANDBOOK_ERROR_MESSAGES.get(
                exc.code, "Não foi possível carregar o brandbook da Azul."
            ),
        )
        return

    try:
        parecer = get_brand_parecer(
            decision_text,
            guidelines_text,
            publico_alvo=extra.get("publico_alvo"),
            canal=extra.get("canal"),
        )
    except BrandAdvisorError as exc:
        logger.error("Falha ao gerar parecer de marca: %s", exc)
        client.chat_postMessage(
            channel=channel_id,
            text="Não consegui gerar o parecer de marca agora. Tente novamente em instantes.",
        )
        insert_decision(
            slack_team_id=team_id,
            slack_channel_id=channel_id,
            slack_user_id=user_id,
            decision_text=decision_text,
            publico_alvo=extra.get("publico_alvo"),
            canal=extra.get("canal"),
            error=str(exc),
        )
        return

    result = client.chat_postMessage(
        channel=channel_id,
        attachments=[format_slack_attachment(parecer)],
        text=format_fallback_text(parecer),
        username="Tucano · Azul",
        icon_emoji=":airplane:",
    )
    insert_decision(
        slack_team_id=team_id,
        slack_channel_id=channel_id,
        slack_user_id=user_id,
        slack_message_ts=result["ts"],
        decision_text=decision_text,
        publico_alvo=extra.get("publico_alvo"),
        canal=extra.get("canal"),
        model_id=parecer.get("_model_id"),
        semaforo=parecer["semaforo"],
        riscos_json=json.dumps(parecer["riscos"], ensure_ascii=False),
        sugestoes_json=json.dumps(parecer["sugestoes"], ensure_ascii=False),
        raw_model_response=parecer.get("_raw"),
        latency_ms=parecer.get("_latency_ms"),
        word_count=parecer.get("_word_count"),
        word_count_exceeded=int(parecer.get("_word_count", 0) > 300),
    )


bolt_app.command("/parecer-marca")(ack=ack_command, lazy=[handle_parecer])
