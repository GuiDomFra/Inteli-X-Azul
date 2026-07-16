import json
import logging
import time

import anthropic
import yaml

from config import ANTHROPIC_API_KEY, BRAND_GUIDELINES_PATH, CLAUDE_MODEL

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
logger = logging.getLogger(__name__)

MAX_REPORT_WORDS = 300
NO_GUIDELINE_SENTINEL = "não há diretriz sobre isso"

RISK_CATEGORIES = {
    "seguranca": {"label": "Segurança Operacional", "cor": "#dc2626", "emoji": "🔴"},
    "promessa_absoluta": {"label": "Promessa Absoluta", "cor": "#dc2626", "emoji": "🔴"},
    "tom_low_cost": {"label": "Tom Low-Cost", "cor": "#dc2626", "emoji": "🔴"},
    "concorrente": {"label": "Menção a Concorrente", "cor": "#dc2626", "emoji": "🔴"},
    "exclusao": {"label": "Exclusão/Estereótipo", "cor": "#dc2626", "emoji": "🔴"},
    "greenwashing": {"label": "Greenwashing/Meio Ambiente", "cor": "#dc2626", "emoji": "🔴"},
    "tom_voz": {"label": "Tom de Voz", "cor": "#d97706", "emoji": "🟡"},
    "posicionamento": {"label": "Posicionamento de Marca", "cor": "#d97706", "emoji": "🟡"},
    "acessibilidade": {"label": "Acessibilidade/Clareza", "cor": "#d97706", "emoji": "🟡"},
    "outro": {"label": "Outro Risco", "cor": "#d97706", "emoji": "🟡"},
}

BRAND_PARECER_SCHEMA = {
    "type": "object",
    "properties": {
        "estado": {
            "type": "string",
            "enum": ["verde", "amarelo", "vermelho"],
            "description": "verde=alinhado, amarelo=atenção, vermelho=conflito com o brandbook.",
        },
        "riscos": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "diretriz": {
                        "type": "string",
                        "description": (
                            "A diretriz específica do brandbook que embasa este risco "
                            f"(título/id da diretriz), ou '{NO_GUIDELINE_SENTINEL}' se o "
                            "brandbook não cobrir o assunto."
                        ),
                    },
                    "risco": {"type": "string", "description": "O risco em si, 1 frase curta."},
                    "categoria": {
                        "type": "string",
                        "enum": list(RISK_CATEGORIES.keys()),
                        "description": "Categoria do risco para indicador visual colorido.",
                    },
                    "severidade": {
                        "type": "string",
                        "enum": ["alto", "medio", "baixo"],
                        "description": "Nível de severidade: alto=vermelho, medio=amarelo, baixo=verde.",
                    },
                },
                "required": ["diretriz", "risco", "categoria", "severidade"],
                "additionalProperties": False,
            },
            "description": "No máximo 3 pontos de risco, cada um citando a diretriz afetada, categoria e severidade.",
        },
        "sugestoes": {
            "type": "array",
            "items": {"type": "string"},
            "description": "No máximo 3 sugestões de ajuste para resolver os conflitos.",
        },
    },
    "required": ["estado", "riscos", "sugestoes"],
    "additionalProperties": False,
}

