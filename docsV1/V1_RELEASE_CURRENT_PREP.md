# Parametric Road Current Release Preparation

Date: 2026-10-11
Status: `1.1.1` release prepared
Scope: post-`1.0.0` v1 updates

## Development Scope After 1.1.1

- Ramp is removed from the active product and development scope.
- Watertight Solid behavior shipped in 1.0.9 remains a compatibility surface, but further development is paused.
- Watertight work is limited to critical defect repair, data-loss prevention, compatibility maintenance, and test preservation.
- The current development and validation runtime is FreeCAD 1.1.1; package metadata retains FreeCAD 1.0.3 as the compatibility floor.
- Documents made with v0 are no longer supported; the legacy object types, panels and commands are gone.

## Purpose

This document tracks release cleanup for the current v1 work after the initial `1.0.0` release baseline.

Use it to keep documentation, release notes, tutorial links, forum messaging, and validation notes aligned after the `1.1.1` release.

## Release Status

- Release version: `1.1.1`
- Release date: `2026-10-11`
- Tag: `v1.1.1`
- GitHub Release: https://github.com/ganadara135/CorridorRoad/releases/tag/v1.1.1
- Tutorial video: https://youtu.be/_xpqwnXPUU8
- Forum thread: https://forum.freecad.org/viewtopic.php?t=103783

Post-release tasks:

- [x] `package.xml` version/date updated to `1.1.1` / `2026-10-11`.
- [x] `CHANGELOG.md` carries the `1.1.1` release section.
- [ ] Git tag and GitHub Release published.
- [ ] FreeCAD manual smoke QA for the published tag. Still open from the session handoff: the Structure Output and Review TIN buttons, a roundabout document from before R7c-3 rebuilding the same ring, and the Drainage low point and `Suggested Inlet` marker.
- [ ] Forum announcement for `1.1.1`, if wanted; the `1.1.0` thread is linked above.
- [ ] GitHub Wiki pages updated from the local `docsV1/wiki/` drafts.

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
- [x] CHANGELOG `1.1.1` contains the intersection kernel, the v1 Project Setup panel, the fixed roundabout circulation, the retired legacy objects, panels and commands, and the defect fixes.
- [x] README and local Wiki drafts now point to the `1.1.1` release.

## Historical Document Notes

The `1.0.0` release planning and validation records still mention Drainage as a placeholder or under-development stage because that was true for the `2026-05-02` release baseline.

Do not rewrite those historical records as current behavior. Current user-facing behavior is tracked in this document, README, Wiki pages, and the latest changelog section.

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

`Parametric Road 1.1.1 builds every intersection (T, Cross and Roundabout) with one parametric kernel from a stored spec, moves Project Setup to a v1 panel, and retires the legacy (v0) object types and panels. Documents made with v0 are no longer supported; documents made with the v1 workflow are unaffected.`

Suggested highlights:

- One parametric intersection kernel builds T, Cross and Roundabout from a stored spec and the roads' Applied Sections; the Intersection panel loads, checks and applies the spec.
- Project Setup is a v1 panel with the same fields; Apply no longer recomputes the whole document, and a stored Coordinate Workflow is kept.
- Roundabouts always circulate counter-clockwise (KDS and AASHTO are right-hand traffic).
- The cross section viewer shows intersection rows across the kernel clip span, lists stations by road, and keeps Next/Previous on the current road.
- The Structure Output and Review TIN buttons work again.
- Legacy (v0) object types, panels and hidden commands are gone; documents made with v0 are no longer supported.

## Tag Readiness

For future release work, do not tag the next release until:

- focused tests for Structures, Drainage, 3D Centerline, Build Corridor, and Watertight Solids pass
- manual FreeCAD smoke QA is complete
- [x] `CHANGELOG.md` is converted from `Unreleased` into the intended version/date section
- [x] `package.xml` version/date is updated for the intended tag
- final `git status` contains only intended release changes

Current packaging state:

- `package.xml` declares version `1.1.1` and date `2026-10-11`.
- The intended release tag is `v1.1.1`.
