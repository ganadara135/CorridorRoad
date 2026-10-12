"""Task panels fit FreeCAD's task panel: wide rows wrap instead of pushing buttons out of view."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from freecad.Corridor_Road.qt_compat import QtWidgets  # noqa: E402
from freecad.Corridor_Road.v1.ui.common.panel_width import (  # noqa: E402
    FlowLayout,
    fit_task_panel_width,
    task_panel_width_limit,
)


def _ensure_qapp():
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _wide_panel():
    form = QtWidgets.QWidget()
    layout = QtWidgets.QVBoxLayout(form)
    layout.addWidget(QtWidgets.QLabel("A status line that is much longer than the task panel is wide, " * 2))
    row = QtWidgets.QHBoxLayout()
    row.addWidget(QtWidgets.QLabel("Preset:"))
    row.addWidget(QtWidgets.QComboBox())
    buttons = [QtWidgets.QPushButton(f"Button number {index}") for index in range(8)]
    for button in buttons:
        row.addWidget(button)
    row.addStretch(1)
    layout.addLayout(row)
    group = QtWidgets.QGroupBox("Group")
    group_row = QtWidgets.QHBoxLayout(group)
    group_buttons = [QtWidgets.QPushButton(f"Group button {index}") for index in range(8)]
    for button in group_buttons:
        group_row.addWidget(button)
    layout.addWidget(group)
    short_row = QtWidgets.QHBoxLayout()
    short_row.addWidget(QtWidgets.QPushButton("Apply"))
    layout.addLayout(short_row)
    return form, buttons, group_buttons, short_row


def test_wide_rows_wrap_within_the_task_panel_width() -> None:
    _ensure_qapp()
    form, buttons, group_buttons, _short_row = _wide_panel()
    limit = task_panel_width_limit(form)
    assert form.minimumSizeHint().width() > limit

    assert fit_task_panel_width(form) is form

    assert form.minimumSizeHint().width() <= limit
    # the same widgets are still in the panel, so references and connections stay valid
    assert all(button.window() is form for button in buttons + group_buttons)


def test_every_button_is_inside_the_panel_at_its_narrowest() -> None:
    _ensure_qapp()
    form, buttons, group_buttons, _short_row = _wide_panel()
    fit_task_panel_width(form)
    width = form.minimumSizeHint().width()
    form.resize(width, form.heightForWidth(width) if form.hasHeightForWidth() else form.sizeHint().height())
    form.show()
    QtWidgets.QApplication.processEvents()

    for button in buttons + group_buttons:
        top_left = button.mapTo(form, button.rect().topLeft())
        bottom_right = button.mapTo(form, button.rect().bottomRight())
        assert top_left.x() >= 0 and bottom_right.x() < form.width(), button.text()
    form.hide()


def test_a_label_stays_with_the_field_after_it_and_short_rows_stay_as_they_are() -> None:
    _ensure_qapp()
    form, buttons, _group_buttons, short_row = _wide_panel()
    fit_task_panel_width(form)

    flows = form.findChildren(FlowLayout)
    assert len(flows) == 2  # the button row and the group's row; the short row is untouched
    first_units = [flow.itemAt(0).widget() for flow in flows]
    pairs = [unit for unit in first_units if unit.findChildren(QtWidgets.QLabel)]
    assert len(pairs) == 1
    assert [label.text() for label in pairs[0].findChildren(QtWidgets.QLabel)] == ["Preset:"]
    assert len(pairs[0].findChildren(QtWidgets.QComboBox)) == 1
    assert short_row.count() == 1
    assert buttons[0].isVisibleTo(form)
