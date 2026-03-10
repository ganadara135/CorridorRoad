import csv


def _norm_key(s: str) -> str:
    t = str(s or "").strip().lower()
    for ch in (" ", "_", "-", "/", "\\", "(", ")", "[", "]"):
        t = t.replace(ch, "")
    return t


_ALIASES_X = {
    "x",
    "e",
    "east",
    "easting",
    "xm",
    "em",
    "xcoord",
    "xcoordinate",
}
_ALIASES_Y = {
    "y",
    "n",
    "north",
    "northing",
    "ym",
    "nm",
    "ycoord",
    "ycoordinate",
}
_ALIASES_R = {
    "r",
    "radius",
    "radiusm",
    "curveradius",
    "horizontalradius",
}
_ALIASES_LS = {
    "ls",
    "transitionls",
    "transitionlsm",
    "transitionl",
    "transitionlength",
    "transitionlengthm",
    "spirallength",
}
_ALIASES_STA = {
    "sta",
    "station",
    "stationm",
    "stationmeter",
    "chainage",
    "chain",
}


def _parse_float(token):
    txt = str(token or "").strip()
    if txt == "":
        return None
    return float(txt)


def _read_text_with_fallback(path: str):
    encodings = ("utf-8-sig", "cp949", "utf-8", "latin-1")
    last_err = None
    for enc in encodings:
        try:
            with open(path, "r", encoding=enc, newline="") as f:
                return f.read(), enc
        except Exception as ex:
            last_err = ex
    raise ValueError(f"Failed to read CSV file: {last_err}")


def _read_text_with_option(path: str, encoding_opt: str):
    enc = str(encoding_opt or "auto").strip().lower()
    if enc in ("", "auto"):
        return _read_text_with_fallback(path)
    try:
        with open(path, "r", encoding=enc, newline="") as f:
            return f.read(), enc
    except Exception as ex:
        raise ValueError(f"Failed to read CSV with encoding '{enc}': {ex}")


def _detect_delimiter(sample_text: str) -> str:
    try:
        s = csv.Sniffer()
        d = s.sniff(sample_text, delimiters=",;\t|")
        return str(getattr(d, "delimiter", ",") or ",")
    except Exception:
        pass
    if "\t" in sample_text:
        return "\t"
    if ";" in sample_text:
        return ";"
    if "|" in sample_text:
        return "|"
    return ","


def _normalize_delimiter_option(delimiter_opt: str):
    d = str(delimiter_opt or "auto")
    if d in ("", "auto", "Auto"):
        return "auto"
    if d in (",", ";", "\t", "|"):
        return d
    key = d.strip().lower()
    if key in ("comma", ","):
        return ","
    if key in ("semicolon", ";"):
        return ";"
    if key in ("tab", "\\t", "t"):
        return "\t"
    if key in ("pipe", "|"):
        return "|"
    return "auto"


def _normalize_header_option(has_header_opt):
    if isinstance(has_header_opt, bool):
        return "yes" if has_header_opt else "no"
    s = str(has_header_opt or "auto").strip().lower()
    if s in ("yes", "y", "true", "1"):
        return "yes"
    if s in ("no", "n", "false", "0"):
        return "no"
    return "auto"


def _is_probable_header(row):
    if not row:
        return False
    hit_alias = False
    for tok in row:
        k = _norm_key(tok)
        if k in _ALIASES_X or k in _ALIASES_Y or k in _ALIASES_R or k in _ALIASES_LS or k in _ALIASES_STA:
            hit_alias = True
        try:
            _ = float(str(tok).strip())
        except Exception:
            return True
    return hit_alias


def _build_col_map(header):
    col_x = -1
    col_y = -1
    col_r = -1
    col_ls = -1
    col_sta = -1
    for i, h in enumerate(header):
        k = _norm_key(h)
        if col_x < 0 and k in _ALIASES_X:
            col_x = i
            continue
        if col_y < 0 and k in _ALIASES_Y:
            col_y = i
            continue
        if col_r < 0 and k in _ALIASES_R:
            col_r = i
            continue
        if col_ls < 0 and k in _ALIASES_LS:
            col_ls = i
            continue
        if col_sta < 0 and k in _ALIASES_STA:
            col_sta = i
            continue
    if col_x < 0 or col_y < 0:
        raise ValueError("CSV header must include X/Y (or E/N) columns.")
    return {
        "x": col_x,
        "y": col_y,
        "r": col_r,
        "ls": col_ls,
        "sta": col_sta,
    }


