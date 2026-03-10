# CorridorRoad Release Operating Model

## Purpose
This document defines the recommended release and version management workflow for the CorridorRoad FreeCAD addon.

## 1. Versioning Policy
- Use semantic versioning in `0.y.z` format while the project is pre-1.0.
- Increment rules:
  - `y` for new features or behavior changes.
  - `z` for bug fixes and small non-breaking improvements.
- Keep one source of truth:
  - `package.xml` `version` and `date` must be updated for every release.
  - Git tag must match the `package.xml` version (`v0.y.z` <-> `0.y.z`).

## 2. Branch Strategy
- `main`: release-ready branch (must always be installable).
- `develop`: integration branch for upcoming release work.
- `feature/*`: feature development branches merged into `develop`.
- `hotfix/*`: urgent production fixes branched from `main`, then merged back to both `main` and `develop`.

## 3. Release Workflow
1. Freeze scope for the target version.
2. Update release metadata:
   - `package.xml` `version`
   - `package.xml` `date` (YYYY-MM-DD)
   - `CHANGELOG.md`
3. Run runtime validation:
   - Workbench load test
   - Core command/task panel smoke tests
   - Addon Manager install/update smoke test
4. Merge release changes into `main`.
5. Create annotated tag:
   - `git tag -a v0.y.z -m "v0.y.z"`
6. Push tag and publish GitHub Release notes.

## 4. Addon Manager Behavior (Important)
- Addon Manager installs from branch HEAD, not from git tags.
- User-facing update detection depends on `package.xml` version bump.
- Do not ship behavior-changing commits to `main` without version and changelog updates.

## 5. Automation and Quality Gates
- Add CI guard at:
  - `.github/workflows/release-guard.yml`
- CI should validate:
  - `package.xml` exists and is parseable.
  - `version` format is valid.
  - `date` format is `YYYY-MM-DD`.
  - On tag builds, `tag == package.xml version` (without leading `v`).
- Add release PR template at:
  - `.github/pull_request_template/release.md`
- Enable branch protection on `main` and require `release-guard` to pass.

## 6. Hotfix Workflow
1. Branch `hotfix/*` from `main`.
2. Apply minimal fix only.
3. Bump patch version (`z`) and update changelog.
4. Merge to `main`, tag, and release.
5. Back-merge hotfix to `develop`.

## 7. Minimum Release Artifacts
- Updated `package.xml` (`version`, `date`).
- Updated `CHANGELOG.md`.
- Passing runtime validation checklist.
- Git tag and GitHub release note.

