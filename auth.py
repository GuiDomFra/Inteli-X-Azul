"""Login simples por vertical — adequado para demo/protótipo acadêmico, não
para produção. Cada vertical tem um usuário de demonstração fixo; a senha é
sempre "azul123" (documentada no README), guardada como hash, nunca em texto
puro.
"""

from werkzeug.security import check_password_hash, generate_password_hash

from verticals import VERTICALS

_DEMO_PASSWORD_HASH = generate_password_hash("azul123")

# username -> vertical_id. Um usuário de demonstração por vertical.
_USERS = {vertical_id: {"vertical": vertical_id, "password_hash": _DEMO_PASSWORD_HASH} for vertical_id in VERTICALS}


def authenticate(username: str, password: str) -> str | None:
    """Retorna o vertical_id se as credenciais forem válidas, senão None."""
    user = _USERS.get(username)
    if not user:
        return None
    if not check_password_hash(user["password_hash"], password):
        return None
    return user["vertical"]
