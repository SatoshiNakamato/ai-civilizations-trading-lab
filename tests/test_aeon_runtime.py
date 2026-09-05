from civilizations.internet_world import InternetWorld
from civilizations.life_engine import LifeEngine


def test_life_persists_memory_reflection_and_relationships():
    life = LifeEngine(seed=7)
    life.register("A001", ["curiosity"])
    life.register("A002", ["cooperation"])
    life.remember("A001", 1, "I discovered a useful pattern.", "discovery", 0.9)
    life.interact("A001", "A002", 2, 0.8)
    reflection = life.reflect("A001", 3)
    assert reflection
    snap = life.snapshot()
    assert snap["memories"] >= 2
    assert snap["relationships"] >= 1
    assert snap["reflections"] == 1


def test_world_confines_artifacts(tmp_path):
    world = InternetWorld(str(tmp_path))
    created = world.create_artifact("A001", "A001/idea.md", "hello")
    assert created == "A001/idea.md"
    assert (tmp_path / created).read_text() == "hello"


def test_world_rejects_non_https_targets(tmp_path):
    world = InternetWorld(str(tmp_path))
    for url in ("http://example.com", "file:///etc/passwd", "ftp://example.com"):
        try:
            world.browse("A001", url)
        except PermissionError:
            pass
        else:
            raise AssertionError(f"unsafe URL scheme was allowed: {url}")


def test_world_rejects_private_and_loopback_hosts(tmp_path):
    world = InternetWorld(str(tmp_path))
    for url in ("https://127.0.0.1", "https://localhost", "https://10.0.0.1"):
        try:
            world.browse("A001", url)
        except PermissionError:
            pass
        else:
            raise AssertionError(f"non-public host was allowed: {url}")
