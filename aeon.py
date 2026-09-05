"""AEON launcher: starts the autonomous world separately from its control console."""
from __future__ import annotations
import gc
import runpy
import sys
from pathlib import Path
from civilizations.background import ensure_daemon

gc.set_threshold(700, 10, 10)


def main() -> int:
    root = Path(__file__).resolve().parent
    sys.path.insert(0, str(root))
    try:
        pid = ensure_daemon()
        print(f"AEON: background civilization online (pid {pid})", flush=True)
        runpy.run_module("civilizations.command_center", run_name="__main__")
    except Exception as exc:
        print(f"AEON STARTUP ERROR: {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
        return 1
    finally:
        gc.collect()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
