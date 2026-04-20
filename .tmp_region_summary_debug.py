import FreeCAD as App
from freecad.Corridor_Road.objects.obj_alignment import HorizontalAlignment
from freecad.Corridor_Road.objects.obj_assembly_template import AssemblyTemplate
from freecad.Corridor_Road.objects.obj_centerline3d_display import Centerline3DDisplay
from freecad.Corridor_Road.objects.obj_corridor import Corridor
from freecad.Corridor_Road.objects.obj_region_plan import RegionPlan
from freecad.Corridor_Road.objects.obj_section_set import SectionSet

def shape_ok(obj):
    shp = getattr(obj, 'Shape', None)
    if shp is None:
        return False
    try:
        return not shp.isNull()
    except Exception:
        return False

doc = App.newDocument('CRRegionCorridorPolicyDbg')
aln = doc.addObject('Part::FeaturePython', 'HorizontalAlignment')
HorizontalAlignment(aln)
aln.IPPoints = [App.Vector(0.0, 0.0, 0.0), App.Vector(100.0, 0.0, 0.0)]
aln.UseTransitionCurves = False

disp = doc.addObject('Part::FeaturePython', 'Centerline3DDisplay')
Centerline3DDisplay(disp)
disp.Alignment = aln
disp.ElevationSource = 'FlatZero'
disp.UseStationing = False

asm = doc.addObject('Part::FeaturePython', 'AssemblyTemplate')
AssemblyTemplate(asm)
asm.UseSideSlopes = False

reg = doc.addObject('Part::FeaturePython', 'RegionPlan')
RegionPlan(reg)
reg.RegionIds = ['BASE_A', 'BASE_SPLIT', 'BASE_SKIP']
reg.RegionTypes = ['roadway', 'bridge_approach', 'earthwork_zone']
reg.Layers = ['base', 'base', 'base']
reg.StartStations = [0.0, 30.0, 70.0]
reg.EndStations = [30.0, 70.0, 90.0]
reg.Priorities = [0, 0, 0]
reg.CorridorPolicies = ['', 'split_only', 'skip_zone']
reg.EnabledFlags = ['true', 'true', 'true']

sec = doc.addObject('Part::FeaturePython', 'SectionSet')
SectionSet(sec)
sec.SourceCenterlineDisplay = disp
sec.AssemblyTemplate = asm
sec.Mode = 'Range'
sec.StartStation = 0.0
sec.EndStation = 100.0
sec.Interval = 20.0
sec.IncludeAlignmentIPStations = False
sec.IncludeAlignmentSCCSStations = False
sec.UseRegionPlan = True
sec.RegionPlan = reg
sec.IncludeRegionBoundaries = True
sec.IncludeRegionTransitions = False
sec.CreateChildSections = False

cor = doc.addObject('Part::FeaturePython', 'Corridor')
Corridor(cor)
cor.SourceSectionSet = sec
cor.UseStructureCorridorModes = False
cor.UseRegionCorridorModes = True
cor.SplitAtStructureZones = True

doc.recompute()
print('shape_ok', shape_ok(cor))
for name in [
    'SegmentSourceSummary',
    'SegmentDriverSourceSummary',
    'SegmentDriverModeSummary',
    'SegmentProfileContractSummary',
    'SegmentPackageSummary',
    'SegmentDisplaySummary',
    'Status',
]:
    print(name + '=', str(getattr(cor, name, '-') or '-'))
print('SegmentPackageRows:')
for row in list(getattr(cor, 'SegmentPackageRows', []) or []):
    print(row)
print('SegmentSummaryRows:')
for row in list(getattr(cor, 'SegmentSummaryRows', []) or []):
    print(row)
App.closeDocument(doc.Name)
