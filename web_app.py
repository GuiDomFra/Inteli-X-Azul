import json
import sqlite3

from flask import Blueprint, redirect, render_template, request, session, url_for

from auth import authenticate
from brand_advisor import BrandAdvisorError, get_brand_parecer, load_brand_guidelines_text
from config import DB_PATH
from db import (
    get_all_decisions,
    get_comments,
    get_decisions_by_vertical,
    insert_comment,
    insert_decision,
    mark_reviewed,
)
from importance import DEFAULT_IMPORTANCE, IMPORTANCE_LEVELS, sort_weight
from verticals import VERTICALS, get_vertical


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(DB_PATH)


web_app = Blueprint("web_app", __name__)

_BRANDBOOK_ERROR_MESSAGES = {
    "brandbook_missing": "Ainda não há um brandbook da Azul configurado.",
    "brandbook_invalid": "O brandbook da Azul está malformado e não pôde ser lido.",
    "brandbook_not_configured": "O brandbook da Azul ainda não foi marcado como configurado.",
}


def _current_vertical() -> dict | None:
    vertical_id = session.get("vertical_id")
    if not vertical_id:
        return None
    info = get_vertical(vertical_id)
    if not info:
        return None
    return {"id": vertical_id, **info}


def _current_user() -> dict | None:
    if not session.get("vertical_id") and not session.get("role"):
        return None
    return {
        "vertical_id": session.get("vertical_id"),
        "role": session.get("role", "vertical"),
    }


@web_app.route("/")
def index():
    if session.get("vertical_id"):
        return redirect(url_for("web_app.painel"))
    if session.get("role") == "marketing":
        return redirect(url_for("web_app.marketing_dashboard"))
    return redirect(url_for("web_app.login"))


@web_app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html", verticals=VERTICALS, error=None)

    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    auth_result = authenticate(username, password)
    if not auth_result:
        return render_template(
            "login.html", verticals=VERTICALS, error="Usuário ou senha inválidos."
        )

    session["vertical_id"] = auth_result["vertical"]
    session["role"] = auth_result["role"]
    return redirect(url_for("web_app.index"))


@web_app.route("/logout", methods=["POST"])
def logout():
    session.pop("vertical_id", None)
    session.pop("role", None)
    return redirect(url_for("web_app.login"))


@web_app.route("/painel", methods=["GET", "POST"])
def painel():
    vertical = _current_vertical()
    if not vertical:
        return redirect(url_for("web_app.login"))

    parecer = None
    error = None
    decision_text = ""
    publico_alvo = ""
    canal = ""
    selected_verticals = [vertical["id"]]
    importancia = DEFAULT_IMPORTANCE

    if request.method == "POST":
        decision_text = request.form.get("decision_text", "").strip()
        publico_alvo = request.form.get("publico_alvo", "").strip()
        canal = request.form.get("canal", "").strip()
        selected_verticals = [
            v for v in request.form.getlist("verticais") if v in VERTICALS
        ] or [vertical["id"]]
        importancia = request.form.get("importancia", DEFAULT_IMPORTANCE)
        if importancia not in IMPORTANCE_LEVELS:
            importancia = DEFAULT_IMPORTANCE

        if not decision_text:
            error = "Descreva a proposta antes de pedir o parecer."
        else:
            try:
                guidelines_text = load_brand_guidelines_text(vertical=selected_verticals)
            except BrandAdvisorError as exc:
                error = _BRANDBOOK_ERROR_MESSAGES.get(
                    exc.code, "Não foi possível carregar o brandbook da Azul."
                )
            else:
                vertical_tag = ",".join(selected_verticals)
                try:
                    parecer = get_brand_parecer(
                        decision_text,
                        guidelines_text,
                        publico_alvo=publico_alvo or None,
                        canal=canal or None,
                    )
                except BrandAdvisorError as exc:
                    error = "Não consegui gerar o parecer de marca agora. Tente novamente em instantes."
                    insert_decision(
                        slack_user_id=f"web:{vertical['id']}",
                        decision_text=decision_text,
                        publico_alvo=publico_alvo or None,
                        canal=canal or None,
                        vertical=vertical_tag,
                        importancia=importancia,
                        error=str(exc),
                    )
                else:
                    insert_decision(
                        slack_user_id=f"web:{vertical['id']}",
                        decision_text=decision_text,
                        publico_alvo=publico_alvo or None,
                        canal=canal or None,
                        vertical=vertical_tag,
                        importancia=importancia,
                        model_id=parecer.get("_model_id"),
                        semaforo=parecer["semaforo"],
                        riscos_json=json.dumps(parecer["riscos"], ensure_ascii=False),
                        sugestoes_json=json.dumps(parecer["sugestoes"], ensure_ascii=False),
                        raw_model_response=parecer.get("_raw"),
                        latency_ms=parecer.get("_latency_ms"),
                        word_count=parecer.get("_word_count"),
                        word_count_exceeded=int(parecer.get("_word_count", 0) > 300),
                    )

    return render_template(
        "painel.html",
        vertical=vertical,
        verticals=VERTICALS,
        selected_verticals=selected_verticals,
        parecer=parecer,
        error=error,
        decision_text=decision_text,
        publico_alvo=publico_alvo,
        canal=canal,
        importance_levels=IMPORTANCE_LEVELS,
        importancia=importancia,
    )