SYSTEM_PROMPT_TEMPLATE = """\
Você é um(a) estrategista de marca sênior da Azul Linhas Aéreas, consultado(a)
ANTES que uma proposta (campanha de destino, promoção TudoAzul, parceria da
Azul Viagens) seja finalizada — para que a visão de marca chegue à mesa de
aprovação com argumentos concretos, e não depois que já é caro mudar.

Você receberá o brandbook da Azul (fonte de verdade) e o texto de um
briefing ou proposta em estágio inicial. Pode também receber, opcionalmente,
público-alvo e canal da campanha.

Regras invioláveis:

1. Você NUNCA aprova nem reprova uma proposta. Você apenas informa riscos de
   marca através do estado e das listas abaixo. A decisão final é sempre
   humana — isso é estrutural, não opcional.

2. Baseie-se exclusivamente nas diretrizes de marca fornecidas em
   <brand_guidelines> abaixo. Não traga boas práticas genéricas de marketing
   que não estejam ali.

3. Nunca invente diretrizes. Se um aspecto da proposta tocar em um assunto que
   o brandbook não cobre, o campo "diretriz" desse item deve ser exatamente
   "não há diretriz sobre isso" — não fabrique uma regra para justificar uma
   opinião. Só inclua um item assim quando for relevante ser transparente
   sobre a ausência de diretriz; não force um item para cada detalhe não
   coberto.

4. Todo risco real deve citar a diretriz específica (pelo título/id em
   `diretrizes_proibidas`, ou o ponto relevante de `tom_de_voz`/`posicionamento`)
   que o embasa. Nunca diga apenas "isso não parece muito Azul" sem apontar a
   fonte.

5. No máximo 3 itens em "riscos" e no máximo 3 itens em "sugestoes". Se
   houver mais conflitos genuínos, mantenha só os 3 mais graves/claros. Se
   nada conflita, "riscos" pode ser uma lista vazia e o estado deve ser
   "verde".

6. Calibre o estado assim: "vermelho" = conflito direto com uma diretriz
   proibida explícita (ex.: tom low-cost, promessa de pontualidade absoluta,
   citar concorrente nominalmente); "amarelo" = desvio de tom/posicionamento
   ou risco menor, sem violar uma proibição explícita; "verde" = alinhado ou
   sem risco relevante o suficiente para sinalizar.

7. As SUAS PRÓPRIAS sugestões nunca podem: usar tom de empresa barata/low
   cost, prometer pontualidade absoluta/100%, ou citar/atacar concorrentes
   nominalmente. É fácil apontar uma violação no texto avaliado e reproduzir
   a mesma violação na sua sugestão de correção — preste atenção especial a
   isso.

8. O relatório completo (soma de todos os textos em "riscos" + "sugestoes")
   deve ter no máximo {max_words} palavras. Seja direto: uma a duas frases
   por item, sem preâmbulos repetidos.

9. Onde não comprometer precisão nem o limite de palavras, reflita o tom de
   voz da Azul (caloroso, brasileiro, acessível) no texto do parecer — isso é
   secundário a ser conciso e sempre citar a fonte.

10. Se público-alvo e/ou canal forem fornecidos no contexto adicional, use-os
    para calibrar a severidade do risco (a mesma frase pode ser um risco menor
    em um e-mail para o programa TudoAzul e um risco maior em mídia paga em
    redes sociais).

11. Se as diretrizes abaixo tiverem uma chave "verticais_ativas", ela lista
    qual(is) vertical(is) da Azul estão sendo avaliadas nesta proposta (ex.:
    Azul Cargo, Azul Viagens, TudoAzul, Azul Linhas Aéreas) — use o campo
    "foco" de cada uma para contextualizar a análise. As diretrizes_proibidas
    já vêm combinadas (núcleo + todas as verticais ativas) e devem ser usadas
    exatamente como estão. Se houver mais de uma vertical ativa (proposta
    conjunta entre verticais, ex. promoção TudoAzul + pacote Azul Viagens),
    considere as diretrizes de todas elas ao apontar riscos e garanta que
    cada sugestão funcione para todas as verticais envolvidas, não só para
    uma.

12. Para cada risco identificado, classifique-o em uma **categoria** e atribua
    uma **severidade**:

    **Categorias de risco (use exatamente estes IDs):**
    - `seguranca`: Segurança operacional (ex.: prometer segurança absoluta, usar segurança como marketing)
    - `promessa_absoluta`: Promessa incondicional de pontualidade, entrega, disponibilidade ou upgrade
    - `tom_low_cost`: Linguagem de empresa barata/low-cost, foco em preço baixo como argumento central
    - `concorrente`: Citar ou atacar concorrentes nominalmente (GOL, LATAM, etc.)
    - `exclusao`: Comunicação que exclui ou estereotipa grupos de pessoas
    - `greenwashing`: Alegação ambiental sem lastro verificável, neutralidade de carbono incondicional
    - `tom_voz`: Desvio do tom caloroso, brasileiro, acessível (ex.: corporativo, frio, jargão técnico)
    - `posicionamento`: Desalinhamento com "melhor experiência de voo do Brasil", malha doméstica, humanização
    - `acessibilidade`: Falta de clareza, jargão sem explicação, informação confusa para o cliente
    - `outro`: Risco real não coberto pelas categorias acima

    **Severidade (use exatamente):**
    - `alto` → 🔴 **bolinha vermelha** — violação direta de diretriz proibida (regras 6, 7, 8, 9, 10, 11, 12 do brandbook)
    - `medio` → 🟡 **bolinha amarela** — desvio de tom/posicionamento, risco menor sem proibição explícita
    - `baixo` → 🟢 **bolinha verde** — alinhado ou observação leve sem impacto material

    O campo `categoria` determina a cor/base do indicador; o campo `severidade` confirma o nível.
    Riscos `alto` sempre puxam o estado geral para "vermelho"; riscos `medio` para "amarelo".
    Se só houver riscos `baixo` ou lista vazia, estado = "verde".

Diretrizes de marca (fonte de verdade):
<brand_guidelines>
{brand_guidelines_text}
</brand_guidelines>
"""


