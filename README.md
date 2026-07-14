# Inteli X Azul

Agente de IA que dá um parecer de marca **antes** que uma decisão (naming, copy,
campanha, posicionamento) seja finalizada, direto no Slack.

Fluxo: alguém roda `/parecer-marca <descrição da decisão>` em qualquer canal →
o agente avalia a decisão à luz das diretrizes de marca (`brand_guidelines.yaml`)
usando Claude → posta um parecer estruturado (veredito, riscos, perguntas em
aberto, recomendação) na thread.

## 1. Instalação

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Preencha o `.env` com `ANTHROPIC_API_KEY` (e os valores do Slack, ver passo 2).

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

## 4. Testar

No Slack, em qualquer canal onde o bot esteja disponível:

```
/parecer-marca Vamos renomear o produto para "SuperApp"
```

Em alguns segundos deve aparecer uma mensagem do bot com veredito, riscos,
perguntas e recomendação. Para conferir o log:

```powershell
sqlite3 data\decisions.db "select id, veredito, risco, decision_text from decisions order by id desc limit 1;"
```

### Testes automatizados

```powershell
pytest
```

Os testes de `brand_advisor.py` mockam a chamada ao Claude — não precisam de
rede, Slack nem `ANTHROPIC_API_KEY` real.

## 5. Diretrizes de marca

`brand_guidelines.yaml` vem com conteúdo de exemplo (placeholder). Edite esse
arquivo com as diretrizes reais da sua marca — tom de voz, valores,
posicionamento, coisas a evitar. Não é necessário mexer em código: o agente
recarrega o arquivo a cada chamada.
