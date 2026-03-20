# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

import csv
import math
import os
from collections import defaultdict

import FreeCAD as App

from freecad.Corridor_Road.objects.obj_project import get_length_scale, local_to_world, world_to_local

_RECOMP_LABEL_SUFFIX = " [Recompute]"


class _CanceledError(Exception):
    pass


def _empty_mesh():
    try:
        import Mesh

        return Mesh.Mesh()
    except Exception:
        return None


def _mark_recompute_flag(obj, needed: bool):
    try:
        if hasattr(obj, "NeedsRecompute"):
            obj.NeedsRecompute = bool(needed)
    except Exception:
        pass

    try:
        label = str(getattr(obj, "Label", "") or "")
        if bool(needed):
            if _RECOMP_LABEL_SUFFIX not in label:
                obj.Label = f"{label}{_RECOMP_LABEL_SUFFIX}"
        else:
            if _RECOMP_LABEL_SUFFIX in label:
                obj.Label = label.replace(_RECOMP_LABEL_SUFFIX, "")
    except Exception:
        pass


def ensure_pointcloud_dem_properties(obj):
    scale = get_length_scale(getattr(obj, "Document", None), default=1.0)

    if not hasattr(obj, "CsvPath"):
        obj.addProperty("App::PropertyString", "CsvPath", "Source", "CSV file path (UTM E/N/Z)")
        obj.CsvPath = ""
    if not hasattr(obj, "Delimiter"):
        obj.addProperty("App::PropertyEnumeration", "Delimiter", "Source", "CSV delimiter mode")
        obj.Delimiter = ["Auto", "Comma", "Semicolon", "Tab", "Pipe"]
        obj.Delimiter = "Auto"
    if not hasattr(obj, "HasHeader"):
        obj.addProperty("App::PropertyBool", "HasHeader", "Source", "CSV has header row")
        obj.HasHeader = True
    if not hasattr(obj, "InputCoords"):
        obj.addProperty("App::PropertyEnumeration", "InputCoords", "Source", "Input coordinate system")
        obj.InputCoords = ["World", "Local"]
        obj.InputCoords = "World"
    if not hasattr(obj, "OutputCoords"):
        obj.addProperty("App::PropertyEnumeration", "OutputCoords", "Source", "Output mesh coordinate system")
        obj.OutputCoords = ["Local", "World"]
        obj.OutputCoords = "Local"

    if not hasattr(obj, "CellSize"):
        obj.addProperty("App::PropertyFloat", "CellSize", "DEM", "DEM cell size (m)")
        obj.CellSize = 4.0 * scale
    if not hasattr(obj, "Aggregation"):
        obj.addProperty("App::PropertyEnumeration", "Aggregation", "DEM", "Cell Z aggregation method")
        obj.Aggregation = ["Mean", "Median", "Min", "Max"]
        obj.Aggregation = "Mean"
    if not hasattr(obj, "MaxCells"):
        obj.addProperty("App::PropertyInteger", "MaxCells", "DEM", "Maximum estimated DEM cells")
        obj.MaxCells = 2000000

    if not hasattr(obj, "AutoUpdate"):
        obj.addProperty("App::PropertyBool", "AutoUpdate", "DEM", "Auto update from property changes")
        obj.AutoUpdate = True
    if not hasattr(obj, "RebuildNow"):
        obj.addProperty("App::PropertyBool", "RebuildNow", "DEM", "Set True to force rebuild now")
        obj.RebuildNow = False
    if not hasattr(obj, "NeedsRecompute"):
        obj.addProperty("App::PropertyBool", "NeedsRecompute", "Result", "Marked when source updates require recompute")
        obj.NeedsRecompute = False

    if not hasattr(obj, "PointCountRaw"):
        obj.addProperty("App::PropertyInteger", "PointCountRaw", "Result", "Raw CSV row count (data rows)")
        obj.PointCountRaw = 0
    if not hasattr(obj, "PointCountUsed"):
        obj.addProperty("App::PropertyInteger", "PointCountUsed", "Result", "Valid point count used")
        obj.PointCountUsed = 0
    if not hasattr(obj, "SkippedRows"):
        obj.addProperty("App::PropertyInteger", "SkippedRows", "Result", "Skipped/invalid row count")
        obj.SkippedRows = 0
    if not hasattr(obj, "GridNX"):
        obj.addProperty("App::PropertyInteger", "GridNX", "Result", "Estimated grid width (cells)")
        obj.GridNX = 0
    if not hasattr(obj, "GridNY"):
        obj.addProperty("App::PropertyInteger", "GridNY", "Result", "Estimated grid height (cells)")
        obj.GridNY = 0
    if not hasattr(obj, "NoDataCount"):
        obj.addProperty("App::PropertyInteger", "NoDataCount", "Result", "No-data cell count")
        obj.NoDataCount = 0
    if not hasattr(obj, "ZMin"):
        obj.addProperty("App::PropertyFloat", "ZMin", "Result", "Minimum DEM elevation")
        obj.ZMin = 0.0
    if not hasattr(obj, "ZMax"):
        obj.addProperty("App::PropertyFloat", "ZMax", "Result", "Maximum DEM elevation")
        obj.ZMax = 0.0
    if not hasattr(obj, "Status"):
        obj.addProperty("App::PropertyString", "Status", "Result", "Execution status")
        obj.Status = "Idle"


