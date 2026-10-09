"""Derived result models for CorridorRoad v1."""

from .applied_section import (
    AppliedSection,
    AppliedSectionFrame,
    AppliedSectionSubassemblyLink,
    AppliedSectionSubassemblyPoint,
    AppliedSectionSubassemblyRow,
    AppliedSectionSubassemblyShape,
)
from .applied_section_solid_profile import (
    AppliedSectionSolidProfile,
    AppliedSectionSolidProfileSet,
    SolidProfileEdge,
    SolidProfileNode,
)
from .applied_section_set import AppliedSectionSet
from .alignment_curve_preview import (
    AlignmentCurvePreviewAnnotationRow,
    AlignmentCurvePreviewElementRow,
    AlignmentCurvePreviewPointRow,
    AlignmentCurvePreviewResult,
)
from .corridor_model import CorridorModel
from .centerline3d import Centerline3DPointRow, Centerline3DResult
from .centerline3d_arc_fit import Centerline3DArcFitResult
from .drainage_pipeline import DrainagePipelineResult, DrainagePipelineSegment
from .earthwork_balance_model import EarthworkBalanceModel
from .intersection_patch_constraint_build import (
    IntersectionPatchConstraintBuildResult,
)
from .intersection_boundary_loop import (
    IntersectionBoundaryLoopResult,
    IntersectionBoundaryLoopRow,
    IntersectionBoundarySegmentRow as IntersectionBoundaryLoopSegmentRow,
)
from .intersection_corridor_clipping import IntersectionCorridorClipResult, IntersectionCorridorClipRow
from .intersection_drainage_hint import IntersectionDrainageHintResult, IntersectionDrainageHintRow
from .intersection_roundabout_approach_leg import (
    IntersectionRoundaboutApproachLegResult,
    IntersectionRoundaboutApproachLegRow,
)
from .intersection_tie_in_edge import IntersectionTieInEdgeRow
from .intersection_edge_network import IntersectionEdgeNetworkResult, IntersectionEdgeNetworkRow
from .intersection_grading_context import IntersectionGradingContextResult, IntersectionGradingContextRow
from .intersection_slope_face_loop import IntersectionSlopeFaceLoopResult, IntersectionSlopeFaceLoopRow
from .intersection_shared_boundary_graph import (
    IntersectionSharedBoundaryCellRow,
    IntersectionSharedBoundaryEdgeRow,
    IntersectionSharedBoundaryGraphResult,
    IntersectionSharedBoundaryNodeRow,
)
from .intersection_surface_zone import IntersectionSurfaceZoneResult, IntersectionSurfaceZoneRow
from .intersection_topology import (
    IntersectionTopologyAnchorRow,
    IntersectionTopologyCornerRow,
    IntersectionTopologyControlAreaRow,
    IntersectionTopologyLaneConnectionRow,
    IntersectionTopologyLegSpanRow,
    IntersectionTopologyResult,
)
from .intersection_trim_boundary import IntersectionTrimBoundaryPair, IntersectionTrimBoundaryResult
from .mass_haul_model import MassHaulModel
from .quantity_model import QuantityModel
from .region_context import RegionContextReviewItem, RegionContextSummary
from .profile_curve_preview import (
    ProfileCurvePreviewAnnotationRow,
    ProfileCurvePreviewCurveRow,
    ProfileCurvePreviewPointRow,
    ProfileCurvePreviewResult,
)
from .solid_edge_network import SolidEdgeNetwork, SolidFaceRow, SolidTopologyEdgeRow
from .shared_breakline import SharedBreaklinePointRow, SharedBreaklineResult, SharedBreaklineRow
from .shared_breakline_audit import (
    SharedBreaklineAdjacencyResult,
    SharedBreaklineAuditResult,
)
from .surface_model import SurfaceModel, SurfaceSpanRow
from .subassembly_bench_profile import BenchProfileSegment, SubassemblyBenchProfileResult
from .tin_surface import TINSurface
from .incremental_rebuild import IncrementalBuildDecision, IncrementalBuildExecution, IncrementalStageRecord
from .output_traceability import OutputTraceabilityResult

__all__ = [
    "AppliedSection",
    "AppliedSectionFrame",
    "AppliedSectionSubassemblyLink",
    "AppliedSectionSubassemblyPoint",
    "AppliedSectionSubassemblyRow",
    "AppliedSectionSubassemblyShape",
    "AppliedSectionSolidProfile",
    "AppliedSectionSolidProfileSet",
    "AppliedSectionSet",
    "AlignmentCurvePreviewAnnotationRow",
    "AlignmentCurvePreviewElementRow",
    "AlignmentCurvePreviewPointRow",
    "AlignmentCurvePreviewResult",
    "Centerline3DPointRow",
    "Centerline3DResult",
    "Centerline3DArcFitResult",
    "CorridorModel",
    "DrainagePipelineResult",
    "DrainagePipelineSegment",
    "EarthworkBalanceModel",
    "IntersectionPatchConstraintBuildResult",
    "IntersectionBoundaryLoopResult",
    "IntersectionBoundaryLoopRow",
    "IntersectionBoundaryLoopSegmentRow",
    "IntersectionCorridorClipResult",
    "IntersectionCorridorClipRow",
    "IntersectionDrainageHintResult",
    "IntersectionDrainageHintRow",
    "IntersectionRoundaboutApproachLegResult",
    "IntersectionRoundaboutApproachLegRow",
    "IntersectionTieInEdgeRow",
    "IntersectionEdgeNetworkResult",
    "IntersectionEdgeNetworkRow",
    "IntersectionGradingContextResult",
    "IntersectionGradingContextRow",
    "IntersectionSlopeFaceLoopResult",
    "IntersectionSlopeFaceLoopRow",
    "IntersectionSharedBoundaryCellRow",
    "IntersectionSharedBoundaryEdgeRow",
    "IntersectionSharedBoundaryGraphResult",
    "IntersectionSharedBoundaryNodeRow",
    "IntersectionSurfaceZoneResult",
    "IntersectionSurfaceZoneRow",
    "IntersectionTopologyAnchorRow",
    "IntersectionTopologyCornerRow",
    "IntersectionTopologyControlAreaRow",
    "IntersectionTopologyLaneConnectionRow",
    "IntersectionTopologyLegSpanRow",
    "IntersectionTopologyResult",
    "IntersectionTrimBoundaryPair",
    "IntersectionTrimBoundaryResult",
    "MassHaulModel",
    "QuantityModel",
    "ProfileCurvePreviewAnnotationRow",
    "ProfileCurvePreviewCurveRow",
    "ProfileCurvePreviewPointRow",
    "ProfileCurvePreviewResult",
    "RegionContextReviewItem",
    "RegionContextSummary",
    "SolidEdgeNetwork",
    "SolidFaceRow",
    "SharedBreaklinePointRow",
    "SharedBreaklineAdjacencyResult",
    "SharedBreaklineAuditResult",
    "SharedBreaklineResult",
    "SharedBreaklineRow",
    "SurfaceModel",
    "SurfaceSpanRow",
    "BenchProfileSegment",
    "SubassemblyBenchProfileResult",
    "SolidTopologyEdgeRow",
    "SolidProfileEdge",
    "SolidProfileNode",
    "TINSurface",
    "IncrementalBuildDecision",
    "IncrementalBuildExecution",
    "IncrementalStageRecord",
    "OutputTraceabilityResult",
]
