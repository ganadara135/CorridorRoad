"""Keep task panels within the width of FreeCAD's task panel.

FreeCAD docks the task panel beside the 3D view, usually only a few hundred pixels wide, and it
cuts off whatever a panel lays out beyond that width. Panels build their rows for a wide window,
so the buttons at the right end of a long row were out of view. `fit_task_panel_width` runs once
after a panel builds its form and narrows it without changing which widgets exist or what they do.
"""

from __future__ import annotations

from freecad.Corridor_Road.qt_compat import QtCore, QtWidgets

# A row may use this many average characters of the panel font before it wraps. The limit follows
# the font, so it holds for any font size and display scaling; at FreeCAD's default font it is
# under 300 pixels, which leaves room for group and tab margins inside the task panel at its usual
# width.
TASK_PANEL_ROW_CHARACTERS = 44

# A combo box shows at least this many characters; longer items are still listed in full when the
# combo box opens.
TASK_PANEL_COMBO_CHARACTERS = 12


class FlowLayout(QtWidgets.QLayout):
    """Lay items out left to right and continue on the next line when the width runs out."""

    def __init__(self, parent=None, spacing: int = 6):
        super().__init__(parent)
        self._items = []
        self._spacing = int(spacing)
        self.setContentsMargins(0, 0, 0, 0)

    def addItem(self, item):  # noqa: N802 - Qt override
        self._items.append(item)

    def count(self):
        return len(self._items)

    def itemAt(self, index):  # noqa: N802 - Qt override
        if 0 <= index < len(self._items):
            return self._items[index]
        return None

    def takeAt(self, index):  # noqa: N802 - Qt override
        if 0 <= index < len(self._items):
            return self._items.pop(index)
        return None

    def expandingDirections(self):  # noqa: N802 - Qt override
        return QtCore.Qt.Orientation(0)

    def hasHeightForWidth(self):  # noqa: N802 - Qt override
        return True

    def heightForWidth(self, width):  # noqa: N802 - Qt override
        return self._arrange(QtCore.QRect(0, 0, int(width), 0), apply=False)

    def setGeometry(self, rect):  # noqa: N802 - Qt override
        super().setGeometry(rect)
        self._arrange(rect, apply=True)

    def sizeHint(self):  # noqa: N802 - Qt override
        # one line when the panel is wide enough
        width = 0
        height = 0
        for item in self._visible_items():
            hint = item.sizeHint()
            width += hint.width() + (self._spacing if width else 0)
            height = max(height, hint.height())
        margins = self.contentsMargins()
        return QtCore.QSize(width + margins.left() + margins.right(), height + margins.top() + margins.bottom())

    def minimumSize(self):  # noqa: N802 - Qt override
        size = QtCore.QSize()
        for item in self._visible_items():
            size = size.expandedTo(item.minimumSize())
        margins = self.contentsMargins()
        return size + QtCore.QSize(margins.left() + margins.right(), margins.top() + margins.bottom())

    def _visible_items(self):
        return [item for item in self._items if not item.isEmpty()]

    def _arrange(self, rect, *, apply: bool) -> int:
        margins = self.contentsMargins()
        area = rect.adjusted(margins.left(), margins.top(), -margins.right(), -margins.bottom())
        x = area.x()
        y = area.y()
        line_height = 0
        for item in self._visible_items():
            hint = item.sizeHint()
            next_x = x + hint.width()
            if line_height and next_x > area.right() + 1:
                x = area.x()
                y += line_height + self._spacing
                next_x = x + hint.width()
                line_height = 0
            if apply:
                item.setGeometry(QtCore.QRect(QtCore.QPoint(x, y), hint))
            x = next_x + self._spacing
            line_height = max(line_height, hint.height())
        return y + line_height - rect.y() + margins.bottom()


def task_panel_width_limit(widget) -> int:
    """The row width, in pixels, past which `fit_task_panel_width` wraps a row of `widget`."""

    try:
        character_width = int(widget.fontMetrics().averageCharWidth())
    except Exception:
        character_width = 7
    return max(1, character_width) * TASK_PANEL_ROW_CHARACTERS


