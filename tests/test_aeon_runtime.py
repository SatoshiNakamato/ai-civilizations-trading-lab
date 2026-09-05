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


def test_world_rejects_unapproved_websites(tmp_path):
    world = InternetWorld(str(tmp_path))
    try:
        world.browse("A001", "https://example.com")
    except PermissionError:
        pass
    else:
        raise AssertionError("unapproved domain was allowed")
