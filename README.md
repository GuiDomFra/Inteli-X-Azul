# Inteli X Azul

Agente de IA que dá um **parecer de impacto de marca** para a Azul **antes**
que uma proposta (campanha de destino, promoção TudoAzul, parceria da Azul
Viagens, comunicação da Azul Cargo...) seja finalizada. O agente nunca aprova
nem reprova — só informa riscos; a decisão final é sempre humana. Duas
interfaces, um só "cérebro" (`brand_advisor.py`):

- **Slack** (`/parecer-marca`) — uso rápido em qualquer canal, sem login,
  não associado a uma vertical específica.
- **Web** (login + painel) — cada vertical da Azul (Linhas Aéreas, Cargo,
  Viagens, TudoAzul) tem seu próprio usuário de demonstração e vê, além do
  brandbook núcleo da Azul, as diretrizes adicionais específicas da sua
  vertical.

Em ambos os casos o agente avalia o briefing à luz do brandbook
(`brand_guidelines.yaml`) usando Claude e devolve um relatório estruturado
com no máximo 300 palavras: semáforo verde/amarelo/vermelho, até 3 pontos de
risco citando a diretriz afetada, até 3 sugestões de ajuste.

## 1. Instalação

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Preencha o `.env` com `ANTHROPIC_API_KEY` — é a única variável obrigatória.
A interface web (seção 4) já funciona só com isso. Os valores de Slack
(`SLACK_BOT_TOKEN`/`SLACK_SIGNING_SECRET`, ver passo 2) são opcionais: se
não forem preenchidos, `python app.py` sobe normalmente e só desativa a rota
`/slack/events`, com um aviso no console.

## 2. Configurar o Slack App

1. Acesse https://api.slack.com/apps → **Create New App** → *From scratch* →
   dê um nome e escolha o workspace.
2. **OAuth & Permissions** → *Bot Token Scopes* → adicione:
   - `commands`
   - `chat:write`
   - `chat:write.public` (permite postar em canais públicos sem `/invite` prévio)
3. **Slash Commands** → *Create New Command*:
   - Command: `/parecer-marca`
   - Request URL: `https://<seu-dominio-ngrok>/slack/events`
   - Short description: "Peça um parecer de marca antes de finalizar uma decisão"
   - Usage hint: `[descrição da decisão]`
4. **Basic Information** → *App Credentials* → copie o **Signing Secret** para
   `SLACK_SIGNING_SECRET` no `.env`.
5. **OAuth & Permissions** → *Install App to Workspace* → autorize → copie o
   **Bot User OAuth Token** (`xoxb-...`) para `SLACK_BOT_TOKEN` no `.env`.
6. Sempre que mudar escopos, clique em **Reinstall App**.

Fora do escopo do MVP (mas fácil de adicionar depois, reaproveitando
`brand_advisor.py`/`slack_formatting.py`): monitoramento passivo de canal via
Events API (`app_mention` + escopo `channels:history`), para acionar o agente
sem precisar digitar o slash command.

## 3. Rodar localmente com ngrok

O Slack exige um endpoint HTTPS público, então em dev local usamos ngrok:

```powershell
python app.py
```

Em outro terminal:

```powershell
ngrok http 5000
```

Copie a URL `https://<algo>.ngrok-free.app`, cole em
`https://<algo>.ngrok-free.app/slack/events` na Request URL do slash command
(passo 2.3) e salve. O tier gratuito do ngrok gera uma URL nova a cada
execução — se reiniciar o ngrok, atualize a Request URL de novo.

> **Nota:** o Flask precisa rodar com `threaded=True` (já configurado em
> `app.py`) para que o lazy listener do Bolt — que faz a chamada ao Claude,
> podendo levar vários segundos — não fique bloqueado atrás da thread
> principal.

## 4. Interface web (login por vertical)

