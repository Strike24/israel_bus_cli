"""Module launcher.

Preferred: python -m israel_bus_cli
This file now supports being executed directly as a script too.
"""

try:  # Normal package execution
    from .cli import main  # type: ignore
except ImportError:  # Direct script execution fallback
    import sys, pathlib, importlib
    pkg_dir = pathlib.Path(__file__).resolve().parent
    root_dir = pkg_dir.parent
    if str(root_dir) not in sys.path:
        sys.path.insert(0, str(root_dir))
    # Now import package normally
    pkg = importlib.import_module("israel_bus_cli.cli")
    main = pkg.main  # type: ignore

if __name__ == "__main__":  # pragma: no cover
    main()
