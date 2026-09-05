"""Reliable Termux launcher for the AEON Creator Command Center."""
from __future__ import annotations
import json
import sys


def main() -> int:
    print("AEON: starting Creator Command Center...", flush=True)
    try:
        from civilizations.command_center import CommandCenter
    except Exception as exc:
        print(f"AEON STARTUP ERROR: {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
        return 1
    center = CommandCenter()
    print("AEON COMMAND CENTER ONLINE", flush=True)
    print("Type commands at the CREATOR> prompt. Do not type CREATOR> yourself.", flush=True)
    print("Try: status | run 1 | inspect A017 | speak hello | shutdown", flush=True)
    while not center.shutdown:
        try:
            line = input("CREATOR> ")
        except (EOFError, KeyboardInterrupt):
            print("\nCommand center closed.")
            break
        if line.strip().lower() in {"exit", "quit"}:
            break
        try:
            print(json.dumps(center.issue(line), indent=2, default=str), flush=True)
        except Exception as exc:
            print(f"COMMAND ERROR: {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
