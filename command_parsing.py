import re

_FLAG_RE = re.compile(r"^\s*(publico|público|canal)\s*:\s*(.+?)\s*$", re.IGNORECASE)
_KEY_MAP = {"publico": "publico_alvo", "público": "publico_alvo", "canal": "canal"}


def parse_parecer_command(raw_text: str) -> tuple[str, dict]:
    """Split `/parecer-marca <briefing> | publico: ... | canal: ...` into
    (briefing_text, {"publico_alvo": ..., "canal": ...}).

    Both flags are optional and order-independent. Unrecognized `|`-segments
    are appended back into the briefing text instead of being dropped, and
    if a flag key repeats, the last occurrence wins.
    """
    segments = raw_text.split("|")
    briefing_parts = [segments[0].strip()]
    extra = {}
    for segment in segments[1:]:
        segment = segment.strip()
        if not segment:
            continue
        match = _FLAG_RE.match(segment)
        if match:
            key = _KEY_MAP[match.group(1).lower()]
            extra[key] = match.group(2).strip()
        else:
            briefing_parts.append(segment)
    return " | ".join(p for p in briefing_parts if p), extra