def fit_task_panel_width(form):
    """Narrow a built task panel form so every control stays inside the task panel.

    - a horizontal row wider than the limit becomes a flow row: its widgets keep their order and
      continue on the next line when the panel is narrow, and a label stays with the field after it
    - form layouts move a field below its label when the two do not fit side by side
    - a label on its own line, or one wider than the limit, wraps its text
    - a combo box no longer widens to its longest item

    Widgets are moved, never recreated, so the panel's references and signal connections stay
    valid. Returns `form` so a panel can write `self.form = fit_task_panel_width(self._build_ui())`.
    """

    if form is None:
        return form
    limit = task_panel_width_limit(form)
    for combo in form.findChildren(QtWidgets.QComboBox):
        _narrow_combo(combo)
    for label in form.findChildren(QtWidgets.QLabel):
        _wrap_label(label, limit)
    for form_layout in form.findChildren(QtWidgets.QFormLayout):
        try:
            form_layout.setRowWrapPolicy(QtWidgets.QFormLayout.WrapLongRows)
        except Exception:
            pass
    # innermost rows first, so an outer row measures its already narrowed children
    rows = sorted(form.findChildren(QtWidgets.QHBoxLayout), key=_layout_depth, reverse=True)
    for row in rows:
        if type(row) is QtWidgets.QHBoxLayout and row.minimumSize().width() > limit:
            _replace_with_flow_row(row)
    # layouts and their widget items cache sizes; drop those measured before the rows changed
    for widget in form.findChildren(QtWidgets.QWidget):
        widget.updateGeometry()
    for layout in form.findChildren(QtWidgets.QLayout):
        layout.invalidate()
    if form.layout() is not None:
        form.layout().invalidate()
        form.layout().activate()
    return form


def _narrow_combo(combo) -> None:
    try:
        if combo.sizeAdjustPolicy() == QtWidgets.QComboBox.AdjustToMinimumContentsLengthWithIcon:
            return
        combo.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToMinimumContentsLengthWithIcon)
        if combo.minimumContentsLength() <= 0:
            combo.setMinimumContentsLength(TASK_PANEL_COMBO_CHARACTERS)
    except Exception:
        pass


def _wrap_label(label, limit: int) -> None:
    if label.wordWrap():
        return
    owner = _owning_layout(label)
    standalone = isinstance(owner, QtWidgets.QVBoxLayout)
    if isinstance(owner, QtWidgets.QFormLayout):
        try:
            _row, role = owner.getWidgetPosition(label)
            standalone = role != QtWidgets.QFormLayout.LabelRole
        except Exception:
            standalone = False
    if standalone or label.minimumSizeHint().width() > limit:
        label.setWordWrap(True)


def _owning_layout(widget):
    parent = widget.parentWidget()
    if parent is None or parent.layout() is None:
        return None
    for layout in [parent.layout()] + parent.layout().findChildren(QtWidgets.QLayout):
        if layout.indexOf(widget) >= 0:
            return layout
    return None


def _layout_depth(layout) -> int:
    depth = 0
    parent = layout.parent()
    while parent is not None:
        depth += 1
        parent = parent.parent()
    return depth


def _flow_units(row) -> list:
    """Take the row's widgets and nested rows out, pairing each label with the field after it."""

    units = []
    pending_label = None
    while row.count():
        item = row.takeAt(0)
        widget = item.widget()
        nested = item.layout()
        if nested is not None:
            holder = QtWidgets.QWidget()
            nested.setContentsMargins(0, 0, 0, 0)
            holder.setLayout(nested)
            widget = holder
        if widget is None:
            continue  # stretches and spacings have no place in a flow row
        if pending_label is not None:
            if isinstance(widget, QtWidgets.QLabel):
                units.append(pending_label)
                pending_label = widget
                continue
            pair = QtWidgets.QWidget()
            pair_layout = QtWidgets.QHBoxLayout(pair)
            pair_layout.setContentsMargins(0, 0, 0, 0)
            pair_layout.addWidget(pending_label)
            pair_layout.addWidget(widget, 1)
            units.append(pair)
            pending_label = None
            continue
        if isinstance(widget, QtWidgets.QLabel):
            pending_label = widget
            continue
        units.append(widget)
    if pending_label is not None:
        units.append(pending_label)
    return units


def _replace_with_flow_row(row) -> None:
    parent = row.parent()
    if isinstance(parent, QtWidgets.QLayout):
        index = parent.indexOf(row)
        if index < 0:
            return
        container = QtWidgets.QWidget()
        flow = FlowLayout(container, spacing=max(0, row.spacing()))
        if isinstance(parent, QtWidgets.QBoxLayout):
            stretch = parent.stretch(index)
            parent.takeAt(index)
            parent.insertWidget(index, container, stretch)
        elif isinstance(parent, QtWidgets.QGridLayout):
            grid_row, grid_column, row_span, column_span = parent.getItemPosition(index)
            parent.takeAt(index)
            parent.addWidget(container, grid_row, grid_column, row_span, column_span)
        elif isinstance(parent, QtWidgets.QFormLayout):
            form_row, role = parent.getItemPosition(index)
            parent.takeAt(index)
            parent.setWidget(form_row, role, container)
        else:
            return
        for unit in _flow_units(row):
            flow.addWidget(unit)
        return
    if isinstance(parent, QtWidgets.QWidget) and parent.layout() is row:
        units = _flow_units(row)
        spacing = max(0, row.spacing())
        margins = row.contentsMargins()
        # a widget holds one layout; handing the emptied row to a discarded widget deletes it
        QtWidgets.QWidget().setLayout(row)
        flow = FlowLayout(parent, spacing=spacing)
        flow.setContentsMargins(margins)
        for unit in units:
            flow.addWidget(unit)