class BrandAdvisorError(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def load_brand_guidelines_text(
    path=BRAND_GUIDELINES_PATH, vertical: str | list[str] | None = None
) -> str:
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = f.read()
    except FileNotFoundError as e:
        raise BrandAdvisorError(
            "brandbook_missing", "Arquivo de brandbook não encontrado."
        ) from e

    try:
        guidelines = yaml.safe_load(raw)
    except yaml.YAMLError as e:
        raise BrandAdvisorError(
            "brandbook_invalid", "Brandbook malformado (YAML inválido)."
        ) from e

    if not guidelines or guidelines.get("metadata", {}).get("status") != "configured":
        raise BrandAdvisorError(
            "brandbook_not_configured",
            "Brandbook ainda não configurado (metadata.status != 'configured').",
        )

    guidelines = _apply_vertical(guidelines, vertical)

    return yaml.dump(guidelines, allow_unicode=True, sort_keys=False)


def _apply_vertical(guidelines: dict, vertical: str | list[str] | None) -> dict:
    """Combina o núcleo do brandbook com as diretrizes adicionais de uma ou
    mais verticais ativas (linhas_aereas/cargo/viagens/tudoazul) — útil para
    analisar de uma vez uma proposta que atravessa várias verticais (ex.:
    promoção conjunta TudoAzul + Azul Viagens), citando as diretrizes
    combinadas de todas as verticais envolvidas em um único parecer.

    Em qualquer caso, a chave "verticais" (metadados de todas as verticais)
    é removida do texto final — o modelo só deve ver as diretrizes que
    realmente se aplicam à análise em questão, nunca as das verticais não
    selecionadas, para não confundir a citação de fonte."""
    all_verticais = guidelines.get("verticais") or {}

    requested = [vertical] if isinstance(vertical, str) else list(vertical or [])
    selected_ids = [v for v in requested if v in all_verticais]

    guidelines = dict(guidelines)
    guidelines.pop("verticais", None)

    if not selected_ids:
        return guidelines

    extra_diretrizes = []
    verticais_ativas = []
    for vertical_id in selected_ids:
        vertical_info = all_verticais[vertical_id]
        verticais_ativas.append(
            {
                "id": vertical_id,
                "nome": vertical_info.get("nome", vertical_id),
                "foco": vertical_info.get("foco", ""),
            }
        )
        extra_diretrizes.extend(vertical_info.get("diretrizes_adicionais", []))

    guidelines["verticais_ativas"] = verticais_ativas
    guidelines["diretrizes_proibidas"] = (
        list(guidelines.get("diretrizes_proibidas", [])) + extra_diretrizes
    )
    return guidelines


def compute_report_word_count(parecer: dict) -> int:
    riscos_text = " ".join(f"{r['diretriz']} {r['risco']}" for r in parecer.get("riscos", []))
    sugestoes_text = " ".join(parecer.get("sugestoes", []))
    return len(f"{riscos_text} {sugestoes_text}".split())


def _analyze_locally(decision_text: str, guidelines: dict, publico_alvo: str | None, canal: str | None) -> dict:
    """Análise local de risco de marca (sem API externa) — implementa as regras do brandbook."""
    text_lower = decision_text.lower()
    riscos = []
    
    # Mapeamento de palavras-chave para categorias de risco
    risk_patterns = {
        "seguranca": {
            "keywords": ["mais seguro", "nunca teve incidente", "zero acidente", "segurança absoluta", "voo mais seguro"],
            "diretriz": "seguranca_operacional",
            "severidade": "alto",
        },
        "promessa_absoluta": {
            "keywords": ["sempre no horário", "nunca atrasa", "pontualidade 100%", "garantia de entrega", "prazo garantido", "sem atraso", "100% pontual"],
            "diretriz": "pontualidade_absoluta",
            "severidade": "alto",
        },
        "tom_low_cost": {
            "keywords": ["mais barato", "mais barata", "preço baixo", "menor preço", "imperdível", "promoção imperdível", "economize", "low cost", "low-cost", "barato", "barata", "desconto agressivo", "preço imbatível", "mais em conta"],
            "diretriz": "tom_low_cost",
            "severidade": "alto",
        },
        "concorrente": {
            "keywords": ["gol", "latam", "azul é melhor que", "superior à gol", "vence a latam", "concorrente"],
            "diretriz": "ataque_concorrente",
            "severidade": "alto",
        },
        "exclusao": {
            "keywords": ["estereotipo", "estereótipo", "preconceito", "exclui", "não para"],
            "diretriz": "exclusao_estereotipo",
            "severidade": "alto",
        },
        "greenwashing": {
            "keywords": ["carbono zero", "neutro de carbono", "100% sustentável", "zero emissão", "verde total", "eco-friendly garantido"],
            "diretriz": "greenwashing",
            "severidade": "alto",
        },
        "tom_voz": {
            "keywords": ["protocolar", "burocrático", "conforme regulamento", "nos termos do contrato", "formalizado", "conforme cláusula"],
            "diretriz": "tom_de_voz",
            "severidade": "medio",
        },
        "posicionamento": {
            "keywords": ["líder de mercado", "maior empresa", "número 1", "dominância", "monopólio"],
            "diretriz": "posicionamento",
            "severidade": "medio",
        },
        "acessibilidade": {
            "keywords": ["slot", "load factor", "lead time", "yield", "revenue management", "pax", "ask", "rpK"],
            "diretriz": "tom_de_voz",
            "severidade": "medio",
        },
    }
    
    # Verifica cada padrão
    for categoria, config in risk_patterns.items():
        for kw in config["keywords"]:
            if kw in text_lower:
                riscos.append({
                    "diretriz": config["diretriz"],
                    "risco": f"Identificado termo sensível: '{kw}'",
                    "categoria": categoria,
                    "severidade": config["severidade"],
                })
                break  # uma ocorrência por categoria basta
    
    # Determina estado geral
    if any(r["severidade"] == "alto" for r in riscos):
        estado = "vermelho"
    elif any(r["severidade"] == "medio" for r in riscos):
        estado = "amarelo"
    else:
        estado = "verde"
    
    # Gera sugestões baseadas nos riscos encontrados
    sugestoes = []
    categorias_encontradas = {r["categoria"] for r in riscos}
    
    if "tom_low_cost" in categorias_encontradas:
        sugestoes.append("Reforce a experiência e o cuidado humano, não o preço — a Azul compete pela melhor experiência, não pelo menor custo.")
    if "promessa_absoluta" in categorias_encontradas:
        sugestoes.append("Substitua garantias absolutas por compromissos: 'pontualidade como prioridade' em vez de 'sempre no horário'.")
    if "concorrente" in categorias_encontradas:
        sugestoes.append("Remova menções nominais a concorrentes; diferencie afirmando o que a Azul oferece (malha, cuidado, experiência).")
    if "seguranca" in categorias_encontradas:
        sugestoes.append("Não use segurança operacional como argumento de marketing — é requisito básico, não diferencial.")
    if "greenwashing" in categorias_encontradas:
        sugestoes.append("Alegações ambientais precisam de lastro auditável/certificado; comunique como compromisso com programas específicos.")
    if "tom_voz" in categorias_encontradas:
        sugestoes.append("Adote tom mais caloroso e acessível: fale como gente, evite jargão corporativo.")
    if "acessibilidade" in categorias_encontradas:
        sugestoes.append("Explique termos técnicos ou substitua por linguagem simples para o cliente final.")
    if "posicionamento" in categorias_encontradas:
        sugestoes.append("Posicione a Azul pela maior malha doméstica e experiência humana, não por dominância de mercado.")
    if "exclusao" in categorias_encontradas:
        sugestoes.append("Revise a linguagem para garantir inclusão e evitar estereótipos regionais ou sociais.")
    
    # Sugestões genéricas se poucos riscos
    if len(sugestoes) < 2 and estado != "verde":
        sugestoes.append("Alinhe o tom ao jeito Azul: caloroso, brasileiro, acessível.")
    if estado == "verde":
        sugestoes = ["Manter tom caloroso e brasileiro", "Garantir acessibilidade na comunicação", "Respeitar identidade visual Azul"]
    
    # Limita a 3 sugestões
    sugestoes = sugestoes[:3]
    
    # Limita riscos a 3
    riscos = riscos[:3]
    
    return {
        "estado": estado,
        "riscos": riscos,
        "sugestoes": sugestoes,
        "_word_count": compute_report_word_count({"riscos": riscos, "sugestoes": sugestoes}),
        "_latency_ms": 0,
        "_model_id": "local-analyzer-v1",
        "_raw": "local",
    }


def get_brand_parecer(
    decision_text: str,
    brand_guidelines_text: str,
    publico_alvo: str | None = None,
    canal: str | None = None,
) -> dict:
    """Analisa a proposta contra as diretrizes da marca Azul (versão local)."""
    import yaml
    guidelines = yaml.safe_load(brand_guidelines_text)
    return _analyze_locally(decision_text, guidelines, publico_alvo, canal)