Além do Slack, `python app.py` também sobe uma interface web em
`http://localhost:5000/login` — sem precisar de ngrok nem de credenciais do
Slack para essa parte.

Cada vertical da Azul tem um usuário de demonstração fixo (a senha é sempre
`azul123`, mostrada na própria tela de login):

| Usuário         | Vertical            |
|-----------------|----------------------|
| `linhas_aereas` | Azul Linhas Aéreas   |
| `cargo`         | Azul Cargo           |
| `viagens`       | Azul Viagens         |
| `tudoazul`      | TudoAzul             |

Depois do login, o painel (`/painel`) mostra um formulário (briefing +
público-alvo/canal opcionais) e o parecer de marca gerado — usando o
brandbook núcleo da Azul **mais** as diretrizes adicionais daquela vertical
específica (definidas em `verticais:` dentro de `brand_guidelines.yaml`; a
lógica de combinação está em `brand_advisor._apply_vertical`). Por exemplo,
o login `cargo` aplica uma diretriz extra sobre não garantir prazo de entrega
de forma incondicional, que não existe para as outras verticais.

> **Nota:** este login é um protótipo acadêmico (usuário/senha fixos, sem
> hashing por usuário real, sem recuperação de senha) — não é um sistema de
> autenticação de produção.

## 5. Testar (Slack)

No Slack, em qualquer canal onde o bot esteja disponível:

```
/parecer-marca Vamos lançar a campanha "voe pagando menos com a Azul" | publico: viajantes de lazer | canal: redes sociais
```

Os filtros `| publico: ...` e `| canal: ...` são opcionais. Em alguns
segundos deve aparecer uma mensagem do bot com semáforo, pontos de risco
(cada um citando a diretriz do brandbook) e sugestões de ajuste. Para
conferir o log:

```powershell
sqlite3 data\decisions.db "select id, semaforo, decision_text from decisions order by id desc limit 1;"
```

### Testes automatizados

```powershell
pytest
```

Os testes padrão (incluindo os de `brand_advisor.py` e `command_parsing.py`)
mockam a chamada ao Claude — não precisam de rede, Slack nem
`ANTHROPIC_API_KEY` real.

### Teste de aceite (chamada real à API)

O critério de aceite da spec (3 violações conhecidas → 3 riscos identificados,
semáforo vermelho, diretriz correta citada, relatório ≤300 palavras) só prova
algo rodando contra o Claude de verdade — está isolado em
`tests/acceptance/` e marcado como `live`, por isso **não roda** num `pytest`
comum:

```powershell
pytest -m live
```

Requer `ANTHROPIC_API_KEY` real no ambiente; consome tokens e leva alguns
segundos.

## 6. Diretrizes de marca

`brand_guidelines.yaml` já traz um primeiro rascunho com o posicionamento
("a melhor experiência de voo do Brasil"), tom de voz (caloroso, brasileiro,
acessível) e a lista de abordagens proibidas da Azul (tom low-cost, promessa
de pontualidade absoluta, ataque a concorrentes nominalmente, entre outras),
derivado diretamente da spec. Além do núcleo, a chave `verticais:` traz
diretrizes adicionais específicas de cada vertical (ex.: `cargo` não pode
garantir prazo de entrega incondicional); veja a seção 4. **Tudo isso ainda
precisa de revisão e validação pelo time de marca real da Azul** antes de
ser considerado definitivo (tagline exata, lista completa de valores e de
abordagens proibidas, por vertical inclusive). Mantenha a chave
`metadata.status: configured` após a revisão — sem ela (ou com outro valor),
o agente se recusa a gerar pareceres e avisa que falta o brandbook. Não é
necessário mexer em código: o agente recarrega o arquivo a cada chamada.

> **Nota:** a cor `AZUL_BLUE` em `slack_formatting.py` também é um valor
> ainda não confirmado com o time de marca — ajustar para o hex exato do
> guia de identidade visual da Azul assim que disponível.
