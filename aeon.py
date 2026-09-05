"""AEON launcher: runs the autonomous world without orphaning workers."""
from __future__ import annotations

import gc
import os
import runpy
import sys
from pathlib import Path

from civilizations.background import ensure_daemon, worker

gc.set_threshold(700, 10, 10)


def main() -> int:
    root = Path(__file__).resolve().parent
    sys.path.insert(0, str(root))
    try:
        # Hosting platforms normally run without a TTY. In that mode the
        # service itself owns the worker process; spawning a detached child
        # would let an old worker survive redeploys and run stale code.
        # Keep the detached daemon only for an interactive local console.
        foreground = os.getenv("AEON_FOREGROUND", "").strip().lower() in {"1", "true", "yes", "on"}
        if foreground or not sys.stdin.isatty():
            worker()
            return 0

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
