"""The flowline profile drawing shared by the Drainage panel and Drainage Review.

Draws one Ditch Run's flowline along station with its points, low and high points, the stretches a
check flags and, when given, the links between points (a pipe thicker than open flow). It only
draws what a `FlowlineProfile` holds; it owns no engineering rule and edits nothing.
"""

from __future__ import annotations

from freecad.Corridor_Road.qt_compat import QtCore, QtGui, QtWidgets

SEVERITY_COLORS = {"error": (200, 40, 40), "warning": (220, 140, 20), "info": (90, 90, 90)}
MARKER_COLORS = {"inlet": (30, 140, 60), "outfall": (20, 60, 170), "culvert": (130, 60, 160)}
PIPE_COLOR = (150, 100, 50)
OPEN_FLOW_COLOR = (120, 170, 120)
SELECTED_COLOR = (230, 90, 0)

LEGEND_TEXT = (
    "Blue line: flowline. Thick orange or red: a flagged stretch. Blue dots: low points; grey: high points. "
    "Squares: inlets (green), outfalls (blue), culverts (purple). Brown band: a pipe; green band: open flow; "
    "orange: the selected link or point."
)


class FlowlineProfileWidget(QtWidgets.QWidget):
    """The flowline elevation along station, with its points, links and flagged stretches."""

    def __init__(self, *, minimum_height: int = 220):
        super().__init__()
        self._profile = None
        self._message = "No flowline to draw."
        self.setMinimumHeight(minimum_height)

    def set_profile(self, profile, message: str = "") -> None:
        """Draw a profile, or the message when there is none."""

        self._profile = profile
        if message:
            self._message = message
        self.update()

    def paintEvent(self, _event):
        painter = QtGui.QPainter(self)
        try:
            painter.setRenderHint(QtGui.QPainter.Antialiasing)
            painter.fillRect(self.rect(), QtGui.QColor(250, 250, 250))
            profile = self._profile
            if profile is None or len(profile.points) < 2:
                painter.setPen(QtGui.QColor(60, 60, 60))
                painter.drawText(
                    self.rect().adjusted(8, 4, -8, -4),
                    QtCore.Qt.AlignCenter | QtCore.Qt.TextWordWrap,
                    self._message,
                )
                return
            stations = [station for station, _z in profile.points]
            elevations = [z for _station, z in profile.points] + [marker.z for marker in profile.markers]
            s0, s1 = min(stations), max(stations)
            z0, z1 = min(elevations), max(elevations)
            if z1 - z0 < 0.1:
                # keep a near-flat flowline readable: at least 0.1 m of height
                middle = (z0 + z1) / 2.0
                z0, z1 = middle - 0.05, middle + 0.05
            left, right, top, bottom = 56, 12, 14, 30
            width = max(self.width() - left - right, 1)
            height = max(self.height() - top - bottom, 1)

            def at(station: float, z: float) -> QtCore.QPointF:
                x = left + (station - s0) / max(s1 - s0, 1.0e-9) * width
                y = top + (z1 - z) / max(z1 - z0, 1.0e-9) * height
                return QtCore.QPointF(x, y)

            painter.setPen(QtGui.QPen(QtGui.QColor(120, 120, 120), 1))
            painter.drawText(4, top + 10, f"{z1:.2f}")
            painter.drawText(4, top + height, f"{z0:.2f}")
            painter.drawText(left, self.height() - 8, f"STA {s0:.1f}")
            painter.drawText(left + width - 80, self.height() - 8, f"STA {s1:.1f}")

            # links go under the flowline, so the line stays readable on top of them
            for link in profile.links:
                start, end = at(link.from_station, link.from_z), at(link.to_station, link.to_z)
                if link.selected:
                    color, thickness = SELECTED_COLOR, 11
                elif link.pipe_diameter_m > 0.0:
                    color, thickness = PIPE_COLOR, 9
                else:
                    color, thickness = OPEN_FLOW_COLOR, 6
                pen = QtGui.QPen(QtGui.QColor(*color), thickness)
                pen.setCapStyle(QtCore.Qt.FlatCap)
                painter.setPen(pen)
                painter.drawLine(start, end)
                self._draw_arrow(painter, start, end, color)
                if link.pipe_diameter_m > 0.0 or link.selected:
                    label = link.link_id + (f" Ø{link.pipe_diameter_m:g}" if link.pipe_diameter_m > 0.0 else "")
                    painter.setPen(QtGui.QPen(QtGui.QColor(*color).darker(140), 1))
                    middle = QtCore.QPointF((start.x() + end.x()) / 2.0, (start.y() + end.y()) / 2.0)
                    painter.drawText(middle + QtCore.QPointF(-12.0, 20.0), label)

            painter.setPen(QtGui.QPen(QtGui.QColor(40, 110, 200), 2))
            painter.drawPolyline(QtGui.QPolygonF([at(station, z) for station, z in profile.points]))
            for start, end, severity in profile.flagged:
                stretch = [at(station, z) for station, z in profile.points if start - 1.0e-6 <= station <= end + 1.0e-6]
                if len(stretch) >= 2:
                    painter.setPen(QtGui.QPen(QtGui.QColor(*SEVERITY_COLORS.get(severity, (90, 90, 90))), 5))
                    painter.drawPolyline(QtGui.QPolygonF(stretch))

            painter.setPen(QtCore.Qt.NoPen)
            painter.setBrush(QtGui.QColor(40, 110, 200))
            for station, z in profile.low_points:
                painter.drawEllipse(at(station, z), 4.0, 4.0)
            painter.setBrush(QtGui.QColor(150, 150, 150))
            for station, z in profile.high_points:
                painter.drawEllipse(at(station, z), 3.0, 3.0)
            for marker in profile.markers:
                point = at(marker.station, marker.z)
                if getattr(marker, "selected", False):
                    painter.setPen(QtGui.QPen(QtGui.QColor(*SELECTED_COLOR), 3))
                    painter.setBrush(QtCore.Qt.NoBrush)
                    painter.drawRect(QtCore.QRectF(point.x() - 8.0, point.y() - 8.0, 16.0, 16.0))
                painter.setPen(QtCore.Qt.NoPen)
                painter.setBrush(QtGui.QColor(*MARKER_COLORS.get(marker.kind, (0, 0, 0))))
                painter.drawRect(QtCore.QRectF(point.x() - 5.0, point.y() - 5.0, 10.0, 10.0))
                painter.setPen(QtGui.QPen(QtGui.QColor(30, 30, 30), 1))
                painter.drawText(point + QtCore.QPointF(6.0, -6.0), marker.label)
        finally:
            painter.end()

    @staticmethod
    def _draw_arrow(painter, start, end, color) -> None:
        """A small arrowhead at the end a link drains into."""

        dx, dy = end.x() - start.x(), end.y() - start.y()
        length = (dx * dx + dy * dy) ** 0.5
        if length < 12.0:
            return
        ux, uy = dx / length, dy / length
        tip = QtCore.QPointF(end.x() - ux * 6.0, end.y() - uy * 6.0)
        base = QtCore.QPointF(tip.x() - ux * 9.0, tip.y() - uy * 9.0)
        wing = QtCore.QPointF(-uy * 5.0, ux * 5.0)
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(QtGui.QColor(*color).darker(130))
        painter.drawPolygon(QtGui.QPolygonF([tip, base + wing, base - wing]))
