"""Small text helpers shared by the review presentation modules."""

from __future__ import annotations


def unique_text_values(values: list[str]) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for value in list(values or []):
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        output.append(text)
    return output


def join_review_notes(*parts: str) -> str:
    return "; ".join(str(part or "").strip() for part in parts if str(part or "").strip())


def display_source_ref(value: object) -> str:
    text = str(value or "").strip()
    if ":" not in text:
        return text
    return text.split(":", 1)[1]


def display_source_id(value: object, prefix: str) -> str:
    text = str(value or "")
    if prefix and text.startswith(prefix):
        return text[len(prefix) :]
    return text


def format_count_summary(counts: dict[str, int], *, limit: int = 5) -> str:
    if not counts:
        return "none"
    rows = sorted(((str(key), int(value)) for key, value in counts.items()), key=lambda item: (-item[1], item[0]))
    text = ", ".join(f"{display_source_ref(key)}:{value}" for key, value in rows[:limit])
    if len(rows) > limit:
        text += f", +{len(rows) - limit} more"
    return text


def unique_refs(values: list[str]) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for value in list(values or []):
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        output.append(text)
    return output
