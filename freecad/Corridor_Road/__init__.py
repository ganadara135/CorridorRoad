import os
import sys


def ensure_package_on_sys_path():
    pkg_dir = os.path.dirname(os.path.abspath(__file__))
    if pkg_dir not in sys.path:
        sys.path.insert(0, pkg_dir)
    return pkg_dir


ensure_package_on_sys_path()


def install_virtual_path_mappings():
    """Install legacy->canonical module aliases for FCStd proxy restore."""
    try:
        from .virtual_paths import install_virtual_path_mappings as _install

        _install()
    except Exception:
        # Keep startup resilient; mapping is best-effort compatibility glue.
        pass


install_virtual_path_mappings()
