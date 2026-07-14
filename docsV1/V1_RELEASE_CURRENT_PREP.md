# Parametric Road Current Release Preparation

Date: 2026-07-10
Status: `1.0.9` release prepared
Scope: post-`1.0.0` v1 updates

## Development Scope After 1.0.9

- Ramp is removed from the active product and development scope.
- Watertight Solid behavior shipped in 1.0.9 remains a compatibility surface, but further development is paused.
- Watertight work is limited to critical defect repair, data-loss prevention, compatibility maintenance, and test preservation.
- The current development and validation runtime is FreeCAD 1.1.1; package metadata retains FreeCAD 1.0.3 as the compatibility floor.

## Purpose

This document tracks release cleanup for the current v1 work after the initial `1.0.0` release baseline.

Use it to keep documentation, release notes, tutorial links, forum messaging, and validation notes aligned after the `1.0.9` release.

## Release Status

- Release version: `1.0.9`
- Release date: `2026-07-10`
- Tag: `v1.0.9`
- GitHub Release: https://github.com/ganadara135/CorridorRoad/releases/tag/v1.0.9
- Tutorial video: https://youtu.be/_xpqwnXPUU8
- Forum thread: https://forum.freecad.org/viewtopic.php?t=103783

Post-release tasks:

- [x] `package.xml` version/date updated to `1.0.9` / `2026-07-10`.
- [x] `CHANGELOG.md` converted from `Unreleased` into the `1.0.9` release section.
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
- Intersections starter sources with multi-alignment Region review and automatic 3D Centerline preview generation
- existing Watertight Solids target discovery and package behavior, retained as paused compatibility

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
- [x] CHANGELOG `1.0.9` contains the maintained Intersection preset, Cross Intersection Tie Slope, Roundabout ownership/clipping, shared breakline audit, and review cleanup work.
- [x] README and local Wiki drafts now point to the `1.0.9` release.

## Historical Document Notes

The `1.0.0` release planning and validation records still mention Drainage as a placeholder or under-development stage because that was true for the `2026-05-02` release baseline.

Do not rewrite those historical records as current behavior. Current user-facing behavior is tracked in this document, README, Wiki pages, and the `1.0.9` changelog section.

## Release Validation Checklist

Before tagging the next release:

1. Restart FreeCAD.
2. Activate the Parametric Road workbench.
3. Confirm toolbar order:
   `Project -> TIN -> Alignment -> Stations/Profile/3D Centerline -> Superelevation -> Assembly/Regions/Structures -> Drainage -> Applied Sections -> Build Corridor -> Review -> Outputs -> AI Assist`
4. Open each primary panel.
5. Run a minimal Alignment -> Stations -> Profile -> 3D Centerline path.
6. Optionally apply Superelevation and confirm sample preview.
7. Apply Assembly and Regions.
8. Apply Structures `Drainage Structures` preset and preview it.
9. Apply Drainage `Drainage Structures Flow` preset and show Flow Network.
10. Run Applied Sections.
11. Run Build Corridor.
12. Optionally open Watertight Solids as a compatibility-only check; do not expand targets or workflow coverage.
13. Confirm the report view has no unexpected traceback.

## Release Notes Draft

Suggested short release description:

`Parametric Road 1.0.9 refines the maintained Intersection preset set, improves Cross Intersection Tie Slope behavior, adds Roundabout-specific surface ownership and clipping, keeps low-level diagnostic rows out of normal user review tables, and updates wiki guidance for the current T, Cross, and Roundabout workflows. Advanced hydraulic analysis, automatic pipe sizing, complete drawing-sheet production, and complete exchange coverage remain future work.`

Suggested highlights:

- Subassembly is now the active v1 cross-section building block in source, result, output, and viewer handoff paths.
- Applied Sections and Cross Section Viewer paths were stabilized after the Component-to-Subassembly transition.
- `Intersection` creates editable source rows and generates a multi-alignment 3D Centerline preview.
- `Intersection Tie Slope Surface` is generated from accepted Applied Section window rows instead of temporary highlight objects.
- `Intersection Upper Slope Face` rectangular panel output is reviewed through generated surface metadata instead of a temporary panel highlight.
- Build Parametric `Intersections` hides obsolete edge-network, surface-zone, drainage-hint, and legacy `intersection_tie_slope` rows by default.
- Breakline Audit exposes compact handoff rows for shared boundary and Intersection Tie Slope window review.
- Shared 3D Centerline review and downstream coordinate ownership, with Smooth Curve / Polyline display options and multi-alignment preview support.
- Superelevation is now a dedicated source stage before Applied Sections, with Auto Calculate and Applied Sections carrying the resolved crossfall into Build Parametric.
- Region source simplification: Regions own station spans and Assembly; Structures and Drainage own their own Region/context refs.
- Structures now support connection-ready native drainage objects and clearer 3D review geometry.
- Drainage now has Elements, Policies, Flow Routes, Structure refs, and Flow Network preview.
- Drainage now opens empty when no source object exists, so users intentionally add rows or load preset data.
- Existing Watertight Solids discovery and package handoff remain available as paused compatibility behavior.
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

- `package.xml` declares version `1.0.9` and date `2026-07-10`.
- The intended release tag is `v1.0.9`.
