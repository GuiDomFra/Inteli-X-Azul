import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from command_parsing import parse_parecer_command


def test_no_flags():
    text, extra = parse_parecer_command("Vamos lançar a campanha X")
    assert text == "Vamos lançar a campanha X"
    assert extra == {}


def test_both_flags():
    text, extra = parse_parecer_command(
        "Campanha X | publico: viajantes de lazer | canal: redes sociais"
    )
    assert text == "Campanha X"
    assert extra == {"publico_alvo": "viajantes de lazer", "canal": "redes sociais"}


def test_flags_reversed_order():
    text, extra = parse_parecer_command("Campanha X | canal: e-mail | publico: corporativo")
    assert text == "Campanha X"
    assert extra == {"publico_alvo": "corporativo", "canal": "e-mail"}


def test_only_one_flag():
    text, extra = parse_parecer_command("Campanha X | canal: TV")
    assert text == "Campanha X"
    assert extra == {"canal": "TV"}


def test_extra_whitespace():
    text, extra = parse_parecer_command("  Campanha X   |   publico :  familias  |canal:email  ")
    assert text == "Campanha X"
    assert extra == {"publico_alvo": "familias", "canal": "email"}


def test_case_insensitive_keys():
    text, extra = parse_parecer_command("Campanha X | Publico: jovens | CANAL: TV")
    assert extra == {"publico_alvo": "jovens", "canal": "TV"}


def test_accented_and_unaccented_publico():
    _, extra1 = parse_parecer_command("Campanha X | publico: jovens")
    _, extra2 = parse_parecer_command("Campanha X | público: jovens")
    assert extra1 == {"publico_alvo": "jovens"}
    assert extra2 == {"publico_alvo": "jovens"}


def test_unrecognized_segment_is_appended_to_briefing():
    text, extra = parse_parecer_command("Campanha X | isso não é uma flag | canal: TV")
    assert text == "Campanha X | isso não é uma flag"
    assert extra == {"canal": "TV"}


def test_repeated_flag_last_wins():
    text, extra = parse_parecer_command("Campanha X | canal: TV | canal: redes sociais")
    assert extra == {"canal": "redes sociais"}


def test_trailing_empty_segment_is_ignored():
    text, extra = parse_parecer_command("Campanha X | canal: TV | ")
    assert text == "Campanha X"
    assert extra == {"canal": "TV"}
