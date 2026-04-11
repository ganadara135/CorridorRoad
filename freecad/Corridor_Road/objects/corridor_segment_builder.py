# SPDX-FileNotice: Part of the Corridor Road addon.


def report_row(kind: str, **fields) -> str:
    parts = [str(kind or "").strip() or "row"]
    for key, value in fields.items():
        parts.append(f"{str(key)}={value}")
    return "|".join(parts)


def parse_report_row(row_text):
    parts = [str(p or "").strip() for p in str(row_text or "").split("|") if str(p or "").strip()]
    kind = str(parts[0] if parts else "row").strip() or "row"
    fields = {}
    for part in parts[1:]:
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        fields[str(key or "").strip()] = str(value or "").strip()
    return kind, fields


def dedupe_text_rows(rows):
    out = []
    seen = set()
    for row in list(rows or []):
        txt = str(row or "").strip()
        if not txt or txt in seen:
            continue
        seen.add(txt)
        out.append(txt)
    return out


def segment_ranges(count: int, boundaries):
    total = int(count or 0)
    if total < 2:
        return []
    idxs = sorted(set(int(i) for i in list(boundaries or []) if 0 < int(i) < total - 1))
    if not idxs:
        return [(0, total - 1)]
    out = []
    start = 0
    for idx in idxs:
        if idx - start >= 1:
            out.append((int(start), int(idx)))
        start = int(idx)
    if (total - 1) - start >= 1:
        out.append((int(start), int(total - 1)))
    return out


def skip_zone_keep_ranges(stations, skip_spans):
    vals = [float(v) for v in list(stations or [])]
    if len(vals) < 2:
        return [], [], []
    covered = [False] * len(vals)
    skipped_rows = []
    for lo, hi, mode in list(skip_spans or []):
        if str(mode or "").strip().lower() != "skip_zone":
            continue
        slo = float(min(lo, hi))
        shi = float(max(lo, hi))
        skipped_rows.append(f"{slo:.3f}-{shi:.3f}")
        for i, sta in enumerate(vals):
            if slo - 1e-6 <= sta <= shi + 1e-6:
                covered[i] = True
    if not any(covered):
        return [(0, len(vals) - 1)], [], []
    keep = []
    skip_runs = []
    i = 0
    while i < len(vals):
        while i < len(vals) and covered[i]:
            i += 1
        if i >= len(vals):
            break
        j = i
        while j + 1 < len(vals) and not covered[j + 1]:
            j += 1
        if j - i >= 1:
            keep.append((int(i), int(j)))
        i = j + 1
    i = 0
    while i < len(vals):
        if not covered[i]:
            i += 1
            continue
        j = i
        while j + 1 < len(vals) and covered[j + 1]:
            j += 1
        skip_runs.append((int(i), int(j)))
        i = j + 1
    dedup = dedupe_text_rows(skipped_rows)
    return keep, dedup, skip_runs


def skip_zone_boundary_summary(stations, skip_runs):
    vals = [float(v) for v in list(stations or [])]
    if len(vals) < 2:
        return "-", [], 0
    rows = []
    cap_count = 0
    for i0, i1 in list(skip_runs or []):
        if 0 <= int(i0) < len(vals):
            rows.append(f"SKIP_START:{vals[int(i0)]:.3f}")
            cap_count += 1
        if 0 <= int(i1) < len(vals):
            rows.append(f"SKIP_END:{vals[int(i1)]:.3f}")
            cap_count += 1
    if skip_runs:
        return "caps_deferred", dedupe_text_rows(rows), int(cap_count)
    return "-", [], 0


def build_segment_summary_rows(stations, segment_ranges_rows, source_tags=None, skipped_station_rows=None):
    vals = [float(v) for v in list(stations or [])]
    out = []
    tags = list(source_tags or [])
    skipped_lookup = set(str(v or "").strip() for v in list(skipped_station_rows or []))
    for idx, (i0, i1) in enumerate(list(segment_ranges_rows or []), start=1):
        if i0 < 0 or i1 >= len(vals) or i1 <= i0:
            continue
        lo = float(vals[int(i0)])
        hi = float(vals[int(i1)])
        out.append(
            report_row(
                "corridor_segment",
                id=f"SEG_{idx:03d}",
                order=int(idx),
                start=f"{lo:.3f}",
                end=f"{hi:.3f}",
                source="+".join(tags) if tags else "full",
                skipped=int(0),
            )
        )
    for idx, span in enumerate(list(skipped_lookup), start=1):
        out.append(report_row("corridor_skip", id=f"SKIP_{idx:03d}", span=str(span), source="skip_zone", skipped=1))
    return out


