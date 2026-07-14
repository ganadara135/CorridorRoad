# Phase 5 Supported Domain Manual QA

Date: 2026-07-13

Status: User accepted on 2026-07-13

Runtime: FreeCAD 1.1.1

## Purpose

This is the final manual acceptance pass for Phase 5. It checks source ownership, result generation, review-only behavior, traceability, and save/reopen continuity across the supported workflow.

Ramp is excluded. Watertight Solid is optional compatibility-only coverage and is not part of the Phase 5 development pass.

## Preparation

1. Restart FreeCAD 1.1.1.
2. Activate `Parametric Road`.
3. Create a new document and create a Parametric Road Project.
4. Keep the Report View visible so unexpected tracebacks are easy to identify.

## Required Workflow

Record each group as `PASS` or `FAIL`.

### A. Source chain

1. Create or load a TIN and confirm it appears under the project without editing the preview mesh directly.
2. Apply an Alignment, generate Stations, apply a Profile, and build 3D Centerline.
3. If Superelevation is used, apply it and confirm its sample rows appear before Applied Sections.
4. Close and reopen one editor without Apply; confirm the source object did not change.

Pass condition: source edits occur only through Apply/Save and the 3D Centerline remains derived from Alignment/Profile.

### B. SubAssembly, Assembly, and Region

1. Open SubAssembly Designer, change a temporary value, close without Save, and confirm no source definition was written.
2. Save a usable definition, place it in Assembly/Subassembly, and apply the Assembly.
3. Create at least one Region that references the Assembly.
4. Confirm Region does not expose editable Structure, Drainage, or Intersection meaning as Region-owned data.

Pass condition: saved definitions and placed rows are source; Section Preview remains review-only.

### C. Intersection, Structure, and Drainage

1. Create or load one ordinary Intersection source and confirm its diagnostics identify missing required refs instead of producing unexplained repair geometry.
2. Create a Structure source row and preview it; confirm editing the preview itself does not change Structure source data.
3. Create Drainage Elements/Policies/Flow Routes or load the existing drainage preset.
4. Open Flow Network and Drainage Review and confirm Structure/Region refs remain visible.

Pass condition: each domain retains its own source ownership and missing intent is diagnostic.

### D. Applied Sections and Build Parametric

1. Generate Applied Sections.
2. Confirm supplemental stations, when present, are result rows and are not directly editable as source stations.
3. Run Build Parametric.
4. Run Build Parametric again without source changes.
5. Confirm Corridor/Surface objects expose accepted build metadata, fingerprints, consumed refs, duration, changed stages, and stale reasons.
6. Change only preview visibility and confirm the engineering result fingerprint does not change.

Pass condition: accepted unchanged results are reusable, presentation changes do not become source changes, and no unexpected traceback appears.

### E. Review and output

1. Open Cross Section Viewer, Plan/Profile Viewer, Quantity/Earthwork review, and Drainage Review where data is available.
2. Navigate or focus a row, then close the viewer.
3. Confirm source rows and generated engineering result rows were not rewritten by review interaction.
4. Build one current normalized output or Structure Output package.
5. Confirm output properties identify project, source refs, and result refs; missing prerequisites must produce a diagnostic.

Pass condition: viewers are read-only review surfaces and output ownership is traceable.

### F. Save and reopen

1. Save the document as an FCStd file.
2. Close and reopen it.
3. Confirm Alignment/Profile/Assembly/Region/Structure/Drainage source identity remains intact.
4. Confirm Applied Sections/Corridor/Surface refs and incremental metadata remain intact.
5. Reopen one editor and one viewer in the same context.

Pass condition: source, result, output refs and review context survive save/reopen.

## Excluded and Optional Checks

- Do not create or expand Ramp data.
- Watertight Solid may be opened only as an optional compatibility check. Do not add targets, topology behavior, simulation features, UI, or exchange coverage.
- Advanced hydraulic analysis and automatic pipe sizing are not Phase 5 failures because they are outside the supported scope.

## Result Record

Fill in:

- FreeCAD version:
- Document path:
- A Source chain:
- B SubAssembly/Assembly/Region:
- C Intersection/Structure/Drainage:
- D Applied Sections/Build Parametric:
- E Review/output:
- F Save/reopen:
- Unexpected traceback:
- Notes:

Phase 5 manual acceptance requires A through F to pass with no unexplained source mutation or unexpected traceback.

## Acceptance Record

- User validation: completed
- Functional acceptance: accepted
- Reported follow-up: overall operation felt slower than before
- Decision: performance investigation is deferred to explicit follow-up maintenance
- Scope rule: the performance follow-up must preserve completed source/result/output ownership, persistence, incremental rebuild, command/service/object/model, and presentation boundaries
- Completion impact: the reported slowdown does not block Phase 5 functional acceptance; no data-loss, source-mutation, or traceback blocker was reported
