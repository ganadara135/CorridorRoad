<!-- SPDX-License-Identifier: LGPL-2.1-or-later -->
<!-- SPDX-FileNotice: Part of the Corridor Road addon. -->

# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog, and this project uses Semantic Versioning.

## [Unreleased]

### Added
- Added Stationing-based Region editing where Region `Start STA` values are selected from generated station values and `End STA` is derived from the next Region start.
- Added Build Corridor Region Boundary review support for displaying the selected Region's built corridor objects, including design, subgrade, slope/daylight, drainage, and structure context where available.
- Added Surface Transition controls in Build Corridor for selecting a Region STA, adjusting transition spacing, reviewing derived sample counts, enabling/disabling transition ranges, and updating transition records.
- Added wiki documentation for Region continuity, Region Boundary review, Surface Transition spacing/update workflow, and troubleshooting guidance.

### Changed
- Updated the `Drainage Control` Region preset to use `STA 100.000` as the drainage-control start station and the current final Stationing value as the closing Region start.
- Renamed the Surface Transition action button in Build Corridor from `Create / Update Transition` to `Update`.
- Clarified Region and Surface Transition design documentation so transition intent remains source-level and generated geometry remains output.

## [1.0.0] - 2026-05-02

### Added
- Introduced the v1 source-driven corridor workflow as the supported release direction.
- Added v1-native TIN, Alignment, Stations, Profile, Assembly, Region, Applied Sections, Build Corridor, review, Earthwork, Structure Output, Outputs & Exchange, and AI Assist stage framing.
- Added a Drainage toolbar/menu entry with a clear under-development message and dedicated drainage icon.
- Added v1 release, drainage implementation, and release-overview documentation for the `1.0.0` release.
- Added v1-native Earthwork report flow from Applied Sections and existing-ground terrain into cut/fill area, quantity, balance, mass-haul, and review outputs.

### Changed
- Rewrote `README.md` and `ADDON_OVERVIEW.md` around the v1 workflow, current release scope, and known in-progress areas.
- Updated the workbench command registration so v1 review and Earthwork handoff commands are available from the active workbench session.
- Clarified Drainage as a planned v1 stage after Region and before Applied Sections.
- Refined Earthwork Review handoff behavior to avoid deleted Qt object access after closing the task panel.

### Known Limitations
- Full Drainage Editor functionality is not complete in `1.0.0`.
- Advanced hydraulic analysis, automatic pipe sizing, complete drawing-sheet production, and full exchange output coverage remain future work.
- Some workflows still retain legacy support paths during the v1 transition, but v1 source/result/output layering is the intended direction.

## [0.2.8] - 2026-04-20

### Changed
- Retired the legacy proxy module `obj_corridor_loft.py` and its internal `CorridorLoft` proxy type, establishing `obj_corridor.py` and `Corridor` as the canonical standard.
- Established backwards compatibility module mappings in `virtual_paths.py` so legacy `.FCStd` files containing `CorridorLoft` and its historical module paths restore transparently to the new `Corridor` proxy.
- Retired the legacy command alias `CorridorRoad_GenerateCorridorLoft` and removed the legacy command-wrapper module.
- Retired the legacy task-panel alias path/class (`task_corridor_loft.py`, `CorridorLoftTaskPanel`) and updated the Loft-retirement gate docs/tests accordingly.
- Retired the hidden project-link property name `CorridorLoft` and switched `CorridorRoadProject` to the canonical hidden `Corridor` link.
- Retired the child ownership property name `ParentCorridorLoft` and switched generated corridor children to `ParentCorridor`.

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

