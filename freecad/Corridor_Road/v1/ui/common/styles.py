"""Shared Qt style helpers for CorridorRoad v1 panels."""

from __future__ import annotations


def clickable_tab_stylesheet(object_name: str) -> str:
    """Return a dark-theme-readable style for tab widgets that should read as clickable."""

    selector = f"QTabWidget#{object_name}"
    return (
        f"{selector}::pane {{ "
        "border: 1px solid #3f4652; border-radius: 4px; top: -1px; background: #15171b; "
        "} "
        f"{selector} QTabBar::tab {{ "
        "background: #242933; color: #f3f4f6; border: 1px solid #4b5563; "
        "border-bottom-color: #3f4652; border-top-left-radius: 4px; border-top-right-radius: 4px; "
        "padding: 7px 10px; margin-right: 2px; font-weight: 500; "
        "} "
        f"{selector} QTabBar::tab:hover {{ "
        "background: #334155; border-color: #64748b; color: #ffffff; "
        "} "
        f"{selector} QTabBar::tab:selected {{ "
        "background: #1d4ed8; color: #ffffff; border-color: #60a5fa; "
        "border-bottom-color: #1d4ed8; font-weight: 700; "
        "} "
        f"{selector} QTabBar::tab:!selected {{ margin-top: 3px; }}"
    )


def apply_clickable_tab_style(tab_widget, object_name: str) -> None:
    """Apply the shared clickable-tab style without making styling a panel blocker."""

    try:
        tab_widget.setObjectName(str(object_name or "CorridorRoadTabs"))
        tab_widget.setStyleSheet(clickable_tab_stylesheet(str(object_name or "CorridorRoadTabs")))
    except Exception:
        pass
