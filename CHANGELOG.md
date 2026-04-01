<!-- SPDX-License-Identifier: LGPL-2.1-or-later -->
<!-- SPDX-FileNotice: Part of the Corridor Road addon. -->

# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog, and this project uses Semantic Versioning.

## [Unreleased]

### Changed
- Placeholder for upcoming changes.

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

