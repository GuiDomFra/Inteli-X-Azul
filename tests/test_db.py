import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import db


def _fresh_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    db.init_db()


def test_insert_decision_defaults_to_not_reviewed(tmp_path, monkeypatch):
    _fresh_db(tmp_path, monkeypatch)
    decision_id = db.insert_decision(slack_user_id="web:cargo", decision_text="teste")
    rows = db.get_decisions_by_vertical("cargo")
    # vertical não foi passado nesse insert, então não deve aparecer aqui
    assert rows == []
    all_rows = db.get_all_decisions()
    assert all_rows[0]["id"] == decision_id
    assert all_rows[0]["reviewed"] == 0


def test_mark_reviewed(tmp_path, monkeypatch):
    _fresh_db(tmp_path, monkeypatch)
    decision_id = db.insert_decision(slack_user_id="web:cargo", decision_text="teste", vertical="cargo")
    db.mark_reviewed(decision_id)
    rows = db.get_decisions_by_vertical("cargo")
    assert rows[0]["reviewed"] == 1


def test_marketing_comment_marks_as_reviewed(tmp_path, monkeypatch):
    _fresh_db(tmp_path, monkeypatch)
    decision_id = db.insert_decision(slack_user_id="web:cargo", decision_text="teste", vertical="cargo")
    db.insert_comment(decision_id, author_role="marketing", author_name="Equipe de Marketing", content="ok")
    rows = db.get_decisions_by_vertical("cargo")
    assert rows[0]["reviewed"] == 1


def test_non_marketing_comment_does_not_mark_as_reviewed(tmp_path, monkeypatch):
    _fresh_db(tmp_path, monkeypatch)
    decision_id = db.insert_decision(slack_user_id="web:cargo", decision_text="teste", vertical="cargo")
    db.insert_comment(decision_id, author_role="vertical", author_name="Cargo", content="dúvida")
    rows = db.get_decisions_by_vertical("cargo")
    assert rows[0]["reviewed"] == 0


def test_get_decisions_by_vertical_matches_multi_vertical_tag(tmp_path, monkeypatch):
    _fresh_db(tmp_path, monkeypatch)
    db.insert_decision(slack_user_id="web:tudoazul", decision_text="conjunta", vertical="tudoazul,viagens")
    rows = db.get_decisions_by_vertical("viagens")
    assert len(rows) == 1
