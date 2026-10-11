# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""Restore-only stub of the retired legacy design terrain.

Phase P5 of docsV1/V1_LEGACY_PROXY_MIGRATION_DESIGN.md removed the implementation. Saved
documents still name this module and these classes as their objects' proxies, so both stay;
the objects keep the properties and geometry they were saved with and no longer recompute.
"""

from .legacy_proxy_stub import RestoreOnlyProxy, RestoreOnlyViewProvider


class DesignTerrain(RestoreOnlyProxy):
    """Restore-only proxy of a legacy DesignTerrain object."""


class ViewProviderDesignTerrain(RestoreOnlyViewProvider):
    """Restore-only view provider of a legacy DesignTerrain object."""
