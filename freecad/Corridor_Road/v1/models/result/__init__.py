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
from .intersection_boundary_segment import IntersectionBoundarySegmentResult, IntersectionBoundarySegmentRow
from .intersection_surface_patch_build import IntersectionSurfacePatchBuildResult
from .intersection_patch_input import (
    IntersectionPatchInputPreparationResult,
    IntersectionPatchSuperelevationContext,
)
from .intersection_patch_grading import IntersectionPatchGradingResult
from .intersection_patch_boundary_selection import (
    IntersectionPatchBoundarySelectionResult,
)
from .intersection_patch_triangulation import (
    IntersectionPatchTriangulationResult,
)
from .intersection_patch_shape_quality import (
    IntersectionPatchShapeQualityResult,
)
from .intersection_patch_drainage_review import (
    IntersectionPatchDrainageReviewResult,
)
from .intersection_patch_boundary_context import (
    IntersectionPatchBoundaryContextResult,
)
from .intersection_patch_constraint_build import (
    IntersectionPatchConstraintBuildResult,
)
from .intersection_patch_tin_assembly import (
    IntersectionPatchTinAssemblyResult,
)
from .intersection_patch_pipeline import IntersectionPatchPipelineResult
from .intersection_patch_preparation_pipeline import (
    IntersectionPatchPreparationPipelineResult,
)
from .intersection_boundary_loop_evaluation_chain import (
    IntersectionBoundaryLoopEvaluationChainResult,
)
from .intersection_shared_breakline_contribution import (
    IntersectionSharedBreaklineContributionResult,
)
from .intersection_boundary_loop import (
    IntersectionBoundaryLoopResult,
    IntersectionBoundaryLoopRow,
    IntersectionBoundarySegmentRow as IntersectionBoundaryLoopSegmentRow,
)
from .intersection_corridor_clipping import IntersectionCorridorClipResult, IntersectionCorridorClipRow
from .intersection_drainage_hint import IntersectionDrainageHintResult, IntersectionDrainageHintRow
from .intersection_patch_boundary import IntersectionPatchBoundaryPointRow, IntersectionPatchBoundaryResult
from .intersection_roundabout_approach_leg import (
    IntersectionRoundaboutApproachLegResult,
    IntersectionRoundaboutApproachLegRow,
)
from .intersection_tie_in_edge import IntersectionTieInEdgeResult, IntersectionTieInEdgeRow
from .intersection_edge_network import IntersectionEdgeNetworkResult, IntersectionEdgeNetworkRow
from .intersection_grading_context import IntersectionGradingContextResult, IntersectionGradingContextRow
from .intersection_slope_face_boundary import IntersectionSlopeFaceBoundaryResult, IntersectionSlopeFaceBoundaryRow
from .intersection_slope_face_cell import IntersectionSlopeFaceCellResult, IntersectionSlopeFaceCellRow
from .intersection_slope_face_loop import IntersectionSlopeFaceLoopResult, IntersectionSlopeFaceLoopRow
from .intersection_tie_slope import IntersectionTieSlopeResult, IntersectionTieSlopeRow
from .intersection_shared_boundary_graph import (
    IntersectionSharedBoundaryCellRow,
    IntersectionSharedBoundaryEdgeRow,
    IntersectionSharedBoundaryGraphResult,
    IntersectionSharedBoundaryNodeRow,
)
from .intersection_surface_patch import (
    IntersectionSurfacePatchBoundaryRow,
    IntersectionSurfacePatchQualityRow,
    IntersectionSurfacePatchResult,
    IntersectionSurfacePatchTriangulationRow,
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
    "IntersectionBoundarySegmentResult",
    "IntersectionSurfacePatchBuildResult",
    "IntersectionPatchInputPreparationResult",
    "IntersectionPatchSuperelevationContext",
    "IntersectionPatchGradingResult",
    "IntersectionPatchBoundarySelectionResult",
    "IntersectionPatchTriangulationResult",
    "IntersectionPatchShapeQualityResult",
    "IntersectionPatchDrainageReviewResult",
    "IntersectionPatchBoundaryContextResult",
    "IntersectionPatchConstraintBuildResult",
    "IntersectionPatchTinAssemblyResult",
    "IntersectionPatchPipelineResult",
    "IntersectionPatchPreparationPipelineResult",
    "IntersectionBoundaryLoopEvaluationChainResult",
    "IntersectionSharedBreaklineContributionResult",
    "IntersectionBoundarySegmentRow",
    "IntersectionBoundaryLoopResult",
    "IntersectionBoundaryLoopRow",
    "IntersectionBoundaryLoopSegmentRow",
    "IntersectionCorridorClipResult",
    "IntersectionCorridorClipRow",
    "IntersectionDrainageHintResult",
    "IntersectionDrainageHintRow",
    "IntersectionPatchBoundaryPointRow",
    "IntersectionPatchBoundaryResult",
    "IntersectionRoundaboutApproachLegResult",
    "IntersectionRoundaboutApproachLegRow",
    "IntersectionTieInEdgeResult",
    "IntersectionTieInEdgeRow",
    "IntersectionEdgeNetworkResult",
    "IntersectionEdgeNetworkRow",
    "IntersectionGradingContextResult",
    "IntersectionGradingContextRow",
    "IntersectionSlopeFaceBoundaryResult",
    "IntersectionSlopeFaceBoundaryRow",
    "IntersectionSlopeFaceCellResult",
    "IntersectionSlopeFaceCellRow",
    "IntersectionSlopeFaceLoopResult",
    "IntersectionSlopeFaceLoopRow",
    "IntersectionTieSlopeResult",
    "IntersectionTieSlopeRow",
    "IntersectionSharedBoundaryCellRow",
    "IntersectionSharedBoundaryEdgeRow",
    "IntersectionSharedBoundaryGraphResult",
    "IntersectionSharedBoundaryNodeRow",
    "IntersectionSurfacePatchBoundaryRow",
    "IntersectionSurfacePatchQualityRow",
    "IntersectionSurfacePatchResult",
    "IntersectionSurfacePatchTriangulationRow",
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
