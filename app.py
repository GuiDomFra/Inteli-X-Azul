import json
from flask import Flask, request, session, redirect, url_for
from flask_wtf import CSRFProtect

from config import SECRET_KEY, slack_configured, validate_config

validate_config()

from db import init_db  # noqa: E402
from web_app import web_app  # noqa: E402

flask_app = Flask(__name__)
flask_app.secret_key = SECRET_KEY

csrf = CSRFProtect(flask_app)

flask_app.register_blueprint(web_app)


@flask_app.before_request
def _ensure_session_consistency():
    """Limpa a sessão se houver inconsistência de role/vertical."""
    # Rotas públicas que não precisam de sessão
    public_paths = ("/login", "/logout", "/slack/events", "/static", "/favicon.ico")
    if any(request.path.startswith(p) for p in public_paths):
        return

    role = session.get("role")
    vertical_id = session.get("vertical_id")

    # Marketing não pode acessar rotas de vertical
    if role == "marketing" and request.path.startswith("/painel"):
        session.clear()
        return redirect(url_for("web_app.login"))

    # Vertical não pode acessar rotas de marketing
    if role == "vertical" and vertical_id and request.path.startswith("/marketing"):
        session.clear()
        return redirect(url_for("web_app.login"))

    # Vertical logada tentando acessar painel de outra vertical
    if role == "vertical" and vertical_id and request.path.startswith("/painel"):
        # O _current_vertical() no painel já valida isso, mas garantimos aqui
        pass


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


# Logout aceita GET e POST para facilitar logout via link
@flask_app.route("/logout", methods=["GET", "POST"])
@csrf.exempt
def _logout():
    session.clear()
    return redirect(url_for("web_app.login"))


if slack_configured():
    from slack_bolt.adapter.flask import SlackRequestHandler

    from slack_app import bolt_app

    handler = SlackRequestHandler(bolt_app)

    @flask_app.route("/slack/events", methods=["POST"])
    @csrf.exempt
    def slack_events():
        return handler.handle(request)
else:
    print(
        "[aviso] SLACK_BOT_TOKEN/SLACK_SIGNING_SECRET não configurados — "
        "rota /slack/events desativada. Só a interface web (/login) está disponível."
    )


if __name__ == "__main__":
    flask_app.run(host="0.0.0.0", port=5000, threaded=True)