@web_app.route("/painel/historico")
def painel_historico():
    """Dashboard da própria vertical: histórico de propostas enviadas ao
    marketing, com status de revisão — deixa claro pra vertical que o
    fluxo é sempre "enviar para o marketing avaliar"."""
    vertical = _current_vertical()
    if not vertical:
        return redirect(url_for("web_app.login"))

    decisions = get_decisions_by_vertical(vertical["id"])
    total = len(decisions)
    reviewed_count = sum(1 for d in decisions if d["reviewed"])
    semaforo_counts = {
        "verde": sum(1 for d in decisions if d["semaforo"] == "verde"),
        "amarelo": sum(1 for d in decisions if d["semaforo"] == "amarelo"),
        "vermelho": sum(1 for d in decisions if d["semaforo"] == "vermelho"),
    }
    return render_template(
        "painel_historico.html",
        vertical=vertical,
        verticals=VERTICALS,
        decisions=decisions,
        total=total,
        reviewed_count=reviewed_count,
        semaforo_counts=semaforo_counts,
        importance_levels=IMPORTANCE_LEVELS,
    )


@web_app.route("/marketing")
def marketing_dashboard():
    """Dashboard da equipe de marketing - vê todas as decisões de todas as verticais."""
    user = _current_user()
    if not user or user["role"] != "marketing":
        return redirect(url_for("web_app.login"))

    all_decisions = get_all_decisions()
    all_decisions = sorted(
        all_decisions, key=lambda d: sort_weight(d["importancia"]), reverse=True
    )
    return render_template(
        "marketing_dashboard.html",
        decisions=all_decisions,
        verticals=VERTICALS,
        importance_levels=IMPORTANCE_LEVELS,
    )


@web_app.route("/marketing/decision/<int:decision_id>", methods=["GET", "POST"])
def marketing_decision_detail(decision_id: int):
    """Detalhe de uma decisão com comentários - marketing pode comentar."""
    user = _current_user()
    if not user or user["role"] != "marketing":
        return redirect(url_for("web_app.login"))

    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        decision = conn.execute("SELECT * FROM decisions WHERE id = ?", (decision_id,)).fetchone()
        if not decision:
            return "Decisão não encontrada", 404

    if request.method == "POST":
        content = request.form.get("comment", "").strip()
        if content:
            insert_comment(
                decision_id=decision_id,
                author_role="marketing",
                author_name="Equipe de Marketing",
                content=content,
            )
            return redirect(url_for("web_app.marketing_decision_detail", decision_id=decision_id))

    comments = get_comments(decision_id)
    return render_template(
        "marketing_decision_detail.html",
        decision=decision,
        comments=comments,
        verticals=VERTICALS,
        importance_levels=IMPORTANCE_LEVELS,
    )


@web_app.route("/marketing/decision/<int:decision_id>/revisar", methods=["POST"])
def marketing_mark_reviewed(decision_id: int):
    """Marca uma decisão como revisada pelo marketing sem precisar comentar."""
    user = _current_user()
    if not user or user["role"] != "marketing":
        return redirect(url_for("web_app.login"))

    mark_reviewed(decision_id)
    return redirect(url_for("web_app.marketing_decision_detail", decision_id=decision_id))
