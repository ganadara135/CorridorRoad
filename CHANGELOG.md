<!-- SPDX-License-Identifier: LGPL-2.1-or-later -->
<!-- SPDX-FileNotice: Part of the Corridor Road addon. -->

# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog, and this project uses Semantic Versioning.

## [Unreleased]

### Changed
- Retired the legacy command alias `CorridorRoad_GenerateCorridorLoft` and removed the legacy command-wrapper module.
- Retired the legacy task-panel alias path/class (`task_corridor_loft.py`, `CorridorLoftTaskPanel`) and updated the Loft-retirement gate docs/tests accordingly.

## [0.2.7] - 2026-04-15

### Added
- Spline-based `3D Centerline` visible wire mode with `SmoothSpline` as the default display path and `Polyline` retained for debug/comparison review.
- Semantic boundary-marker child objects and task-panel diagnostics for region/structure-aware 3D centerline display review.
- Regression coverage for 3D centerline display segmentation, task-panel default-source selection, and alignment transition geometry/downstream behavior.
- Design notes for segmented 3D centerline display and horizontal transition geometry stabilization.

### Changed
- Refined `3D Centerline` task-panel defaults so existing `Stationing`, `VerticalAlignment`, `ProfileBundle`, `RegionPlan`, and `StructureSet` objects are auto-selected when available.
- Removed legacy `Sampled*` / `Sampling*` compatibility-shadow properties from `Centerline3DDisplay` and standardized on `Display*` result properties.
- Updated `README.md` and wiki documentation to reflect project-level local/world coordinate transforms, spline-based 3D centerline display, and the current display-versus-engineering-source-of-truth policy.
- Clarified the recent visible zig-zag / wiggly 3D centerline issue as a display-side geometry/rendering problem rather than a station-based design-model error.

## [0.2.4] - 2026-04-07

### Added
- `Typical Section` now supports explicit ditch `Shape=v`, `Shape=u`, and `Shape=trapezoid` modes, plus focused ditch-shape sample CSVs and regression coverage.
- `Typical Section` gained manual `Refresh Preview` driven 3D live preview with selected-row highlight overlay and separate `PavementDisplay` / `SelectedComponentPreview` support.

### Changed
- `Typical Section` task-panel UX was refined: helper buttons were simplified, row action layout was cleaned up, hover-driven row activation was removed, and `Shape` is now active only on `ditch` rows.
- `Sections`, `Cross Section Viewer`, and report contracts now preserve station-local ditch shape information so downstream review keeps the intended ditch mode visible.
- README/wiki/developer documentation were synchronized with the current `Typical Section` CSV schema, preview workflow, and ditch-shape behavior.

## [0.2.3] - 2026-04-05

### Added
- `Cross Section Viewer` station-review workflow with station-local component segments, scope-aware rendering for `typical`, `side_slope`, and `daylight`, plus PNG/SVG/Sheet SVG export support.
- `Sections` bench convenience workflow with `Repeat first row to daylight` controls on both left/right bench tables.

### Changed
- `Cross Section Viewer` annotation and summary behavior was expanded so component guides, labels, dimensions, daylight markers, and grouped review summary blocks better reflect `SectionSet` runtime contracts.
- `Cross Section Viewer` task-panel layout was reorganized for faster station navigation and section refresh during review.
- `Edit Structures` task-panel UX was refined, including preset placement, profile-table action layout, and preset-driven station-profile point loading for the sample presets.
- `Sections` and `Cross Section Viewer` now preserve resolved daylight-bound side-slope/bench component extents per station instead of reusing fixed-width viewer assumptions.
- Wiki and developer documentation were synchronized with the current `Cross Section Viewer`, `Sections`, and `Edit Structures` behavior.

## [0.2.2] - 2026-04-01

### Added
- Surface-first corridor workflow with practical grading/cut-fill expansion, including structure-aware notch/skip diagnostics and richer section/corridor report contracts.
- Manual FG productivity tools in `Edit Profiles`, including FG CSV import, FG wizard generation modes, and starter FG sample files.
- Starter-default and inline-guided `Edit PVI` workflow with BVC/EVC-aware summaries.
- Side-slope bench workflow with daylight-aware bench shaping, multi-bench support, table-based bench-row editing, and expanded headless smoke coverage.
- Practical-scope and short-term regression runners plus new sample-driven smoke tests for structures, typical sections, cut/fill, FG tools, and bench workflows.

### Changed
- `CorridorLoft` now uses surface output as the primary corridor representation instead of closed solid generation.
- Structure, section, grading, and cut/fill status wording was expanded for validation, trust/quality reporting, and mixed-workflow diagnostics.
- Wiki and developer documentation were updated for practical engineering scope, FG/PVI workflows, and bench-row editing.

## [0.2.0] - 2026-03-28

### Added
- Typical Section workflow with component presets, pavement layer presets, CSV import/export, and section/corridor integration.
- Expanded structure workflow with template, external-shape, and station-profile support.
- Alignment presets and project-driven coordinate workflow defaults for faster setup.

### Changed
- Improved task panel UX for Typical Section, Edit Structures, Alignment, and Profiles/PVI workflows.
- Clarified terminology by using `berm` for road-edge platforms and reserving `bench` for future earthwork mid-slope use.
- Adopted branch-based addon listing with release/version management on `main` using `package.xml`, `CHANGELOG.md`, tags, and GitHub Releases.

## [0.1.0] - 2026-03-08

### Added
- Initial public release of the CorridorRoad FreeCAD workbench.
- Fixed Civil3D-style project tree schema under `CorridorRoadProject`.
- Horizontal alignment workflow:
  - Sample alignment creation.
  - Practical alignment editing (PI/radius/transition).
  - Design standards selector (`KDS` / `AASHTO`).
  - Sketch import and CSV import/export for alignment PI data.
- Stationing generation from alignment.
- Profile/PVI workflow:
  - Profile data editing and terrain sampling.
  - PVI-based vertical alignment.
  - FG display and profile bundle integration.
- 3D modeling workflow:
  - Centerline3D display generation.
  - Assembly template and section generation.
  - Corridor loft generation.
  - Design grading surface generation.
  - Design terrain generation.
- Cut/Fill analysis workflow with progress and guardrails.
- Namespaced addon structure under `freecad/Corridor_Road`.
- Qt compatibility layer (`qt_compat.py`) for Qt5/Qt6 runtime handling.
- Release automation assets:
  - `.github/workflows/release-guard.yml`
  - `.github/pull_request_template/release.md`

