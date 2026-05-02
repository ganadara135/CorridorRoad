# CorridorRoad V1 Release 1.0.0 Plan

Date: 2026-05-02
Status: Draft release plan
Target version: `1.0.0`
Target tag: `v1.0.0`

Depends on:

- `docsV1/V1_MASTER_PLAN.md`
- `docsV1/V1_IMPLEMENTATION_PHASE_PLAN.md`
- `docsV1/V1_REAL_DOCUMENT_VIEWER_CHECKLIST.md`
- `docsV1/V1_MANUAL_QA_QUICKSTART.md`
- `docsV1/V1_DRAINAGE_IMPLEMENTATION_PLAN.md`
- `ADDON_OVERVIEW.md`
- `CHANGELOG.md`
- `package.xml`

## 1. Purpose

This plan defines the release process for CorridorRoad `1.0.0`.

The release should present v1 as the supported workflow reset: source models, evaluated results, review viewers, and output packages are the main product direction.

## 2. Release Scope

Included in the `1.0.0` release scope:

- v1 project workflow and project tree routing
- TIN-first terrain workflow
- Alignment, Stations, and Profile v1 workflow
- Assembly editor with ditch, bench, and preset support
- Region editor and Region-based application flow
- Structure editor and Structure Output workflow
- Applied Sections generation and review handoff
- Build Corridor preview surfaces and diagnostics
- Cross Section Viewer
- Plan/Profile Connection Review
- Earthwork Viewer and v1-native earthwork report path
- Outputs & Exchange entry point
- AI Assist entry point
- Drainage toolbar/menu placeholder and drainage implementation plan

Excluded from the `1.0.0` release scope:

- full Drainage Editor implementation
- full hydraulic drainage analysis
- automatic pipe sizing
- complete drawing-sheet production
- complete LandXML/DXF/IFC output coverage
- v0 migration as a primary workflow

## 3. Release Positioning

`1.0.0` is not a patch release.

It should be described as the first v1 workflow release.

Important user-facing wording:

- "v1 workflow reset"
- "source-driven corridor design"
- "review and output handoff surfaces"
- "Drainage is exposed as a planned stage, with full editor work still in progress"

Avoid wording that implies:

- all drainage authoring is complete
- full hydraulic analysis is available
- generated meshes are editable source truth
- v0 workflows remain the primary product direction

## 4. Pre-Release Freeze

Before release freeze:

1. Stop feature additions except release blockers.
2. Keep only bug fixes, documentation fixes, and release metadata updates.
3. Record any known issues instead of rushing broad refactors.
4. Confirm no placeholder command is misleadingly labeled as complete functionality.

Acceptance criteria:

- all primary toolbar entries open without command registration errors
- placeholder stages show clear under-development messages
- docs describe current scope honestly

## 5. Metadata Updates

Required updates:

- update `package.xml`:
  - `<version>1.0.0</version>`
  - `<date>2026-05-02</date>` or the actual release date
  - description should reflect v1 road corridor workflow
- update `CHANGELOG.md`:
  - add `## [1.0.0] - YYYY-MM-DD`
  - summarize v1 workflow reset
  - list known incomplete areas under release notes or known limitations
- confirm `ADDON_OVERVIEW.md` reflects the release scope
- confirm `docsV1/README.md` links release-relevant v1 documents

Do not update package metadata until the release candidate branch is ready.

## 6. Validation Plan

Automated checks:

- run focused v1 contract tests
- run affected command/viewer tests
- run `py_compile` on changed v1 command, service, object, and viewer modules
- confirm no missing command registration for toolbar/menu actions

Recommended test command pattern:

```powershell
& 'D:\Program Files\FreeCAD 1.0\bin\python.exe' tests/contracts/v1/test_earthwork_review_handoff.py
```

Manual QA:

1. Start a clean FreeCAD session.
2. Activate the CorridorRoad workbench.
3. Confirm toolbar order:
   `Project -> TIN -> Alignment -> Stations/Profile -> Assembly/Structures/Region -> Drainage -> Applied Sections -> Build Corridor -> Review -> Outputs`
4. Open each primary toolbar command.
5. Confirm Drainage shows the under-development message.
6. Create or open a small sample corridor document.
7. Run TIN, Alignment, Stations, Profile, Assembly, Region, Applied Sections, and Build Corridor through the minimal path.
8. Open Cross Section Viewer.
9. Open Plan/Profile Connection Review.
10. Open Earthwork Viewer.
11. Check FreeCAD report view for unexpected traceback errors.

Release blocker examples:

