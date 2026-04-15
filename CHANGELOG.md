<!-- SPDX-License-Identifier: LGPL-2.1-or-later -->
<!-- SPDX-FileNotice: Part of the Corridor Road addon. -->

# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog, and this project uses Semantic Versioning.

## [Unreleased]

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

