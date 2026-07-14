from flask import Flask, request
from slack_bolt.adapter.flask import SlackRequestHandler

from db import init_db
from slack_app import bolt_app

flask_app = Flask(__name__)
handler = SlackRequestHandler(bolt_app)
init_db()


@flask_app.route("/slack/events", methods=["POST"])
def slack_events():
    return handler.handle(request)


if __name__ == "__main__":
    # threaded=True: necessário para o lazy listener do Bolt (chamada ao
    # Claude, que pode levar vários segundos) não ficar preso atrás da
    # thread principal do servidor de desenvolvimento do Flask.
    flask_app.run(port=5000, threaded=True)
