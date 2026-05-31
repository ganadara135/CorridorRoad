# Parametric Road Current Release Preparation

Date: 2026-05-31
Status: `1.0.3` release prepared
Scope: post-`1.0.0` v1 updates

## Purpose

This document tracks release cleanup for the current v1 work after the initial `1.0.0` release baseline.

Use it to keep documentation, release notes, tutorial links, forum messaging, and validation notes aligned after the `1.0.3` release.

## Release Status

- Release version: `1.0.3`
- Release date: `2026-05-31`
- Tag: `v1.0.3`
- GitHub Release: https://github.com/ganadara135/CorridorRoad/releases/tag/v1.0.3
- Tutorial video: https://youtu.be/_xpqwnXPUU8
- Forum thread: https://forum.freecad.org/viewtopic.php?t=103783

Post-release tasks:

- [x] `package.xml` version/date updated to `1.0.3` / `2026-05-31`.
- [x] `CHANGELOG.md` converted from `Unreleased` into the `1.0.3` release section.
- [x] Git tag and GitHub Release published.
- [x] Tutorial video link added to README, Addon overview, and Wiki draft pages.
- [x] Forum announcement draft prepared in `docsV1/V1_1_0_1_FORUM_ANNOUNCEMENT.md`.
- [x] Manual smoke QA checklist prepared in `docsV1/V1_1_0_1_MANUAL_SMOKE_QA.md`.
- [x] FreeCAD manual smoke QA for the published tag.
- [x] Forum announcement posted or updated with the `Corridor Road` -> `Parametric Road` rename explanation.
- [x] GitHub Wiki pages published/updated from the local `docsV1/wiki/` drafts.

## Current User-Facing Scope

Available or actively represented in the current v1 workflow:

- shared `3D Centerline` stage after Plan/Profile review
- Superelevation source editing after `3D Centerline`, with station sample review and Applied Sections handoff
- Superelevation Auto Calculate for Alignment-criteria-based crossfall rows
- Assembly and continuous Region source editing
- Structures source editing with Native/External geometry source modes
- Structure connection points for drainage-ready ports
- Native inlet, pipe culvert, outlet, and headwall 3D review details
- Drainage Elements, Policies, and Flow Routes
- Drainage editor empty-start behavior with explicit preset loading
- Structure-backed Drainage Flow Network preview
- Drainage Review tables for pipeline candidates, segments, networks, and junctions
- Build Corridor Region Boundary and Surface Transition review
- Watertight Solids target discovery, validation, selected/enabled build actions, display controls, and package export

## Current Future Work

Keep these listed as future or incremental work:

- advanced hydraulic analysis
- automatic pipe sizing
- full drainage reports
- complete drawing-sheet production
- complete LandXML/DXF/IFC coverage
- terrain-inclusive final boolean composition after independent watertight target validation

## Documentation Cleanup Checklist

- [x] README scope updated from Drainage placeholder wording to current Drainage source/editor workflow.
- [x] Addon overview updated for 3D Centerline, Drainage Flow Routes, Structures connection points, and Watertight Solids.
- [x] Wiki Home updated for current toolbar order and current scope.
- [x] Wiki Quick Start updated with Review Plan/Profile, 3D Centerline, Structures after Regions, Drainage, and Watertight Solids.
- [x] Wiki Troubleshooting updated for Drainage Flow Network, Structure preview, and Watertight Solids.
- [x] Wiki Structures page updated for drainage-ready native Structure previews.
- [x] Wiki Review page updated for 3D Centerline and Drainage Review.
- [x] CHANGELOG `1.0.3` contains recent Superelevation, Drainage, and 3D Centerline UX notes.
- [x] README and local Wiki drafts now point to the `1.0.3` release.

## Historical Document Notes

The `1.0.0` release planning and validation records still mention Drainage as a placeholder or under-development stage because that was true for the `2026-05-02` release baseline.

Do not rewrite those historical records as current behavior. Current user-facing behavior is tracked in this document, README, Wiki pages, and the `1.0.3` changelog section.

## Release Validation Checklist

Before tagging the next release:

1. Restart FreeCAD.
2. Activate the Parametric Road workbench.
3. Confirm toolbar order:
   `Project -> TIN -> Alignment -> Stations/Profile/3D Centerline -> Superelevation -> Assembly/Regions/Structures -> Drainage -> Applied Sections -> Build Corridor -> Review -> Outputs -> AI Assist -> Watertight Solids`
4. Open each primary panel.
5. Run a minimal Alignment -> Stations -> Profile -> 3D Centerline path.
6. Optionally apply Superelevation and confirm sample preview.
7. Apply Assembly and Regions.
8. Apply Structures `Drainage Structures` preset and preview it.
9. Apply Drainage `Drainage Structures Flow` preset and show Flow Network.
10. Run Applied Sections.
11. Run Build Corridor.
12. Open Watertight Solids and confirm target discovery.
13. Build one Structure or Drainage target where prerequisites are available.
14. Confirm the report view has no unexpected traceback.

## Release Notes Draft

Suggested short release description:

`Parametric Road 1.0.3 improves the source-driven v1 workflow with Superelevation Auto Calculate, clearer Superelevation Apply feedback, smoother 3D Centerline display options, and a cleaner Drainage editor first-entry experience with empty tables and explicit preset loading. Advanced hydraulic analysis, automatic pipe sizing, and complete exchange coverage remain future work.`

Suggested highlights:

- Shared 3D Centerline review and downstream coordinate ownership, with Smooth Curve / Polyline display options.
- Superelevation is now a dedicated source stage before Applied Sections, with Auto Calculate and Applied Sections carrying the resolved crossfall into Build Parametric.
- Region source simplification: Regions own station spans and Assembly; Structures and Drainage own their own Region/context refs.
- Structures now support connection-ready native drainage objects and clearer 3D review geometry.
- Drainage now has Elements, Policies, Flow Routes, Structure refs, and Flow Network preview.
- Drainage now opens empty when no source object exists, so users intentionally add rows or load preset data.
- Watertight Solids now discovers and builds road, component, drainage, and structure targets with package handoff.
- Build Parametric and Watertight Solid outputs are easier to inspect from the FreeCAD tree.
- Drainage Flow Network previews now follow shared 3D Centerline elevation context more reliably.
- Applied Sections row review now shows the selected Assembly line without station marker clutter.

## Tag Readiness

For future release work, do not tag the next release until:

- focused tests for Structures, Drainage, 3D Centerline, Build Corridor, and Watertight Solids pass
- manual FreeCAD smoke QA is complete
- [x] `CHANGELOG.md` is converted from `Unreleased` into the intended version/date section
- [x] `package.xml` version/date is updated for the intended tag
- final `git status` contains only intended release changes

Current packaging state:

- `package.xml` declares version `1.0.3` and date `2026-05-31`.
- The intended release tag is `v1.0.3`.
