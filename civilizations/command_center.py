from __future__ import annotations

import argparse
import json
import shlex
from dataclasses import dataclass, field
from datetime import datetime, timezone

from .aeon_runtime import AEONRuntime
from .charter import CreatorCharter
from .inbox import Inbox
from .treasury import Treasury


@dataclass
class CreatorCommand:
    text: str
    timestamp: str
    acknowledged: bool = True


@dataclass
class CommandCenter:
    """Termux-friendly Creator interface for the local AEON simulation."""

    runtime: AEONRuntime | None = None
    inbox: Inbox | None = None
    treasury: Treasury | None = None
    minimum_balance: float = 10_000.0
    charter: CreatorCharter = field(default_factory=CreatorCharter)
    paused: bool = False
    shutdown: bool = False
    history: list[CreatorCommand] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.runtime is None:
            self.runtime = AEONRuntime()

    def send_to_all(self, text: str, tick: int) -> dict:
        if self.inbox is None:
            self.runtime.civilization.events.append(f"CREATOR: {text}")
            return {"sender": "CREATOR", "recipient": "ALL", "text": text, "tick": tick}
        return self.inbox.send("OWNER", "ALL", text, tick).__dict__

    def send_to_agent(self, agent_id: str, text: str, tick: int) -> dict:
        if self.inbox is None:
            self.runtime.civilization.events.append(f"CREATOR -> {agent_id}: {text}")
            return {"sender": "CREATOR", "recipient": agent_id, "text": text, "tick": tick}
        return self.inbox.send("OWNER", agent_id, text, tick).__dict__

    def monthly_reminder(self, month: int, tick: int) -> dict | None:
        if self.treasury is not None and self.treasury.balance < self.minimum_balance:
            return self.inbox.send("TREASURY", "OWNER", f"Month {month}: simulated treasury is below the operating reserve. Top-up required before the next monthly cycle.", tick).__dict__
        return None

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
        if command.startswith("tell "):
            parts = shlex.split(text)
            if len(parts) < 3:
                return {"ok": False, "error": "usage: tell <agent_id> <message>"}
            return {"ok": True, "message": self.send_to_agent(parts[1], " ".join(parts[2:]), self.runtime.civilization.tick)}
        if command.startswith("run "):
            if self.paused or self.shutdown:
                return {"ok": False, "error": "civilization is paused"}
            try:
                steps = max(1, min(100, int(shlex.split(text)[1])))
            except (IndexError, ValueError):
                return {"ok": False, "error": "usage: run <1-100>"}
            return {"ok": True, "state": self.runtime.run(steps)}
        return {"ok": False, "error": "try: status | charter | speak <message> | tell <agent> <message> | run <n> | pause | resume | shutdown"}

    def status(self) -> dict:
        state = self.runtime.civilization.snapshot()
        state.update({"paused": self.paused, "shutdown": self.shutdown, "creator": self.charter.creator_name, "charter_fingerprint": self.charter.fingerprint, "commands": len(self.history)})
        if self.treasury is not None:
            state["treasury"] = round(self.treasury.balance, 2)
        return state


def main() -> None:
    parser = argparse.ArgumentParser(description="AEON Creator Command Center")
    parser.add_argument("--once", help="execute one command and exit")
    args = parser.parse_args()
    center = CommandCenter()
    print("AEON COMMAND CENTER ONLINE")
    print("Creator authority initialized.")
    print("Type: charter | status | speak <message> | tell <agent> <message> | run <n> | pause | resume | shutdown | exit")
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
