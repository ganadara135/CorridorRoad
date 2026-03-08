# FreeCAD Addon Submission Checklist (CorridorRoad)

Last updated: 2026-03-08

## Latest Verification Run
- Date: 2026-03-08
- Scope: Official Addon Manager listing/installability pre-check
- Result: `CorridorRoad` not found in official sources yet
  - `https://raw.githubusercontent.com/FreeCAD/FreeCAD-addons/master/.gitmodules` -> not found
  - `https://freecad.org/addons/addon_cache.json` -> not found
- Conclusion: Official Addon Manager install verification is blocked until upstream listing PR is merged and cache refresh completes.

## A. Local Metadata and Package Shape
- [x] Root `package.xml` exists and is valid XML.
- [x] Workbench metadata is filled (`name`, `description`, `version`, `date`).
- [x] Maintainer and email are set.
- [x] License is declared as `LGPL-2.1-or-later`.
- [x] Repository/README/bugtracker URLs are set.
- [x] Workbench class mapping is set (`CorridorRoadWorkbench`).
- [x] Package and workbench icons are declared.

## B. Workbench Runtime Basics
- [x] Workbench class exists in `InitGui.py`.
- [x] `MenuText` and `ToolTip` are defined.
- [x] `Icon` path is connected to `resources/icons/corridorroad_workbench.svg`.

## C. Repository Baseline
- [x] User-facing `README.md` exists.
- [x] `LICENSE` file exists and matches package license.
- [x] Icon asset exists in repository.
- [x] `main` merge completed (user confirmed on 2026-03-08).

## D. Remaining Pre-Submission Checks
- [ ] Validate clean install on a clean FreeCAD user profile via Addon Manager.
- [ ] Validate update path (install old commit/tag -> update to latest).
- [ ] Confirm all commands/task panels load without import/runtime errors.
- [ ] Confirm README images and links render correctly on GitHub web UI.

## E. Upstream Submission (FreeCAD/FreeCAD-addons)
- [ ] Open PR to `FreeCAD/FreeCAD-addons` per its submission guide/template.
- [ ] Fill PR template completely (addon URL, license, summary, maintenance info).
- [ ] Monitor CI/checks and fix requested metadata/path issues.
- [ ] Respond to maintainer review and update PR until merged.
- [ ] After merge, wait for addons cache refresh cycle and verify listing in Addon Manager.

## Notes
- This checklist is project-side readiness tracking.
- Final acceptance criteria and timing are controlled by `FreeCAD/FreeCAD-addons` maintainers.
