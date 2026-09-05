from __future__ import annotations
import json, os, subprocess, sys, time, uuid
from pathlib import Path

ROOT = Path("world_state")
PID = ROOT / "aeon-daemon.pid"
COMMANDS = ROOT / "daemon_commands.jsonl"
RESPONSES = ROOT / "daemon_responses"
LATEST = ROOT / "latest.json"
LOG = ROOT / "daemon.log"


def _alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ValueError):
        return False


def ensure_daemon() -> int:
    """Ensure one detached civilization worker is running and return its PID."""
    ROOT.mkdir(parents=True, exist_ok=True)
    RESPONSES.mkdir(parents=True, exist_ok=True)
    if PID.exists():
        try:
            pid = int(PID.read_text(encoding="utf-8").strip())
            if _alive(pid):
                return pid
        except Exception:
            pass
        PID.unlink(missing_ok=True)
    with LOG.open("a", encoding="utf-8") as log:
        process = subprocess.Popen(
            [sys.executable, "-u", "-m", "civilizations.background", "--worker"],
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    return process.pid


def submit(command: str, timeout: float = 20.0) -> dict:
    """Send a control-plane request to the background civilization worker."""
    ensure_daemon()
    request_id = uuid.uuid4().hex
    response_path = RESPONSES / f"{request_id}.json"
    with COMMANDS.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"id": request_id, "command": command}) + "\n")
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if response_path.exists():
            try:
                result = json.loads(response_path.read_text(encoding="utf-8"))
                response_path.unlink(missing_ok=True)
                return result
            except (OSError, json.JSONDecodeError):
                pass
        time.sleep(0.05)
    return {"ok": False, "error": "background service did not respond in time"}


def _handle(command: str, world) -> dict:
    parts = command.strip().split()
    cmd = parts[0].lower() if parts else ""
    latest = json.loads(LATEST.read_text(encoding="utf-8")) if LATEST.exists() else world.step()

    if cmd in {"status", "observe", "look"}:
        return {"ok": True, "status": latest, "daemon": {"pid": os.getpid(), "running": True}}
    if cmd in {"health", "memory"}:
        return {"ok": True, "health": {"endurance": world.endurance.snapshot(world.platform.active_budget), "memory": world.endurance.rss_mb(), "gc_objects": world.endurance.collections, "python_pid": os.getpid()}}
    if cmd == "inspect" and len(parts) == 2:
        return {"ok": True, "agent": parts[1], "life": world.life.inspect(parts[1])}
    if cmd in {"world", "observatory"}:
        return {"ok": True, "observatory": world.platform.observatory()}
    if cmd in {"culture", "memes"}:
        return {"ok": True, "culture": world.platform.culture}
    if cmd in {"economy", "markets"}:
        return {"ok": True, "economy": {"markets": world.platform.markets, "resources": world.platform.resources, "jobs": len(world.platform.jobs)}}
    if cmd in {"organizations", "orgs"}:
        return {"ok": True, "organizations": world.platform.observatory()["organizations"]}
    if cmd in {"science", "discoveries"}:
        return {"ok": True, "science": world.platform.science[-20:], "discoveries": world.platform.metrics["discoveries"]}
    if cmd in {"metrics", "analytics"}:
        return {"ok": True, "metrics": world.platform.metrics}
    if cmd in {"pause", "freeze"}:
        return {"ok": True, "message": "Civilization paused."}
    if cmd in {"resume", "continue"}:
        return {"ok": True, "message": "Civilization resumed."}
    if cmd in {"shutdown", "kill"}:
        return {"ok": True, "message": "Autonomous background service stopped."}
    if cmd == "run":
        steps = max(1, min(1000, int(parts[1]))) if len(parts) > 1 else 1
        return {"ok": True, "result": world.run(steps)}
    if cmd == "save":
        world.platform.save()
        return {"ok": True, "message": "civilization persisted"}
    if cmd in {"speak", "tell"}:
        message = command[len(parts[0]):].strip()
        world.runtime.civilization.events.append(f"CREATOR: {message}")
        world.runtime.civilization.events = world.runtime.civilization.events[-100:]
        return {"ok": True, "message": "Message delivered to the civilization.", "text": message}
    if cmd == "chat":
        message = command[len(parts[0]):].strip()
        ranked = sorted(world.runtime.civilization.agents.values(), key=lambda a: world.life.self_models[a.agent_id].get("individuality", 0), reverse=True)[:3]
        replies = []
        for agent in ranked:
            model = world.life.self_models[agent.agent_id]
            state = world.life.states[agent.agent_id]
            replies.append({"agent": agent.agent_id, "reply": f"I am focused on {model.get('purpose', 'learning')}. My curiosity is {state.curiosity:.2f} and wellbeing is {state.wellbeing:.2f}. I will keep working while you are away.", "context": message})
        return {"ok": True, "replies": replies, "background_active": True}
    if cmd == "browse" and len(parts) == 3:
        result = world.world.browse(parts[1], parts[2])
        result["content"] = result["content"][:12000]
        return {"ok": True, "observation": result}
    return {"ok": False, "error": "unknown command"}


def worker() -> None:
    from .aeon_runtime import AEONRuntime
    from .autonomous_world import AutonomousWorld

    ROOT.mkdir(parents=True, exist_ok=True)
    RESPONSES.mkdir(parents=True, exist_ok=True)
    PID.write_text(str(os.getpid()), encoding="utf-8")
    paused = False
    shutdown = False
    cursor = 0
    try:
        runtime = AEONRuntime()
        world = AutonomousWorld(runtime, root=str(ROOT))
        while not shutdown:
            if COMMANDS.exists():
                lines = COMMANDS.read_text(encoding="utf-8").splitlines()
                while cursor < len(lines):
                    item = json.loads(lines[cursor])
                    cursor += 1
                    command = item["command"]
                    try:
                        response = _handle(command, world)
                    except Exception as exc:
                        response = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
                    normalized = command.strip().split()
                    name = normalized[0].lower() if normalized else ""
                    if name in {"pause", "freeze"}:
                        paused = True
                    elif name in {"resume", "continue"}:
                        paused = False
                    elif name in {"shutdown", "kill"}:
                        shutdown = True
                        paused = True
                    (RESPONSES / f"{item['id']}.json").write_text(json.dumps(response, default=str), encoding="utf-8")
                if cursor > 1000:
                    COMMANDS.write_text("\n".join(lines[cursor:]) + ("\n" if lines[cursor:] else ""), encoding="utf-8")
                    cursor = 0
            if not paused and not shutdown:
                world.run(1)
            time.sleep(0.25)
    finally:
        PID.unlink(missing_ok=True)


if __name__ == "__main__" and "--worker" in sys.argv:
    worker()
