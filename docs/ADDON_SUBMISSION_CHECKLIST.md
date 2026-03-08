# FreeCAD Addon Submission Checklist (CorridorRoad)

Last updated: 2026-03-08

## 1) Metadata (`package.xml`)
- [x] `package.xml` exists at repository root.
- [x] `name`, `description`, `version`, `date` are set.
- [x] `maintainer` with email is set.
- [x] `license` is set to `LGPL-2.1-or-later`.
- [x] `url type="repository"` points to GitHub repository.
- [x] `url type="readme"` points to `README.md`.
- [x] `url type="bugtracker"` points to GitHub issues.
- [x] `content/workbench/name` and `classname` are set.
- [x] `icon` path is set for package and workbench.

## 2) Workbench Loading
- [x] Workbench class exists: `CorridorRoadWorkbench` in `InitGui.py`.
- [x] `MenuText` and `ToolTip` are set.
- [x] `Icon` is wired to repository icon path.

## 3) Assets and Docs
- [x] Workbench icon file exists: `resources/icons/corridorroad_workbench.svg`.
- [x] User-facing `README.md` exists.
- [x] License file exists: `LICENSE`.

## 4) Repository Readiness (before PR to FreeCAD/Addons)
- [ ] Commit/push latest metadata and icon changes to `main`.
- [ ] Verify Addon install/update in clean FreeCAD profile using Addon Manager.
- [ ] Confirm command registration and task panels open without import errors.
- [ ] Confirm README screenshots/links render correctly on GitHub.

## 5) Upstream Submission
- [ ] Open PR to `FreeCAD/Addons` following its current `Documentation/Submission.md`.
- [ ] Fill PR template fields (summary, license, repo URL, maintenance status).
- [ ] Respond to review comments and adjust metadata if requested.

## Notes
- This file is a project-side readiness checklist.
- Final acceptance criteria are determined by maintainers of `FreeCAD/Addons`.
