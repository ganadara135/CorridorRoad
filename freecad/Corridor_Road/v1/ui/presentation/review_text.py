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
