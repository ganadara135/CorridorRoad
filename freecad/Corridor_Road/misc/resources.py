import os


_PKG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_RESOURCES_DIR = os.path.join(_PKG_DIR, "resources")
_ICONS_DIR = os.path.join(_RESOURCES_DIR, "icons")
_UI_DIR = os.path.join(_RESOURCES_DIR, "ui")


def package_path(*parts):
    return os.path.join(_PKG_DIR, *parts)


def resource_path(*parts):
    return os.path.join(_RESOURCES_DIR, *parts)


def icon_path(filename):
    return os.path.join(_ICONS_DIR, filename)


def ui_path(filename):
    return os.path.join(_UI_DIR, filename)
