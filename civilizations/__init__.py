"""AI civilization package."""

__all__ = ["Agent", "Civilization", "Idea"]


def __getattr__(name):
    if name in __all__:
        from .core import Agent, Civilization, Idea
        return {"Agent": Agent, "Civilization": Civilization, "Idea": Idea}[name]
    raise AttributeError(name)
