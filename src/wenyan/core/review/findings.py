_FINDING_TEXT_KEYS: tuple[str, ...] = ("message", "reason", "finding", "problem", "detail")


def format_review_finding(finding: dict[str, object]) -> str:
    prefix_parts: list[str] = []
    surface = finding.get("surface")
    if isinstance(surface, str) and surface:
        prefix_parts.append(surface)
    note_id = finding.get("noteId")
    if isinstance(note_id, str) and note_id:
        prefix_parts.append(f"note {note_id[:8]}…")
    token_id = finding.get("tokenId")
    if isinstance(token_id, str) and token_id and not prefix_parts:
        prefix_parts.append(f"token {token_id[:8]}…")

    text_parts: list[str] = []
    seen: set[str] = set()
    for key in _FINDING_TEXT_KEYS:
        value = finding.get(key)
        if isinstance(value, str) and value and value not in seen:
            text_parts.append(value)
            seen.add(value)

    if prefix_parts and text_parts:
        return f"{prefix_parts[0]} — {text_parts[0]}" + (
            f" — {text_parts[1]}" if len(text_parts) > 1 else ""
        )
    if text_parts:
        return " — ".join(text_parts)
    if prefix_parts:
        return prefix_parts[0]
    return str(finding)


def format_review_findings(findings: tuple[dict[str, object], ...]) -> tuple[str, ...]:
    return tuple(format_review_finding(finding) for finding in findings if finding)
