"""Metadados das verticais da Azul usadas pela interface web (login + painel).

As chaves aqui (ex.: "linhas_aereas") devem bater com as chaves em
`verticais:` no brand_guidelines.yaml, para que o parecer de marca use as
diretrizes adicionais corretas de cada vertical.
"""

VERTICALS = {
    "linhas_aereas": {
        "nome": "Azul Linhas Aéreas",
        "cor": "#003DA6",
        "icone": "✈️",
    },
    "cargo": {
        "nome": "Azul Cargo",
        "cor": "#0056B3",
        "icone": "📦",
    },
    "viagens": {
        "nome": "Azul Viagens",
        "cor": "#00A19A",
        "icone": "🧳",
    },
    "tudoazul": {
        "nome": "TudoAzul",
        "cor": "#0078D4",
        "icone": "⭐",
    },
}


def get_vertical(vertical_id: str) -> dict | None:
    return VERTICALS.get(vertical_id)