def _parse_mapping(mapping, cols_count: int):
    if mapping is None:
        return None
    if not isinstance(mapping, dict):
        raise ValueError("CSV mapping must be a dictionary or None.")

    def _idx(name, default=-1):
        v = mapping.get(name, default)
        if v is None:
            return -1
        try:
            i = int(v)
        except Exception:
            return -1
        if i < 0:
            return -1
        if cols_count > 0 and i >= cols_count:
            return -1
        return i

    out = {
        "x": _idx("x", -1),
        "y": _idx("y", -1),
        "r": _idx("r", -1),
        "ls": _idx("ls", -1),
        "sta": _idx("sta", -1),
    }
    if out["x"] < 0 or out["y"] < 0:
        raise ValueError("CSV mapping requires valid X/Y column indices.")
    return out


def inspect_alignment_csv(path: str, encoding: str = "auto", delimiter: str = "auto"):
    if str(path or "").strip() == "":
        raise ValueError("CSV file path is empty.")

    text, used_encoding = _read_text_with_option(path, encoding_opt=encoding)
    delim_opt = _normalize_delimiter_option(delimiter)
    used_delim = _detect_delimiter(text[:4096]) if delim_opt == "auto" else delim_opt

    rows_raw = []
    for row in csv.reader(text.splitlines(), delimiter=used_delim):
        cells = [str(c or "").strip() for c in row]
        if not cells:
            continue
        if len(cells) == 1 and cells[0] == "":
            continue
        if str(cells[0]).startswith("#"):
            continue
        rows_raw.append(cells)

    if not rows_raw:
        raise ValueError("CSV has no data rows.")

    guessed_header = _is_probable_header(rows_raw[0])
    if guessed_header:
        columns = list(rows_raw[0])
        try:
            guess = _build_col_map(columns)
        except Exception:
            guess = {"x": 0, "y": 1, "r": 2, "ls": 3, "sta": -1}
        sample_rows = rows_raw[1:6]
    else:
        ncols = max(len(r) for r in rows_raw)
        columns = [f"col{i}" for i in range(ncols)]
        guess = {"x": 0, "y": 1, "r": 2, "ls": 3, "sta": -1}
        sample_rows = rows_raw[:5]

    if "sta" not in guess:
        guess["sta"] = -1

    return {
        "columns": columns,
        "sample_rows": sample_rows,
        "delimiter": used_delim,
        "encoding": used_encoding,
        "header_guess": guessed_header,
        "guess_mapping": guess,
        "row_count": len(rows_raw),
    }


