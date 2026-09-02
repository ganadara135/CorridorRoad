import FreeCAD as App

from freecad.Corridor_Road.qt_compat import QtWidgets
from freecad.Corridor_Road.v1.commands.cmd_alignment_editor import V1AlignmentEditorTaskPanel
from freecad.Corridor_Road.v1.commands.cmd_drainage_editor import V1DrainageEditorTaskPanel
from freecad.Corridor_Road.v1.commands.cmd_drainage_review import V1DrainageReviewTaskPanel
from freecad.Corridor_Road.v1.commands.cmd_edit_tin import V1TINEditorTaskPanel
from freecad.Corridor_Road.v1.commands.cmd_profile_editor import V1ProfileEditorTaskPanel
from freecad.Corridor_Road.v1.commands.cmd_structure_editor import V1StructureEditorTaskPanel
from freecad.Corridor_Road.v1.commands.cmd_subassembly_designer import V1SubAssemblyDesignerTaskPanel
from freecad.Corridor_Road.v1.commands.cmd_subassembly_editor import V1AssemblySubassemblyEditorTaskPanel
from freecad.Corridor_Road.v1.objects.obj_subassembly_library import find_v1_subassembly_library
from freecad.Corridor_Road.v1.ui.editors.alignment_editor import (
    V1AlignmentEditorTaskPanel as UIAlignmentPanel,
)
from freecad.Corridor_Road.v1.ui.editors.drainage_editor import (
    V1DrainageEditorTaskPanel as UIDrainagePanel,
)
from freecad.Corridor_Road.v1.ui.editors.profile_editor import V1ProfileEditorTaskPanel as UIProfilePanel
from freecad.Corridor_Road.v1.ui.editors.structure_editor import V1StructureEditorTaskPanel as UIStructurePanel
from freecad.Corridor_Road.v1.ui.editors.subassembly_designer import (
    V1SubAssemblyDesignerTaskPanel as UISubAssemblyDesignerPanel,
)
from freecad.Corridor_Road.v1.ui.editors.subassembly_editor import (
    V1AssemblySubassemblyEditorTaskPanel as UIAssemblySubassemblyPanel,
)
from freecad.Corridor_Road.v1.ui.editors.tin_editor import V1TINEditorTaskPanel as UITINPanel
from freecad.Corridor_Road.v1.ui.viewers.drainage_review_view import (
    V1DrainageReviewTaskPanel as UIDrainageReviewPanel,
)


def _ensure_qapp():
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def test_command_exports_are_the_ui_owned_phase3_panel_classes() -> None:
    assert V1StructureEditorTaskPanel is UIStructurePanel
    assert V1ProfileEditorTaskPanel is UIProfilePanel
    assert V1SubAssemblyDesignerTaskPanel is UISubAssemblyDesignerPanel
    assert V1AssemblySubassemblyEditorTaskPanel is UIAssemblySubassemblyPanel
    assert V1DrainageEditorTaskPanel is UIDrainagePanel
    assert V1DrainageReviewTaskPanel is UIDrainageReviewPanel
    assert V1AlignmentEditorTaskPanel is UIAlignmentPanel
    assert V1TINEditorTaskPanel is UITINPanel


def test_subassembly_designer_open_and_close_does_not_persist_source() -> None:
    _ensure_qapp()
    document = App.newDocument("CRPhase3SubAssemblyDesignerBoundary")
    try:
        assert find_v1_subassembly_library(document) is None

        panel = V1SubAssemblyDesignerTaskPanel(document=document)

        assert panel.form is not None
        assert panel.reject() is True
        assert find_v1_subassembly_library(document) is None
    finally:
        App.closeDocument(document.Name)
