"""Reliable Termux launcher for the AEON Creator Command Center."""
from __future__ import annotations
import sys


def main() -> int:
    print("AEON: starting Creator Command Center...", flush=True)
    try:
        from civilizations.command_center import main as command_main
    except Exception as exc:
        print(f"AEON STARTUP ERROR: {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
        print("Run: git pull --rebase", file=sys.stderr, flush=True)
        return 1
    command_main()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
