# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

DEFAULT_STANDARD = "KDS"
SUPPORTED_STANDARDS = ("KDS", "AASHTO")


def normalize_standard(value, default: str = DEFAULT_STANDARD) -> str:
    s = str(value or "").strip().upper()
    if s in SUPPORTED_STANDARDS:
        return s
    d = str(default or DEFAULT_STANDARD).strip().upper()
    if d in SUPPORTED_STANDARDS:
        return d
    return DEFAULT_STANDARD


def _interp_by_speed(table, speed_kph: float):
    rows = sorted(list(table or []), key=lambda r: float(r[0]))
    if not rows:
        return {
            "min_radius_m": 0.0,
            "min_tangent_m": 0.0,
            "min_transition_m": 0.0,
            "reverse_min_tangent_m": 0.0,
            "reverse_min_transition_m": 0.0,
        }

    v = float(max(0.0, speed_kph))
    if v <= float(rows[0][0]):
        return {
            "min_radius_m": float(rows[0][1]),
            "min_tangent_m": float(rows[0][2]),
            "min_transition_m": float(rows[0][3]),
            "reverse_min_tangent_m": float(rows[0][4]),
            "reverse_min_transition_m": float(rows[0][5]),
        }
    if v >= float(rows[-1][0]):
        return {
            "min_radius_m": float(rows[-1][1]),
            "min_tangent_m": float(rows[-1][2]),
            "min_transition_m": float(rows[-1][3]),
            "reverse_min_tangent_m": float(rows[-1][4]),
            "reverse_min_transition_m": float(rows[-1][5]),
        }

    for i in range(len(rows) - 1):
        v0, r0, t0, l0, rt0, rl0 = rows[i]
        v1, r1, t1, l1, rt1, rl1 = rows[i + 1]
        v0 = float(v0)
        v1 = float(v1)
        if v0 <= v <= v1:
            if abs(v1 - v0) <= 1e-12:
                a = 0.0
            else:
                a = (v - v0) / (v1 - v0)
            return {
                "min_radius_m": float(r0) + (float(r1) - float(r0)) * a,
                "min_tangent_m": float(t0) + (float(t1) - float(t0)) * a,
                "min_transition_m": float(l0) + (float(l1) - float(l0)) * a,
                "reverse_min_tangent_m": float(rt0) + (float(rt1) - float(rt0)) * a,
                "reverse_min_transition_m": float(rl0) + (float(rl1) - float(rl0)) * a,
            }

    # Fallback (should not happen because table is covered above).
    last = rows[-1]
    return {
        "min_radius_m": float(last[1]),
        "min_tangent_m": float(last[2]),
        "min_transition_m": float(last[3]),
        "reverse_min_tangent_m": float(last[4]),
        "reverse_min_transition_m": float(last[5]),
    }


def _radius_from_ef(speed_kph: float, e_pct: float, f_side: float) -> float:
    v = max(0.0, float(speed_kph))
    e = max(0.0, float(e_pct)) / 100.0
    f = max(0.01, float(f_side))
    denom = 127.0 * (e + f)
    if denom <= 1e-12:
        return 0.0
    return float(v * v / denom)


_KDS_TABLE = (
    # speed(kph), min_radius(m), min_tangent(m), min_transition(m), reverse_min_tangent(m), reverse_min_transition(m)
    (40.0, 90.0, 15.0, 15.0, 20.0, 20.0),
    (60.0, 170.0, 25.0, 25.0, 35.0, 30.0),
    (80.0, 280.0, 40.0, 50.0, 55.0, 60.0),
    (100.0, 420.0, 60.0, 70.0, 80.0, 85.0),
    (120.0, 600.0, 80.0, 90.0, 110.0, 110.0),
)

_AASHTO_TABLE = (
    # speed(kph), min_radius(m), min_tangent(m), min_transition(m), reverse_min_tangent(m), reverse_min_transition(m)
    (40.0, 95.0, 20.0, 20.0, 25.0, 25.0),
    (60.0, 180.0, 30.0, 35.0, 40.0, 40.0),
    (80.0, 300.0, 50.0, 60.0, 65.0, 70.0),
    (100.0, 450.0, 70.0, 85.0, 90.0, 95.0),
    (120.0, 650.0, 90.0, 110.0, 120.0, 120.0),
)

_DEFAULT_EF = {
    "KDS": {"e_pct": 8.0, "f_side": 0.15},
    "AASHTO": {"e_pct": 6.0, "f_side": 0.14},
}


def criteria_defaults(standard: str, speed_kph: float, scale: float = 1.0):
    std = normalize_standard(standard)
    sc = max(1e-12, float(scale))

    if std == "AASHTO":
        base = _interp_by_speed(_AASHTO_TABLE, speed_kph)
    else:
        base = _interp_by_speed(_KDS_TABLE, speed_kph)

    ef = _DEFAULT_EF.get(std, _DEFAULT_EF[DEFAULT_STANDARD])
    r_ef = _radius_from_ef(speed_kph, ef["e_pct"], ef["f_side"])
    r_table = max(0.0, float(base.get("min_radius_m", 0.0)))
    r_m = max(r_table, r_ef)

    return {
        "standard": std,
        "e_default_pct": float(ef["e_pct"]),
        "f_default": float(ef["f_side"]),
        "min_radius": float(r_m * sc),
        "min_tangent": float(max(0.0, float(base.get("min_tangent_m", 0.0))) * sc),
        "min_transition": float(max(0.0, float(base.get("min_transition_m", 0.0))) * sc),
        "reverse_min_tangent": float(max(0.0, float(base.get("reverse_min_tangent_m", 0.0))) * sc),
        "reverse_min_transition": float(max(0.0, float(base.get("reverse_min_transition_m", 0.0))) * sc),
    }
