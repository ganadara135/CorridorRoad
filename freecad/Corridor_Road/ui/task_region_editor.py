# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

import csv
import io
import FreeCAD as App
import FreeCADGui as Gui
import re

from freecad.Corridor_Road.qt_compat import QtCore, QtGui, QtWidgets

from freecad.Corridor_Road.objects.doc_query import find_project
from freecad.Corridor_Road.objects import design_standards as _ds
from freecad.Corridor_Road.objects import unit_policy as _units
from freecad.Corridor_Road.objects.obj_project import assign_project_region_plan, find_region_plan_objects, get_design_standard, resolve_project_region_plan
from freecad.Corridor_Road.objects.obj_region_plan import (
    ALLOWED_CORRIDOR_POLICIES,
    ALLOWED_REGION_LAYERS,
    COMMON_REGION_TYPES,
    RegionPlan,
    ViewProviderRegionPlan,
    ensure_region_plan_properties,
)
from freecad.Corridor_Road.objects.obj_structure_set import StructureSet as StructureSetSource
from freecad.Corridor_Road.objects.obj_structure_set import ALLOWED_TYPES as STRUCTURE_REGION_TYPES
from freecad.Corridor_Road.objects.obj_typical_section_template import (
    component_rows as typical_component_rows,
    roadside_library_rows as typical_roadside_library_rows,
)
from freecad.Corridor_Road.objects.project_links import link_project


COL_HEADERS = [
    "Id",
    "RegionType",
    "Layer",
    "StartStation",
    "EndStation",
    "Priority",
    "TransitionIn",
    "TransitionOut",
    "TemplateName",
    "AssemblyName",
    "RuleSet",
    "SidePolicy",
    "DaylightPolicy",
    "CorridorPolicy",
    "Enabled",
    "Notes",
    "HintSource",
    "HintStatus",
    "HintReason",
    "HintConfidence",
]

REGION_PRESET_NAMES = [
    "Project Linked Seed",
    "Basic Base Regions",
    "Section Override Sample",
    "Corridor Override Sample",
    "Base + Overlay Mixed",
]

REGION_TYPE_ITEMS = [""] + sorted(
    {
        str(v or "").strip()
        for v in list(COMMON_REGION_TYPES) + list(STRUCTURE_REGION_TYPES)
        if str(v or "").strip()
    }
)
COMBO_COLUMN_ITEMS = {
    1: list(REGION_TYPE_ITEMS),
}
HINT_STATUS_PENDING = "pending"
HINT_STATUS_ACCEPTED = "accepted"
HINT_STATUS_IGNORED = "ignored"
HINT_NOTE_PREFIXES = {
    HINT_STATUS_ACCEPTED: "[Accepted Hint]",
    HINT_STATUS_IGNORED: "[Ignored Hint]",
}
CSV_COMMENT_PREFIX = "#"
CSV_LINEAR_UNIT_KEYS = {
    "linear",
    "linearunit",
    "linear_unit",
    "lengthunit",
    "length_unit",
    "unit",
    "units",
}
OVERRIDE_KIND_ITEMS = [
    "Ditch / Berm",
    "Urban Edge",
    "Corridor Zone",
    "Other",
]
OVERRIDE_SCOPE_ITEMS = [
    "Left",
    "Right",
    "Both",
]
OVERRIDE_ACTION_ITEMS = [
    "Berm",
    "Daylight Off",
    "Split Corridor",
    "Skip Corridor",
    "-",
]


def _find_region_sets(doc):
    return find_region_plan_objects(doc)


def _normalize_csv_linear_unit(value):
    token = str(value or "").strip().lower()
    if token in ("m", "meter", "meters", "metre", "metres"):
        return "m"
    if token in ("mm", "millimeter", "millimeters", "millimetre", "millimetres"):
        return "mm"
    if token == "custom":
        return "custom"
    return ""


def _parse_csv_unit_metadata(lines):
    meta = {}
    for raw_line in list(lines or []):
        line = str(raw_line or "").strip()
        if not line.startswith(CSV_COMMENT_PREFIX):
            continue
        body = line[1:].strip()
        if not body:
            continue
        for part in body.replace(";", ",").split(","):
            seg = str(part or "").strip()
            if "=" not in seg:
                continue
            key, value = seg.split("=", 1)
            norm_key = "".join(ch for ch in str(key or "").strip().lower() if ch.isalnum() or ch == "_")
            if norm_key in CSV_LINEAR_UNIT_KEYS:
                token = _normalize_csv_linear_unit(value)
                if token:
                    meta["linear_unit"] = token
    return meta


