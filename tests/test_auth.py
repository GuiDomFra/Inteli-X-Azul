import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from auth import authenticate
from verticals import VERTICALS


def test_authenticate_valid_credentials_for_each_vertical():
    for vertical_id in VERTICALS:
        result = authenticate(vertical_id, "azul123")
        assert result is not None
        assert result["vertical"] == vertical_id
        assert result["role"] == "vertical"


def test_authenticate_marketing_user():
    result = authenticate("marketing", "azul123")
    assert result is not None
    assert result["vertical"] is None
    assert result["role"] == "marketing"


def test_authenticate_wrong_password():
    assert authenticate("linhas_aereas", "senha_errada") is None


def test_authenticate_unknown_username():
    assert authenticate("nao_existe", "azul123") is None
