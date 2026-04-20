# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""Central compatibility names for remaining corridor migration boundaries."""

PREFERRED_COMMAND_ID = "CorridorRoad_GenerateCorridor"

PREFERRED_COMMAND_MODULE = "freecad.Corridor_Road.commands.cmd_generate_corridor"

PREFERRED_TASK_MODULE = "freecad.Corridor_Road.ui.task_corridor"

PREFERRED_TASK_PANEL_CLASS = "CorridorTaskPanel"

CORRIDOR_PROXY_TYPE = "CorridorLoft"
CORRIDOR_NAME_PREFIX = "CorridorLoft"
CORRIDOR_PROJECT_PROPERTY = "Corridor"
CORRIDOR_CHILD_LINK_PROPERTY = "ParentCorridor"
CORRIDOR_SKIP_MARKER_NAME = "CorridorSkipMarker"
CORRIDOR_SEGMENT_NAME = "CorridorSegment"