class PointCloudDEM:
    def __init__(self, obj):
        obj.Proxy = self
        self.Type = "PointCloudDEM"
        self._bulk_updating = False
        self._progress_cb = None
        ensure_pointcloud_dem_properties(obj)

    def _report_progress(self, pct: float, message: str = "") -> bool:
        cb = getattr(self, "_progress_cb", None)
        if cb is None:
            return False
        try:
            p = max(0.0, min(100.0, float(pct)))
            return bool(cb(p, str(message or "")))
        except Exception:
            return False

    @staticmethod
    def _delimiter_char(mode: str):
        t = str(mode or "Auto")
        if t == "Comma":
            return ","
        if t == "Semicolon":
            return ";"
        if t == "Tab":
            return "\t"
        if t == "Pipe":
            return "|"
        return None

    @staticmethod
    def _norm_col(name: str) -> str:
        return "".join(ch for ch in str(name or "").strip().lower() if ch.isalnum())

    @staticmethod
    def _resolve_columns(fieldnames):
        cols = list(fieldnames or [])
        by_norm = {PointCloudDEM._norm_col(c): c for c in cols}
        aliases = {
            "e": ("easting", "e", "x", "utme"),
            "n": ("northing", "n", "y", "utmn"),
            "z": ("elevation", "z", "height", "rl"),
        }
        out = {}
        for key, cand in aliases.items():
            hit = None
            for a in cand:
                k = PointCloudDEM._norm_col(a)
                if k in by_norm:
                    hit = by_norm[k]
                    break
            out[key] = hit
        return out

    @staticmethod
    def _count_lines(path: str) -> int:
        n = 0
        with open(path, "r", encoding="utf-8-sig", errors="ignore", newline="") as f:
            for _ in f:
                n += 1
        return int(n)

    @staticmethod
    def _sniff_delimiter(path: str):
        with open(path, "r", encoding="utf-8-sig", errors="ignore", newline="") as f:
            sample = f.read(4096)
        if not sample:
            return ","
        try:
            d = csv.Sniffer().sniff(sample, delimiters=",;\t|").delimiter
            if d:
                return d
        except Exception:
            pass
        return ","

    def _read_points(self, obj, path: str, delimiter_mode: str, has_header: bool, input_coords: str, output_coords: str):
        delim = self._delimiter_char(delimiter_mode)
        if delim is None:
            delim = self._sniff_delimiter(path)

        total_lines = self._count_lines(path)
        total_rows = max(1, total_lines - (1 if has_header else 0))

        points = []
        raw = 0
        skipped = 0

        with open(path, "r", encoding="utf-8-sig", errors="ignore", newline="") as f:
            if has_header:
                rdr = csv.DictReader(f, delimiter=delim)
                mapping = self._resolve_columns(rdr.fieldnames)
                ck_e = mapping.get("e", None)
                ck_n = mapping.get("n", None)
                ck_z = mapping.get("z", None)
                if (not ck_e) or (not ck_n) or (not ck_z):
                    raise Exception("Missing required columns. Need easting/northing/elevation (or aliases).")

                for i, row in enumerate(rdr, start=1):
                    raw += 1
                    try:
                        e = float(str(row.get(ck_e, "")).strip())
                        n = float(str(row.get(ck_n, "")).strip())
                        z = float(str(row.get(ck_z, "")).strip())
                        if (not math.isfinite(e)) or (not math.isfinite(n)) or (not math.isfinite(z)):
                            raise Exception("non-finite")
                        in_world = str(input_coords or "World") == "World"
                        out_world = str(output_coords or "Local") == "World"
                        if in_world and (not out_world):
                            x, y, zz = world_to_local(obj, e, n, z)
                        elif (not in_world) and out_world:
                            x, y, zz = local_to_world(obj, e, n, z)
                        else:
                            x, y, zz = e, n, z
                        points.append((float(x), float(y), float(zz)))
                    except Exception:
                        skipped += 1

                    if (i % 2000) == 0:
                        pct = 5.0 + 35.0 * (float(i) / float(total_rows))
                        if self._report_progress(pct, f"Reading CSV rows: {i}/{total_rows}"):
                            raise _CanceledError("Canceled by user.")
            else:
                rdr = csv.reader(f, delimiter=delim)
                for i, row in enumerate(rdr, start=1):
                    raw += 1
                    try:
                        if len(row) < 3:
                            raise Exception("too few columns")
                        e = float(str(row[0]).strip())
                        n = float(str(row[1]).strip())
                        z = float(str(row[2]).strip())
                        if (not math.isfinite(e)) or (not math.isfinite(n)) or (not math.isfinite(z)):
                            raise Exception("non-finite")
                        in_world = str(input_coords or "World") == "World"
                        out_world = str(output_coords or "Local") == "World"
                        if in_world and (not out_world):
                            x, y, zz = world_to_local(obj, e, n, z)
                        elif (not in_world) and out_world:
                            x, y, zz = local_to_world(obj, e, n, z)
                        else:
                            x, y, zz = e, n, z
                        points.append((float(x), float(y), float(zz)))
                    except Exception:
                        skipped += 1

                    if (i % 2000) == 0:
                        pct = 5.0 + 35.0 * (float(i) / float(total_rows))
                        if self._report_progress(pct, f"Reading CSV rows: {i}/{total_rows}"):
                            raise _CanceledError("Canceled by user.")

        return points, int(raw), int(skipped)

    @staticmethod
    def _grid_index(x: float, y: float, xmin: float, ymin: float, cell: float):
        ix = int(math.floor((float(x) - float(xmin)) / float(cell)))
        iy = int(math.floor((float(y) - float(ymin)) / float(cell)))
        return ix, iy

    @staticmethod
    def _cell_center(ix: int, iy: int, xmin: float, ymin: float, cell: float):
        x = float(xmin) + (float(ix) + 0.5) * float(cell)
        y = float(ymin) + (float(iy) + 0.5) * float(cell)
        return x, y

    def execute(self, obj):
        ensure_pointcloud_dem_properties(obj)
        try:
            if self._report_progress(1.0, "Preparing PointCloud DEM"):
                raise _CanceledError("Canceled by user.")

            path = str(getattr(obj, "CsvPath", "") or "").strip()
            if not path:
                raise Exception("CsvPath is empty.")
            if not os.path.isfile(path):
                raise Exception(f"CSV file not found: {path}")

            scale = get_length_scale(getattr(obj, "Document", None), default=1.0)
            cell = float(getattr(obj, "CellSize", 4.0 * scale))
            min_cell = 0.2 * scale
            if (not math.isfinite(cell)) or cell < min_cell:
                cell = float(min_cell)
                obj.CellSize = float(min_cell)

            max_cells = int(getattr(obj, "MaxCells", 2000000))
            if max_cells <= 0:
                max_cells = 2000000
                obj.MaxCells = max_cells

            delim_mode = str(getattr(obj, "Delimiter", "Auto") or "Auto")
            has_header = bool(getattr(obj, "HasHeader", True))
            input_coords = str(getattr(obj, "InputCoords", "World") or "World")
            output_coords = str(getattr(obj, "OutputCoords", "Local") or "Local")
            agg_mode = str(getattr(obj, "Aggregation", "Mean") or "Mean")

            if self._report_progress(3.0, "Reading CSV"):
                raise _CanceledError("Canceled by user.")
            pts, raw_count, skipped = self._read_points(obj, path, delim_mode, has_header, input_coords, output_coords)
            if not pts:
                raise Exception("No valid points were parsed from CSV.")

            xmin = min(p[0] for p in pts)
            xmax = max(p[0] for p in pts)
            ymin = min(p[1] for p in pts)
            ymax = max(p[1] for p in pts)
            if (xmax - xmin) <= 1e-12 or (ymax - ymin) <= 1e-12:
                raise Exception("Point XY bounds are degenerate.")

            nx = int(math.floor((xmax - xmin) / cell)) + 1
            ny = int(math.floor((ymax - ymin) / cell)) + 1
            est_cells = int(max(1, nx) * max(1, ny))
            if est_cells > max_cells:
                raise Exception(f"Estimated cells {est_cells} exceed MaxCells {max_cells}. Increase CellSize.")

            if self._report_progress(45.0, "Aggregating points into DEM cells"):
                raise _CanceledError("Canceled by user.")

            if agg_mode == "Mean":
                accum = {}
                npt = max(1, int(len(pts)))
                for i, (x, y, z) in enumerate(pts, start=1):
                    k = self._grid_index(x, y, xmin, ymin, cell)
                    s, c = accum.get(k, (0.0, 0))
                    accum[k] = (float(s) + float(z), int(c) + 1)
                    if (i % 5000) == 0:
                        pct = 45.0 + 30.0 * (float(i) / float(npt))
                        if self._report_progress(pct, f"Aggregating points: {i}/{npt}"):
                            raise _CanceledError("Canceled by user.")
                z_cells = {k: (float(v[0]) / float(max(1, v[1]))) for k, v in accum.items()}
            else:
                bins = defaultdict(list)
                npt = max(1, int(len(pts)))
                for i, (x, y, z) in enumerate(pts, start=1):
                    k = self._grid_index(x, y, xmin, ymin, cell)
                    bins[k].append(float(z))
                    if (i % 5000) == 0:
                        pct = 45.0 + 30.0 * (float(i) / float(npt))
                        if self._report_progress(pct, f"Aggregating points: {i}/{npt}"):
                            raise _CanceledError("Canceled by user.")

                z_cells = {}
                for k, vals in bins.items():
                    if not vals:
                        continue
                    if agg_mode == "Median":
                        arr = sorted(vals)
                        m = len(arr) // 2
                        if len(arr) % 2 == 1:
                            z_cells[k] = float(arr[m])
                        else:
                            z_cells[k] = 0.5 * (float(arr[m - 1]) + float(arr[m]))
                    elif agg_mode == "Min":
                        z_cells[k] = float(min(vals))
                    else:
                        z_cells[k] = float(max(vals))

            if not z_cells:
                raise Exception("No populated DEM cells were generated.")

            mesh_out = _empty_mesh()
            if mesh_out is None:
                raise Exception("Mesh module is not available.")

            half = 0.5 * float(cell)
            total_cells = max(1, int(len(z_cells)))
            for i, (k, z) in enumerate(z_cells.items(), start=1):
                ix, iy = int(k[0]), int(k[1])
                cx, cy = self._cell_center(ix, iy, xmin, ymin, cell)
                zf = float(z)
                p1 = App.Vector(float(cx - half), float(cy - half), zf)
                p2 = App.Vector(float(cx + half), float(cy - half), zf)
                p3 = App.Vector(float(cx + half), float(cy + half), zf)
                p4 = App.Vector(float(cx - half), float(cy + half), zf)
                mesh_out.addFacet(p1, p2, p3)
                mesh_out.addFacet(p1, p3, p4)

                if (i % 2000) == 0:
                    pct = 75.0 + 23.0 * (float(i) / float(total_cells))
                    if self._report_progress(pct, f"Building DEM mesh: {i}/{total_cells}"):
                        raise _CanceledError("Canceled by user.")

            if hasattr(obj, "Mesh"):
                obj.Mesh = mesh_out

            zvals = list(z_cells.values())
            obj.PointCountRaw = int(raw_count)
            obj.PointCountUsed = int(len(pts))
            obj.SkippedRows = int(skipped)
            obj.GridNX = int(nx)
            obj.GridNY = int(ny)
            obj.NoDataCount = int(max(0, est_cells - len(z_cells)))
            obj.ZMin = float(min(zvals))
            obj.ZMax = float(max(zvals))
            obj.Status = (
                f"OK: points={len(pts)}/{raw_count}, skipped={skipped}, "
                f"grid={nx}x{ny}, cells={len(z_cells)}, nodata={obj.NoDataCount}, "
                f"agg={agg_mode}, coords={input_coords}->{output_coords}"
            )
            _mark_recompute_flag(obj, False)
            if bool(getattr(obj, "RebuildNow", False)):
                obj.RebuildNow = False
            self._report_progress(100.0, "Completed")

        except _CanceledError:
            try:
                obj.Status = "CANCELED: user requested cancel"
            except Exception:
                pass
            try:
                if bool(getattr(obj, "RebuildNow", False)):
                    obj.RebuildNow = False
            except Exception:
                pass

        except Exception as ex:
            try:
                if hasattr(obj, "Mesh"):
                    em = _empty_mesh()
                    if em is not None:
                        obj.Mesh = em
            except Exception:
                pass
            obj.PointCountRaw = 0
            obj.PointCountUsed = 0
            obj.SkippedRows = 0
            obj.GridNX = 0
            obj.GridNY = 0
            obj.NoDataCount = 0
            obj.ZMin = 0.0
            obj.ZMax = 0.0
            obj.Status = f"ERROR: {ex}"
            _mark_recompute_flag(obj, False)

    def onChanged(self, obj, prop):
        if bool(getattr(self, "_bulk_updating", False)):
            return

        if prop in (
            "CsvPath",
            "Delimiter",
            "HasHeader",
            "InputCoords",
            "OutputCoords",
            "CellSize",
            "Aggregation",
            "MaxCells",
            "AutoUpdate",
            "RebuildNow",
        ):
            try:
                if prop == "RebuildNow":
                    if not bool(getattr(obj, "RebuildNow", False)):
                        return
                elif prop == "AutoUpdate":
                    if not bool(getattr(obj, "AutoUpdate", True)):
                        return
                else:
                    if not bool(getattr(obj, "AutoUpdate", True)):
                        obj.Status = "NEEDS_RECOMPUTE: source/parameters changed"
                        _mark_recompute_flag(obj, True)
                        return
                obj.touch()
                if prop == "RebuildNow" and bool(getattr(obj, "RebuildNow", False)) and obj.Document is not None:
                    obj.Document.recompute()
            except Exception:
                pass


class ViewProviderPointCloudDEM:
    def __init__(self, vobj):
        vobj.Proxy = self

    def attach(self, vobj):
        try:
            vobj.Visibility = True
            vobj.DisplayMode = "Shaded"
            vobj.LineWidth = 1
            vobj.Transparency = 20
        except Exception:
            pass

    def getIcon(self):
        return ""

    def updateData(self, obj, prop):
        return

    def onChanged(self, vobj, prop):
        return

    def getDisplayModes(self, vobj):
        return ["Wireframe", "Flat Lines", "Shaded"]

    def getDefaultDisplayMode(self):
        return "Shaded"

    def setDisplayMode(self, mode):
        return mode
