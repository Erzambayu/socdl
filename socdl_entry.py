"""PyInstaller entry point.

Frozen binaries can't use the `socdl` console-script shim, so we expose
a tiny module that PyInstaller can point at directly.
"""
from socdl.cli import main

if __name__ == "__main__":
    main()