def summarize_segment_rows(rows):
    counts = {
        "segment_rows": 0,
        "skip_rows": 0,
        "full_segments": 0,
        "region_segments": 0,
        "structure_segments": 0,
        "notch_segments": 0,
        "mixed_segments": 0,
    }
    source_tokens = []
    for row_text in list(rows or []):
        kind, fields = parse_report_row(row_text)
        source_value = str(fields.get("source", "") or "").strip()
        tokens = [str(v or "").strip() for v in source_value.split("+") if str(v or "").strip()]
        for token in tokens:
            if token not in source_tokens:
                source_tokens.append(token)
        if kind == "corridor_skip":
            counts["skip_rows"] += 1
            continue
        if kind != "corridor_segment":
            continue
        counts["segment_rows"] += 1
        if not tokens or tokens == ["full"]:
            counts["full_segments"] += 1
            continue
        unique_tokens = sorted(set(tokens))
        if len(unique_tokens) >= 2:
            counts["mixed_segments"] += 1
            continue
        token = unique_tokens[0]
        if token == "region":
            counts["region_segments"] += 1
        elif token == "structure":
            counts["structure_segments"] += 1
        elif token == "notch":
            counts["notch_segments"] += 1
        else:
            counts["full_segments"] += 1

    def _summary(parts):
        rows = []
        for key, label in parts:
            value = int(counts.get(key, 0) or 0)
            if value > 0:
                rows.append(f"{label}={value}")
        return ", ".join(rows) if rows else "-"

    return {
        "counts": dict(counts),
        "source_tokens": list(source_tokens),
        "kind_summary": _summary(
            [
                ("segment_rows", "segment"),
                ("skip_rows", "skip"),
            ]
        ),
        "source_summary": _summary(
            [
                ("full_segments", "full"),
                ("region_segments", "region"),
                ("structure_segments", "structure"),
                ("notch_segments", "notch"),
                ("mixed_segments", "mixed"),
            ]
        ),
    }


def build_segment_package_rows(stations, segment_ranges_rows, summary_rows=None, point_count_hint: int = 0):
    vals = [float(v) for v in list(stations or [])]
    row_lookup = {}
    for row_text in list(summary_rows or []):
        kind, fields = parse_report_row(row_text)
        if kind != "corridor_segment":
            continue
        try:
            order = int(fields.get("order", "0") or 0)
        except Exception:
            order = 0
        if order > 0:
            row_lookup[order] = dict(fields)

    out = []
    point_count = max(0, int(point_count_hint or 0))
    for idx, (i0, i1) in enumerate(list(segment_ranges_rows or []), start=1):
        if i0 < 0 or i1 >= len(vals) or i1 <= i0:
            continue
        fields = dict(row_lookup.get(idx, {}) or {})
        pair_count = max(0, int(i1) - int(i0))
        expected_faces = 0
        if point_count >= 2 and pair_count >= 1:
            expected_faces = int(2 * pair_count * max(0, point_count - 1))
        out.append(
            report_row(
                "corridor_package",
                id=f"PKG_{idx:03d}",
                segmentId=str(fields.get("id", f"SEG_{idx:03d}") or f"SEG_{idx:03d}"),
                order=int(idx),
                start=f"{vals[int(i0)]:.3f}",
                end=f"{vals[int(i1)]:.3f}",
                stationCount=int(pair_count + 1),
                pairCount=int(pair_count),
                pointCount=int(point_count),
                expectedFaces=int(expected_faces),
                source=str(fields.get("source", "full") or "full"),
                build="strip_compound",
            )
        )
    return out