class RegionEditorTaskPanel:
    def __init__(self):
        self.doc = App.ActiveDocument
        self._regions = []
        self._loading = False
        self._workflow_syncing = False
        self._timeline_real_row_count = 0
        self._workflow_action_buttons = {}
        self._workflow_group_boxes = {}
        self.form = self._build_ui()
        self._refresh_context()

    def getStandardButtons(self):
        return 0

    def accept(self):
        Gui.Control.closeDialog()

    def reject(self):
        Gui.Control.closeDialog()

    def _unit_context(self):
        prj = find_project(self.doc)
        return prj if prj is not None else self.doc

    def _meters_from_csv(self, value, linear_unit: str = "") -> float:
        return _units.meters_from_user_length(self._unit_context(), self._safe_float(value, default=0.0), unit=linear_unit, use_default="import")

    def _csv_from_meters(self, meters, linear_unit: str = "") -> float:
        return _units.user_length_from_meters(self._unit_context(), self._safe_float(meters, default=0.0), unit=linear_unit, use_default="export")

    def _display_unit_label(self) -> str:
        return str(_units.get_linear_display_unit(self._unit_context()) or "m")

    def _display_from_meters(self, meters) -> float:
        return _units.user_length_from_meters(
            self._unit_context(),
            self._safe_float(meters, default=0.0),
            use_default="display",
        )

    def _meters_from_display(self, value) -> float:
        return _units.meters_from_user_length(
            self._unit_context(),
            self._safe_float(value, default=0.0),
            use_default="display",
        )

    def _format_display_length(self, meters, digits: int = 3) -> str:
        return f"{self._display_from_meters(meters):.{int(digits)}f}"

    @staticmethod
    def _fmt_obj(prefix, obj):
        return f"[{prefix}] {obj.Label} ({obj.Name})"

    @staticmethod
    def _safe_float(value, default: float = 0.0) -> float:
        try:
            return float(value)
        except Exception:
            return float(default)

    @staticmethod
    def _safe_int(value, default: int = 0) -> int:
        try:
            return int(round(float(value)))
        except Exception:
            return int(default)

    @staticmethod
    def _label_name(obj):
        if obj is None:
            return ""
        return str(getattr(obj, "Label", "") or getattr(obj, "Name", "") or "").strip()

    @staticmethod
    def _sanitize_id_token(text: str, default_text: str = "OTHER") -> str:
        raw = str(text or "").strip().upper()
        raw = re.sub(r"[^A-Z0-9_]+", "_", raw)
        raw = re.sub(r"_+", "_", raw).strip("_")
        return raw or str(default_text)

    @staticmethod
    def _control_width_hint(widget, text: str, *, padding: int = 36, minimum: int = 80, maximum: int = 320) -> int:
        try:
            fm = widget.fontMetrics()
            width = int(fm.horizontalAdvance(str(text or ""))) + int(padding)
            return max(int(minimum), min(int(maximum), width))
        except Exception:
            return int(max(minimum, min(maximum, 160)))

    def _set_compact_button(self, button, *, padding: int = 34, minimum: int = 92, maximum: int = 220):
        if button is None:
            return
        width = self._control_width_hint(button, button.text(), padding=padding, minimum=minimum, maximum=maximum)
        button.setSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Fixed)
        button.setMaximumWidth(width)

    def _set_compact_combo(self, combo, *, sample_texts=None, minimum: int = 150, maximum: int = 320):
        if combo is None:
            return
        texts = [str(v or "") for v in list(sample_texts or []) if str(v or "")]
        if not texts:
            try:
                texts = [str(combo.itemText(i) or "") for i in range(combo.count()) if str(combo.itemText(i) or "")]
            except Exception:
                texts = []
        longest = max(texts, key=len) if texts else ""
        width = self._control_width_hint(combo, longest, padding=56, minimum=minimum, maximum=maximum)
        combo.setSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Fixed)
        combo.setMaximumWidth(width)

    def _set_compact_line_edit(self, edit, *, sample_text: str = "1000.000", minimum: int = 110, maximum: int = 180):
        if edit is None:
            return
        width = self._control_width_hint(edit, sample_text, padding=28, minimum=minimum, maximum=maximum)
        edit.setSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Fixed)
        edit.setMaximumWidth(width)

    @classmethod
    def _auto_region_id(cls, layer: str, region_type: str, existing_ids, exclude_id: str = "") -> str:
        prefix = "BASE" if str(layer or "").strip().lower() == "base" else "OVR"
        type_token = cls._sanitize_id_token(region_type, default_text="OTHER")
        taken = {
            str(v or "").strip().upper()
            for v in list(existing_ids or [])
            if str(v or "").strip() and str(v or "").strip().upper() != str(exclude_id or "").strip().upper()
        }
        idx = 1
        while idx < 1000:
            candidate = f"{prefix}_{type_token}_{idx:02d}"
            if candidate.upper() not in taken:
                return candidate
            idx += 1
        return f"{prefix}_{type_token}_999"

    @staticmethod
    def _is_generated_region_id(text: str) -> bool:
        return bool(re.match(r"^(BASE|OVR)_[A-Z0-9_]+_\d{2,3}$", str(text or "").strip().upper()))

    @staticmethod
    def _region_record(
        rid: str,
        region_type: str,
        layer: str,
        start_station: float,
        end_station: float,
        *,
        priority: int = 0,
        transition_in: float = 0.0,
        transition_out: float = 0.0,
        template_name: str = "",
        assembly_name: str = "",
        rule_set: str = "",
        side_policy: str = "",
        daylight_policy: str = "",
        corridor_policy: str = "",
        enabled: bool = True,
        notes: str = "",
        hint_source: str = "",
        hint_status: str = "",
        hint_reason: str = "",
        hint_confidence: float = 0.0,
    ):
        return {
            "Id": str(rid or ""),
            "RegionType": str(region_type or ""),
            "Layer": str(layer or "base"),
            "StartStation": float(start_station or 0.0),
            "EndStation": float(end_station or 0.0),
            "Priority": int(priority or 0),
            "TransitionIn": float(transition_in or 0.0),
            "TransitionOut": float(transition_out or 0.0),
            "TemplateName": str(template_name or ""),
            "AssemblyName": str(assembly_name or ""),
            "RuleSet": str(rule_set or ""),
            "SidePolicy": str(side_policy or ""),
            "DaylightPolicy": str(daylight_policy or ""),
            "CorridorPolicy": str(corridor_policy or ""),
            "Enabled": bool(enabled),
            "Notes": str(notes or ""),
            "HintSource": str(hint_source or ""),
            "HintStatus": str(hint_status or ""),
            "HintReason": str(hint_reason or ""),
            "HintConfidence": float(hint_confidence or 0.0),
        }

    def _make_region_preset(self, name: str):
        preset = str(name or "").strip()
        if preset == "Project Linked Seed":
            return self._make_project_seed_rows()
        if preset == "Basic Base Regions":
            return [
                self._region_record("BASE_01", "roadway", "base", 0.0, 35.0, notes="Default roadway zone"),
                self._region_record("BASE_02", "widening", "base", 35.0, 70.0, notes="Main widening span"),
                self._region_record("BASE_03", "bridge_approach", "base", 70.0, 100.0, notes="Bridge approach span"),
            ]
        if preset == "Section Override Sample":
            return [
                self._region_record("BASE_01", "roadway", "base", 0.0, 40.0, notes="Default roadway"),
                self._region_record("BASE_02", "widening", "base", 40.0, 70.0, side_policy="both:stub", notes="Suppressed side slopes in widening"),
                self._region_record("BASE_03", "bridge_approach", "base", 70.0, 100.0, daylight_policy="both:off", notes="Disable daylight near bridge approach"),
                self._region_record(
                    "OVR_01",
                    "ditch_override",
                    "overlay",
                    48.0,
                    52.0,
                    priority=10,
                    side_policy="left:berm",
                    notes="Local ditch or berm treatment on the left side",
                ),
            ]
        if preset == "Corridor Override Sample":
            return [
                self._region_record("BASE_01", "roadway", "base", 0.0, 35.0, notes="Default roadway"),
                self._region_record("BASE_02", "widening", "base", 35.0, 70.0, notes="Widening span"),
                self._region_record("BASE_03", "bridge_approach", "base", 70.0, 100.0, notes="Bridge approach span"),
                self._region_record(
                    "OVR_01",
                    "retaining_wall_zone",
                    "overlay",
                    30.0,
                    60.0,
                    priority=20,
                    transition_in=3.0,
                    transition_out=3.0,
                    corridor_policy="split_only",
                    notes="Corridor split zone without skipping",
                ),
                self._region_record(
                    "OVR_02",
                    "bridge_approach",
                    "overlay",
                    72.0,
                    88.0,
                    priority=30,
                    transition_in=4.0,
                    transition_out=4.0,
                    corridor_policy="skip_zone",
                    notes="Skip corridor generation through localized bridge work zone",
                ),
            ]
        if preset == "Base + Overlay Mixed":
            return [
                self._region_record("BASE_01", "roadway", "base", 0.0, 35.0, template_name="roadway_default", notes="Base roadway"),
                self._region_record(
                    "BASE_02",
                    "widening",
                    "base",
                    35.0,
                    70.0,
                    template_name="roadway_widening",
                    side_policy="both:stub",
                    notes="Base widening with side suppression",
                ),
                self._region_record(
                    "BASE_03",
                    "bridge_approach",
                    "base",
                    70.0,
                    100.0,
                    template_name="bridge_approach",
                    daylight_policy="both:off",
                    notes="Base bridge approach with daylight off",
                ),
                self._region_record(
                    "OVR_01",
                    "ditch_override",
                    "overlay",
                    46.0,
                    54.0,
                    priority=15,
                    side_policy="left:berm",
                    notes="Overlay left-side ditch adjustment",
                ),
                self._region_record(
                    "OVR_02",
                    "retaining_wall_zone",
                    "overlay",
                    58.0,
                    64.0,
                    priority=25,
                    corridor_policy="split_only",
                    notes="Overlay retaining wall split zone",
                ),
                self._region_record(
                    "OVR_03",
                    "bridge_approach",
                    "overlay",
                    78.0,
                    84.0,
                    priority=35,
                    transition_in=2.0,
                    transition_out=2.0,
                    corridor_policy="skip_zone",
                    daylight_policy="right:off",
                    notes="Localized bridge work overlay",
                ),
            ]
        return []

    def _project_seed_context(self):
        prj = find_project(self.doc)
        if prj is None:
            return {
                "project": None,
                "assembly": None,
                "typical": None,
                "structure": None,
            }
        return {
            "project": prj,
            "assembly": getattr(prj, "AssemblyTemplate", None) if hasattr(prj, "AssemblyTemplate") else None,
            "typical": getattr(prj, "TypicalSectionTemplate", None) if hasattr(prj, "TypicalSectionTemplate") else None,
            "structure": getattr(prj, "StructureSet", None) if hasattr(prj, "StructureSet") else None,
            "alignment": getattr(prj, "Alignment", None) if hasattr(prj, "Alignment") else None,
        }

    def _project_seed_span(self, structure_obj):
        if structure_obj is None:
            return (0.0, 100.0, [])
        recs = list(StructureSetSource.records(structure_obj) or [])
        spans = []
        for rec in recs:
            s0 = self._safe_float(rec.get("StartStation", 0.0), default=0.0)
            s1 = self._safe_float(rec.get("EndStation", 0.0), default=0.0)
            sc = self._safe_float(rec.get("CenterStation", 0.0), default=0.0)
            if s1 < s0:
                s0, s1 = s1, s0
            if abs(s1 - s0) <= 1e-9:
                margin = max(
                    2.0,
                    abs(self._safe_float(rec.get("CorridorMargin", 0.0), default=0.0)),
                    0.5 * abs(self._safe_float(rec.get("Width", 0.0), default=0.0)),
                )
                if abs(sc) > 1e-9 or abs(s0) > 1e-9:
                    center = sc if abs(sc) > 1e-9 else s0
                    s0 = center - margin
                    s1 = center + margin
            if s1 > s0 + 1e-9:
                spans.append((float(s0), float(s1)))
        if not spans:
            return (0.0, 100.0, recs)
        start = min(span[0] for span in spans)
        end = max(span[1] for span in spans)
        length = max(0.0, float(end - start))
        pad = max(10.0, 0.15 * length)
        start = float(start - pad)
        end = float(end + pad)
        if start > 0.0:
            start = max(0.0, start)
        if end <= start + 1e-9:
            end = start + 100.0
        return (start, end, recs)

    def _project_seed_typical_notes(self, typical_obj):
        if typical_obj is None:
            return []
        notes = []
        typ_name = self._label_name(typical_obj)
        if typ_name:
            notes.append(f"Typical={typ_name}")
        mode = str(getattr(typical_obj, "PracticalSectionMode", "") or "").strip()
        if mode:
            notes.append(f"practical={mode}")
        left_edge = str(getattr(typical_obj, "LeftEdgeComponentType", "") or "").strip()
        right_edge = str(getattr(typical_obj, "RightEdgeComponentType", "") or "").strip()
        if not left_edge and not right_edge:
            try:
                rows = [row for row in list(typical_component_rows(typical_obj) or []) if bool(row.get("Enabled", True))]
            except Exception:
                rows = []
            left_rows = [row for row in rows if str(row.get("Side", "") or "").strip().lower() == "left"]
            right_rows = [row for row in rows if str(row.get("Side", "") or "").strip().lower() == "right"]
            if left_rows:
                left_edge = str(left_rows[-1].get("Type", "") or "").strip()
            if right_rows:
                right_edge = str(right_rows[-1].get("Type", "") or "").strip()
        if left_edge or right_edge:
            notes.append(f"edges=({left_edge or '-'}, {right_edge or '-'})")
        pavement = self._safe_float(getattr(typical_obj, "PavementTotalThickness", 0.0), default=0.0)
        if pavement > 1e-9:
            notes.append(f"pavement={pavement:.3f}m")
        try:
            roadside_rows = list(typical_roadside_library_rows(typical_component_rows(typical_obj)) or [])
        except Exception:
            roadside_rows = []
        if roadside_rows:
            notes.append("roadside=" + ",".join(str(row) for row in roadside_rows))
        return notes

    @staticmethod
    def _seed_confidence_label(value: float) -> str:
        score = max(0.0, min(1.0, float(value or 0.0)))
        if score >= 0.85:
            return "High"
        if score >= 0.65:
            return "Medium"
        return "Low"

    def _typical_hint_confidence(self, family: str, side: str, practical_mode: str = "") -> float:
        fam = str(family or "").strip().lower()
        mode = str(practical_mode or "").strip().lower()
        score = 0.65
        if fam in ("ditch_edge", "urban_edge"):
            score = 0.9
        elif fam == "shoulder_edge":
            score = 0.6
        if fam == "ditch_edge" and mode in ("rural", "ditch", "open"):
            score = max(score, 0.95)
        if fam == "urban_edge" and mode in ("urban", "closed"):
            score = max(score, 0.95)
        if fam == "shoulder_edge" and mode in ("simple", "rural", "open"):
            score = max(score, 0.75)
        if str(side or "").strip().lower() not in ("left", "right", "both"):
            score = max(0.5, score - 0.15)
        return float(max(0.0, min(1.0, score)))

    def _structure_hint_defaults(self, rec) -> dict:
        stype = str(rec.get("Type", "") or "").strip().lower() or "other"
        side = str(rec.get("Side", "") or "").strip().lower() or "both"
        corridor_policy = str(rec.get("CorridorMode", "") or "").strip().lower()
        if corridor_policy == "none":
            corridor_policy = ""
        side_policy = ""
        daylight_policy = ""
        confidence = 0.7
        reason = "Linked StructureSet span can be reviewed as a local override."

        if stype in ("retaining_wall",):
            daylight_policy = f"{side if side in ('left', 'right', 'both') else 'both'}:off"
            confidence = 0.92
            reason = f"Retaining wall span on the {side} side may need daylight suppression."
        elif stype in ("bridge_zone", "abutment_zone"):
            if not corridor_policy:
                corridor_policy = "split_only"
            confidence = 0.88
            reason = "Bridge-related work zone may need corridor splitting through the localized structure span."
        elif stype in ("culvert", "crossing"):
            confidence = 0.95 if corridor_policy in ("split_only", "skip_zone") else 0.75
            reason = f"{self._title_case_token(stype)} span can be reviewed as a local structure override."
        else:
            confidence = 0.6 if corridor_policy else 0.5

        family = stype or "other"
        return {
            "family": family,
            "corridor_policy": corridor_policy,
            "side_policy": side_policy,
            "daylight_policy": daylight_policy,
            "confidence": float(max(0.0, min(1.0, confidence))),
            "reason": str(reason or ""),
        }

    def _project_mode_seed_rows(self, typical_obj, start_station: float, end_station: float, assembly_name: str = ""):
        if typical_obj is None or end_station <= start_station + 1e-9:
            return []
        mode = str(getattr(typical_obj, "PracticalSectionMode", "") or "").strip().lower()
        if mode not in ("urban", "rural", "open", "closed"):
            return []
        region_type = "retaining_wall_zone" if mode in ("urban", "closed") else "earthwork_zone"
        daylight_policy = "both:off" if mode in ("urban", "closed") else ""
        hint_confidence = 0.7 if mode in ("open",) else 0.82
        return [
            self._region_record(
                f"MODE_{mode.upper()}",
                region_type,
                "overlay",
                start_station,
                end_station,
                priority=18,
                assembly_name=assembly_name,
                rule_set=f"project:practical_mode:{mode}",
                daylight_policy=daylight_policy,
                enabled=False,
                hint_source="project",
                hint_status=HINT_STATUS_PENDING,
                hint_reason=f"Practical section mode `{mode}` suggests reviewing corridor-side region defaults.",
                hint_confidence=hint_confidence,
                notes="Project mode hint; review before accepting because it reflects the broad section mode, not a localized event.",
            )
        ]

    def _project_standard_seed_rows(self, project_obj, alignment_obj, start_station: float, end_station: float, assembly_name: str = ""):
        if project_obj is None or end_station <= start_station + 1e-9:
            return []
        standard = get_design_standard(project_obj)
        speed_kph = self._safe_float(getattr(alignment_obj, "DesignSpeedKph", 60.0) if alignment_obj is not None else 60.0, default=60.0)
        criteria = _ds.criteria_defaults(standard, speed_kph, scale=1.0)
        min_transition = self._safe_float(criteria.get("min_transition", 0.0), default=0.0)
        min_tangent = self._safe_float(criteria.get("min_tangent", 0.0), default=0.0)
        std_tag = str(standard or "").strip().upper() or _ds.DEFAULT_STANDARD
        speed_tag = int(round(float(speed_kph)))
        unit_label = self._display_unit_label()
        reason = (
            f"{std_tag} at {float(speed_kph):.0f} km/h suggests reviewing localized transition lengths "
            f"(>= {self._format_display_length(min_transition, digits=1)} {unit_label}) and "
            f"tangent buffers (>= {self._format_display_length(min_tangent, digits=1)} {unit_label}) around bridge or work-zone overrides."
        )
        return [
            self._region_record(
                f"STD_{std_tag}_{speed_tag:03d}",
                "other",
                "overlay",
                start_station,
                end_station,
                priority=16,
                assembly_name=assembly_name,
                rule_set=f"standard:{std_tag}:{speed_tag}",
                enabled=False,
                hint_source="standard",
                hint_status=HINT_STATUS_PENDING,
                hint_reason=reason,
                hint_confidence=0.8,
                notes=(
                    f"Standards-driven review hint ({std_tag}, {float(speed_kph):.0f} km/h); "
                    "informational seed only until a localized override needs explicit transition review."
                ),
            )
        ]

    def _make_typical_overlay_seed_rows(self, typical_obj, start_station: float, end_station: float, assembly_name: str = ""):
        if typical_obj is None or end_station <= start_station + 1e-9:
            return []
        try:
            roadside_rows = list(typical_roadside_library_rows(typical_component_rows(typical_obj)) or [])
        except Exception:
            roadside_rows = []
        if not roadside_rows:
            return []

        out = []
        priority = 20
        practical_mode = str(getattr(typical_obj, "PracticalSectionMode", "") or "").strip().lower()
        for item in roadside_rows:
            family, _, side = str(item or "").partition(":")
            family = family.strip().lower()
            side = side.strip().lower()
            if family == "ditch_edge" and side in ("left", "right"):
                confidence = self._typical_hint_confidence(family, side, practical_mode)
                out.append(
                    self._region_record(
                        f"TYP_{side.upper()}_DITCH",
                        "ditch_override",
                        "overlay",
                        start_station,
                        end_station,
                        priority=priority,
                        assembly_name=assembly_name,
                        rule_set=f"typical:{family}:{side}",
                        side_policy=f"{side}:berm",
                        enabled=False,
                        hint_source="typical",
                        hint_status=HINT_STATUS_PENDING,
                        hint_reason=f"Detected ditch roadside pattern on the {side} side.",
                        hint_confidence=confidence,
                        notes=(
                            f"Auto roadside hint from Typical Section ({family}:{side}, confidence={self._seed_confidence_label(confidence)}); "
                            "enable after reviewing berm/ditch behavior."
                        ),
                    )
                )
                priority += 1
            elif family == "urban_edge" and side in ("left", "right"):
                confidence = self._typical_hint_confidence(family, side, practical_mode)
                out.append(
                    self._region_record(
                        f"TYP_{side.upper()}_URBAN",
                        "retaining_wall_zone",
                        "overlay",
                        start_station,
                        end_station,
                        priority=priority,
                        assembly_name=assembly_name,
                        rule_set=f"typical:{family}:{side}",
                        daylight_policy=f"{side}:off",
                        enabled=False,
                        hint_source="typical",
                        hint_status=HINT_STATUS_PENDING,
                        hint_reason=f"Detected urban edge roadside pattern on the {side} side.",
                        hint_confidence=confidence,
                        notes=(
                            f"Auto roadside hint from Typical Section ({family}:{side}, confidence={self._seed_confidence_label(confidence)}); "
                            "use when the urban edge should suppress daylight on that side."
                        ),
                    )
                )
                priority += 1
            elif family == "shoulder_edge" and side in ("left", "right"):
                confidence = self._typical_hint_confidence(family, side, practical_mode)
                out.append(
                    self._region_record(
                        f"TYP_{side.upper()}_SHOULDER",
                        "earthwork_zone",
                        "overlay",
                        start_station,
                        end_station,
                        priority=priority,
                        assembly_name=assembly_name,
                        rule_set=f"typical:{family}:{side}",
                        enabled=False,
                        hint_source="typical",
                        hint_status=HINT_STATUS_PENDING,
                        hint_reason=f"Detected open shoulder edge on the {side} side.",
                        hint_confidence=confidence,
                        notes=(
                            f"Auto roadside hint from Typical Section ({family}:{side}, confidence={self._seed_confidence_label(confidence)}); "
                            "review whether the open shoulder edge needs an earthwork or daylight override."
                        ),
                    )
                )
                priority += 1
        return out

    def _project_seed_bundle(self):
        ctx = self._project_seed_context()
        if ctx.get("project") is None and ctx.get("assembly") is None and ctx.get("typical") is None and ctx.get("structure") is None:
            return {"base_rows": [], "hint_rows": []}
        asm = ctx.get("assembly")
        typ = ctx.get("typical")
        struct = ctx.get("structure")
        aln = ctx.get("alignment")
        prj = ctx.get("project")
        base_start, base_end, struct_recs = self._project_seed_span(struct)
        assembly_name = self._label_name(asm)
        template_name = self._label_name(typ)
        rule_set = f"typical:{getattr(typ, 'Name', '')}" if typ is not None else ""

        base_notes = ["Auto-seeded from project links"]
        base_notes.extend(self._project_seed_typical_notes(typ))
        if assembly_name:
            base_notes.append(f"Assembly={assembly_name}")
        if struct is not None and struct_recs:
            base_notes.append(f"Structure hints={len(struct_recs)}")

        base_rows = [
            self._region_record(
                "BASE_01",
                "roadway",
                "base",
                base_start,
                base_end,
                template_name=template_name,
                assembly_name=assembly_name,
                rule_set=rule_set,
                notes=" | ".join(base_notes),
            )
        ]
        hint_rows = list(self._make_typical_overlay_seed_rows(typ, base_start, base_end, assembly_name=assembly_name))
        hint_rows.extend(self._project_mode_seed_rows(typ, base_start, base_end, assembly_name=assembly_name))
        hint_rows.extend(self._project_standard_seed_rows(prj, aln, base_start, base_end, assembly_name=assembly_name))

        for idx, rec in enumerate(struct_recs, 1):
            sid = str(rec.get("Id", "") or f"STR_{idx:02d}").strip() or f"STR_{idx:02d}"
            s0 = self._safe_float(rec.get("StartStation", 0.0), default=0.0)
            s1 = self._safe_float(rec.get("EndStation", 0.0), default=0.0)
            sc = self._safe_float(rec.get("CenterStation", 0.0), default=0.0)
            if s1 < s0:
                s0, s1 = s1, s0
            if abs(s1 - s0) <= 1e-9:
                margin = max(
                    2.0,
                    abs(self._safe_float(rec.get("CorridorMargin", 0.0), default=0.0)),
                    0.5 * abs(self._safe_float(rec.get("Width", 0.0), default=0.0)),
                )
                center = sc if abs(sc) > 1e-9 else s0
                s0 = center - margin
                s1 = center + margin
            if s1 <= s0 + 1e-9:
                continue
            stype = str(rec.get("Type", "") or "").strip() or "other"
            defaults = self._structure_hint_defaults(rec)
            hint_rows.append(
                self._region_record(
                    f"AUTO_{idx:02d}_{sid}",
                    stype if stype in COMMON_REGION_TYPES else stype,
                    "overlay",
                    s0,
                    s1,
                    priority=50 + idx,
                    template_name=str(rec.get("TemplateName", "") or "").strip(),
                    assembly_name=assembly_name,
                    rule_set=f"structure:{defaults.get('family', stype)}:{sid}",
                    side_policy=str(defaults.get("side_policy", "") or ""),
                    daylight_policy=str(defaults.get("daylight_policy", "") or ""),
                    corridor_policy=str(defaults.get("corridor_policy", "") or ""),
                    enabled=False,
                    hint_source="structure",
                    hint_status=HINT_STATUS_PENDING,
                    hint_reason=str(defaults.get("reason", "") or f"Linked StructureSet span {sid} can be reviewed as a local override."),
                    hint_confidence=float(defaults.get("confidence", 0.7) or 0.7),
                    notes=(
                        f"Auto seed from linked StructureSet ({stype}); disabled by default to avoid double-driving "
                        "until the region rules are reviewed."
                    ),
                )
            )
        return {
            "base_rows": list(base_rows),
            "hint_rows": list(hint_rows),
        }

    def _make_project_seed_rows(self):
        bundle = self._project_seed_bundle()
        return list(bundle.get("base_rows", []) or []) + list(bundle.get("hint_rows", []) or [])

    @staticmethod
    def _is_enabled_row(rec) -> bool:
        return str(rec.get("Enabled", "true") or "true").strip().lower() not in ("false", "0", "no", "off", "disabled")

    def _is_seed_managed_hint(self, rec) -> bool:
        if self._is_enabled_row(rec):
            return False
        source = str(rec.get("HintSource", "") or "").strip().lower()
        rule_set = str(rec.get("RuleSet", "") or "").strip().lower()
        return source in ("typical", "structure", "seed", "project", "standard") or rule_set.startswith("typical:") or rule_set.startswith("structure:") or rule_set.startswith("standard:") or rule_set.startswith("project:")

    def _merge_project_seed_rows(self, existing_rows):
        bundle = self._project_seed_bundle()
        base_rows = list(bundle.get("base_rows", []) or [])
        hint_rows = list(bundle.get("hint_rows", []) or [])
        current_rows = [dict(row) for row in list(existing_rows or [])]
        if not base_rows and not hint_rows:
            return {
                "rows": current_rows,
                "base_added": 0,
                "hint_added": 0,
                "hint_replaced": 0,
            }

        existing_has_base = any(str(row.get("Layer", "") or "").strip().lower() == "base" for row in current_rows)
        seed_hint_ids = {str(row.get("Id", "") or "").strip() for row in hint_rows if str(row.get("Id", "") or "").strip()}
        merged_rows = []
        hint_replaced = 0
        for row in current_rows:
            rid = str(row.get("Id", "") or "").strip()
            if rid and rid in seed_hint_ids and self._is_seed_managed_hint(row):
                hint_replaced += 1
                continue
            merged_rows.append(dict(row))

        if (not existing_has_base) and base_rows:
            merged_rows = list(base_rows) + merged_rows

        merged_ids = {str(row.get("Id", "") or "").strip() for row in merged_rows if str(row.get("Id", "") or "").strip()}
        hint_added = 0
        for row in hint_rows:
            rid = str(row.get("Id", "") or "").strip()
            if rid and rid in merged_ids:
                continue
            merged_rows.append(dict(row))
            if rid:
                merged_ids.add(rid)
            hint_added += 1

        return {
            "rows": merged_rows,
            "base_added": len(base_rows) if (base_rows and not existing_has_base) else 0,
            "hint_added": hint_added,
            "hint_replaced": hint_replaced,
        }

    def _build_ui(self):
        w = QtWidgets.QWidget()
        w.setWindowTitle("CorridorRoad - Manage Region Plan")

        main = QtWidgets.QVBoxLayout(w)
        main.setContentsMargins(10, 10, 10, 10)
        main.setSpacing(8)

        self.lbl_info = QtWidgets.QLabel("")
        self.lbl_info.setWordWrap(True)
        main.addWidget(self.lbl_info)

        form_target = QtWidgets.QFormLayout()
        self.cmb_target = QtWidgets.QComboBox()
        self._set_compact_combo(self.cmb_target, sample_texts=["[New] Create new Region Plan"], minimum=240, maximum=440)
        form_target.addRow("Target Region Plan:", self.cmb_target)
        self.chk_auto_seed_project = QtWidgets.QCheckBox("Auto-seed [New]")
        self.chk_auto_seed_project.setChecked(True)
        form_target.addRow("New Plan:", self.chk_auto_seed_project)
        preset_row = QtWidgets.QHBoxLayout()
        self.cmb_preset = QtWidgets.QComboBox()
        self.cmb_preset.addItem("")
        self.cmb_preset.addItems(list(REGION_PRESET_NAMES))
        self.cmb_preset.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self._set_compact_combo(self.cmb_preset, sample_texts=REGION_PRESET_NAMES, minimum=150, maximum=230)
        self.cmb_preset.setMinimumWidth(190)
        self.cmb_preset.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
        self.btn_load_preset = QtWidgets.QPushButton("Load Preset Data")
        self.btn_seed_project = QtWidgets.QPushButton("Seed From Project")
        self._set_compact_button(self.btn_load_preset, minimum=120, maximum=180)
        self._set_compact_button(self.btn_seed_project, minimum=120, maximum=175)
        preset_row.addWidget(self.cmb_preset, 0)
        preset_row.addWidget(self.btn_load_preset)
        preset_row.addWidget(self.btn_seed_project)
        preset_row.addStretch(1)
        preset_wrap = QtWidgets.QWidget()
        preset_wrap.setLayout(preset_row)
        form_target.addRow("Preset Data:", preset_wrap)
        csv_row = QtWidgets.QHBoxLayout()
        self.btn_import_csv = QtWidgets.QPushButton("Import CSV")
        self.btn_export_csv = QtWidgets.QPushButton("Export CSV")
        self._set_compact_button(self.btn_import_csv, minimum=105, maximum=135)
        self._set_compact_button(self.btn_export_csv, minimum=105, maximum=135)
        csv_row.addWidget(self.btn_import_csv)
        csv_row.addWidget(self.btn_export_csv)
        csv_row.addStretch(1)
        csv_wrap = QtWidgets.QWidget()
        csv_wrap.setLayout(csv_row)
        form_target.addRow("CSV:", csv_wrap)
        main.addLayout(form_target)

        self.tabs = QtWidgets.QTabWidget()
        workflow_tab = QtWidgets.QWidget()
        workflow_layout = QtWidgets.QVBoxLayout(workflow_tab)
        workflow_layout.setContentsMargins(0, 0, 0, 0)
        workflow_layout.setSpacing(8)

        workflow_hint = QtWidgets.QLabel(
            "Workflow keeps confirmed design data separate from pending hints.\n"
            "Use Base Regions for the main span layout, Overrides for local changes, and Hints only after review."
        )
        workflow_hint.setWordWrap(True)
        workflow_layout.addWidget(workflow_hint)
        workflow_layout.addWidget(self._build_timeline_summary())

        self.tbl_base = self._build_summary_table(["Id", "Purpose", "Span", "Template"])
        self.tbl_override = self._build_summary_table(["Id", "Kind", "Scope", "Span", "Action"])
        self.tbl_hint = self._build_summary_table(["Id", "Source", "Suggestion", "Span", "Confidence", "Status", "Reason"])
        self._apply_table_stylesheet(self.tbl_base, kind="base")
        self._apply_table_stylesheet(self.tbl_override, kind="override")
        self._apply_table_stylesheet(self.tbl_hint, kind="hint")

        workflow_layout.addWidget(
            self._build_summary_group(
                "Base Regions",
                self.tbl_base,
                [
                    ("Add Base Region", self._add_base_row),
                    ("Split Selected", self._split_selected_base_row),
                    ("Merge Selected", self._merge_selected_base_row),
                ],
                group_key="base",
                subtitle="Confirmed design data. Build the main span plan here.",
            )
        )
        workflow_layout.addWidget(
            self._build_summary_group(
                "Overrides",
                self.tbl_override,
                [
                    ("Add Override", self._add_override_row),
                    ("Ditch Left", self._add_override_ditch_left),
                    ("Ditch Right", self._add_override_ditch_right),
                    ("Urban Left", self._add_override_urban_left),
                    ("Urban Right", self._add_override_urban_right),
                    ("Split Zone", self._add_override_split_zone),
                    ("Skip Zone", self._add_override_skip_zone),
                ],
                extra_widget=self._build_override_editor(),
                group_key="override",
                subtitle="Confirmed local changes. Use structured actions instead of raw policy strings.",
            )
        )
        workflow_layout.addWidget(
            self._build_summary_group(
                "Hints",
                self.tbl_hint,
                [
                    ("Add Hint", self._add_hint_row),
                    ("Accept", self._accept_selected_hint),
                    ("Accept and Edit", self._accept_and_edit_selected_hint),
                    ("Ignore", self._ignore_selected_hint),
                ],
                group_key="hint",
                subtitle="Pending suggestions from seed rules. Hints do not become design data until you accept them.",
            )
        )

        advanced_tab = QtWidgets.QWidget()
        advanced_layout = QtWidgets.QVBoxLayout(advanced_tab)
        advanced_layout.setContentsMargins(0, 0, 0, 0)
        advanced_layout.setSpacing(8)

        self.chk_enable_advanced_edit = QtWidgets.QCheckBox("Enable direct flat-row editing (Legacy)")
        self.chk_enable_advanced_edit.setChecked(False)
        advanced_layout.addWidget(self.chk_enable_advanced_edit)
        self.lbl_advanced_preview = QtWidgets.QLabel("Flat runtime preview | Base=0 | Override=0 | Hint=0")
        self.lbl_advanced_preview.setWordWrap(True)
        advanced_layout.addWidget(self.lbl_advanced_preview)
        self.txt_advanced_diagnostics = QtWidgets.QPlainTextEdit()
        self.txt_advanced_diagnostics.setReadOnly(True)
        self.txt_advanced_diagnostics.setMinimumHeight(88)
        self.txt_advanced_diagnostics.setPlainText("Diagnostics unavailable.")
        advanced_layout.addWidget(self.txt_advanced_diagnostics)

        self.table = QtWidgets.QTableWidget(0, len(COL_HEADERS))
        self.table.setHorizontalHeaderLabels(list(COL_HEADERS))
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setMinimumHeight(260)
        self._apply_table_stylesheet(self.table, kind="neutral")
        advanced_layout.addWidget(self.table)

        hint = QtWidgets.QLabel(
            "Advanced tab shows the exported flat runtime rows.\n"
            "Direct legacy editing is available only while creating a new Region Plan.\n"
            "Existing Region Plans stay preview-only here; use the grouped workflow instead.\n"
            "Layer uses `base` or `overlay`.\n"
            "Enabled accepts `true/false` and defaults to true.\n"
            "CorridorPolicy values currently recognized: "
            + ", ".join([v for v in ALLOWED_CORRIDOR_POLICIES if v])
        )
        hint.setWordWrap(True)
        advanced_layout.addWidget(hint)

        self.tabs.addTab(workflow_tab, "Workflow")
        self.tabs.addTab(advanced_tab, "Advanced")
        main.addWidget(self.tabs)

        btn_row = QtWidgets.QHBoxLayout()
        self.btn_add = QtWidgets.QPushButton("Add Advanced Row")
        self.btn_remove = QtWidgets.QPushButton("Remove Row")
        self.btn_sort = QtWidgets.QPushButton("Sort by Start")
        self.btn_apply = QtWidgets.QPushButton("Apply")
        self.btn_close = QtWidgets.QPushButton("Close")
        for _btn in (self.btn_add, self.btn_remove, self.btn_sort, self.btn_apply, self.btn_close):
            self._set_compact_button(_btn)
        btn_row.addWidget(self.btn_add)
        btn_row.addWidget(self.btn_remove)
        btn_row.addWidget(self.btn_sort)
        btn_row.addStretch(1)
        btn_row.addWidget(self.btn_apply)
        btn_row.addWidget(self.btn_close)
        main.addLayout(btn_row)

        self.lbl_status = QtWidgets.QLabel("Ready")
        self.lbl_status.setWordWrap(True)
        main.addWidget(self.lbl_status)

        self.cmb_target.currentIndexChanged.connect(self._on_target_changed)
        self.btn_load_preset.clicked.connect(self._load_preset)
        self.btn_seed_project.clicked.connect(self._seed_from_project)
        self.btn_import_csv.clicked.connect(self._import_csv)
        self.btn_export_csv.clicked.connect(self._export_csv)
        self.chk_enable_advanced_edit.toggled.connect(self._set_advanced_edit_enabled)
        self.btn_add.clicked.connect(self._add_row)
        self.btn_remove.clicked.connect(self._remove_row)
        self.btn_sort.clicked.connect(self._sort_rows)
        self.btn_apply.clicked.connect(self._apply)
        self.btn_close.clicked.connect(self.reject)
        self.table.itemChanged.connect(self._on_table_item_changed)
        self.tbl_base.itemDoubleClicked.connect(lambda _item: self._jump_from_summary_table(self.tbl_base))
        self.tbl_override.itemDoubleClicked.connect(lambda _item: self._jump_from_summary_table(self.tbl_override))
        self.tbl_hint.itemDoubleClicked.connect(lambda _item: self._jump_from_summary_table(self.tbl_hint))
        self.tbl_base.currentCellChanged.connect(lambda *_args: self._sync_timeline_from_summary_table(self.tbl_base))
        self.tbl_override.currentCellChanged.connect(lambda *_args: self._sync_timeline_from_summary_table(self.tbl_override))
        self.tbl_hint.currentCellChanged.connect(lambda *_args: self._sync_timeline_from_summary_table(self.tbl_hint))
        self.tbl_override.currentCellChanged.connect(lambda *_args: self._load_selected_override_into_editor())
        self._set_advanced_edit_enabled(False)
        return w

    def _build_summary_table(self, headers):
        table = QtWidgets.QTableWidget(0, len(list(headers or [])))
        table.setHorizontalHeaderLabels(list(headers or []))
        table.verticalHeader().setVisible(False)
        table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        table.horizontalHeader().setStretchLastSection(True)
        table.setAlternatingRowColors(True)
        table.setHorizontalScrollMode(QtWidgets.QAbstractItemView.ScrollPerPixel)
        table.setVerticalScrollMode(QtWidgets.QAbstractItemView.ScrollPerPixel)
        table.setMinimumHeight(110)
        return table

    def _build_summary_group(self, title: str, table, buttons, extra_widget=None, group_key: str = "", subtitle: str = ""):
        box = QtWidgets.QGroupBox(str(title or ""))
        layout = QtWidgets.QVBoxLayout(box)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)
        if subtitle:
            lbl = QtWidgets.QLabel(str(subtitle))
            lbl.setWordWrap(True)
            layout.addWidget(lbl)
        row = QtWidgets.QHBoxLayout()
        btn_map = {}
        btn_wrap = QtWidgets.QWidget()
        btn_grid = QtWidgets.QGridLayout(btn_wrap)
        btn_grid.setContentsMargins(0, 0, 0, 0)
        btn_grid.setHorizontalSpacing(6)
        btn_grid.setVerticalSpacing(4)
        cols = 3 if len(list(buttons or [])) > 3 else max(1, len(list(buttons or [])))
        for idx, (label, handler) in enumerate(list(buttons or [])):
            btn = QtWidgets.QPushButton(str(label or ""))
            btn.clicked.connect(handler)
            self._set_compact_button(btn, minimum=108, maximum=180)
            btn_grid.addWidget(btn, idx // cols, idx % cols)
            btn_map[str(label or "")] = btn
        row.addWidget(btn_wrap, 0, QtCore.Qt.AlignLeft)
        row.addStretch(1)
        layout.addLayout(row)
        layout.addWidget(table)
        if extra_widget is not None:
            layout.addWidget(extra_widget)
        if group_key:
            self._workflow_action_buttons[str(group_key)] = btn_map
            self._workflow_group_boxes[str(group_key)] = box
        return box

    def _build_timeline_summary(self):
        box = QtWidgets.QGroupBox("Station Timeline")
        layout = QtWidgets.QVBoxLayout(box)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)
        self.tbl_timeline = self._build_summary_table(["Type", "Id", "Span", "State"])
        self.tbl_timeline.setMinimumHeight(140)
        self._apply_table_stylesheet(self.tbl_timeline, kind="neutral")
        layout.addWidget(self.tbl_timeline)
        self.txt_timeline_summary = QtWidgets.QPlainTextEdit()
        self.txt_timeline_summary.setReadOnly(True)
        self.txt_timeline_summary.setMinimumHeight(96)
        self.txt_timeline_summary.setPlainText("No region rows.")
        layout.addWidget(self.txt_timeline_summary)
        layout.addWidget(self._build_timeline_editor())
        self.tbl_timeline.currentCellChanged.connect(self._on_timeline_selection_changed)
        return box

    def _build_timeline_editor(self):
        box = QtWidgets.QGroupBox("Selected Timeline Span")
        layout = QtWidgets.QFormLayout(box)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        self.lbl_timeline_editor = QtWidgets.QLabel("Select a timeline row to move, resize, or split it.")
        self.lbl_timeline_editor.setWordWrap(True)
        self.txt_timeline_start = QtWidgets.QLineEdit()
        self.txt_timeline_end = QtWidgets.QLineEdit()
        self._set_compact_line_edit(self.txt_timeline_start)
        self._set_compact_line_edit(self.txt_timeline_end)
        self.btn_apply_timeline_span = QtWidgets.QPushButton("Apply Span Edit")
        self.btn_split_timeline_base = QtWidgets.QPushButton("Split Selected Base")
        self.btn_open_timeline_selection = QtWidgets.QPushButton("Focus Workflow Selection")
        self._set_compact_button(self.btn_apply_timeline_span, minimum=120, maximum=165)
        self._set_compact_button(self.btn_split_timeline_base, minimum=135, maximum=185)
        self._set_compact_button(self.btn_open_timeline_selection, minimum=145, maximum=195)

        action_row = QtWidgets.QHBoxLayout()
        action_row.addWidget(self.btn_apply_timeline_span)
        action_row.addWidget(self.btn_split_timeline_base)
        action_row.addWidget(self.btn_open_timeline_selection)
        action_row.addStretch(1)
        action_wrap = QtWidgets.QWidget()
        action_wrap.setLayout(action_row)

        layout.addRow("Selection:", self.lbl_timeline_editor)
        layout.addRow("Start:", self.txt_timeline_start)
        layout.addRow("End:", self.txt_timeline_end)
        layout.addRow("", action_wrap)

        self.btn_apply_timeline_span.clicked.connect(self._apply_timeline_span_edit)
        self.btn_split_timeline_base.clicked.connect(self._split_selected_timeline_base)
        self.btn_open_timeline_selection.clicked.connect(self._focus_selected_timeline_row)
        return box

    def _build_override_editor(self):
        box = QtWidgets.QGroupBox("Selected Override")
        layout = QtWidgets.QFormLayout(box)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        self.cmb_override_kind = QtWidgets.QComboBox()
        self.cmb_override_kind.addItems(list(OVERRIDE_KIND_ITEMS))
        self.cmb_override_scope = QtWidgets.QComboBox()
        self.cmb_override_scope.addItems(list(OVERRIDE_SCOPE_ITEMS))
        self.cmb_override_action = QtWidgets.QComboBox()
        self.cmb_override_action.addItems(list(OVERRIDE_ACTION_ITEMS))
        self.txt_override_start = QtWidgets.QLineEdit()
        self.txt_override_end = QtWidgets.QLineEdit()
        self._set_compact_combo(self.cmb_override_kind, sample_texts=OVERRIDE_KIND_ITEMS, minimum=150, maximum=210)
        self._set_compact_combo(self.cmb_override_scope, sample_texts=OVERRIDE_SCOPE_ITEMS, minimum=110, maximum=150)
        self._set_compact_combo(self.cmb_override_action, sample_texts=OVERRIDE_ACTION_ITEMS, minimum=120, maximum=170)
        self._set_compact_line_edit(self.txt_override_start)
        self._set_compact_line_edit(self.txt_override_end)
        self.lbl_override_editor = QtWidgets.QLabel("Select an override row to edit it here.")
        self.lbl_override_editor.setWordWrap(True)
        self.btn_apply_override_editor = QtWidgets.QPushButton("Apply Override Edit")
        self.btn_open_override_advanced = QtWidgets.QPushButton("Open In Advanced")
        self._set_compact_button(self.btn_apply_override_editor, minimum=135, maximum=185)
        self._set_compact_button(self.btn_open_override_advanced, minimum=120, maximum=165)

        action_row = QtWidgets.QHBoxLayout()
        action_row.addWidget(self.btn_apply_override_editor)
        action_row.addWidget(self.btn_open_override_advanced)
        action_row.addStretch(1)
        action_wrap = QtWidgets.QWidget()
        action_wrap.setLayout(action_row)

        layout.addRow("Kind:", self.cmb_override_kind)
        layout.addRow("Scope:", self.cmb_override_scope)
        layout.addRow("Action:", self.cmb_override_action)
        layout.addRow("Start:", self.txt_override_start)
        layout.addRow("End:", self.txt_override_end)
        layout.addRow("Selection:", self.lbl_override_editor)
        layout.addRow("", action_wrap)

        self.btn_apply_override_editor.clicked.connect(self._apply_override_editor)
        self.btn_open_override_advanced.clicked.connect(lambda: self._jump_from_summary_table(self.tbl_override))
        return box

    def _legacy_edit_allowed_for_current_target(self) -> bool:
        return self._current_target() is None

    def _open_advanced_if_legacy_allowed(self):
        if not self._legacy_edit_allowed_for_current_target():
            return
        try:
            self.tabs.setCurrentIndex(1)
        except Exception:
            pass

    def _refresh_advanced_mode_availability(self):
        allow_legacy = self._legacy_edit_allowed_for_current_target()
        prev = bool(self.chk_enable_advanced_edit.blockSignals(True))
        try:
            self.chk_enable_advanced_edit.setEnabled(allow_legacy)
            if allow_legacy:
                self.chk_enable_advanced_edit.setToolTip("Direct flat-row editing is available while creating a new Region Plan.")
            else:
                self.chk_enable_advanced_edit.setChecked(False)
                self.chk_enable_advanced_edit.setToolTip(
                    "Existing Region Plans are preview-only here. Use the Workflow tab to edit the grouped model."
                )
        finally:
            self.chk_enable_advanced_edit.blockSignals(prev)
        self._set_advanced_edit_enabled(bool(self.chk_enable_advanced_edit.isChecked()))

    def _refresh_advanced_diagnostics(self, grouped=None):
        model = dict(grouped or self._group_rows())
        target = self._current_target()
        mode = "new-plan authoring" if target is None else "existing-plan preview"
        legacy = "enabled" if (bool(self.chk_enable_advanced_edit.isChecked()) and self._legacy_edit_allowed_for_current_target()) else "disabled"
        base_rows = list(model.get("base_rows", []) or [])
        override_rows = list(model.get("override_rows", []) or [])
        hint_rows = list(model.get("hint_rows", []) or [])
        flat_rows = self._flatten_group_rows(model)
        lines = [
            f"Mode: {mode}",
            f"Target: {self._label_name(target) or '[New] Region Plan'}",
            f"Legacy Editing: {legacy}",
            f"Grouped Model: Base={len(base_rows)} | Override={len(override_rows)} | Hint={len(hint_rows)}",
            f"Exported Runtime Rows: {len(flat_rows)}",
        ]
        if flat_rows:
            preview_ids = [str(row.get("Id", "") or "-") for row in flat_rows[:5]]
            more = "" if len(flat_rows) <= 5 else f" ... (+{len(flat_rows) - 5})"
            lines.append("Preview Order: " + ", ".join(preview_ids) + more)
        self.txt_advanced_diagnostics.setPlainText("\n".join(lines))

    def _set_advanced_edit_enabled(self, enabled: bool):
        allow = bool(enabled) and self._legacy_edit_allowed_for_current_target()
        self.table.setEditTriggers(
            QtWidgets.QAbstractItemView.AllEditTriggers if allow else QtWidgets.QAbstractItemView.NoEditTriggers
        )
        self.btn_add.setEnabled(allow)
        self.btn_remove.setEnabled(allow)
        self.btn_sort.setEnabled(allow)
        if allow:
            self.lbl_advanced_preview.setText("Legacy flat-row editing enabled. Changes here bypass the grouped workflow model.")
        else:
            self._refresh_advanced_preview_summary()
        self._refresh_advanced_diagnostics()

    @staticmethod
    def _strip_hint_note_prefixes(text: str) -> str:
        note = str(text or "").strip()
        changed = True
        while changed:
            changed = False
            for prefix in HINT_NOTE_PREFIXES.values():
                if note.startswith(prefix):
                    note = note[len(prefix):].strip()
                    changed = True
        return note

    @classmethod
    def _note_with_hint_status(cls, text: str, status: str) -> str:
        note = cls._strip_hint_note_prefixes(text)
        prefix = HINT_NOTE_PREFIXES.get(str(status or "").strip().lower(), "")
        if prefix:
            return f"{prefix} {note}".strip()
        return note

    @classmethod
    def _hint_status_for_row(cls, rec) -> str:
        explicit = str(rec.get("HintStatus", "") or "").strip().lower()
        if explicit in (HINT_STATUS_PENDING, HINT_STATUS_ACCEPTED, HINT_STATUS_IGNORED):
            return explicit
        enabled = str(rec.get("Enabled", "true") or "true").strip().lower() not in ("false", "0", "no", "off", "disabled")
        note = str(rec.get("Notes", "") or "").strip()
        if enabled:
            return HINT_STATUS_ACCEPTED
        if note.startswith(HINT_NOTE_PREFIXES[HINT_STATUS_IGNORED]):
            return HINT_STATUS_IGNORED
        return HINT_STATUS_PENDING

    @staticmethod
    def _title_case_token(text: str) -> str:
        token = str(text or "").strip().replace("_", " ")
        return " ".join(part[:1].upper() + part[1:] for part in token.split() if part)

    @classmethod
    def _hint_status_label_for_row(cls, rec) -> str:
        status = cls._hint_status_for_row(rec)
        return cls._title_case_token(status) or "Pending"

    @classmethod
    def _hint_family_for_row(cls, rec) -> str:
        rule_set = str(rec.get("RuleSet", "") or "").strip()
        parts = [part.strip() for part in rule_set.split(":") if str(part or "").strip()]
        if len(parts) >= 2:
            return cls._title_case_token(parts[1]) or "General"
        source = str(rec.get("HintSource", "") or "").strip().lower()
        if source == "structure":
            region_type = str(rec.get("RegionType", "") or "").strip()
            return cls._title_case_token(region_type) or "Structure"
        return "General"

    @classmethod
    def _hint_confidence_for_row(cls, rec) -> float:
        try:
            explicit = float(rec.get("HintConfidence", 0.0) or 0.0)
        except Exception:
            explicit = 0.0
        if explicit > 1e-9:
            return float(max(0.0, min(1.0, explicit)))
        source = cls._hint_source_for_row(rec).lower()
        family = cls._hint_family_for_row(rec).lower()
        if source == "structureset":
            return 0.9 if family in ("culvert", "retaining wall", "bridge zone", "abutment zone") else 0.7
        if source == "typical section":
            return 0.85 if family in ("ditch edge", "urban edge") else 0.65
        if source == "project seed":
            return 0.75
        return 0.5

    @classmethod
    def _hint_confidence_label_for_row(cls, rec) -> str:
        score = cls._hint_confidence_for_row(rec)
        if score >= 0.85:
            return f"High ({score:.2f})"
        if score >= 0.65:
            return f"Medium ({score:.2f})"
        return f"Low ({score:.2f})"

    @classmethod
    def _hint_source_for_row(cls, rec) -> str:
        explicit = str(rec.get("HintSource", "") or "").strip()
        if explicit:
            lookup = {
                "typical": "Typical Section",
                "structure": "StructureSet",
                "preset": "Preset",
                "seed": "Project Seed",
                "project": "Project Seed",
                "standard": "Design Standard",
                "manual": "Manual",
            }
            explicit_lower = explicit.lower()
            return lookup.get(explicit_lower, explicit)
        rule_set = str(rec.get("RuleSet", "") or "").strip()
        note = cls._strip_hint_note_prefixes(str(rec.get("Notes", "") or ""))
        parts = [part.strip() for part in rule_set.split(":") if str(part or "").strip()]
        family = str(parts[0] if parts else "").lower()
        if family == "typical":
            return "Typical Section"
        if family == "structure":
            return "StructureSet"
        if family == "preset":
            return "Preset"
        if family in ("seed", "project"):
            return "Project Seed"
        note_lower = note.lower()
        if "typical section" in note_lower:
            return "Typical Section"
        if "structureset" in note_lower or "linked structure" in note_lower:
            return "StructureSet"
        if "seed" in note_lower or "auto" in note_lower:
            return "Project Seed"
        return "Manual"

    @classmethod
    def _hint_reason_for_row(cls, rec) -> str:
        explicit = str(rec.get("HintReason", "") or "").strip()
        if explicit:
            return explicit
        note = cls._strip_hint_note_prefixes(str(rec.get("Notes", "") or ""))
        if note:
            return note
        rule_set = str(rec.get("RuleSet", "") or "").strip()
        parts = [part.strip() for part in rule_set.split(":") if str(part or "").strip()]
        family = str(parts[0] if parts else "").lower()
        if family == "typical" and len(parts) >= 3:
            return f"{cls._title_case_token(parts[1])} on {cls._title_case_token(parts[2])}"
        if family == "structure" and len(parts) >= 2:
            return f"Linked structure {parts[1]}"
        if rule_set:
            return rule_set
        return "Pending review"

    def _fill_targets(self, selected=None):
        self.cmb_target.clear()
        self.cmb_target.addItem("[New] Create new Region Plan")
        for obj in self._regions:
            self.cmb_target.addItem(self._fmt_obj("Region Plan", obj))
        self._set_compact_combo(
            self.cmb_target,
            sample_texts=[self.cmb_target.itemText(i) for i in range(self.cmb_target.count())],
            minimum=240,
            maximum=440,
        )
        idx = 0
        if selected is not None:
            for i, obj in enumerate(self._regions):
                if obj == selected:
                    idx = i + 1
                    break
        self.cmb_target.setCurrentIndex(idx)

    def _current_target(self):
        idx = int(self.cmb_target.currentIndex()) - 1
        if idx < 0 or idx >= len(self._regions):
            return None
        return self._regions[idx]

    def _set_rows(self, count: int):
        target = max(1, int(count))
        while self.table.rowCount() < target:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self._ensure_combo_cells(row)

    def _get_cell_text(self, row: int, col: int) -> str:
        cmb = self.table.cellWidget(int(row), int(col))
        if isinstance(cmb, QtWidgets.QComboBox):
            return str(cmb.currentText() or "")
        item = self.table.item(int(row), int(col))
        return "" if item is None else str(item.text() or "")

    def _set_cell_text(self, row: int, col: int, text: str):
        cmb = self.table.cellWidget(int(row), int(col))
        if isinstance(cmb, QtWidgets.QComboBox):
            self._set_combo_value(cmb, text)
            return
        item = self.table.item(int(row), int(col))
        if item is None:
            item = QtWidgets.QTableWidgetItem()
            self.table.setItem(int(row), int(col), item)
        item.setText(str(text or ""))

    @staticmethod
    def _set_combo_value(cmb, value):
        txt = str(value or "")
        idx = cmb.findText(txt)
        if idx < 0 and txt:
            cmb.addItem(txt)
            idx = cmb.findText(txt)
        if idx < 0:
            idx = cmb.findText("")
            if idx < 0:
                cmb.addItem("")
                idx = cmb.findText("")
        cmb.setCurrentIndex(max(0, idx))

    def _ensure_combo_cells(self, row: int):
        for col, items in COMBO_COLUMN_ITEMS.items():
            cmb = self.table.cellWidget(int(row), int(col))
            if cmb is None:
                cmb = QtWidgets.QComboBox()
                cmb.addItems(list(items))
                cmb.currentTextChanged.connect(lambda _txt, cc=int(col), ww=cmb: self._on_combo_changed(ww, cc))
                self.table.setCellWidget(int(row), int(col), cmb)

    def _table_row_for_widget(self, widget) -> int:
        if widget is None:
            return -1
        for row in range(self.table.rowCount()):
            for col in COMBO_COLUMN_ITEMS:
                if self.table.cellWidget(row, col) == widget:
                    return row
        return -1

    def _row_has_content(self, row: int, include_id: bool = False) -> bool:
        start_col = 0 if include_id else 1
        for col in range(start_col, len(COL_HEADERS)):
            if str(self._get_cell_text(row, col) or "").strip():
                return True
        return False

    def _materialize_row_ids(self, *, force_if_generated: bool = False):
        changed = False
        rows = self.table.rowCount()
        for row in range(rows):
            if not self._row_has_content(row, include_id=False):
                continue
            rid = str(self._get_cell_text(row, 0) or "").strip()
            region_type = str(self._get_cell_text(row, 1) or "").strip()
            layer = str(self._get_cell_text(row, 2) or "base").strip().lower() or "base"
            if rid and (not force_if_generated or not self._is_generated_region_id(rid)):
                continue
            existing_ids = [self._get_cell_text(r, 0) for r in range(rows) if r != row]
            new_id = self._auto_region_id(layer, region_type, existing_ids, exclude_id=rid)
            if new_id != rid:
                self._loading = True
                try:
                    self._set_cell_text(row, 0, new_id)
                finally:
                    self._loading = False
                changed = True
        return changed

    def _normalize_region_type_cells(self):
        self._loading = True
        try:
            for row in range(self.table.rowCount()):
                cmb = self.table.cellWidget(row, 1)
                if not isinstance(cmb, QtWidgets.QComboBox):
                    continue
                txt = str(cmb.currentText() or "").strip()
                if txt and cmb.findText(txt) < 0:
                    self._set_combo_value(cmb, "")
        finally:
            self._loading = False

    def _on_combo_changed(self, widget, col: int):
        if self._loading:
            return
        row = self._table_row_for_widget(widget)
        if row < 0:
            return
        if int(col) == 1:
            self._materialize_row_ids(force_if_generated=True)
        self._refresh_validation_status()

    def _read_rows(self):
        rows = []
        for r in range(self.table.rowCount()):
            vals = [self._get_cell_text(r, c).strip() for c in range(len(COL_HEADERS))]
            if not any(vals):
                continue
            rows.append(
                {
                    "_table_row": int(r),
                    "Id": vals[0],
                    "RegionType": vals[1],
                    "Layer": vals[2],
                    "StartStation": self._meters_from_display(vals[3]),
                    "EndStation": self._meters_from_display(vals[4]),
                    "Priority": vals[5],
                    "TransitionIn": self._meters_from_display(vals[6]),
                    "TransitionOut": self._meters_from_display(vals[7]),
                    "TemplateName": vals[8],
                    "AssemblyName": vals[9],
                    "RuleSet": vals[10],
                    "SidePolicy": vals[11],
                    "DaylightPolicy": vals[12],
                    "CorridorPolicy": vals[13],
                    "Enabled": vals[14],
                    "Notes": vals[15],
                    "HintSource": vals[16],
                    "HintStatus": vals[17],
                    "HintReason": vals[18],
                    "HintConfidence": vals[19],
                }
            )
        return rows

    def _group_rows(self, rows=None):
        data_rows = [dict(row) for row in list(rows if rows is not None else self._read_rows())]
        grouped = {
            "base_rows": [],
            "override_rows": [],
            "hint_rows": [],
        }
        for row in data_rows:
            layer = str(row.get("Layer", "") or "").strip().lower()
            if not self._is_enabled_row(row):
                grouped["hint_rows"].append(dict(row))
            elif layer == "base":
                grouped["base_rows"].append(dict(row))
            else:
                grouped["override_rows"].append(dict(row))

        def _sorted(items):
            return sorted(
                list(items or []),
                key=lambda rec: (
                    self._safe_float(rec.get("StartStation", 0.0), default=0.0),
                    self._safe_float(rec.get("EndStation", 0.0), default=0.0),
                    str(rec.get("Id", "") or ""),
                ),
            )

        grouped["base_rows"] = _sorted(grouped["base_rows"])
        grouped["override_rows"] = _sorted(grouped["override_rows"])
        grouped["hint_rows"] = _sorted(grouped["hint_rows"])
        return grouped

    def _flatten_group_rows(self, grouped):
        model = dict(grouped or {})
        return list(model.get("base_rows", []) or []) + list(model.get("override_rows", []) or []) + list(model.get("hint_rows", []) or [])

    def _refresh_advanced_preview_summary(self, grouped=None):
        model = dict(grouped or self._group_rows())
        base_count = len(list(model.get("base_rows", []) or []))
        override_count = len(list(model.get("override_rows", []) or []))
        hint_count = len(list(model.get("hint_rows", []) or []))
        if bool(self.chk_enable_advanced_edit.isChecked()) and self._legacy_edit_allowed_for_current_target():
            self.lbl_advanced_preview.setText(
                f"Legacy flat-row editing enabled | Base={base_count} | Override={override_count} | Hint={hint_count}"
            )
        elif not self._legacy_edit_allowed_for_current_target():
            self.lbl_advanced_preview.setText(
                f"Flat runtime preview only for existing Region Plans | Base={base_count} | Override={override_count} | Hint={hint_count}"
            )
        else:
            self.lbl_advanced_preview.setText(
                f"Flat runtime preview | Base={base_count} | Override={override_count} | Hint={hint_count}"
            )

    def _populate_table(self, rows):
        self._loading = True
        try:
            self.table.setRowCount(0)
            self._set_rows(max(3, len(list(rows or []))))
            for r, rec in enumerate(list(rows or [])):
                self._set_cell_text(r, 0, str(rec.get("Id", "") or ""))
                self._set_cell_text(r, 1, str(rec.get("RegionType", "") or ""))
                self._set_cell_text(r, 2, str(rec.get("Layer", "") or "base"))
                self._set_cell_text(r, 3, self._format_display_length(rec.get("StartStation", 0.0)))
                self._set_cell_text(r, 4, self._format_display_length(rec.get("EndStation", 0.0)))
                self._set_cell_text(r, 5, f"{int(rec.get('Priority', 0) or 0)}")
                self._set_cell_text(r, 6, self._format_display_length(rec.get("TransitionIn", 0.0)))
                self._set_cell_text(r, 7, self._format_display_length(rec.get("TransitionOut", 0.0)))
                self._set_cell_text(r, 8, str(rec.get("TemplateName", "") or ""))
                self._set_cell_text(r, 9, str(rec.get("AssemblyName", "") or ""))
                self._set_cell_text(r, 10, str(rec.get("RuleSet", "") or ""))
                self._set_cell_text(r, 11, str(rec.get("SidePolicy", "") or ""))
                self._set_cell_text(r, 12, str(rec.get("DaylightPolicy", "") or ""))
                self._set_cell_text(r, 13, str(rec.get("CorridorPolicy", "") or ""))
                enabled_text = str(rec.get("Enabled", "true") or "true").strip().lower()
                enabled_flag = enabled_text not in ("false", "0", "no", "off", "disabled")
                self._set_cell_text(r, 14, "true" if enabled_flag else "false")
                self._set_cell_text(r, 15, str(rec.get("Notes", "") or ""))
                self._set_cell_text(r, 16, str(rec.get("HintSource", "") or ""))
                self._set_cell_text(r, 17, str(rec.get("HintStatus", "") or ""))
                self._set_cell_text(r, 18, str(rec.get("HintReason", "") or ""))
                self._set_cell_text(r, 19, f"{self._safe_float(rec.get('HintConfidence', 0.0), default=0.0):.3f}")
        finally:
            self._loading = False
        self._materialize_row_ids(force_if_generated=False)
        self._refresh_workflow_tables()
        self._refresh_validation_status()

    def _refresh_context(self):
        if self.doc is None:
            self.lbl_info.setText("No active document.")
            return
        self._regions = _find_region_sets(self.doc)
        prj = find_project(self.doc)
        selected = resolve_project_region_plan(prj)
        if selected is None and self._regions:
            selected = self._regions[0]
        self._loading = True
        try:
            self._fill_targets(selected=selected)
        finally:
            self._loading = False
        msg = [
            f"Region plan objects: {len(self._regions)} found",
            f"Display unit: {self._display_unit_label()}",
            "",
            "Workflow:",
            "1) Define base regions and local overrides for the active alignment",
            "2) Or start from Preset Data / Seed From Project for common region-plan layouts",
            "3) Apply to save the region plan",
            "4) Link it in Generate Sections to merge region boundaries into StationValues",
        ]
        self.lbl_info.setText("\n".join(msg))
        self._on_target_changed()

    def _on_target_changed(self):
        if self._loading:
            return
        obj = self._current_target()
        if obj is None:
            rows = self._make_project_seed_rows() if bool(self.chk_auto_seed_project.isChecked()) else []
            if not rows:
                rows = [
                    self._region_record(
                        "BASE_01",
                        "roadway",
                        "base",
                        0.0,
                        100.0,
                        notes="Default seed",
                    )
                ]
            self._populate_table(rows)
            self._refresh_advanced_mode_availability()
            if bool(self.chk_auto_seed_project.isChecked()):
                hint_count = sum(1 for row in rows if not self._is_enabled_row(row))
                self.lbl_status.setText(f"New Region Plan will be created. Auto-seeded base/rows={len(rows) - hint_count}/{len(rows)} | hints={hint_count}")
            else:
                self.lbl_status.setText("New Region Plan will be created.")
            return
        ensure_region_plan_properties(obj)
        grouped_rows = list(RegionPlan.export_records_from_grouped(obj) or [])
        self._populate_table(grouped_rows if grouped_rows else RegionPlan.records(obj))
        self._refresh_advanced_mode_availability()
        self.lbl_status.setText(str(getattr(obj, "Status", "Loaded") or "Loaded"))

    def _ensure_target(self):
        obj = self._current_target()
        if obj is not None:
            ensure_region_plan_properties(obj)
            return obj
        obj = self.doc.addObject("Part::FeaturePython", "RegionPlan")
        RegionPlan(obj)
        ViewProviderRegionPlan(obj.ViewObject)
        obj.Label = "Region Plan"
        return obj

    def _add_row(self):
        self._set_rows(self.table.rowCount() + 1)
        row = self.table.rowCount() - 1
        self._set_cell_text(row, 1, "other")
        self._set_cell_text(row, 2, "overlay")
        self._set_cell_text(row, 14, "true")
        self._materialize_row_ids(force_if_generated=False)
        self.table.setCurrentCell(row, 0)
        self._open_advanced_if_legacy_allowed()
        self._refresh_validation_status()

    def _add_base_row(self):
        self._add_workflow_row(layer="base", enabled=True, region_type="roadway", notes="Base region")

    def _add_override_row(self):
        self._add_workflow_row(layer="overlay", enabled=True, region_type="ditch_override", notes="Override region")

    def _add_override_ditch_left(self):
        self._add_structured_override(region_type="ditch_override", side_policy="left:berm", notes="Left ditch or berm override")

    def _add_override_ditch_right(self):
        self._add_structured_override(region_type="ditch_override", side_policy="right:berm", notes="Right ditch or berm override")

    def _add_override_urban_left(self):
        self._add_structured_override(region_type="retaining_wall_zone", daylight_policy="left:off", notes="Left urban edge override")

    def _add_override_urban_right(self):
        self._add_structured_override(region_type="retaining_wall_zone", daylight_policy="right:off", notes="Right urban edge override")

    def _add_override_split_zone(self):
        self._add_structured_override(region_type="other", corridor_policy="split_only", notes="Corridor split zone")

    def _add_override_skip_zone(self):
        self._add_structured_override(region_type="other", corridor_policy="skip_zone", notes="Corridor skip zone")

    def _add_hint_row(self):
        self._add_workflow_row(
            layer="overlay",
            enabled=False,
            region_type="other",
            notes="Pending hint",
            hint_source="manual",
            hint_status=HINT_STATUS_PENDING,
            hint_reason="Manual hint awaiting review.",
        )

    def _add_structured_override(
        self,
        *,
        region_type: str,
        side_policy: str = "",
        daylight_policy: str = "",
        corridor_policy: str = "",
        notes: str = "",
    ):
        self._set_rows(self.table.rowCount() + 1)
        row = self.table.rowCount() - 1
        self._set_cell_text(row, 1, str(region_type or "other"))
        self._set_cell_text(row, 2, "overlay")
        self._set_cell_text(row, 11, str(side_policy or ""))
        self._set_cell_text(row, 12, str(daylight_policy or ""))
        self._set_cell_text(row, 13, str(corridor_policy or ""))
        self._set_cell_text(row, 14, "true")
        self._set_cell_text(row, 15, str(notes or "Override region"))
        self._materialize_row_ids(force_if_generated=False)
        self.table.setCurrentCell(row, 0)
        self._open_advanced_if_legacy_allowed()
        self._refresh_workflow_tables()
        self._refresh_validation_status()

    def _add_workflow_row(self, *, layer: str, enabled: bool, region_type: str, notes: str, hint_source: str = "", hint_status: str = "", hint_reason: str = ""):
        self._set_rows(self.table.rowCount() + 1)
        row = self.table.rowCount() - 1
        self._set_cell_text(row, 1, str(region_type or ""))
        self._set_cell_text(row, 2, str(layer or "overlay"))
        self._set_cell_text(row, 14, "true" if bool(enabled) else "false")
        self._set_cell_text(row, 15, str(notes or ""))
        self._set_cell_text(row, 16, str(hint_source or ""))
        self._set_cell_text(row, 17, str(hint_status or ""))
        self._set_cell_text(row, 18, str(hint_reason or ""))
        self._materialize_row_ids(force_if_generated=False)
        self.table.setCurrentCell(row, 0)
        self._open_advanced_if_legacy_allowed()
        self._refresh_workflow_tables()
        self._refresh_validation_status()

    def _split_selected_base_row(self):
        rec, idx, rows = self._selected_workflow_record(self.tbl_base)
        if rec is None or idx < 0:
            self.lbl_status.setText("Select a base region row first.")
            return
        if str(rec.get("Layer", "") or "").strip().lower() != "base" or not self._is_enabled_row(rec):
            self.lbl_status.setText("Only enabled base regions can be split.")
            return
        s0 = self._safe_float(rec.get("StartStation", 0.0), default=0.0)
        s1 = self._safe_float(rec.get("EndStation", 0.0), default=0.0)
        if s1 < s0:
            s0, s1 = s1, s0
        if abs(s1 - s0) <= 1e-6:
            self.lbl_status.setText("Selected base region is too short to split.")
            return
        split_station = round(0.5 * (s0 + s1), 3)
        if split_station <= s0 + 1e-6 or split_station >= s1 - 1e-6:
            self.lbl_status.setText("Could not determine a valid split station.")
            return
        left = dict(rec)
        right = dict(rec)
        left_id, right_id = self._split_region_id_pair(str(rec.get("Id", "") or ""))
        left["Id"] = left_id
        right["Id"] = right_id
        left["StartStation"] = s0
        left["EndStation"] = split_station
        right["StartStation"] = split_station
        right["EndStation"] = s1
        source_id = str(rec.get("Id", "") or "")
        left["Notes"] = self._merge_note_text(str(rec.get("Notes", "") or ""), f"Split from {source_id or 'selected base'}")
        right["Notes"] = self._merge_note_text(str(rec.get("Notes", "") or ""), f"Split from {source_id or 'selected base'}")
        left.pop("_table_row", None)
        right.pop("_table_row", None)
        new_rows = list(rows[:idx]) + [left, right] + list(rows[idx + 1 :])
        self._populate_table(new_rows)
        self._sort_rows()
        self.lbl_status.setText(f"Base region split at {split_station:.3f}: {source_id or 'selected row'}")

    def _merge_selected_base_row(self):
        rec, idx, rows = self._selected_workflow_record(self.tbl_base)
        if rec is None or idx < 0:
            self.lbl_status.setText("Select a base region row first.")
            return
        if str(rec.get("Layer", "") or "").strip().lower() != "base" or not self._is_enabled_row(rec):
            self.lbl_status.setText("Only enabled base regions can be merged.")
            return
        selected_row_index = int(rec.get("_table_row", -1))
        base_rows = []
        for item in rows:
            if str(item.get("Layer", "") or "").strip().lower() == "base" and self._is_enabled_row(item):
                s0 = self._safe_float(item.get("StartStation", 0.0), default=0.0)
                s1 = self._safe_float(item.get("EndStation", 0.0), default=0.0)
                if s1 < s0:
                    s0, s1 = s1, s0
                row_copy = dict(item)
                row_copy["_norm_start"] = s0
                row_copy["_norm_end"] = s1
                base_rows.append(row_copy)
        base_rows.sort(key=lambda row: (float(row.get("_norm_start", 0.0)), float(row.get("_norm_end", 0.0))))
        pos = -1
        for i, item in enumerate(base_rows):
            if int(item.get("_table_row", -1)) == selected_row_index:
                pos = i
                break
        if pos < 0:
            self.lbl_status.setText("Selected base region could not be resolved for merge.")
            return
        partner = None
        if pos + 1 < len(base_rows):
            partner = dict(base_rows[pos + 1])
        elif pos - 1 >= 0:
            partner = dict(base_rows[pos - 1])
        if partner is None:
            self.lbl_status.setText("No adjacent base region is available to merge.")
            return
        rec_start = min(
            self._safe_float(rec.get("StartStation", 0.0), default=0.0),
            self._safe_float(rec.get("EndStation", 0.0), default=0.0),
        )
        rec_end = max(
            self._safe_float(rec.get("StartStation", 0.0), default=0.0),
            self._safe_float(rec.get("EndStation", 0.0), default=0.0),
        )
        partner_start = min(
            self._safe_float(partner.get("StartStation", 0.0), default=0.0),
            self._safe_float(partner.get("EndStation", 0.0), default=0.0),
        )
        partner_end = max(
            self._safe_float(partner.get("StartStation", 0.0), default=0.0),
            self._safe_float(partner.get("EndStation", 0.0), default=0.0),
        )
        if partner_start > rec_end + 1e-6 or rec_start > partner_end + 1e-6:
            self.lbl_status.setText("Merge requires touching base regions without a gap.")
            return
        if self._base_merge_signature(rec) != self._base_merge_signature(partner):
            self.lbl_status.setText("Merge requires adjacent base regions with matching properties.")
            return
        merged = dict(rec)
        merged["Id"] = self._merge_region_id(str(rec.get("Id", "") or ""), str(partner.get("Id", "") or ""))
        merged["StartStation"] = min(rec_start, partner_start)
        merged["EndStation"] = max(rec_end, partner_end)
        merged["Notes"] = self._merge_note_text(str(rec.get("Notes", "") or ""), str(partner.get("Notes", "") or ""))
        merged.pop("_table_row", None)
        partner_row = int(partner.get("_table_row", -1))
        new_rows = []
        inserted = False
        for item in rows:
            table_row = int(item.get("_table_row", -1))
            if table_row in (selected_row_index, partner_row):
                if not inserted:
                    new_rows.append(dict(merged))
                    inserted = True
                continue
            row_copy = dict(item)
            row_copy.pop("_table_row", None)
            new_rows.append(row_copy)
        self._populate_table(new_rows)
        self._sort_rows()
        self.lbl_status.setText(
            f"Base regions merged: {str(rec.get('Id', '') or 'selected')} + {str(partner.get('Id', '') or 'adjacent')}"
        )

    def _selected_summary_table_row(self, table):
        row = int(table.currentRow())
        if row < 0:
            return -1
        item = table.item(row, 0)
        if item is None:
            return -1
        try:
            return int(item.data(QtCore.Qt.UserRole))
        except Exception:
            return -1

    def _select_summary_row_by_table_row(self, table, target_row: int) -> bool:
        if int(target_row) < 0:
            return False
        for row in range(table.rowCount()):
            item = table.item(row, 0)
            if item is None:
                continue
            try:
                source_row = int(item.data(QtCore.Qt.UserRole))
            except Exception:
                source_row = -1
            if source_row == int(target_row):
                table.setCurrentCell(row, 0)
                return True
        return False

    def _selected_workflow_record(self, table):
        row = self._selected_summary_table_row(table)
        if row < 0:
            return None, -1, []
        grouped = self._group_rows()
        if table == self.tbl_base:
            rows = list(grouped.get("base_rows", []) or [])
        elif table == self.tbl_override:
            rows = list(grouped.get("override_rows", []) or [])
        elif table == self.tbl_hint:
            rows = list(grouped.get("hint_rows", []) or [])
        else:
            rows = self._flatten_group_rows(grouped)
        for idx, rec in enumerate(rows):
            if int(rec.get("_table_row", -1)) == int(row):
                return dict(rec), idx, rows
        return None, -1, rows

    @staticmethod
    def _split_region_id_pair(rid: str):
        base_id = str(rid or "").strip()
        if not base_id:
            return "", ""
        if re.match(r"^(BASE|OVR)_[A-Z0-9_]+_\d{2,3}$", base_id.upper()):
            return "", ""
        return f"{base_id}_A", f"{base_id}_B"

    @staticmethod
    def _merge_region_id(left_id: str, right_id: str):
        left = str(left_id or "").strip()
        right = str(right_id or "").strip()
        if left and not re.match(r"^(BASE|OVR)_[A-Z0-9_]+_\d{2,3}$", left.upper()):
            return left
        if right and not re.match(r"^(BASE|OVR)_[A-Z0-9_]+_\d{2,3}$", right.upper()):
            return right
        return ""

    @staticmethod
    def _merge_note_text(left_note: str, right_note: str):
        parts = []
        for text in (left_note, right_note):
            clean = str(text or "").strip()
            if clean and clean not in parts:
                parts.append(clean)
        return " | ".join(parts)

    @staticmethod
    def _base_merge_signature(rec):
        return (
            str(rec.get("RegionType", "") or "").strip(),
            str(rec.get("TemplateName", "") or "").strip(),
            str(rec.get("AssemblyName", "") or "").strip(),
            str(rec.get("RuleSet", "") or "").strip(),
            str(rec.get("SidePolicy", "") or "").strip(),
            str(rec.get("DaylightPolicy", "") or "").strip(),
            str(rec.get("CorridorPolicy", "") or "").strip(),
            str(rec.get("Enabled", "") or "").strip().lower(),
        )

    def _can_merge_base_record(self, rec, rows) -> bool:
        if rec is None:
            return False
        if str(rec.get("Layer", "") or "").strip().lower() != "base" or not self._is_enabled_row(rec):
            return False
        selected_row_index = int(rec.get("_table_row", -1))
        base_rows = []
        for item in list(rows or []):
            if str(item.get("Layer", "") or "").strip().lower() == "base" and self._is_enabled_row(item):
                s0 = self._safe_float(item.get("StartStation", 0.0), default=0.0)
                s1 = self._safe_float(item.get("EndStation", 0.0), default=0.0)
                if s1 < s0:
                    s0, s1 = s1, s0
                row_copy = dict(item)
                row_copy["_norm_start"] = s0
                row_copy["_norm_end"] = s1
                base_rows.append(row_copy)
        base_rows.sort(key=lambda row: (float(row.get("_norm_start", 0.0)), float(row.get("_norm_end", 0.0))))
        pos = -1
        for i, item in enumerate(base_rows):
            if int(item.get("_table_row", -1)) == selected_row_index:
                pos = i
                break
        if pos < 0:
            return False
        partners = []
        if pos + 1 < len(base_rows):
            partners.append(dict(base_rows[pos + 1]))
        if pos - 1 >= 0:
            partners.append(dict(base_rows[pos - 1]))
        rec_start = min(
            self._safe_float(rec.get("StartStation", 0.0), default=0.0),
            self._safe_float(rec.get("EndStation", 0.0), default=0.0),
        )
        rec_end = max(
            self._safe_float(rec.get("StartStation", 0.0), default=0.0),
            self._safe_float(rec.get("EndStation", 0.0), default=0.0),
        )
        for partner in partners:
            partner_start = min(
                self._safe_float(partner.get("StartStation", 0.0), default=0.0),
                self._safe_float(partner.get("EndStation", 0.0), default=0.0),
            )
            partner_end = max(
                self._safe_float(partner.get("StartStation", 0.0), default=0.0),
                self._safe_float(partner.get("EndStation", 0.0), default=0.0),
            )
            if partner_start > rec_end + 1e-6 or rec_start > partner_end + 1e-6:
                continue
            if self._base_merge_signature(rec) == self._base_merge_signature(partner):
                return True
        return False

    @staticmethod
    def _override_scope_for_row(rec) -> str:
        scopes = []
        for token in (
            str(rec.get("SidePolicy", "") or "").strip(),
            str(rec.get("DaylightPolicy", "") or "").strip(),
        ):
            head, _, _tail = token.partition(":")
            head = head.strip().lower()
            if head in ("left", "right", "both") and head not in scopes:
                scopes.append(head)
        if not scopes:
            return "Both"
        if len(scopes) == 1:
            return RegionEditorTaskPanel._title_case_token(scopes[0])
        return "Mixed"

    @classmethod
    def _override_kind_for_row(cls, rec) -> str:
        corridor_policy = str(rec.get("CorridorPolicy", "") or "").strip().lower()
        side_policy = str(rec.get("SidePolicy", "") or "").strip().lower()
        daylight_policy = str(rec.get("DaylightPolicy", "") or "").strip().lower()
        region_type = str(rec.get("RegionType", "") or "").strip().lower()
        if side_policy.endswith(":berm") or region_type == "ditch_override":
            return "Ditch / Berm"
        if daylight_policy.endswith(":off") or region_type == "retaining_wall_zone":
            return "Urban Edge"
        if corridor_policy in ("split_only", "skip_zone"):
            return "Corridor Zone"
        return cls._title_case_token(region_type) or "Override"

    @classmethod
    def _override_action_for_row(cls, rec) -> str:
        corridor_policy = str(rec.get("CorridorPolicy", "") or "").strip().lower()
        if corridor_policy == "split_only":
            return "Split Corridor"
        if corridor_policy == "skip_zone":
            return "Skip Corridor"
        side_policy = str(rec.get("SidePolicy", "") or "").strip()
        if side_policy:
            _head, _, tail = side_policy.partition(":")
            if tail.strip():
                return cls._title_case_token(tail)
        daylight_policy = str(rec.get("DaylightPolicy", "") or "").strip()
        if daylight_policy:
            _head, _, tail = daylight_policy.partition(":")
            if tail.strip():
                return f"Daylight {cls._title_case_token(tail)}"
        return "-"

    def _timeline_line_for_row(self, rec) -> str:
        rid = str(rec.get("Id", "") or "-")
        start = self._safe_float(rec.get("StartStation", 0.0), default=0.0)
        end = self._safe_float(rec.get("EndStation", 0.0), default=0.0)
        if end < start:
            start, end = end, start
        span = f"{self._format_display_length(start):>8} -> {self._format_display_length(end):>8}"
        if not self._is_enabled_row(rec):
            source = self._hint_source_for_row(rec)
            status = self._hint_status_label_for_row(rec)
            confidence = self._hint_confidence_label_for_row(rec)
            suggestion = self._title_case_token(str(rec.get("RegionType", "") or "")) or "Hint"
            return f"HINT {span} | {rid} | {source} | {confidence} | {status} | {suggestion}"
        layer = str(rec.get("Layer", "") or "").strip().lower()
        if layer == "base":
            purpose = self._title_case_token(str(rec.get("RegionType", "") or "")) or "Base"
            template = str(rec.get("TemplateName", "") or "").strip() or "-"
            return f"BASE {span} | {rid} | {purpose} | tpl={template}"
        kind = self._override_kind_for_row(rec)
        scope = self._override_scope_for_row(rec)
        action = self._override_action_for_row(rec)
        return f"OVR  {span} | {rid} | {kind} | {scope} | {action}"

    def _refresh_timeline_summary(self, rows=None):
        data_rows = [dict(row) for row in list(rows if rows is not None else self._read_rows())]
        if not data_rows:
            self.tbl_timeline.setRowCount(0)
            self.txt_timeline_summary.setPlainText("No region rows.")
            self._populate_timeline_editor(None)
            return
        data_rows.sort(
            key=lambda rec: (
                self._safe_float(rec.get("StartStation", 0.0), default=0.0),
                self._safe_float(rec.get("EndStation", 0.0), default=0.0),
                str(rec.get("Id", "") or ""),
            )
        )
        base_count = sum(
            1
            for rec in data_rows
            if self._is_enabled_row(rec) and str(rec.get("Layer", "") or "").strip().lower() == "base"
        )
        override_count = sum(
            1
            for rec in data_rows
            if self._is_enabled_row(rec) and str(rec.get("Layer", "") or "").strip().lower() != "base"
        )
        hint_count = sum(1 for rec in data_rows if not self._is_enabled_row(rec))
        lines = [f"Base={base_count} | Override={override_count} | Hint={hint_count}"]
        lines.extend(self._timeline_line_for_row(rec) for rec in data_rows)
        current_row = self._selected_timeline_table_row()
        self._fill_timeline_table(data_rows)
        self.txt_timeline_summary.setPlainText("\n".join(lines))
        if current_row >= 0 and self._select_timeline_row_by_table_row(current_row):
            pass
        else:
            self._populate_timeline_editor(None)

    def _load_selected_override_into_editor(self):
        rec, _idx, _rows = self._selected_workflow_record(self.tbl_override)
        if rec is None:
            self.lbl_override_editor.setText("Select an override row to edit it here.")
            self._set_combo_value(self.cmb_override_kind, "Ditch / Berm")
            self._set_combo_value(self.cmb_override_scope, "Both")
            self._set_combo_value(self.cmb_override_action, "-")
            self.txt_override_start.setText("")
            self.txt_override_end.setText("")
            self.btn_apply_override_editor.setEnabled(False)
            self.btn_open_override_advanced.setEnabled(False)
            return
        self._set_combo_value(self.cmb_override_kind, self._override_kind_for_row(rec))
        self._set_combo_value(self.cmb_override_scope, self._override_scope_for_row(rec))
        self._set_combo_value(self.cmb_override_action, self._override_action_for_row(rec))
        self.txt_override_start.setText(self._format_display_length(rec.get("StartStation", 0.0)))
        self.txt_override_end.setText(self._format_display_length(rec.get("EndStation", 0.0)))
        self.lbl_override_editor.setText(f"Editing {str(rec.get('Id', '') or 'selected override')}")
        self.btn_apply_override_editor.setEnabled(True)
        self.btn_open_override_advanced.setEnabled(True)

    @staticmethod
    def _override_scope_token(scope_text: str) -> str:
        scope = str(scope_text or "").strip().lower()
        if scope in ("left", "right", "both"):
            return scope
        return "both"

    def _apply_override_editor(self):
        rec, _idx, _rows = self._selected_workflow_record(self.tbl_override)
        if rec is None:
            self.lbl_status.setText("Select an override row first.")
            return
        row = int(rec.get("_table_row", -1))
        if row < 0:
            self.lbl_status.setText("Selected override could not be resolved.")
            return
        start_default = self._safe_float(rec.get("StartStation", 0.0), default=0.0)
        end_default = self._safe_float(rec.get("EndStation", 0.0), default=0.0)
        start_val = self._meters_from_display(
            self._safe_float(self.txt_override_start.text(), default=self._display_from_meters(start_default))
        )
        end_val = self._meters_from_display(
            self._safe_float(self.txt_override_end.text(), default=self._display_from_meters(end_default))
        )
        if end_val < start_val:
            start_val, end_val = end_val, start_val
        kind = str(self.cmb_override_kind.currentText() or "").strip()
        scope = self._override_scope_token(self.cmb_override_scope.currentText())
        action = str(self.cmb_override_action.currentText() or "").strip()

        region_type = "other"
        side_policy = ""
        daylight_policy = ""
        corridor_policy = ""
        if kind == "Ditch / Berm":
            region_type = "ditch_override"
            side_policy = f"{scope}:berm"
            action = "Berm"
        elif kind == "Urban Edge":
            region_type = "retaining_wall_zone"
            daylight_policy = f"{scope}:off"
            action = "Daylight Off"
        elif kind == "Corridor Zone":
            region_type = "other"
            if action == "Skip Corridor":
                corridor_policy = "skip_zone"
            else:
                corridor_policy = "split_only"
                action = "Split Corridor"
        else:
            region_type = "other"
            action = "-"

        self._loading = True
        try:
            self._set_cell_text(row, 1, region_type)
            self._set_cell_text(row, 3, self._format_display_length(start_val))
            self._set_cell_text(row, 4, self._format_display_length(end_val))
            self._set_cell_text(row, 11, side_policy)
            self._set_cell_text(row, 12, daylight_policy)
            self._set_cell_text(row, 13, corridor_policy)
        finally:
            self._loading = False
        self._materialize_row_ids(force_if_generated=True)
        self._refresh_workflow_tables()
        self._refresh_validation_status()
        self.lbl_status.setText(
            f"Override updated: {str(rec.get('Id', '') or 'selected')} | {kind} | {action} | {self._format_display_length(start_val)}-{self._format_display_length(end_val)} {self._display_unit_label()}"
        )

    def _set_advanced_row_enabled(self, row: int, enabled: bool):
        if row < 0 or row >= self.table.rowCount():
            return False
        self._loading = True
        try:
            self._set_cell_text(row, 14, "true" if bool(enabled) else "false")
        finally:
            self._loading = False
        return True

    def _set_advanced_row_notes(self, row: int, note_text: str):
        if row < 0 or row >= self.table.rowCount():
            return False
        self._loading = True
        try:
            self._set_cell_text(row, 15, str(note_text or ""))
        finally:
            self._loading = False
        return True

    def _set_advanced_row_hint_status(self, row: int, status_text: str):
        if row < 0 or row >= self.table.rowCount():
            return False
        self._loading = True
        try:
            self._set_cell_text(row, 17, str(status_text or ""))
        finally:
            self._loading = False
        return True

    def _accept_selected_hint(self):
        self._apply_hint_action(accept=True, jump_to_edit=False)

    def _accept_and_edit_selected_hint(self):
        self._apply_hint_action(accept=True, jump_to_edit=True)

    def _ignore_selected_hint(self):
        self._apply_hint_action(accept=False, jump_to_edit=False)

    def _apply_hint_action(self, *, accept: bool, jump_to_edit: bool):
        row = self._selected_summary_table_row(self.tbl_hint)
        if row < 0:
            self.lbl_status.setText("Select a hint row first.")
            return
        rows = self._read_rows()
        rec = None
        for item in rows:
            if int(item.get("_table_row", -1)) == int(row):
                rec = dict(item)
                break
        if rec is None:
            self.lbl_status.setText("Selected hint row could not be resolved.")
            return
        current_status = self._hint_status_for_row(rec)
        new_status = HINT_STATUS_ACCEPTED if bool(accept) else HINT_STATUS_IGNORED
        self._set_advanced_row_enabled(row, bool(accept))
        self._set_advanced_row_hint_status(row, new_status)
        self._set_advanced_row_notes(row, self._strip_hint_note_prefixes(str(rec.get("Notes", "") or "")))
        self._refresh_workflow_tables()
        self._refresh_validation_status()
        if bool(accept):
            self.lbl_status.setText(f"Hint accepted: {str(rec.get('Id', '') or '')}")
        else:
            self.lbl_status.setText(f"Hint ignored: {str(rec.get('Id', '') or '')}")
        if bool(accept) and bool(jump_to_edit):
            selected = self._select_summary_row_by_table_row(self.tbl_override, row)
            try:
                self.tabs.setCurrentIndex(0)
            except Exception:
                pass
            if not selected:
                try:
                    self.tabs.setCurrentIndex(1)
                except Exception:
                    pass
                self.table.setCurrentCell(row, 0)
            else:
                self._load_selected_override_into_editor()
                self.lbl_status.setText(f"Hint accepted and loaded into workflow override editor: {str(rec.get('Id', '') or '')}")
        elif (not accept) and current_status == HINT_STATUS_IGNORED:
            self.lbl_status.setText(f"Hint already ignored: {str(rec.get('Id', '') or '')}")

    def _remove_row(self):
        row = int(self.table.currentRow())
        if row < 0:
            row = self.table.rowCount() - 1
        if row >= 0:
            self.table.removeRow(row)
        if self.table.rowCount() <= 0:
            self._set_rows(1)
        self._refresh_validation_status()

    def _sort_rows(self):
        grouped = self._group_rows()
        self._populate_table(self._flatten_group_rows(grouped))

    def _load_preset(self):
        preset_name = str(self.cmb_preset.currentText() or "").strip()
        rows = list(self._make_region_preset(preset_name) or [])
        if not rows:
            QtWidgets.QMessageBox.information(None, "Manage Region Plan", "Select preset data first.")
            return
        self._populate_table(rows)
        self.lbl_status.setText(f"Loaded preset data: {preset_name} | rows={len(rows)}")

    def _seed_from_project(self):
        merge = self._merge_project_seed_rows(self._read_rows())
        rows = list(merge.get("rows", []) or [])
        if not rows or (int(merge.get("base_added", 0) or 0) <= 0 and int(merge.get("hint_added", 0) or 0) <= 0 and int(merge.get("hint_replaced", 0) or 0) <= 0):
            QtWidgets.QMessageBox.information(None, "Manage Region Plan", "No linked project data was found for seeding.")
            return
        self._populate_table(rows)
        self.lbl_status.setText(
            "Seeded from project links | "
            f"base added={int(merge.get('base_added', 0) or 0)} | "
            f"hints added={int(merge.get('hint_added', 0) or 0)} | "
            f"hints refreshed={int(merge.get('hint_replaced', 0) or 0)}"
        )

    @staticmethod
    def _csv_bool(value) -> bool:
        return str(value or "true").strip().lower() not in ("false", "0", "no", "off", "disabled")

    def _normalized_csv_record(self, rec, linear_unit: str = ""):
        return self._region_record(
            str(rec.get("Id", "") or ""),
            str(rec.get("RegionType", "") or ""),
            str(rec.get("Layer", "") or "base"),
            self._meters_from_csv(rec.get("StartStation", 0.0), linear_unit),
            self._meters_from_csv(rec.get("EndStation", 0.0), linear_unit),
            priority=self._safe_int(rec.get("Priority", 0), default=0),
            transition_in=self._meters_from_csv(rec.get("TransitionIn", 0.0), linear_unit),
            transition_out=self._meters_from_csv(rec.get("TransitionOut", 0.0), linear_unit),
            template_name=str(rec.get("TemplateName", "") or ""),
            assembly_name=str(rec.get("AssemblyName", "") or ""),
            rule_set=str(rec.get("RuleSet", "") or ""),
            side_policy=str(rec.get("SidePolicy", "") or ""),
            daylight_policy=str(rec.get("DaylightPolicy", "") or ""),
            corridor_policy=str(rec.get("CorridorPolicy", "") or ""),
            enabled=self._csv_bool(rec.get("Enabled", "true")),
            notes=str(rec.get("Notes", "") or ""),
            hint_source=str(rec.get("HintSource", "") or ""),
            hint_status=str(rec.get("HintStatus", "") or ""),
            hint_reason=str(rec.get("HintReason", "") or ""),
            hint_confidence=self._safe_float(rec.get("HintConfidence", 0.0), default=0.0),
        )

    def _rows_to_csv_text(self, rows):
        buf = io.StringIO()
        linear_unit = str(_units.get_linear_export_unit(self._unit_context()) or "m")
        buf.write(f"# CorridorRoadUnits,linear={linear_unit}\n")
        writer = csv.DictWriter(buf, fieldnames=list(COL_HEADERS), extrasaction="ignore")
        writer.writeheader()
        for row in list(rows or []):
            clean = {key: "" for key in COL_HEADERS}
            for key in COL_HEADERS:
                val = row.get(key, "")
                if key == "Enabled":
                    clean[key] = "true" if self._csv_bool(val) else "false"
                elif key in ("StartStation", "EndStation", "TransitionIn", "TransitionOut"):
                    clean[key] = f"{self._csv_from_meters(val, linear_unit):.3f}"
                else:
                    clean[key] = "" if val is None else str(val)
            writer.writerow(clean)
        return buf.getvalue()

    def _rows_from_csv_text(self, text: str):
        lines = str(text or "").splitlines()
        metadata = _parse_csv_unit_metadata(lines)
        linear_unit = str((metadata or {}).get("linear_unit", "") or "")
        data_lines = [line for line in lines if not str(line or "").lstrip().startswith(CSV_COMMENT_PREFIX)]
        buf = io.StringIO("\n".join(data_lines))
        reader = csv.DictReader(buf)
        if not reader.fieldnames:
            return []
        rows = []
        for raw in reader:
            clean = {key: str((raw or {}).get(key, "") or "").strip() for key in COL_HEADERS}
            if not any(clean.values()):
                continue
            rows.append(self._normalized_csv_record(clean, linear_unit=linear_unit))
        return rows

    def _import_csv(self):
        path, _flt = QtWidgets.QFileDialog.getOpenFileName(
            None,
            "Import Region Plan CSV",
            "",
            "CSV Files (*.csv);;All Files (*)",
        )
        if not str(path or "").strip():
            return
        try:
            with open(path, "r", encoding="utf-8-sig", newline="") as fp:
                text = fp.read()
            rows = self._rows_from_csv_text(text)
            linear_unit = str(_parse_csv_unit_metadata(str(text or "").splitlines()).get("linear_unit", "") or _units.get_linear_import_unit(self._unit_context()))
        except Exception as ex:
            QtWidgets.QMessageBox.warning(None, "Manage Region Plan", f"CSV import failed: {ex}")
            return
        if not rows:
            QtWidgets.QMessageBox.information(None, "Manage Region Plan", "No region rows were found in the CSV file.")
            return
        current_rows = self._read_rows()
        if current_rows:
            reply = QtWidgets.QMessageBox.question(
                None,
                "Manage Region Plan",
                "Replace the current grouped workflow rows with the imported CSV rows?",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.No,
            )
            if reply != QtWidgets.QMessageBox.Yes:
                return
        self._populate_table(rows)
        self.lbl_status.setText(f"Imported CSV rows: {len(rows)} | linear={linear_unit}")

    def _export_csv(self):
        grouped = self._group_rows()
        rows = self._flatten_group_rows(grouped)
        if not rows:
            QtWidgets.QMessageBox.information(None, "Manage Region Plan", "No region rows are available to export.")
            return
        path, _flt = QtWidgets.QFileDialog.getSaveFileName(
            None,
            "Export Region Plan CSV",
            "region_plan.csv",
            "CSV Files (*.csv);;All Files (*)",
        )
        if not str(path or "").strip():
            return
        try:
            with open(path, "w", encoding="utf-8", newline="") as fp:
                fp.write(self._rows_to_csv_text(rows))
        except Exception as ex:
            QtWidgets.QMessageBox.warning(None, "Manage Region Plan", f"CSV export failed: {ex}")
            return
        self.lbl_status.setText(f"Exported CSV rows: {len(rows)} | linear={_units.get_linear_export_unit(self._unit_context())}")

    def _refresh_validation_status(self):
        self._materialize_row_ids(force_if_generated=False)
        rows = self._read_rows()
        self._refresh_workflow_tables(rows=rows)
        if not rows:
            self.lbl_status.setText("No region rows.")
            return
        issues = list(RegionPlan.validate_records(rows) or [])
        if issues:
            self.lbl_status.setText(
                f"Validation warnings: {len(issues)} | "
                + " | ".join(list(issues[:3]))
            )
        else:
            self.lbl_status.setText(f"Validation OK | rows={len(rows)}")

    def _on_table_item_changed(self, item):
        if self._loading:
            return
        try:
            col = int(getattr(item, "column", lambda: -1)())
        except Exception:
            col = -1
        if col in (0, 2):
            self._materialize_row_ids(force_if_generated=True)
        self._refresh_validation_status()

    def _refresh_workflow_tables(self, rows=None):
        grouped = self._group_rows(rows=rows)
        base_rows = [dict(row, _row_index=int(row.get("_table_row", 0))) for row in list(grouped.get("base_rows", []) or [])]
        override_rows = [dict(row, _row_index=int(row.get("_table_row", 0))) for row in list(grouped.get("override_rows", []) or [])]
        hint_rows = [dict(row, _row_index=int(row.get("_table_row", 0))) for row in list(grouped.get("hint_rows", []) or [])]
        self._fill_summary_table(self.tbl_base, base_rows, kind="base")
        self._fill_summary_table(self.tbl_override, override_rows, kind="override")
        self._fill_summary_table(self.tbl_hint, hint_rows, kind="hint")
        self._refresh_timeline_summary(rows=self._flatten_group_rows(grouped))
        self._refresh_advanced_preview_summary(grouped=grouped)
        self._refresh_advanced_diagnostics(grouped=grouped)
        self._load_selected_override_into_editor()
        self._refresh_workflow_group_titles(grouped=grouped)
        self._refresh_workflow_action_state(grouped=grouped)

    def _refresh_workflow_group_titles(self, grouped=None):
        model = dict(grouped or self._group_rows())
        counts = {
            "base": len(list(model.get("base_rows", []) or [])),
            "override": len(list(model.get("override_rows", []) or [])),
            "hint": len(list(model.get("hint_rows", []) or [])),
        }
        titles = {
            "base": "Base Regions",
            "override": "Overrides",
            "hint": "Hints",
        }
        for key, box in dict(self._workflow_group_boxes or {}).items():
            title = titles.get(str(key), str(key or "").title())
            box.setTitle(f"{title} ({int(counts.get(key, 0))})")

    def _set_workflow_button_enabled(self, group_key: str, label: str, enabled: bool):
        btn = dict(self._workflow_action_buttons.get(str(group_key), {}) or {}).get(str(label), None)
        if btn is not None:
            btn.setEnabled(bool(enabled))

    def _refresh_workflow_action_state(self, grouped=None):
        model = dict(grouped or self._group_rows())
        base_rec, _base_idx, base_rows = self._selected_workflow_record(self.tbl_base)
        override_rec, _ovr_idx, _ovr_rows = self._selected_workflow_record(self.tbl_override)
        hint_rec, _hint_idx, _hint_rows = self._selected_workflow_record(self.tbl_hint)
        timeline_rec = self._timeline_record_for_table_row(self._selected_timeline_table_row())

        can_split_base = bool(base_rec is not None and self._is_enabled_row(base_rec) and str(base_rec.get("Layer", "") or "").strip().lower() == "base")
        can_merge_base = self._can_merge_base_record(base_rec, base_rows)
        has_override = bool(override_rec is not None)
        has_hint = bool(hint_rec is not None)
        can_split_timeline = bool(timeline_rec is not None and self._is_enabled_row(timeline_rec) and str(timeline_rec.get("Layer", "") or "").strip().lower() == "base")

        self._set_workflow_button_enabled("base", "Split Selected", can_split_base)
        self._set_workflow_button_enabled("base", "Merge Selected", can_merge_base)
        self._set_workflow_button_enabled("hint", "Accept", has_hint)
        self._set_workflow_button_enabled("hint", "Accept and Edit", has_hint)
        self._set_workflow_button_enabled("hint", "Ignore", has_hint)
        self.btn_apply_override_editor.setEnabled(has_override)
        self.btn_open_override_advanced.setEnabled(has_override)
        self.btn_apply_timeline_span.setEnabled(timeline_rec is not None)
        self.btn_open_timeline_selection.setEnabled(timeline_rec is not None)
        self.btn_split_timeline_base.setEnabled(can_split_timeline)

    def _fill_summary_table(self, table, rows, *, kind: str):
        table.setRowCount(0)
        for row_idx, rec in enumerate(list(rows or [])):
            table.insertRow(row_idx)
            values = self._summary_values_for_row(rec, kind=kind)
            for col_idx, value in enumerate(values):
                item = QtWidgets.QTableWidgetItem(str(value or ""))
                item.setData(QtCore.Qt.UserRole, int(rec.get("_row_index", row_idx)))
                self._apply_table_row_visuals(item, kind=kind)
                table.setItem(row_idx, col_idx, item)

    @staticmethod
    def _qcolor_lightness(color) -> float:
        try:
            qcolor = QtGui.QColor(color)
            if not qcolor.isValid():
                return 255.0
            return float(qcolor.lightness())
        except Exception:
            return 255.0

    @staticmethod
    def _qcolor_name(color, fallback: str) -> str:
        try:
            qcolor = QtGui.QColor(color)
            if qcolor.isValid():
                return str(qcolor.name())
        except Exception:
            pass
        return str(fallback or "#000000")

    @classmethod
    def _palette_color_hex(cls, role, fallback: str) -> str:
        app = QtWidgets.QApplication.instance()
        palettes = []
        try:
            main_window = Gui.getMainWindow()
            if main_window is not None:
                palettes.append(main_window.palette())
        except Exception:
            pass
        if app is not None:
            try:
                active_window = app.activeWindow()
                if active_window is not None:
                    palettes.append(active_window.palette())
            except Exception:
                pass
            try:
                focus_widget = app.focusWidget()
                if focus_widget is not None:
                    palettes.append(focus_widget.palette())
            except Exception:
                pass
            try:
                palettes.append(app.palette())
            except Exception:
                pass
        for palette in palettes:
            try:
                color = palette.color(role)
                if color.isValid():
                    return cls._qcolor_name(color, fallback)
            except Exception:
                continue
        return cls._qcolor_name(fallback, fallback)

    @classmethod
    def _mix_color_hex(cls, color_a, color_b, ratio: float) -> str:
        try:
            qa = QtGui.QColor(color_a)
            qb = QtGui.QColor(color_b)
            if not qa.isValid():
                qa = QtGui.QColor("#000000")
            if not qb.isValid():
                qb = QtGui.QColor("#000000")
            t = max(0.0, min(1.0, float(ratio)))
            mix = QtGui.QColor(
                int(round(qa.red() * (1.0 - t) + qb.red() * t)),
                int(round(qa.green() * (1.0 - t) + qb.green() * t)),
                int(round(qa.blue() * (1.0 - t) + qb.blue() * t)),
            )
            return str(mix.name())
        except Exception:
            return cls._qcolor_name(color_a, "#000000")

    @classmethod
    def _contrast_text_hex(cls, bg_hex: str) -> str:
        return "#111111" if cls._qcolor_lightness(bg_hex) >= 140.0 else "#f4f7fb"

    @classmethod
    def _is_dark_theme(cls) -> bool:
        window_hex = cls._palette_color_hex(QtGui.QPalette.Window, "#2f343f")
        base_hex = cls._palette_color_hex(QtGui.QPalette.Base, "#2f343f")
        text_hex = cls._palette_color_hex(QtGui.QPalette.WindowText, "#f2f4f8")
        window_l = cls._qcolor_lightness(window_hex)
        base_l = cls._qcolor_lightness(base_hex)
        text_l = cls._qcolor_lightness(text_hex)
        if window_l <= 140.0:
            return True
        if base_l <= 140.0:
            return True
        return ((window_l + base_l) * 0.5) < (text_l - 12.0)

    @classmethod
    def _table_palette_for_kind(cls, kind: str):
        token = str(kind or "").strip().lower()
        accent_map = {
            "base": "#4d9c69",
            "override": "#5f97c7",
            "hint": "#c2942d",
            "neutral": "#7a7f87",
        }
        accent_hex = accent_map.get(token, accent_map["neutral"])
        if cls._is_dark_theme():
            window_hex = cls._palette_color_hex(QtGui.QPalette.Window, "#2f343f")
            base_hex = cls._mix_color_hex(window_hex, "#11161c", 0.35)
            alt_base_hex = cls._mix_color_hex(base_hex, accent_hex, 0.08)
            text_hex = cls._palette_color_hex(QtGui.QPalette.Text, "#eef2f7")
            highlight_hex = cls._palette_color_hex(QtGui.QPalette.Highlight, "#4a90d9")
            bg_hex = cls._mix_color_hex(base_hex, accent_hex, 0.22)
            alt_bg_hex = cls._mix_color_hex(alt_base_hex, accent_hex, 0.16)
            sel_hex = cls._mix_color_hex(highlight_hex, accent_hex, 0.18)
            grid_hex = cls._mix_color_hex(text_hex, base_hex, 0.82)
        else:
            base_hex = cls._palette_color_hex(QtGui.QPalette.Base, "#ffffff")
            alt_base_hex = cls._palette_color_hex(QtGui.QPalette.AlternateBase, base_hex)
            text_hex = cls._palette_color_hex(QtGui.QPalette.Text, "#111111")
            highlight_hex = cls._palette_color_hex(QtGui.QPalette.Highlight, "#4a90d9")
            bg_hex = cls._mix_color_hex(base_hex, accent_hex, 0.18)
            alt_bg_hex = cls._mix_color_hex(alt_base_hex, accent_hex, 0.12)
            sel_hex = cls._mix_color_hex(highlight_hex, accent_hex, 0.15)
            grid_hex = cls._mix_color_hex(text_hex, base_hex, 0.72)
        fg_hex = cls._contrast_text_hex(bg_hex)
        sel_fg_hex = cls._contrast_text_hex(sel_hex)
        return {
            "bg": bg_hex,
            "alt_bg": alt_bg_hex,
            "fg": fg_hex,
            "sel_bg": sel_hex,
            "sel_fg": sel_fg_hex,
            "grid": grid_hex,
            "base": base_hex,
            "text": text_hex,
        }

    @classmethod
    def _apply_table_row_visuals(cls, item, *, kind: str):
        colors = cls._table_palette_for_kind(kind)
        bg_hex = str(colors.get("bg", "#ffffff"))
        fg_hex = str(colors.get("fg", "#111111"))
        sel_hex = str(colors.get("sel_bg", "#4a90d9"))
        try:
            item.setBackground(QtGui.QBrush(QtGui.QColor(bg_hex)))
            item.setForeground(QtGui.QBrush(QtGui.QColor(fg_hex)))
            item.setData(QtCore.Qt.BackgroundRole, QtGui.QColor(bg_hex))
            item.setData(QtCore.Qt.ForegroundRole, QtGui.QColor(fg_hex))
            item.setData(QtCore.Qt.UserRole + 1, str(sel_hex))
        except Exception:
            pass

    @classmethod
    def _apply_table_stylesheet(cls, table, *, kind: str):
        colors = cls._table_palette_for_kind(kind)
        base_hex = str(colors.get("base", "#ffffff"))
        alt_bg_hex = str(colors.get("alt_bg", base_hex))
        text_hex = str(colors.get("text", "#111111"))
        sel_hex = str(colors.get("sel_bg", "#4a90d9"))
        sel_fg_hex = str(colors.get("sel_fg", "#ffffff"))
        grid_hex = str(colors.get("grid", "#808080"))
        try:
            pal = QtGui.QPalette(table.palette())
            for group in (
                QtGui.QPalette.Active,
                QtGui.QPalette.Inactive,
                QtGui.QPalette.Disabled,
            ):
                pal.setColor(group, QtGui.QPalette.Base, QtGui.QColor(base_hex))
                pal.setColor(group, QtGui.QPalette.AlternateBase, QtGui.QColor(alt_bg_hex))
                pal.setColor(group, QtGui.QPalette.Text, QtGui.QColor(text_hex))
                pal.setColor(group, QtGui.QPalette.Window, QtGui.QColor(base_hex))
                pal.setColor(group, QtGui.QPalette.WindowText, QtGui.QColor(text_hex))
                pal.setColor(group, QtGui.QPalette.Button, QtGui.QColor(base_hex))
                pal.setColor(group, QtGui.QPalette.ButtonText, QtGui.QColor(text_hex))
                pal.setColor(group, QtGui.QPalette.Highlight, QtGui.QColor(sel_hex))
                pal.setColor(group, QtGui.QPalette.HighlightedText, QtGui.QColor(sel_fg_hex))
            table.setPalette(pal)
            viewport = table.viewport()
            if viewport is not None:
                viewport.setPalette(pal)
                viewport.setAutoFillBackground(True)
                viewport.setAttribute(QtCore.Qt.WA_StyledBackground, True)
                viewport.setStyleSheet(f"background-color: {base_hex}; color: {text_hex};")
            table.setAutoFillBackground(True)
            table.setAttribute(QtCore.Qt.WA_StyledBackground, True)
        except Exception:
            pass
        table.setStyleSheet(
            "QAbstractItemView {"
            f" background-color: {base_hex};"
            f" alternate-background-color: {alt_bg_hex};"
            f" color: {text_hex};"
            f" gridline-color: {grid_hex};"
            "}"
            "QAbstractScrollArea {"
            f" background-color: {base_hex};"
            f" color: {text_hex};"
            "}"
            "QAbstractScrollArea > QWidget {"
            f" background-color: {base_hex};"
            f" color: {text_hex};"
            "}"
            "QTableWidget, QTableView {"
            f" background-color: {base_hex};"
            f" alternate-background-color: {alt_bg_hex};"
            f" color: {text_hex};"
            f" gridline-color: {grid_hex};"
            "}"
            "QTableWidget::viewport, QTableView::viewport {"
            f" background-color: {base_hex};"
            f" alternate-background-color: {alt_bg_hex};"
            f" color: {text_hex};"
            f" gridline-color: {grid_hex};"
            "}"
            "QTableWidget > QWidget {"
            f" background-color: {base_hex};"
            f" color: {text_hex};"
            "}"
            "QTableWidget::item {"
            f" color: {text_hex};"
            "}"
            "QTableWidget::item:selected {"
            f" background-color: {sel_hex};"
            f" color: {sel_fg_hex};"
            "}"
        )

    def _summary_values_for_row(self, rec, *, kind: str):
        rid = str(rec.get("Id", "") or "")
        region_type = str(rec.get("RegionType", "") or "")
        start = self._safe_float(rec.get("StartStation", 0.0), default=0.0)
        end = self._safe_float(rec.get("EndStation", 0.0), default=0.0)
        span = f"{self._format_display_length(start)} - {self._format_display_length(end)}"
        if kind == "base":
            return [
                rid,
                region_type or "roadway",
                span,
                str(rec.get("TemplateName", "") or "-") or "-",
            ]
        if kind == "override":
            kind_text = self._override_kind_for_row(rec)
            scope = self._override_scope_for_row(rec)
            action = self._override_action_for_row(rec)
            return [
                rid,
                kind_text,
                scope,
                span,
                action,
            ]
        hint_status = self._hint_status_for_row(rec)
        source = self._hint_source_for_row(rec)
        family = self._hint_family_for_row(rec)
        reason = self._hint_reason_for_row(rec)
        return [
            rid,
            f"{source} / {family}",
            self._title_case_token(region_type) or "Hint",
            span,
            self._hint_confidence_label_for_row(rec),
            self._hint_status_label_for_row(rec),
            reason,
        ]

    def _timeline_values_for_row(self, rec):
        start = self._safe_float(rec.get("StartStation", 0.0), default=0.0)
        end = self._safe_float(rec.get("EndStation", 0.0), default=0.0)
        if end < start:
            start, end = end, start
        span = f"{self._format_display_length(start)} - {self._format_display_length(end)}"
        rid = str(rec.get("Id", "") or "")
        if not self._is_enabled_row(rec):
            return [
                "Hint",
                rid,
                span,
                self._hint_status_label_for_row(rec),
            ]
        if str(rec.get("Layer", "") or "").strip().lower() == "base":
            return [
                "Base",
                rid,
                span,
                self._title_case_token(str(rec.get("RegionType", "") or "")) or "Roadway",
            ]
        return [
            "Override",
            rid,
            span,
            self._override_action_for_row(rec),
        ]

    def _fill_timeline_table(self, rows):
        self.tbl_timeline.setRowCount(0)
        self._timeline_real_row_count = len(list(rows or []))
        for row_idx, rec in enumerate(list(rows or [])):
            self.tbl_timeline.insertRow(row_idx)
            values = self._timeline_values_for_row(rec)
            timeline_kind = "hint"
            if self._is_enabled_row(rec):
                timeline_kind = "base" if str(rec.get("Layer", "") or "").strip().lower() == "base" else "override"
            for col_idx, value in enumerate(values):
                item = QtWidgets.QTableWidgetItem(str(value or ""))
                item.setData(QtCore.Qt.UserRole, int(rec.get("_table_row", row_idx)))
                self._apply_table_row_visuals(item, kind=timeline_kind)
                self.tbl_timeline.setItem(row_idx, col_idx, item)
        self._fill_timeline_empty_area()

    def _timeline_fill_colors(self):
        colors = self._table_palette_for_kind("neutral")
        base_hex = str(colors.get("base", "#2b3038"))
        text_hex = str(colors.get("text", "#eef2f7"))
        try:
            summary = getattr(self, "txt_timeline_summary", None)
            if summary is not None:
                summary_base = summary.palette().color(QtGui.QPalette.Base)
                summary_text = summary.palette().color(QtGui.QPalette.Text)
                if summary_base.isValid() and self._qcolor_lightness(summary_base) < 220.0:
                    base_hex = str(summary_base.name())
                if summary_text.isValid():
                    text_hex = str(summary_text.name())
        except Exception:
            pass
        return base_hex, text_hex

    def _fill_timeline_empty_area(self):
        table = getattr(self, "tbl_timeline", None)
        if table is None:
            return
        real_count = max(0, int(getattr(self, "_timeline_real_row_count", 0) or 0))
        while table.rowCount() > real_count:
            table.removeRow(table.rowCount() - 1)
        try:
            header_h = max(0, int(table.horizontalHeader().height()))
        except Exception:
            header_h = 24
        try:
            viewport_h = max(int(table.viewport().height()), int(table.minimumHeight()) - header_h - 4)
        except Exception:
            viewport_h = max(0, int(table.minimumHeight()) - header_h - 4)
        try:
            row_h = max(18, int(table.verticalHeader().defaultSectionSize()))
        except Exception:
            row_h = 24
        used_h = 0
        for row in range(real_count):
            try:
                used_h += max(1, int(table.rowHeight(row)))
            except Exception:
                used_h += row_h
        remaining_h = max(0, viewport_h - used_h)
        filler_rows = min(64, int((remaining_h + row_h - 1) // row_h) + 1) if remaining_h > 0 else 0
        if filler_rows <= 0:
            return
        base_hex, text_hex = self._timeline_fill_colors()
        for _idx in range(filler_rows):
            row = table.rowCount()
            table.insertRow(row)
            table.setRowHeight(row, row_h)
            for col in range(table.columnCount()):
                item = QtWidgets.QTableWidgetItem("")
                item.setFlags(QtCore.Qt.NoItemFlags)
                item.setData(QtCore.Qt.UserRole, -1)
                try:
                    item.setBackground(QtGui.QBrush(QtGui.QColor(base_hex)))
                    item.setForeground(QtGui.QBrush(QtGui.QColor(text_hex)))
                    item.setData(QtCore.Qt.BackgroundRole, QtGui.QColor(base_hex))
                    item.setData(QtCore.Qt.ForegroundRole, QtGui.QColor(text_hex))
                except Exception:
                    pass
                table.setItem(row, col, item)

    def _selected_timeline_table_row(self) -> int:
        row = int(self.tbl_timeline.currentRow())
        if row < 0:
            return -1
        item = self.tbl_timeline.item(row, 0)
        if item is None:
            return -1
        try:
            target_row = int(item.data(QtCore.Qt.UserRole))
            return target_row if target_row >= 0 else -1
        except Exception:
            return -1

    def _select_timeline_row_by_table_row(self, target_row: int) -> bool:
        if int(target_row) < 0:
            return False
        for row in range(self.tbl_timeline.rowCount()):
            item = self.tbl_timeline.item(row, 0)
            if item is None:
                continue
            try:
                source_row = int(item.data(QtCore.Qt.UserRole))
            except Exception:
                source_row = -1
            if source_row == int(target_row):
                self.tbl_timeline.setCurrentCell(row, 0)
                return True
        return False

    def _clear_summary_selections(self, *, exclude=None):
        for table in (self.tbl_base, self.tbl_override, self.tbl_hint):
            if table == exclude:
                continue
            table.clearSelection()
            table.setCurrentCell(-1, -1)

    def _populate_timeline_editor(self, rec):
        if rec is None:
            self.lbl_timeline_editor.setText("Select a timeline row to move, resize, or split it.")
            self.txt_timeline_start.setText("")
            self.txt_timeline_end.setText("")
            self.btn_apply_timeline_span.setEnabled(False)
            self.btn_split_timeline_base.setEnabled(False)
            self.btn_open_timeline_selection.setEnabled(False)
            return
        start = self._safe_float(rec.get("StartStation", 0.0), default=0.0)
        end = self._safe_float(rec.get("EndStation", 0.0), default=0.0)
        if end < start:
            start, end = end, start
        row_kind = "Hint"
        if self._is_enabled_row(rec):
            row_kind = "Base" if str(rec.get("Layer", "") or "").strip().lower() == "base" else "Override"
        self.lbl_timeline_editor.setText(f"{row_kind}: {str(rec.get('Id', '') or '-')}")
        self.txt_timeline_start.setText(self._format_display_length(start))
        self.txt_timeline_end.setText(self._format_display_length(end))
        self.btn_apply_timeline_span.setEnabled(True)
        self.btn_split_timeline_base.setEnabled(row_kind == "Base")
        self.btn_open_timeline_selection.setEnabled(True)

    def _timeline_record_for_table_row(self, target_row: int):
        for rec in self._flatten_group_rows(self._group_rows()):
            if int(rec.get("_table_row", -1)) == int(target_row):
                return dict(rec)
        return None

    def _on_timeline_selection_changed(self, *_args):
        if self._workflow_syncing:
            return
        target_row = self._selected_timeline_table_row()
        rec = self._timeline_record_for_table_row(target_row)
        self._populate_timeline_editor(rec)
        if rec is None:
            self._clear_summary_selections()
            return
        self._workflow_syncing = True
        try:
            if not self._is_enabled_row(rec):
                self._clear_summary_selections(exclude=self.tbl_hint)
                self._select_summary_row_by_table_row(self.tbl_hint, target_row)
            elif str(rec.get("Layer", "") or "").strip().lower() == "base":
                self._clear_summary_selections(exclude=self.tbl_base)
                self._select_summary_row_by_table_row(self.tbl_base, target_row)
            else:
                self._clear_summary_selections(exclude=self.tbl_override)
                self._select_summary_row_by_table_row(self.tbl_override, target_row)
        finally:
            self._workflow_syncing = False
        self._load_selected_override_into_editor()

    def _sync_timeline_from_summary_table(self, table):
        if self._workflow_syncing:
            return
        target_row = self._selected_summary_table_row(table)
        self._workflow_syncing = True
        try:
            if target_row >= 0:
                self._select_timeline_row_by_table_row(target_row)
            elif table.currentRow() < 0:
                self.tbl_timeline.clearSelection()
                self.tbl_timeline.setCurrentCell(-1, -1)
                self._populate_timeline_editor(None)
        finally:
            self._workflow_syncing = False

    def _focus_selected_timeline_row(self):
        target_row = self._selected_timeline_table_row()
        if target_row < 0:
            self.lbl_status.setText("Select a timeline row first.")
            return
        rec = self._timeline_record_for_table_row(target_row)
        if rec is None:
            self.lbl_status.setText("Selected timeline row could not be resolved.")
            return
        self._on_timeline_selection_changed()
        self.lbl_status.setText(f"Focused workflow selection: {str(rec.get('Id', '') or '-')}")

    def _apply_timeline_span_edit(self):
        target_row = self._selected_timeline_table_row()
        if target_row < 0:
            self.lbl_status.setText("Select a timeline row first.")
            return
        rec = self._timeline_record_for_table_row(target_row)
        if rec is None:
            self.lbl_status.setText("Selected timeline row could not be resolved.")
            return
        start_default = self._safe_float(rec.get("StartStation", 0.0), default=0.0)
        end_default = self._safe_float(rec.get("EndStation", 0.0), default=0.0)
        start_val = self._meters_from_display(
            self._safe_float(self.txt_timeline_start.text(), default=self._display_from_meters(start_default))
        )
        end_val = self._meters_from_display(
            self._safe_float(self.txt_timeline_end.text(), default=self._display_from_meters(end_default))
        )
        if end_val < start_val:
            start_val, end_val = end_val, start_val
        self._loading = True
        try:
            self._set_cell_text(target_row, 3, self._format_display_length(start_val))
            self._set_cell_text(target_row, 4, self._format_display_length(end_val))
        finally:
            self._loading = False
        self._refresh_workflow_tables()
        self._refresh_validation_status()
        self._select_timeline_row_by_table_row(target_row)
        self.lbl_status.setText(
            f"Timeline span updated: {str(rec.get('Id', '') or '-')} | {self._format_display_length(start_val)}-{self._format_display_length(end_val)} {self._display_unit_label()}"
        )

    def _split_selected_timeline_base(self):
        target_row = self._selected_timeline_table_row()
        if target_row < 0:
            self.lbl_status.setText("Select a timeline base row first.")
            return
        rec = self._timeline_record_for_table_row(target_row)
        if rec is None or (not self._is_enabled_row(rec)) or str(rec.get("Layer", "") or "").strip().lower() != "base":
            self.lbl_status.setText("Only enabled base timeline rows can be split.")
            return
        self._select_summary_row_by_table_row(self.tbl_base, target_row)
        self._split_selected_base_row()

    def _jump_from_summary_table(self, table):
        row = int(table.currentRow())
        if row < 0:
            return
        item = table.item(row, 0)
        if item is None:
            return
        try:
            target_row = int(item.data(QtCore.Qt.UserRole))
        except Exception:
            target_row = -1
        if target_row < 0:
            return
        try:
            self.tabs.setCurrentIndex(1)
        except Exception:
            pass
        self.table.setCurrentCell(target_row, 0)

    def _apply(self):
        if self.doc is None:
            QtWidgets.QMessageBox.warning(None, "Manage Region Plan", "No active document.")
            return
        self._materialize_row_ids(force_if_generated=False)
        grouped = self._group_rows()
        rows = self._flatten_group_rows(grouped)
        if not rows:
            QtWidgets.QMessageBox.warning(None, "Manage Region Plan", "No region rows to save.")
            return
        issues = list(RegionPlan.validate_records(rows) or [])
        if issues:
            reply = QtWidgets.QMessageBox.question(
                None,
                "Manage Region Plan",
                "Save with validation warnings?\n\n" + "\n".join(list(issues[:10])),
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.No,
            )
            if reply != QtWidgets.QMessageBox.Yes:
                return
        try:
            obj = self._ensure_target()
            RegionPlan.apply_records(obj, rows)
            obj.touch()

            prj = find_project(self.doc)
            if prj is not None:
                assign_project_region_plan(prj, obj)
                link_project(prj, links={"RegionPlan": obj}, adopt_extra=[obj])

            self.doc.recompute()
            self.lbl_status.setText(str(getattr(obj, "Status", "Applied") or "Applied"))
            QtWidgets.QMessageBox.information(
                None,
                "Manage Region Plan",
                f"Region plan saved.\nRows: {len(rows)}\nStatus: {getattr(obj, 'Status', 'Applied')}",
            )
            self._refresh_context()
            try:
                Gui.ActiveDocument.ActiveView.fitAll()
            except Exception:
                pass
        except Exception as ex:
            self.lbl_status.setText(f"ERROR: {ex}")
            QtWidgets.QMessageBox.warning(None, "Manage Region Plan", f"Apply failed: {ex}")
