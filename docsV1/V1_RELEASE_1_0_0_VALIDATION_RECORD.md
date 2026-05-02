# CorridorRoad V1 Release 1.0.0 Validation Record

Date: 2026-05-02
Target version: `1.0.0`
Target tag: `v1.0.0`
Status: automated validation complete, manual QA pending

## 1. Metadata Updated

- [x] `package.xml` version set to `1.0.0`
- [x] `package.xml` date set to `2026-05-02`
- [x] `CHANGELOG.md` includes `## [1.0.0] - 2026-05-02`
- [x] `README.md` rewritten for the v1 release scope
- [x] `ADDON_OVERVIEW.md` rewritten for the v1 release scope
- [x] `docsV1/V1_RELEASE_1_0_0_PLAN.md` added
- [x] `docsV1/V1_WIKI_1_0_0_UPDATE_CHECKLIST.md` added
- [x] `docsV1/V1_DRAINAGE_IMPLEMENTATION_PLAN.md` added

## 2. Automated Validation

Commands run with:

`D:\Program Files\FreeCAD 1.0\bin\python.exe`

Passed:

- [x] `py_compile freecad/Corridor_Road/init_gui.py`
- [x] `py_compile freecad/Corridor_Road/v1/commands/cmd_drainage_editor.py`
- [x] `py_compile freecad/Corridor_Road/v1/ui/viewers/earthwork_review_view.py`
- [x] `tests/contracts/v1/test_earthwork_review_handoff.py`
- [x] `tests/contracts/v1/test_earthwork_analysis_service.py`
- [x] `tests/contracts/v1/test_earthwork_quantity_service.py`
- [x] `tests/contracts/v1/test_earthwork_report_service.py`
- [x] `tests/contracts/v1/test_earthwork_command_v1_report.py`

Registration checks:

- [x] `CorridorRoad_V1EditDrainage` is registered in `init_gui.py`
- [x] `drainage.svg` is referenced by the Drainage command
- [x] release plan and Wiki checklist are linked from `docsV1/README.md`

## 3. Manual QA Pending

Manual FreeCAD QA still required before tagging:

- [x] restart FreeCAD and activate the CorridorRoad workbench
- [x] confirm toolbar order visually
- [x] open every primary toolbar command
- [x] confirm Drainage shows the under-development message
- [x] run a minimal TIN -> Alignment -> Stations -> Profile -> Assembly -> Region -> Applied Sections -> Build Corridor path
- [x] open Cross Section Viewer
- [x] open Plan/Profile Connection Review
- [x] open Earthwork Viewer
- [x] confirm no unexpected traceback appears in the FreeCAD report view

## 4. Wiki Pending

The local repository does not contain editable Wiki page sources in `docs/wiki/`.

Before publishing the GitHub release:

- [ ] update GitHub Wiki pages using `docsV1/V1_WIKI_1_0_0_UPDATE_CHECKLIST.md`
- [ ] confirm Quick Start follows the same order as README
- [ ] confirm Drainage limitations are visible
- [ ] confirm Troubleshooting includes restart/reload guidance

## 5. Known Release Limitations

- Full Drainage Editor is not implemented in `1.0.0`.
- Advanced hydraulic analysis and automatic pipe sizing are not included.
- Complete drawing-sheet production remains future work.
- Full exchange coverage remains incremental.

## 6. Tag Readiness

Do not tag `v1.0.0` until:

- [ ] manual QA is complete
- [ ] Wiki updates are complete
- [ ] release notes are reviewed
- [ ] final `git status` contains only intended release changes
