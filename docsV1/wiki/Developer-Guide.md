# Developer Guide

CorridorRoad v1 development should follow the source -> evaluation -> result -> output -> presentation layering.

## Key Directories

- `freecad/Corridor_Road/init_gui.py`
- `freecad/Corridor_Road/v1/commands/`
- `freecad/Corridor_Road/v1/models/source/`
- `freecad/Corridor_Road/v1/models/result/`
- `freecad/Corridor_Road/v1/models/output/`
- `freecad/Corridor_Road/v1/services/`
- `freecad/Corridor_Road/v1/ui/`
- `docsV1/`

## Ownership Rule

Durable design intent belongs in source models.

Generated geometry, preview objects, report rows, and exchange packages are outputs.

## Preferred Flow

1. Add or update source contracts.
2. Add evaluation services.
3. Store result models.
4. Map results to output packages.
5. Present outputs through task panels or review viewers.

## Tests

Use FreeCAD Python for tests that depend on FreeCAD modules.

Preferred local path:

```powershell
& 'D:\Program Files\FreeCAD 1.0\bin\python.exe' tests/contracts/v1/test_earthwork_review_handoff.py
```

Prefer focused contract and service tests over UI-only manual checking.

## Release Notes

For `1.0.0`, see:

- `docsV1/V1_RELEASE_1_0_0_PLAN.md`
- `docsV1/V1_RELEASE_1_0_0_VALIDATION_RECORD.md`
- `docsV1/V1_WIKI_1_0_0_UPDATE_CHECKLIST.md`
