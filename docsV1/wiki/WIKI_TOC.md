# Parametric Road V1 Wiki Drafts

Target release: `v1.0.8`

These files are draft source pages for the GitHub Wiki.

Current release links:

- GitHub Release: https://github.com/ganadara135/CorridorRoad/releases/tag/v1.0.8
- Tutorial video: https://youtu.be/_xpqwnXPUU8
- FreeCAD Forum: https://forum.freecad.org/viewtopic.php?t=103783

Current local FreeCAD environment:

- FreeCAD version: `1.1.1`
- Workbench path: `C:\Users\ganad\AppData\Roaming\FreeCAD\v1-1\Mod\CorridorRoad`
- FreeCADCmd: `D:\Program Files\FreeCAD 1.1\bin\FreeCADCmd.exe`

Recommended publish order:

1. [Home](./Home.md)
2. [Quick Start](./Quick-Start.md)
3. [Workflow](./Workflow.md)
4. [TIN Terrain](./TIN-Terrain.md)
5. [Alignment Stations Profile](./Alignment-Stations-Profile.md)
6. [Superelevation](./Superelevation.md)
7. [SubAssembly Designer](./SubAssembly-Designer.md)
8. [Assembly Region](./Assembly-Region.md)
9. [Intersections](./Intersections.md)
10. [Applied Sections Build Corridor](./Applied-Sections-Build-Corridor.md)
11. [Review](./Review.md)
12. [Earthwork](./Earthwork.md)
13. [Structures Structure Output](./Structures-Structure-Output.md)
14. [Drainage](./Drainage.md)
15. [Troubleshooting](./Troubleshooting.md)
16. [Developer Guide](./Developer-Guide.md)

Release rule:

- v1 is the primary workflow.
- Superelevation is the source stage after 3D Centerline and before Assembly.
- SubAssembly Designer owns reusable cross-section behavior; Assembly places those definitions and Applied Sections evaluates them.
- Intersections can create starter multi-alignment sources and a matching 3D Centerline preview.
- Drainage is an active source stage with Elements, Policies, Flow Routes, Structure refs, Flow Network preview, and Drainage Review.
- Advanced hydraulic analysis and automatic pipe sizing remain future work.
- Watertight Solids is the final output stage after AI Assist and is gated on Build Corridor prerequisites.
- Generated geometry, preview meshes, markers, and reports are outputs, not source truth.
