"""Metadados das verticais da Azul usadas pela interface web (login + painel).

As chaves aqui (ex.: "linhas_aereas") devem bater com as chaves em
`verticais:` no brand_guidelines.yaml, para que o parecer de marca use as
diretrizes adicionais corretas de cada vertical.
"""

# Paleta unificada em tons de azul (do mais escuro ao mais claro) — cada
# vertical tem seu próprio tom, mas todas ficam claramente dentro da
# identidade "Azul". Importante: isso é só a cor de destaque/tema da
# interface — não tem relação com o semáforo (verde/amarelo/vermelho) do
# parecer de marca, que continua com as cores de risco originais porque
# ali a cor tem significado funcional (nível de risco), não decorativo.
VERTICALS = {
    "linhas_aereas": {
        "nome": "Azul Linhas Aéreas",
        "cor": "#002F6C",
        "icone": "✈️",
    },
    "conecta": {
        "nome": "Azul Conecta",
        "cor": "#3D6FB4",
        "icone": "🛩️",
    },
    "cargo": {
        "nome": "Azul Cargo Express",
        "cor": "#0B4F8A",
        "icone": "📦",
    },
    "viagens": {
        "nome": "Azul Viagens",
        "cor": "#2E86D6",
        "icone": "🧳",
    },
    "tudoazul": {
        "nome": "TudoAzul",
        "cor": "#5CACE8",
        "icone": "⭐",
    },
    "sustentabilidade": {
        "nome": "Azul Sustentabilidade",
        "cor": "#0E4C7A",
        "icone": "🌱",
    },
}


def get_vertical(vertical_id: str) -> dict | None:
    return VERTICALS.get(vertical_id)
