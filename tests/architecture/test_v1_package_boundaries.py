"""Static dependency guards for the CorridorRoad v1 package boundaries."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path


V1_ROOT = Path(__file__).resolve().parents[2] / "freecad" / "Corridor_Road" / "v1"


@dataclass(frozen=True)
class ImportRef:
    path: str
    module: str
    symbol: str
    line: int


def _python_files(package: str) -> list[Path]:
    return sorted((V1_ROOT / package).rglob("*.py"))


def _imports(package: str) -> list[ImportRef]:
    result: list[ImportRef] = []
    for path in _python_files(package):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        relative_path = path.relative_to(V1_ROOT).as_posix()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                result.extend(
                    ImportRef(relative_path, alias.name, "", node.lineno)
                    for alias in node.names
                )
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                result.extend(
                    ImportRef(relative_path, module, alias.name, node.lineno)
                    for alias in node.names
                )
    return result


def _module_has_segment(module: str, segment: str) -> bool:
    return segment in module.split(".")


def _format(refs: list[ImportRef]) -> str:
    return "\n".join(
        f"{ref.path}:{ref.line}: {ref.module}:{ref.symbol}"
        for ref in refs
    )


def test_models_do_not_depend_on_runtime_or_outer_layers() -> None:
    banned_segments = {
        "commands",
        "objects",
        "ui",
        "FreeCAD",
        "FreeCADGui",
        "Part",
        "PySide",
        "PySide2",
        "PySide6",
        "qt_compat",
    }
    violations = [
        ref
        for ref in _imports("models")
        if any(_module_has_segment(ref.module, segment) for segment in banned_segments)
    ]
    assert not violations, _format(violations)


def test_services_do_not_depend_on_commands_or_ui() -> None:
    violations = [
        ref
        for ref in _imports("services")
        if any(_module_has_segment(ref.module, segment) for segment in ("commands", "ui"))
    ]
    assert not violations, _format(violations)


def test_objects_do_not_depend_on_commands_or_ui() -> None:
    violations = [
        ref
        for ref in _imports("objects")
        if any(_module_has_segment(ref.module, segment) for segment in ("commands", "ui"))
    ]
    assert not violations, _format(violations)


def test_ui_to_command_dependencies_are_limited_to_known_compatibility_shims() -> None:
    allowed = set()
    actual = {
        (ref.path, ref.module, ref.symbol)
        for ref in _imports("ui")
        if _module_has_segment(ref.module, "commands")
    }
    assert actual == allowed, (
        "UI-to-command dependencies changed. Remove the reverse dependency or update the "
        f"explicit compatibility list deliberately.\nactual={sorted(actual)!r}"
    )


def test_commands_do_not_add_private_service_imports() -> None:
    allowed = set()
    actual = {
        (ref.path, ref.module, ref.symbol)
        for ref in _imports("commands")
        if _module_has_segment(ref.module, "services") and ref.symbol.startswith("_")
    }
    assert actual == allowed, (
        "Private service imports from commands changed. Use a public service API or update "
        f"the temporary compatibility list deliberately.\nactual={sorted(actual)!r}"
    )


def test_build_corridor_preview_shape_failures_are_marked() -> None:
    """A failed preview Shape assignment must not return an unmarked object.

    These handlers guard `obj.Shape = ...` and then return the object. Without a
    marker the caller receives a document object that has no Shape and never
    reached its record-kind tagging, which is indistinguishable from a
    successful empty preview.
    """

    command_path = V1_ROOT / "commands" / "cmd_build_corridor.py"
    source = command_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(command_path))
    source_lines = source.splitlines()

    unmarked: list[int] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Try):
            continue
        guarded = "\n".join(
            source_lines[node.body[0].lineno - 1: node.body[-1].end_lineno]
        )
        if "obj.Shape =" not in guarded:
            continue
        for handler in node.handlers:
            for statement in ast.walk(handler):
                if not isinstance(statement, ast.Return):
                    continue
                returned = statement.value
                if isinstance(returned, ast.Name) and returned.id == "obj":
                    unmarked.append(statement.lineno)

    assert not unmarked, (
        "Preview shape failure returns an unmarked object at lines "
        f"{sorted(unmarked)}. Return _mark_preview_shape_failure(obj, ...) instead "
        "so the fallback is visible on the document."
    )


def test_build_corridor_phase2_owners_are_outside_the_command_module() -> None:
    command_path = V1_ROOT / "commands" / "cmd_build_corridor.py"
    command_tree = ast.parse(
        command_path.read_text(encoding="utf-8"),
        filename=str(command_path),
    )
    command_classes = {
        node.name for node in command_tree.body if isinstance(node, ast.ClassDef)
    }
    assert "V1BuildCorridorTaskPanel" not in command_classes

    viewer_path = V1_ROOT / "ui" / "viewers" / "build_corridor_view.py"
    viewer_tree = ast.parse(
        viewer_path.read_text(encoding="utf-8"),
        filename=str(viewer_path),
    )
    viewer_classes = {
        node.name for node in viewer_tree.body if isinstance(node, ast.ClassDef)
    }
    assert {
        "BuildCorridorViewModel",
        "V1BuildCorridorTaskPanel",
    } <= viewer_classes

    service_names = {
        "intersection_shared_breakline_service.py",
        "intersection_slope_face_boundary_evaluation_service.py",
        "intersection_tie_slope_evaluation_service.py",
        "intersection_slope_face_cell_evaluation_service.py",
        "intersection_shared_boundary_graph_evaluation_service.py",
    }
    available = {
        path.name
        for path in (V1_ROOT / "services" / "evaluation").glob("*.py")
    }
    assert service_names <= available

    builder_names = {
        "intersection_daylight_tin_service.py",
        "intersection_exclusion_geometry_service.py",
        "intersection_slope_face_tin_builder_service.py",
        "intersection_tin_clip_service.py",
        "roundabout_surface_builder_service.py",
        "roundabout_tin_clip_service.py",
        "shared_breakline_tin_builder_service.py",
    }
    available_builders = {
        path.name
        for path in (V1_ROOT / "services" / "builders").glob("*.py")
    }
    assert builder_names <= available_builders

    runtime_segments = {"FreeCAD", "FreeCADGui", "Part", "PySide", "qt_compat"}
    builder_import_violations = [
        ref
        for ref in _imports("services")
        if ref.path.rsplit("/", 1)[-1] in builder_names
        and any(
            _module_has_segment(ref.module, segment)
            for segment in runtime_segments
        )
    ]
    assert not builder_import_violations, _format(builder_import_violations)

    command_functions = {
        node.name: node
        for node in command_tree.body
        if isinstance(node, ast.FunctionDef)
    }
    wrapper_limits = {
        "_clip_tin_surface_by_intersection_exclusion": 35,
        "_clip_tin_surface_by_roundabout_ownership": 35,
        "_build_roundabout_circulatory_surface_tin": 25,
        "_build_roundabout_apron_surface_tin": 25,
        "_build_roundabout_entry_exit_connector_surface_tin": 25,
        "_build_roundabout_subgrade_surface_tin": 25,
        "_build_roundabout_slope_face_surface_tin": 25,
    }
    for name, maximum_lines in wrapper_limits.items():
        node = command_functions[name]
        assert node.end_lineno - node.lineno + 1 <= maximum_lines, name

    removed_implementation_names = {
        # Deleted by M5 chunk 8: review helpers that nothing referenced.
        "_intersection_drainage_element_rows",
        "corridor_subassembly_guided_review_summary",
        # Deleted by M4 batch 2: the remaining service delegation shims.
        "_bbox3d_overlaps",
        "_clip_polyline_points_to_anchor_window",
        "_clip_segment_to_anchor_box",
        "_cross3",
        "_dot3",
        "_intersection_boundary_loop_exclusion_polygon_candidate",
        "_intersection_boundary_loop_tin_vertices",
        "_intersection_curb_return_surface_arc_stats",
        "_intersection_grading_policy_for",
        "_intersection_patch_boundary_hull",
        "_intersection_patch_boundary_role_counts",
        "_intersection_patch_boundary_role_summary",
        "_intersection_patch_ear_clip_indices",
        "_intersection_ready_outer_boundary_loop_row",
        "_intersection_surface_part_is_valid",
        "_length3",
        "_lerp_xyz",
        "_ordered_outer_boundary_from_segments",
        "_point_in_triangle_3d",
        "_point_segment_distance_with_ratio",
        "_sub3",
        "_tin_rows_with_shared_breakline_constraint_edges",
        "_tin_surface_all_edge_rows",
        "_tin_surface_boundary_edge_rows",
        "_tin_surface_reference_triangles",
        "_tin_surface_z_at_xy_from_reference_triangles",
        "_tin_triangle_overlap_sample_points_xy",
        "_tin_triangle_xy_overlaps_reference_triangles",
        "_triangle_edges_intersect_other_triangle_plane",
        "_triangle_plane",
        "_triangle_triangle_intersection_segment",
        "_triangle_xyz_bbox",
        "_triangle_z_at_xy",
        "_unique_xyz_points",
        "_vertex_xyz",
        "_xy_closed_edges",
        "_xy_distance",
        "_xy_intersect_polygon_with_convex_polygon",
        "_xy_point_in_polygon",
        "_xy_point_in_polygon_strict",
        "_xy_point_in_triangle",
        "_xy_point_on_segment",
        "_xy_point_tuple",
        "_xy_polygon_area",
        "_xy_polygon_is_convex",
        "_xy_polygon_outer_difference_candidate",
        "_xy_polygon_signed_area",
        "_xy_polygon_union_outer_boundary",
        "_xy_segment_distance",
        "_xy_segment_intersection_point",
        "_xy_segment_parameter",
        "_xy_segments_cross_strict",
        "_xy_segments_intersect",
        "_xy_subtract_convex_polygon_from_polygon",
        "_xy_triangle_area",
        "_xy_triangle_intersects_polygon",
        "_xy_triangle_intrudes_pavement_strip_protection",
        "_xy_triangle_polygon_intersection_kind",
        "_xy_triangle_quality_ratio",
        "_xy_triangulate_simple_polygon_points",
        "_xyz_distance",
        "_xyz_tuple",
        # Deleted by M4 batch 1: delegation wrappers whose callers now use the service APIs.
        "_apply_intersection_grading_policy",
        "_intersection_grading_plane_for_policy",
        "_intersection_curb_return_surface_parts",
        "_intersection_patch_ordered_polygon_triangulation",
        "_intersection_patch_structured_strip_triangulation",
        "_intersection_tie_in_strip_polygon",
        "_normalize_intersection_tie_in_strip_polygon",
        "_intersection_patch_boundary_tin_vertices",
        "_intersection_practical_exclusion_polygon_candidate_from_boundary_segments",
        "_intersection_practical_exclusion_polygon_from_boundary_segments",
        "_xy_triangle_near_curb_return_arc_protection",
        "_intersection_surface_tin_with_shared_breakline_constraint_edges",
        "_tin_surface_with_shared_breakline_constraint_edges",
        "_tin_surface_with_shared_breakline_metadata",
        "_suppress_daylight_triangles_above_intersection_surface",
        "_suppress_daylight_triangles_inside_intersection_slope_face_loop_footprint",
        "_suppress_daylight_triangles_inside_intersection_surface_footprint",
        "_trim_daylight_triangles_above_intersection_surface_by_intersection_lines",
        "_xy_area_from_xyz_points",
        "_xy_polygon_exterior_hull_boundary",
        "_xy_xyz_polygon_self_crossing",
        "_build_intersection_slope_face_surface_from_ready_loops",
        "_intersection_slope_face_boundary_target_segments",
        "_append_intersection_upper_slope_face_panel_tin",
        "_append_intersection_slope_face_cell_tin",
        "_append_intersection_slope_face_graph_cell_tin",
        "_append_intersection_boundary_loop_slope_face_transition_tin",
        "_roundabout_boundary_exact_clip_fragments",
        "_xy_subtract_exclusion_area_from_polygon",
    }
    assert not (removed_implementation_names & command_functions.keys())


def test_phase3_task_panel_owners_are_outside_command_modules() -> None:
    owners = {
        "cmd_structure_editor.py": ("ui/editors/structure_editor.py", {"V1StructureEditorTaskPanel"}),
        "cmd_profile_editor.py": (
            "ui/editors/profile_editor.py",
            {"_ProfileCurvePreviewWidget", "V1ProfileEditorTaskPanel"},
        ),
        "cmd_subassembly_designer.py": (
            "ui/editors/subassembly_designer.py",
            {"V1SubAssemblyDesignerTaskPanel", "_DefinitionTableComboBox", "_ZoomablePreviewView"},
        ),
        "cmd_subassembly_editor.py": (
            "ui/editors/subassembly_editor.py",
            {"_AssemblyTableComboBox", "V1AssemblySubassemblyEditorTaskPanel", "_AssemblySectionPreviewView"},
        ),
        "cmd_drainage_editor.py": ("ui/editors/drainage_editor.py", {"V1DrainageEditorTaskPanel"}),
        "cmd_drainage_review.py": ("ui/viewers/drainage_review_view.py", {"V1DrainageReviewTaskPanel"}),
        "cmd_alignment_editor.py": (
            "ui/editors/alignment_editor.py",
            {"_AlignmentCurvePreviewWidget", "V1AlignmentEditorTaskPanel"},
        ),
        "cmd_edit_tin.py": (
            "ui/editors/tin_editor.py",
            {"V1TINEditorTaskPanel", "_TINFacePickObserver"},
        ),
    }

    for command_name, (owner_path, expected_classes) in owners.items():
        command_tree = ast.parse((V1_ROOT / "commands" / command_name).read_text(encoding="utf-8"))
        command_classes = {node.name for node in command_tree.body if isinstance(node, ast.ClassDef)}
        assert not (expected_classes & command_classes), command_name

        owner_tree = ast.parse((V1_ROOT / owner_path).read_text(encoding="utf-8"))
        owner_classes = {node.name for node in owner_tree.body if isinstance(node, ast.ClassDef)}
        assert expected_classes <= owner_classes, owner_path

    editing_services = {path.name for path in (V1_ROOT / "services" / "editing").glob("*.py")}
    assert {"editor_source_service.py", "tin_edit_service.py"} <= editing_services


def test_legacy_tree_routing_is_limited_to_adapter_and_recorded_object_compatibility_paths() -> None:
    compatibility_paths = {
        "objects/obj_alignment.py",
        "objects/obj_applied_section.py",
        "objects/obj_corridor.py",
        "objects/obj_drainage.py",
        "objects/obj_exchange_package.py",
        "objects/obj_intersection.py",
        "objects/obj_intersection_trim_boundary.py",
        "objects/obj_landxml_import.py",
        "objects/obj_profile.py",
        "objects/obj_quantity.py",
        "objects/obj_region.py",
        "objects/obj_simulation_package.py",
        "objects/obj_simulation_qa.py",
        "objects/obj_structure.py",
        "objects/obj_subassembly_assembly.py",
        "objects/obj_subassembly_library.py",
        "objects/obj_subassembly_preset_library.py",
        "objects/obj_superelevation.py",
        "objects/obj_surface.py",
        "objects/obj_surface_transition.py",
        "objects/obj_watertight_solid.py",
    }
    # The per-object compatibility paths listed above were migrated to
    # project_document_adapter.route_object_to_project_tree. The adapter is now
    # the single v1 owner of tree routing, so the recorded exception list is
    # empty and the guard covers every v1 package rather than objects alone.
    assert compatibility_paths, "keep the migrated path record for review history"
    allowed = {"objects/project_document_adapter.py"}
    actual = {
        ref.path
        for package in ("models", "services", "objects", "ui", "commands", "exchange", "common")
        for ref in _imports(package)
        if all(
            (
                ref.module in {"freecad.Corridor_Road.objects.obj_project", "objects.obj_project"},
                ref.symbol == "route_to_v1_tree",
            )
        )
    }
    assert actual == allowed, (
        "Direct legacy tree routing changed. v1 modules must call "
        "route_object_to_project_tree or ProjectDocumentAdapter instead of importing "
        f"route_to_v1_tree from the legacy project object.\nactual={sorted(actual)!r}"
    )