def attach_package_profile_contract(package_rows, profile_contract_source: str):
    source = str(profile_contract_source or "").strip() or "-"
    out = []
    for row_text in list(package_rows or []):
        kind, fields = parse_report_row(row_text)
        if kind != "corridor_package":
            out.append(str(row_text or ""))
            continue
        merged = dict(fields)
        merged["profileContract"] = source
        display_label = str(merged.get("displayLabel", "") or "").strip()
        display_summary = str(merged.get("displaySummary", display_label) or display_label).strip()
        if display_label:
            merged["displayLabel"] = f"{display_label}[{source}]"
        if display_summary:
            merged["displaySummary"] = f"{display_summary}|contract={source}"
        out.append(report_row(kind, **merged))
    return out


def resolve_segment_driver(record_rows, station_mid: float):
    best = None
    ss = float(station_mid or 0.0)
    for rec in list(record_rows or []):
        try:
            s0 = float(rec.get("ResolvedStartStation", 0.0) or 0.0)
            s1 = float(rec.get("ResolvedEndStation", 0.0) or 0.0)
        except Exception:
            continue
        lo = min(s0, s1) - 1e-6
        hi = max(s0, s1) + 1e-6
        if ss < lo or ss > hi:
            continue
        if best is None:
            best = dict(rec)
            continue
        best_span = abs(float(best.get("ResolvedEndStation", 0.0) or 0.0) - float(best.get("ResolvedStartStation", 0.0) or 0.0))
        cur_span = abs(float(s1) - float(s0))
        if cur_span < best_span - 1e-9:
            best = dict(rec)
    return dict(best or {})


def attach_segment_drivers(package_rows, driver_records):
    out = []
    for row_text in list(package_rows or []):
        kind, fields = parse_report_row(row_text)
        if kind != "corridor_package":
            out.append(str(row_text or ""))
            continue
        try:
            s0 = float(fields.get("start", "0") or 0.0)
            s1 = float(fields.get("end", "0") or 0.0)
        except Exception:
            out.append(str(row_text or ""))
            continue
        mid = 0.5 * (s0 + s1)
        driver = resolve_segment_driver(driver_records, mid)
        if driver:
            fields["driverId"] = str(driver.get("Id", "") or "-")
            fields["driverMode"] = str(driver.get("ResolvedCorridorMode", "") or "-")
            fields["driverSource"] = str(driver.get("ResolvedStationSource", driver.get("Type", "")) or "-")
            fields["driverStart"] = f"{float(driver.get('ResolvedStartStation', s0) or s0):.3f}"
            fields["driverEnd"] = f"{float(driver.get('ResolvedEndStation', s1) or s1):.3f}"
        else:
            fields["driverId"] = "-"
            fields["driverMode"] = "-"
            fields["driverSource"] = "full"
            fields["driverStart"] = f"{s0:.3f}"
            fields["driverEnd"] = f"{s1:.3f}"
        driver_src = str(fields.get("driverSource", "full") or "full")
        driver_id = str(fields.get("driverId", "-") or "-")
        driver_mode = str(fields.get("driverMode", "-") or "-")
        fields["displayLabel"] = f"{driver_src}:{driver_id}:{driver_mode}"
        fields["displaySummary"] = f"{driver_src}:{driver_id}:{driver_mode}@{s0:.3f}-{s1:.3f}"
        out.append(report_row(kind, **fields))
    return out


