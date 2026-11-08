"""Text of the Drainage editor's flow tree (DR-6a).

Pure Python: rows of words for `drainage_flow_service.FlowNode`s; the panel only places them.
"""

from __future__ import annotations

from freecad.Corridor_Road.v1.services.editing.drainage_flow_service import CHECK_ERROR, CHECK_WARNING, FlowNode

LOOP_GROUP_TITLE = "Drain into a loop (no outlet)"
# A grade this close to zero reads as flat; the Policy's minimum grade is checked elsewhere.
FLAT_GRADE_PERCENT = 0.005


def flow_node_text(node: FlowNode) -> str:
    """`inlet:3  STA 120.000  falls 0.80 % into outfall:1  [1 warning]`."""

    parts = [f"{node.point_id}  STA {node.station:.3f}"]
    if node.drains_to_missing:
        parts.append(f"drains into {node.drains_to}, which is not in the Points table")
    elif node.drains_to:
        parts.append(f"{_grade_words(node.link_grade_percent)} into {node.drains_to}".strip())
    elif node.kind == "inlet":
        parts.append("drains nowhere")
    counts = _severity_counts(node)
    if counts:
        parts.append(f"[{counts}]")
    if node.pending == "point":
        parts.insert(0, "+")
        parts.append("(proposed)")
    elif node.pending == "link":
        parts.append("(proposed link)")
    return "  ".join(parts)


def flow_group_title(alignment_ref: str, node_count: int) -> str:
    """A road's group in a document of several roads."""

    return f"{alignment_ref or '(no road)'}  ({node_count} point(s))"


def flow_tree_note(*, point_count: int, root_count: int, loop_count: int, result_note: str = "") -> str:
    """One line under the tree: what it holds, and why checks may be missing."""

    if not point_count:
        text = "No points yet. Add them in the Points tab, or add the suggestions."
    else:
        text = f"{point_count} point(s) in {root_count} flow(s)."
        if loop_count:
            text += f" {loop_count} point(s) drain into a loop."
    return f"{text}\n{result_note}".strip()


def _grade_words(grade_percent: float | None) -> str:
    if grade_percent is None:
        return "drains"
    if abs(grade_percent) < FLAT_GRADE_PERCENT:
        return "drains flat"
    return f"{'falls' if grade_percent < 0.0 else 'rises'} {abs(grade_percent):.2f} %"


def _severity_counts(node: FlowNode) -> str:
    words = []
    for severity, noun in ((CHECK_ERROR, "error"), (CHECK_WARNING, "warning")):
        count = sum(1 for row in node.check_rows if row.severity == severity)
        if count:
            words.append(f"{count} {noun}{'' if count == 1 else 's'}")
    return ", ".join(words)
