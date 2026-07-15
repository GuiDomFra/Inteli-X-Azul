import json
from flask import Flask, request

from config import SECRET_KEY, slack_configured, validate_config

validate_config()

from db import init_db  # noqa: E402
from web_app import web_app  # noqa: E402

flask_app = Flask(__name__)
flask_app.secret_key = SECRET_KEY
flask_app.register_blueprint(web_app)

@flask_app.template_filter('from_json')
def from_json_filter(value):
    """Converte string JSON para objeto Python no template."""
    if not value:
        return []
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return []

init_db()

if slack_configured():
    from slack_bolt.adapter.flask import SlackRequestHandler

    from slack_app import bolt_app

    handler = SlackRequestHandler(bolt_app)

    @flask_app.route("/slack/events", methods=["POST"])
    def slack_events():
        return handler.handle(request)
else:
    print(
        "[aviso] SLACK_BOT_TOKEN/SLACK_SIGNING_SECRET não configurados — "
        "rota /slack/events desativada. Só a interface web (/login) está disponível."
    )


if __name__ == "__main__":
    # host="0.0.0.0": escuta em todas as interfaces, não só 127.0.0.1 —
    # necessário para o encaminhamento de porta do Codespace/devcontainer
    # detectar e expor a porta automaticamente.
    # threaded=True: necessário para o lazy listener do Bolt (chamada ao
    # Claude, que pode levar vários segundos) não ficar preso atrás da
    # thread principal do servidor de desenvolvimento do Flask.
    flask_app.run(host="0.0.0.0", port=5000, threaded=True)
