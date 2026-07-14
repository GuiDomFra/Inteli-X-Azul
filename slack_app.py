import json

from slack_bolt import App

from brand_advisor import BrandAdvisorError, get_brand_parecer, load_brand_guidelines_text
from config import SLACK_BOT_TOKEN, SLACK_SIGNING_SECRET
from db import insert_decision
from slack_formatting import format_fallback_text, format_slack_attachment

bolt_app = App(token=SLACK_BOT_TOKEN, signing_secret=SLACK_SIGNING_SECRET)


def ack_command(ack):
    ack()


def handle_parecer(body, client, logger):
    decision_text = body.get("text", "").strip()
    channel_id = body["channel_id"]
    user_id = body["user_id"]
    team_id = body.get("team_id")

    if not decision_text:
        client.chat_postEphemeral(
            channel=channel_id,
            user=user_id,
            text="Use assim: `/parecer-marca <descrição da decisão>`",
        )
        return

    guidelines_text = load_brand_guidelines_text()
    try:
        parecer = get_brand_parecer(decision_text, guidelines_text)
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
            error=str(exc),
        )
        return

    result = client.chat_postMessage(
        channel=channel_id,
        attachments=[format_slack_attachment(parecer)],
        text=format_fallback_text(parecer),
        username="Parecer de Marca · Azul",
        icon_emoji=":airplane:",
    )
    insert_decision(
        slack_team_id=team_id,
        slack_channel_id=channel_id,
        slack_user_id=user_id,
        slack_message_ts=result["ts"],
        decision_text=decision_text,
        model_id=parecer.get("_model_id"),
        veredito=parecer["veredito"],
        risco=parecer["risco"],
        resumo=parecer["resumo"],
        riscos_json=json.dumps(parecer["principais_riscos"]),
        perguntas_json=json.dumps(parecer["perguntas_antes_de_aprovar"]),
        recomendacao=parecer["recomendacao"],
        raw_model_response=parecer.get("_raw"),
        latency_ms=parecer.get("_latency_ms"),
    )


bolt_app.command("/parecer-marca")(ack=ack_command, lazy=[handle_parecer])
