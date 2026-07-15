"""Nível de importância/urgência que a vertical atribui à própria proposta ao
enviar para análise — é só metadado de triagem para o marketing priorizar a
fila de revisão, não influencia o parecer de marca em si (isso continua
sendo só sobre risco de marca, calculado pela IA)."""

IMPORTANCE_LEVELS = {
    "alta": {"label": "Alta", "icone": "🔺", "peso": 3},
    "media": {"label": "Média", "icone": "▪️", "peso": 2},
    "baixa": {"label": "Baixa", "icone": "🔻", "peso": 1},
}

DEFAULT_IMPORTANCE = "media"


def get_importance(importance_id: str) -> dict | None:
    return IMPORTANCE_LEVELS.get(importance_id)


def sort_weight(importance_id: str | None) -> int:
    info = IMPORTANCE_LEVELS.get(importance_id or "")
    return info["peso"] if info else 0
