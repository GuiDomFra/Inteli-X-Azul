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
    importancia         TEXT,
    model_id            TEXT,
    estado              TEXT,
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
    recomendacao        TEXT,
    reviewed            INTEGER NOT NULL DEFAULT 0,
    archived            INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_decisions_channel_created
    ON decisions (slack_channel_id, created_at);

CREATE TABLE IF NOT EXISTS comments (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    decision_id     INTEGER NOT NULL REFERENCES decisions(id) ON DELETE CASCADE,
    author_role     TEXT NOT NULL,
    author_name     TEXT NOT NULL,
    content         TEXT NOT NULL,
    created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

CREATE INDEX IF NOT EXISTS idx_comments_decision_created
    ON comments (decision_id, created_at);
"""

# Colunas introduzidas após o upgrade para a spec da Azul (semáforo/riscos/
# sugestões). Aplicadas via ALTER TABLE em bancos já existentes; a SCHEMA
# acima já cobre instalações novas. veredito/risco/resumo/perguntas_json/
# recomendacao são mantidas (não destrutivo) mas não são mais escritas.
NEW_COLUMNS = {
    "publico_alvo": "TEXT",
    "canal": "TEXT",
    "vertical": "TEXT",
    "importancia": "TEXT",
    "estado": "TEXT",
    "sugestoes_json": "TEXT",
    "word_count": "INTEGER",
    "word_count_exceeded": "INTEGER",
    "reviewed": "INTEGER NOT NULL DEFAULT 0",
    "archived": "INTEGER NOT NULL DEFAULT 0",
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


def get_all_decisions(include_archived: bool = False) -> list[sqlite3.Row]:
    """Retorna todas as decisões ordenadas por data (mais recentes primeiro).
    Por padrão, não inclui decisões arquivadas."""
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        if include_archived:
            return list(conn.execute("""
                SELECT * FROM decisions
                ORDER BY created_at DESC
            """))
        return list(conn.execute("""
            SELECT * FROM decisions
            WHERE archived = 0
            ORDER BY created_at DESC
        """))


def get_decisions_by_vertical(vertical_id: str, include_archived: bool = False) -> list[sqlite3.Row]:
    """Retorna decisões de uma vertical específica.
    Por padrão, não inclui decisões arquivadas."""
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        if include_archived:
            return list(conn.execute("""
                SELECT * FROM decisions
                WHERE vertical LIKE ?
                ORDER BY created_at DESC
            """, (f"%{vertical_id}%",)))
        return list(conn.execute("""
            SELECT * FROM decisions
            WHERE vertical LIKE ? AND archived = 0
            ORDER BY created_at DESC
        """, (f"%{vertical_id}%",)))


def get_archived_decisions() -> list[sqlite3.Row]:
    """Retorna todas as decisões arquivadas ordenadas por data (mais recentes primeiro)."""
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        return list(conn.execute("""
            SELECT * FROM decisions
            WHERE archived = 1
            ORDER BY created_at DESC
        """))


def archive_decision(decision_id: int) -> bool:
    """Arquiva uma decisão (soft delete). Retorna True se arquivou, False se não encontrou."""
    with get_connection() as conn:
        cursor = conn.execute("UPDATE decisions SET archived = 1 WHERE id = ?", (decision_id,))
        return cursor.rowcount > 0


def unarchive_decision(decision_id: int) -> bool:
    """Desarquiva uma decisão. Retorna True se desarquivou, False se não encontrou."""
    with get_connection() as conn:
        cursor = conn.execute("UPDATE decisions SET archived = 0 WHERE id = ?", (decision_id,))
        return cursor.rowcount > 0


def insert_comment(decision_id: int, author_role: str, author_name: str, content: str) -> int:
    """Insere um comentário em uma decisão e marca a decisão como revisada
    pelo marketing — comentar é o sinal mais claro de que alguém do
    marketing efetivamente olhou aquela proposta."""
    with get_connection() as conn:
        cursor = conn.execute(
            """INSERT INTO comments (decision_id, author_role, author_name, content)
               VALUES (?, ?, ?, ?)""",
            (decision_id, author_role, author_name, content)
        )
        if author_role == "marketing":
            conn.execute(
                "UPDATE decisions SET reviewed = 1 WHERE id = ?", (decision_id,)
            )
        return cursor.lastrowid


def mark_reviewed(decision_id: int) -> None:
    """Marca uma decisão como revisada pelo marketing, mesmo sem comentário
    (ex.: marketing olhou e concordou, sem nada a acrescentar)."""
    with get_connection() as conn:
        conn.execute("UPDATE decisions SET reviewed = 1 WHERE id = ?", (decision_id,))


def get_comments(decision_id: int) -> list[sqlite3.Row]:
    """Retorna todos os comentários de uma decisão ordenados por data."""
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        return list(conn.execute("""
            SELECT * FROM comments
            WHERE decision_id = ?
            ORDER BY created_at ASC
        """, (decision_id,)))
