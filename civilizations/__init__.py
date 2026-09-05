"""AI civilization package."""

__all__ = ["Agent", "Civilization", "Idea", "CivilizationArena", "ArenaConfig", "ForecastCommitment", "ForecastOutcome", "CivilizationScore"]


def __getattr__(name):
    if name in {"Agent", "Civilization", "Idea"}:
        from .core import Agent, Civilization, Idea
        return {"Agent": Agent, "Civilization": Civilization, "Idea": Idea}[name]
    if name in {"CivilizationArena", "ArenaConfig", "ForecastCommitment", "ForecastOutcome", "CivilizationScore"}:
        from .arena import ArenaConfig, CivilizationArena, CivilizationScore, ForecastCommitment, ForecastOutcome
        return {"CivilizationArena": CivilizationArena, "ArenaConfig": ArenaConfig, "ForecastCommitment": ForecastCommitment, "ForecastOutcome": ForecastOutcome}[name]
    raise AttributeError(name)
