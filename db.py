import sqlite3

from config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS decisions (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at          TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    slack_team_id       TEXT,
    slack_channel_id    TEXT,
    slack_user_id       TEXT NOT NULL,
    slack_message_ts    TEXT,
    decision_text       TEXT NOT NULL,
    model_id            TEXT,
    veredito            TEXT,
    risco               TEXT,
    resumo              TEXT,
    riscos_json         TEXT,
    perguntas_json      TEXT,
    recomendacao        TEXT,
    raw_model_response  TEXT,
    latency_ms          INTEGER,
    error               TEXT
);

CREATE INDEX IF NOT EXISTS idx_decisions_channel_created
    ON decisions (slack_channel_id, created_at);
"""


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(DB_PATH)


def init_db() -> None:
    with get_connection() as conn:
        conn.executescript(SCHEMA)


def insert_decision(**fields) -> int:
    columns = ", ".join(fields.keys())
    placeholders = ", ".join(f":{key}" for key in fields)
    with get_connection() as conn:
        cursor = conn.execute(
            f"INSERT INTO decisions ({columns}) VALUES ({placeholders})", fields
        )
        return cursor.lastrowid
