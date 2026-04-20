# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

QUALITY_PRESETS = ("Fast", "Balanced", "Precise", "Custom")


def build_quality_presets(scale: float, max_samples_by_name):
    sc = float(scale)
    max_samples_by_name = dict(max_samples_by_name or {})
    return {
        "Fast": {
            "cell": 2.0 * sc,
            "max_samples": int(max_samples_by_name.get("Fast", 120000)),
            "max_tri_src": 80000,
            "max_cand": 1200,
            "max_checks": 120000000,
        },
        "Balanced": {
            "cell": 1.0 * sc,
            "max_samples": int(max_samples_by_name.get("Balanced", 200000)),
            "max_tri_src": 150000,
            "max_cand": 2500,
            "max_checks": 250000000,
        },
        "Precise": {
            "cell": 0.5 * sc,
            "max_samples": int(max_samples_by_name.get("Precise", 500000)),
            "max_tri_src": 300000,
            "max_cand": 4000,
            "max_checks": 600000000,
        },
    }


def get_preset_values(presets, name: str):
    return dict(presets or {}).get(str(name), None)


def apply_preset_to_widgets(vals, spin_cell, spin_max_samples, spin_max_tri_src, spin_max_cand, spin_max_checks):
    if vals is None:
        return
    spin_cell.setValue(float(vals["cell"]))
    spin_max_samples.setValue(int(vals["max_samples"]))
    spin_max_tri_src.setValue(int(vals["max_tri_src"]))
    spin_max_cand.setValue(int(vals["max_cand"]))
    spin_max_checks.setValue(int(vals["max_checks"]))


def guess_preset_name(presets, cell, max_samples, max_tri, max_cand, max_checks, scale: float):
    for name in ("Fast", "Balanced", "Precise"):
        vals = get_preset_values(presets, name)
        if vals is None:
            continue
        if (
            abs(float(cell) - float(vals["cell"])) <= max(1e-6, 1e-3 * float(scale))
            and int(max_samples) == int(vals["max_samples"])
            and int(max_tri) == int(vals["max_tri_src"])
            and int(max_cand) == int(vals["max_cand"])
            and int(max_checks) == int(vals["max_checks"])
        ):
            return name
    return "Custom"


def estimate_triangle_checks(est_samples, cell, area, tri_a, tri_b, max_cand):
    if est_samples is None:
        return None
    area = max(1e-9, float(area))
    tri_sum = float(max(1, int(tri_a) + int(tri_b)))
    cand = 9.0 * float(cell) * float(cell) * tri_sum / area
    cand = min(float(max(1, 2 * int(max_cand))), max(1.0, cand))
    return int(float(est_samples) * cand)


def update_estimate_label(label, est_samples, est_checks, max_samples, max_checks, empty_text: str):
    if est_samples is None:
        label.setText(str(empty_text))
        label.setStyleSheet("")
        return
    max_s = int(max_samples)
    max_c = int(max_checks)
    warn = (int(est_samples) > max_s) or (est_checks is not None and int(est_checks) > max_c)
    checks_txt = "-" if est_checks is None else f"{int(est_checks):,}"
    label.setText(f"samples ~ {int(est_samples):,} / limit {max_s:,}, triangle checks ~ {checks_txt} / limit {max_c:,}")
    label.setStyleSheet("color:#b71c1c;" if warn else "")
