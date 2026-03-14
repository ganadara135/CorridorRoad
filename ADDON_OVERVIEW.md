# CorridorRoad Addon Overview

CorridorRoad is a FreeCAD workbench for road corridor design.
It provides a practical workflow from alignment setup to corridor and cut/fill analysis.

## Who This Is For
- Civil/road designers who need a corridor-oriented workflow in FreeCAD.
- Users who want a fixed project tree and guided task panels.

## Main Features
- Fixed Civil3D-style project tree with automatic object routing.
- Horizontal alignment editing (IP/radius/transition).
- Station generation.
- Profile editing (EG/FG workflow).
- PVI-based vertical alignment editing.
- 3D centerline generation.
- Section generation with assembly/daylight options.
- Corridor loft generation.
- Design terrain generation.
- Cut/Fill calculation.

## Typical Workflow
1. Create a new CorridorRoad project.
2. Configure project setup (design standard, coordinate settings).
3. Create/edit horizontal alignment.
4. Generate stations and edit profiles.
5. Edit PVI and generate 3D centerline.
6. Generate sections and corridor loft.
7. Generate design terrain and run cut/fill analysis.

## Wiki Documentation
- Online Wiki: https://github.com/ganadara135/CorridorRoad/wiki
- Main pages:
1. Quick Start: https://github.com/ganadara135/CorridorRoad/wiki/Quick-Start
2. Workflow: https://github.com/ganadara135/CorridorRoad/wiki/Workflow
3. CSV Format: https://github.com/ganadara135/CorridorRoad/wiki/CSV-Format
4. Troubleshooting: https://github.com/ganadara135/CorridorRoad/wiki/Troubleshooting
- Local wiki draft source: `docs/wiki/`

## Sample Test Data
- Use these files for point cloud DEM testing.
- `tests/samples/pointcloud_utm_realistic_hilly.csv`
- `tests/samples/alignment_utm_realistic_hilly.csv`
1. Import `pointcloud_utm_realistic_hilly.csv` as terrain source.
2. Import `alignment_utm_realistic_hilly.csv` for horizontal alignment.
3. Continue with stations/profiles/sections to validate EG/FG and daylight behavior.

## Requirements
- FreeCAD `1.0.2` or newer recommended.
- Windows 11 used for current development and validation.

## Video
- https://youtu.be/22JhV0dys3E

## Screenshots
![CorridorRoad screenshot 01](https://github.com/user-attachments/assets/8afd06ad-2e84-46fe-b8a7-0ca4490f2902)
![CorridorRoad screenshot 02](https://github.com/user-attachments/assets/da25c711-88a1-4101-acd5-1353fba72ea4)

## License
- LGPL-2.1-or-later
- See [LICENSE](./LICENSE)
