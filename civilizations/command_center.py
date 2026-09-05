from __future__ import annotations

import argparse
import json
import shlex
from dataclasses import dataclass, field
from datetime import datetime, timezone

from .aeon_runtime import AEONRuntime
from .charter import CreatorCharter


@dataclass
class CreatorCommand:
    text: str
    timestamp: str
    acknowledged: bool = True


@dataclass
class CommandCenter:
    """Termux-friendly local control console for an AEON civilization.

    It provides creator communication, simulation control, and an emergency
    freeze. Generated programs are never executed by this console.
    """

    runtime: AEONRuntime = field(default_factory=AEONRuntime)
    charter: CreatorCharter = field(default_factory=CreatorCharter)
    paused: bool = False
    shutdown: bool = False
    history: list[CreatorCommand] = field(default_factory=list)

    def issue(self, text: str) -> dict:
        text = text.strip()
        if not text:
            return {"ok": False, "error": "empty command"}
        self.history.append(CreatorCommand(text, datetime.now(timezone.utc).isoformat()))
        command = text.lower()
        if command in {"status", "observe", "look"}:
            return {"ok": True, "status": self.status()}
        if command in {"pause", "freeze"}:
            self.paused = True
            return {"ok": True, "message": "Civilization paused."}
        if command in {"resume", "continue"}:
            if self.shutdown:
                return {"ok": False, "error": "world is shut down; start a new runtime to restart"}
            self.paused = False
            return {"ok": True, "message": "Civilization resumed."}
        if command in {"shutdown", "kill", "emergency shutdown"}:
            self.shutdown = True
            self.paused = True
            return {"ok": True, "message": "EMERGENCY SHUTDOWN: civilization frozen; host files untouched."}
        if command == "charter":
            return {"ok": True, "charter": self.charter.prompt(), "fingerprint": self.charter.fingerprint}
        if command.startswith("speak "):
            message = text[6:].strip()
            self.runtime.civilization.events.append(f"CREATOR: {message}")
            self.runtime.civilization.events = self.runtime.civilization.events[-100:]
            return {"ok": True, "message": "Creator message entered into the civilization event stream.", "text": message}
        if command.startswith("run "):
            if self.paused or self.shutdown:
                return {"ok": False, "error": "civilization is paused"}
            try:
                steps = max(1, min(100, int(shlex.split(text)[1])))
            except (IndexError, ValueError):
                return {"ok": False, "error": "usage: run <1-100>"}
            return {"ok": True, "state": self.runtime.run(steps)}
        return {"ok": False, "error": "try: status | charter | speak <message> | run <n> | pause | resume | shutdown"}

    def status(self) -> dict:
        state = self.runtime.civilization.snapshot()
        state.update({"paused": self.paused, "shutdown": self.shutdown, "creator": self.charter.creator_name, "charter_fingerprint": self.charter.fingerprint, "commands": len(self.history)})
        return state


def main() -> None:
    parser = argparse.ArgumentParser(description="AEON Creator Command Center")
    parser.add_argument("--once", help="execute one command and exit")
    args = parser.parse_args()
    center = CommandCenter()
    print("AEON COMMAND CENTER ONLINE")
    print("Creator authority initialized.")
    print("Type: charter | status | speak <message> | run <n> | pause | resume | shutdown | exit")
    if args.once:
        print(json.dumps(center.issue(args.once), indent=2, default=str))
        return
    while not center.shutdown:
        try:
            line = input("CREATOR> ")
        except (EOFError, KeyboardInterrupt):
            print("\nCommand center closed.")
            break
        if line.strip().lower() in {"exit", "quit"}:
            break
        print(json.dumps(center.issue(line), indent=2, default=str))


if __name__ == "__main__":
    main()
