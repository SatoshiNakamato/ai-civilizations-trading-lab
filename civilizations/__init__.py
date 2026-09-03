"""AI civilization package.

Core classes are exposed lazily so ``python -m civilizations.core`` does not
load the core module twice before execution.
"""

__all__ = ["Agent", "Civilization", "Idea"]


def __getattr__(name):
    if name in __all__:
        from .core import Agent, Civilization, Idea
        return {"Agent": Agent, "Civilization": Civilization, "Idea": Idea}[name]
    raise AttributeError(name)
