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
    publico_alvo        TEXT,
    canal               TEXT,
    vertical            TEXT,
    model_id            TEXT,
    semaforo            TEXT,
    riscos_json         TEXT,
    sugestoes_json      TEXT,
    raw_model_response  TEXT,
    latency_ms          INTEGER,
    word_count          INTEGER,
    word_count_exceeded INTEGER,
    error               TEXT,
    veredito            TEXT,
    risco               TEXT,
    resumo              TEXT,
    perguntas_json      TEXT,
    recomendacao        TEXT
);

CREATE INDEX IF NOT EXISTS idx_decisions_channel_created
    ON decisions (slack_channel_id, created_at);
"""

# Colunas introduzidas após o upgrade para a spec da Azul (semáforo/riscos/
# sugestões). Aplicadas via ALTER TABLE em bancos já existentes; a SCHEMA
# acima já cobre instalações novas. veredito/risco/resumo/perguntas_json/
# recomendacao são mantidas (não destrutivo) mas não são mais escritas.
NEW_COLUMNS = {
    "publico_alvo": "TEXT",
    "canal": "TEXT",
    "vertical": "TEXT",
    "semaforo": "TEXT",
    "sugestoes_json": "TEXT",
    "word_count": "INTEGER",
    "word_count_exceeded": "INTEGER",
}


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(DB_PATH)


def init_db() -> None:
    with get_connection() as conn:
        conn.executescript(SCHEMA)
        existing = {row[1] for row in conn.execute("PRAGMA table_info(decisions)")}
        for name, coltype in NEW_COLUMNS.items():
            if name not in existing:
                conn.execute(f"ALTER TABLE decisions ADD COLUMN {name} {coltype}")


def insert_decision(**fields) -> int:
    columns = ", ".join(fields.keys())
    placeholders = ", ".join(f":{key}" for key in fields)
    with get_connection() as conn:
        cursor = conn.execute(
            f"INSERT INTO decisions ({columns}) VALUES ({placeholders})", fields
        )
        return cursor.lastrowid
