import os
import sys


def ensure_package_on_sys_path():
    pkg_dir = os.path.dirname(os.path.abspath(__file__))
    if pkg_dir not in sys.path:
        sys.path.insert(0, pkg_dir)
    return pkg_dir


ensure_package_on_sys_path()