- workbench fails to load
- primary toolbar command is not registered
- project setup cannot open
- Applied Sections cannot run on a simple valid sample
- Build Corridor crashes on a simple valid sample
- review handoff buttons raise command errors

Non-blocker examples if documented:

- Drainage Editor is not implemented beyond placeholder
- advanced exchange output is partial
- some complex terrain/slope edge cases need later refinement

## 7. Wiki Update Plan

The Wiki should be updated before publishing the GitHub release announcement.

Recommended update order:

1. `Home`
   - describe CorridorRoad `1.0.0` as the v1 workflow release
   - link to Quick Start, Workflow, and Known Limitations
2. `Quick Start`
   - update workflow to match the v1 toolbar order
   - include Drainage as an in-progress stage after Region and before Applied Sections
3. `Workflow`
   - document source -> evaluation -> result -> output -> presentation
   - describe the current primary v1 commands
4. `TIN / Terrain`
   - describe TIN-first terrain preparation
5. `Alignment / Stations / Profile`
   - update user steps for the current v1 editors
6. `Assembly / Region`
   - document ditch, bench, Region references, and singular Assembly/Structure expectation
7. `Applied Sections / Build Corridor`
   - document that Applied Sections are generated results and Build Corridor consumes them
8. `Review`
   - add Cross Section Viewer, Plan/Profile Connection Review, and Earthwork Viewer
9. `Earthwork`
   - describe the v1-native earthwork review path and known limitations
10. `Structures / Structure Output`
   - document the Structure Output package and export readiness diagnostics
11. `Drainage`
   - add a clear "planned stage / under development" page or section
   - link to `docsV1/V1_DRAINAGE_IMPLEMENTATION_PLAN.md` if publishing docs links is acceptable
12. `Troubleshooting`
   - add common command registration/restart guidance
   - add guidance for placeholder stages and missing prerequisites
13. `Developer Guide`
   - summarize v1 source/result/output layering
   - link to `docsV1/`

Wiki acceptance criteria:

- Wiki no longer presents v0 corridor loft as the main workflow.
- Wiki states that Drainage full editing is not complete in `1.0.0`.
- Wiki Quick Start follows the same order as the toolbar.
- Wiki troubleshooting includes "restart FreeCAD or reload workbench after update".

## 8. Release Notes Draft

Suggested GitHub release title:

`CorridorRoad 1.0.0 - v1 Workflow Release`

Suggested short description:

`CorridorRoad 1.0.0 introduces the v1 source-driven corridor workflow, including v1 Alignment, Stations, Profile, Assembly, Region, Applied Sections, Build Corridor review surfaces, Earthwork Review, and Structure Output. Drainage is exposed as a planned workflow stage and will continue after this release.`

Suggested sections:

- Highlights
- New v1 workflow
- Review and diagnostics
- Structure and output improvements
- Earthwork improvements
- In-progress areas
- Known limitations
- Upgrade notes
- Wiki and documentation

## 9. Release Steps

1. Create release branch or release candidate state.
2. Freeze feature work.
3. Run automated validation.
4. Complete manual QA.
5. Update `package.xml` to `1.0.0`.
6. Update `CHANGELOG.md`.
7. Finalize `ADDON_OVERVIEW.md`.
8. Update Wiki pages.
9. Commit release metadata and documentation.
10. Tag:

```powershell
git tag v1.0.0
```

11. Push branch and tag.
12. Create GitHub Release from `v1.0.0`.
13. Confirm Addon Manager metadata displays the updated overview and version.

## 10. Post-Release Checks

After publishing:

- install/update through the expected user path
- confirm FreeCAD loads the workbench from the released state
- confirm `package.xml` version is visible as `1.0.0`
- confirm Wiki links in README and release notes work
- record any immediate hotfix issues

## 11. Follow-Up After Release

Recommended next development order:

1. Drainage D2: document object persistence
2. Drainage D3: real Drainage Editor shell
3. Drainage D4-D6: element authoring, Region handoff, Applied Section drainage evaluation
4. Drainage Review viewer
5. drainage quantities and reports
6. exchange output expansion

## 12. Release Decision Checklist

Release can proceed when:

- [ ] `package.xml` version/date are updated
- [ ] `CHANGELOG.md` has `1.0.0`
- [ ] `ADDON_OVERVIEW.md` matches release scope
- [ ] key automated tests pass
- [ ] manual QA smoke test is recorded
- [ ] Wiki Quick Start and Workflow are updated
- [ ] Drainage limitations are visible in docs and Wiki
- [ ] known issues are listed in release notes
- [ ] `v1.0.0` tag is created from the intended commit
