"""Low-memory Termux launcher for the AEON Creator Command Center."""
from __future__ import annotations
import gc
import runpy
import sys
from pathlib import Path

# Keep the mobile process conservative before importing the civilization graph.
gc.set_threshold(700, 10, 10)

def main() -> int:
    root = Path(__file__).resolve().parent
    sys.path.insert(0, str(root))
    print("AEON: starting Creator Command Center...", flush=True)
    try:
        runpy.run_module("civilizations.command_center", run_name="__main__")
    except Exception as exc:
        print(f"AEON STARTUP ERROR: {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
        return 1
    finally:
        gc.collect()

if __name__ == "__main__":
    raise SystemExit(main())