def read_alignment_csv(
    path: str,
    encoding: str = "auto",
    delimiter: str = "auto",
    has_header="auto",
    mapping=None,
    sort_mode: str = "input",
    drop_consecutive_duplicates: bool = False,
    clamp_negative: bool = False,
    enforce_endpoints: bool = False,
):
    if str(path or "").strip() == "":
        raise ValueError("CSV file path is empty.")

    text, used_encoding = _read_text_with_option(path, encoding_opt=encoding)
    delim_opt = _normalize_delimiter_option(delimiter)
    delim = _detect_delimiter(text[:4096]) if delim_opt == "auto" else delim_opt
    rows_raw = []
    for row in csv.reader(text.splitlines(), delimiter=delim):
        cells = [str(c or "").strip() for c in row]
        if not cells:
            continue
        if len(cells) == 1 and cells[0] == "":
            continue
        if str(cells[0]).startswith("#"):
            continue
        rows_raw.append(cells)

    if not rows_raw:
        raise ValueError("CSV has no data rows.")

    header = None
    data_start = 0
    hdr_opt = _normalize_header_option(has_header)
    if hdr_opt == "yes":
        header = rows_raw[0]
        data_start = 1
        cmap = _parse_mapping(mapping, cols_count=len(header)) if mapping is not None else _build_col_map(header)
    elif hdr_opt == "no":
        ncols = max(len(r) for r in rows_raw)
        cmap = _parse_mapping(mapping, cols_count=ncols) if mapping is not None else {"x": 0, "y": 1, "r": 2, "ls": 3, "sta": -1}
    elif _is_probable_header(rows_raw[0]):
        header = rows_raw[0]
        data_start = 1
        cmap = _parse_mapping(mapping, cols_count=len(header)) if mapping is not None else _build_col_map(header)
    else:
        ncols = max(len(r) for r in rows_raw)
        cmap = _parse_mapping(mapping, cols_count=ncols) if mapping is not None else {"x": 0, "y": 1, "r": 2, "ls": 3, "sta": -1}

    out = []
    skipped = 0
    skip_reasons = []
    sta_vals = []

    for ridx, row in enumerate(rows_raw[data_start:], start=(data_start + 1)):
        try:
            xi = cmap["x"]
            yi = cmap["y"]
            if xi >= len(row) or yi >= len(row):
                skipped += 1
                if len(skip_reasons) < 5:
                    skip_reasons.append(f"row {ridx}: missing X/Y column")
                continue

            xv = _parse_float(row[xi])
            yv = _parse_float(row[yi])
            if xv is None or yv is None:
                skipped += 1
                if len(skip_reasons) < 5:
                    skip_reasons.append(f"row {ridx}: invalid X/Y")
                continue

            rr = 0.0
            li = int(cmap.get("r", -1))
            if li >= 0 and li < len(row):
                try:
                    rv = _parse_float(row[li])
                    rr = float(rv) if rv is not None else 0.0
                except Exception:
                    rr = 0.0

            ls = 0.0
            ti = int(cmap.get("ls", -1))
            if ti >= 0 and ti < len(row):
                try:
                    lv = _parse_float(row[ti])
                    ls = float(lv) if lv is not None else 0.0
                except Exception:
                    ls = 0.0

            si = int(cmap.get("sta", -1))
            sta = None
            if si >= 0 and si < len(row):
                try:
                    sv = _parse_float(row[si])
                    sta = float(sv) if sv is not None else None
                except Exception:
                    sta = None

            if clamp_negative:
                rr = max(0.0, float(rr))
                ls = max(0.0, float(ls))

            out.append((float(xv), float(yv), float(rr), float(ls)))
            sta_vals.append(sta)
        except Exception:
            skipped += 1
            if len(skip_reasons) < 5:
                skip_reasons.append(f"row {ridx}: parse error")

    smode = str(sort_mode or "input").strip().lower()
    if smode in ("sta", "station"):
        zipped = list(zip(out, sta_vals))
        # Keep non-station rows at the end in original relative order.
        zipped.sort(key=lambda z: (1 if z[1] is None else 0, float(z[1]) if z[1] is not None else 0.0))
        out = [z[0] for z in zipped]
    elif smode in ("xy", "x/y", "x", "y"):
        out = sorted(out, key=lambda t: (float(t[0]), float(t[1])))

    if drop_consecutive_duplicates:
        ded = []
        tol = 1e-9
        for row in out:
            if not ded:
                ded.append(row)
                continue
            dx = float(row[0]) - float(ded[-1][0])
            dy = float(row[1]) - float(ded[-1][1])
            if (dx * dx + dy * dy) <= tol:
                continue
            ded.append(row)
        out = ded

    if enforce_endpoints and len(out) >= 2:
        out = list(out)
        x0, y0, _r0, _l0 = out[0]
        x1, y1, _r1, _l1 = out[-1]
        out[0] = (float(x0), float(y0), 0.0, 0.0)
        out[-1] = (float(x1), float(y1), 0.0, 0.0)

    if len(out) < 2:
        raise ValueError("CSV must contain at least 2 valid rows with X/Y.")

    return {
        "rows": out,
        "loaded": len(out),
        "skipped": skipped,
        "skip_reasons": skip_reasons,
        "delimiter": delim,
        "encoding": used_encoding,
        "header": header is not None,
        "mapping": cmap,
    }


def write_alignment_csv(
    path: str,
    rows,
    x_header: str = "X",
    y_header: str = "Y",
    delimiter: str = ",",
    encoding: str = "utf-8-sig",
    include_header: bool = True,
):
    if str(path or "").strip() == "":
        raise ValueError("CSV file path is empty.")

    delim = _normalize_delimiter_option(delimiter)
    if delim == "auto":
        delim = ","

    enc = str(encoding or "utf-8-sig").strip().lower()
    if enc in ("", "auto"):
        enc = "utf-8-sig"

    written = 0
    with open(path, "w", encoding=enc, newline="") as f:
        w = csv.writer(f, delimiter=delim)
        if include_header:
            w.writerow([str(x_header), str(y_header), "Radius", "TransitionLs"])
        for row in list(rows or []):
            if row is None:
                continue
            vals = list(row)
            if len(vals) < 2:
                continue
            x = float(vals[0])
            y = float(vals[1])
            r = float(vals[2]) if len(vals) >= 3 else 0.0
            ls = float(vals[3]) if len(vals) >= 4 else 0.0
            w.writerow([x, y, r, ls])
            written += 1

    return {
        "path": str(path),
        "written": int(written),
        "delimiter": str(delim),
        "encoding": str(enc),
        "header": bool(include_header),
    }
