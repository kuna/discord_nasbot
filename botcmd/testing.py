from pathlib import Path

from botcmd.loader import _import_handler


def load_plugin_handler(test_file):
    """Import the handler.py that sits next to a plugin's test file.

    Usage from plugins/<name>/test_handler.py:
        module = load_plugin_handler(__file__)
    """
    plugin_dir = Path(test_file).resolve().parent
    return _import_handler(plugin_dir.parent.name, plugin_dir.name, plugin_dir / "handler.py")
