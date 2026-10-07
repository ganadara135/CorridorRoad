"""Test-wide fixtures.

The task panels report their outcome through `QMessageBox.information`, `warning` and
`question`. Those are modal: under a real desktop session they open a window and wait for
a click, so a test that drives a panel handler without stubbing them hangs the whole run.
It happened to `test_panel_review_surface_accepts_the_preset_rows_in_the_document` and
`test_superelevation_editor_apply_persists_source_object_and_routes_tree`, and to the
contract gate as a result. Stubbing them here covers every present and future test; a test
that needs a particular answer still sets its own, which takes precedence.
"""

import pytest


@pytest.fixture(autouse=True)
def _modal_message_boxes_never_block(monkeypatch):
    try:
        from freecad.Corridor_Road.qt_compat import QtWidgets

        box = QtWidgets.QMessageBox
    except Exception:  # pure-Python tests that never touch Qt
        yield
        return
    acknowledged = getattr(box, "Ok", None)
    declined = getattr(box, "No", None)
    for name in ("information", "warning", "critical"):
        monkeypatch.setattr(box, name, staticmethod(lambda *args, _answer=acknowledged, **kwargs: _answer))
    # a confirmation that nobody answered is a refusal, the safe default for a write
    monkeypatch.setattr(box, "question", staticmethod(lambda *args, _answer=declined, **kwargs: _answer))
    yield
