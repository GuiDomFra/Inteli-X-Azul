import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "")
SLACK_SIGNING_SECRET = os.environ.get("SLACK_SIGNING_SECRET", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
# Assina o cookie de sessão da interface web (login por vertical). Em dev,
# cai para um valor fixo se não configurado; troque em qualquer ambiente
# compartilhado.
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-troque-em-producao")

CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "claude-opus-4-8")

BRAND_GUIDELINES_PATH = BASE_DIR / "brand_guidelines.yaml"
DB_PATH = BASE_DIR / "data" / "decisions.db"

REQUIRED_VARS = ["ANTHROPIC_API_KEY"]


def validate_config() -> None:
    missing = [name for name in REQUIRED_VARS if not globals()[name]]
    if missing:
        raise RuntimeError(
            "Variáveis de ambiente obrigatórias ausentes: "
            + ", ".join(missing)
            + ". Configure o .env (veja .env.example)."
        )


def slack_configured() -> bool:
    """A integração com Slack é opcional: a interface web (login por
    vertical) funciona sozinha só com ANTHROPIC_API_KEY. Slack só liga se
    SLACK_BOT_TOKEN e SLACK_SIGNING_SECRET também estiverem preenchidos."""
    return bool(SLACK_BOT_TOKEN and SLACK_SIGNING_SECRET)