def summarize_segment_packages(rows):
    source_counts = {}
    mode_counts = {}
    profile_contract_counts = {}
    package_count = 0
    for row_text in list(rows or []):
        kind, fields = parse_report_row(row_text)
        if kind != "corridor_package":
            continue
        package_count += 1
        src = str(fields.get("driverSource", fields.get("source", "full")) or "full").strip() or "full"
        mode = str(fields.get("driverMode", "-") or "-").strip() or "-"
        profile_contract = str(fields.get("profileContract", "-") or "-").strip() or "-"
        source_counts[src] = int(source_counts.get(src, 0) or 0) + 1
        mode_counts[mode] = int(mode_counts.get(mode, 0) or 0) + 1
        profile_contract_counts[profile_contract] = int(profile_contract_counts.get(profile_contract, 0) or 0) + 1

    def _summary(counts):
        if not counts:
            return "-"
        parts = []
        for key in sorted(counts):
            parts.append(f"{key}={int(counts[key])}")
        return ", ".join(parts) if parts else "-"

    package_summary = "-"
    src_summary = _summary(source_counts)
    mode_summary = _summary(mode_counts)
    contract_summary = _summary(profile_contract_counts)
    summary_parts = []
    if src_summary != "-":
        summary_parts.append(f"src[{src_summary}]")
    if mode_summary != "-":
        summary_parts.append(f"mode[{mode_summary}]")
    if contract_summary != "-":
        summary_parts.append(f"contract[{contract_summary}]")
    if summary_parts:
        package_summary = " ".join(summary_parts)

    return {
        "package_count": int(package_count),
        "driver_source_summary": src_summary,
        "driver_mode_summary": mode_summary,
        "profile_contract_summary": contract_summary,
        "package_summary": package_summary,
        "driver_source_counts": dict(source_counts),
        "driver_mode_counts": dict(mode_counts),
        "profile_contract_counts": dict(profile_contract_counts),
        "display_summary": summarize_segment_display(rows),
    }


def summarize_segment_display(rows, limit: int = 3):
    labels = []
    for row_text in list(rows or []):
        kind, fields = parse_report_row(row_text)
        if kind != "corridor_package":
            continue
        label = str(fields.get("displaySummary", fields.get("displayLabel", "")) or "").strip()
        if label and label not in labels:
            labels.append(label)
    if not labels:
        return "-"
    if len(labels) <= int(limit):
        return "; ".join(labels)
    head = labels[: int(limit)]
    return f"{'; '.join(head)}; ... ({len(labels)} packages)"


def resolve_segment_plan(
    stations,
    structure_split_idx=None,
    structure_split_rows=None,
    region_split_idx=None,
    region_split_rows=None,
    notch_split_idx=None,
    notch_split_rows=None,
    corridor_spans=None,
    driver_records=None,
):
    split_idx = list(structure_split_idx or []) + list(region_split_idx or []) + list(notch_split_idx or [])
    split_rows = dedupe_text_rows(list(structure_split_rows or []) + list(region_split_rows or []) + list(notch_split_rows or []))
    ranges = segment_ranges(len(list(stations or [])), split_idx)
    split_count = len(ranges) if ranges else 0
    use_segmented_ranges = bool(ranges and len(ranges) >= 2)

    skip_ranges, skipped_station_rows, skip_runs = skip_zone_keep_ranges(stations, corridor_spans)
    skip_boundary_behavior, skip_boundary_rows, skip_boundary_cap_count = skip_zone_boundary_summary(stations, skip_runs)
    if skip_ranges:
        ranges = list(skip_ranges)
        split_count = len(ranges) if ranges else 0
        use_segmented_ranges = bool(
            ranges and not (len(ranges) == 1 and ranges[0] == (0, len(list(stations or [])) - 1))
        )
    source_tags = []
    if structure_split_idx:
        source_tags.append("structure")
    if region_split_idx:
        source_tags.append("region")
    if notch_split_idx:
        source_tags.append("notch")
    summary_rows = build_segment_summary_rows(
        stations,
        ranges,
        source_tags=source_tags,
        skipped_station_rows=skipped_station_rows,
    )
    package_rows = build_segment_package_rows(stations, ranges, summary_rows=summary_rows)
    package_rows = attach_segment_drivers(package_rows, driver_records)
    return {
        "split_indices": list(split_idx),
        "split_rows": list(split_rows),
        "ranges": list(ranges),
        "split_count": int(split_count),
        "use_segmented_ranges": bool(use_segmented_ranges),
        "skipped_station_rows": list(skipped_station_rows),
        "skip_runs": list(skip_runs),
        "skip_boundary_behavior": str(skip_boundary_behavior or "-"),
        "skip_boundary_rows": list(skip_boundary_rows),
        "skip_boundary_cap_count": int(skip_boundary_cap_count),
        "summary_rows": list(summary_rows),
        "package_rows": list(package_rows),
    }
