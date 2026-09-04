from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class TickerChoice:
    symbol: str
    name: str
    score: float
    reasons: tuple[str, ...]


class TickerBrain:
    """Generate short, pronounceable, theme-linked token symbols.

    The generator is deterministic for a given thesis/agent/cycle, so the same
    research event can be reproduced from the audit log. It does not claim a
    ticker is legally or commercially available; callers should still check
    live launch validation before broadcasting.
    """

    VOWELS = "AEIOU"
    BAD = {"TEST", "COIN", "TOKEN", "SCAM", "RUG", "MOON", "SAFE"}

    def choose(self, *, thesis: str, agent: str, cycle: int, existing: set[str] | None = None) -> TickerChoice:
        existing = {self.clean(x) for x in (existing or set())}
        seed = hashlib.sha256(f"{agent}|{cycle}|{thesis}".encode()).hexdigest().upper()
        words = re.findall(r"[A-Za-z]{3,12}", thesis.upper())
        theme = next((w for w in words if w not in {"TOKEN", "RESEARCH", "HYPOTHESIS"}), "NOVA")

        candidates = []
        for offset in range(12):
            chunk = seed[offset * 2: offset * 2 + 8]
            a = chr(65 + int(chunk[:2], 16) % 26)
            b = chr(65 + int(chunk[2:4], 16) % 26)
            c = chr(65 + int(chunk[4:6], 16) % 26)
            prefix = re.sub(r"[^A-Z]", "", theme)[:3]
            forms = [prefix, prefix + a, a + b + c, prefix[:2] + a + b]
            for symbol in forms:
                symbol = self.clean(symbol)
                if 3 <= len(symbol) <= 6:
                    candidates.append(symbol)

        scored = []
        for symbol in candidates:
            if symbol in existing or symbol in self.BAD:
                continue
            vowels = sum(ch in self.VOWELS for ch in symbol)
            unique = len(set(symbol)) / len(symbol)
            pronounceable = 1.0 if 1 <= vowels <= max(1, len(symbol) // 2) else 0.55
            short = 1.0 - abs(len(symbol) - 4) * 0.12
            score = max(0.0, min(1.0, 0.35 * unique + 0.35 * pronounceable + 0.30 * short))
            scored.append((score, symbol))
        score, symbol = max(scored or [(0.5, "NOVA")])
        return TickerChoice(
            symbol=symbol,
            name=f"{theme.title()} Civilization {cycle}",
            score=score,
            reasons=("short", "pronounceable", "thesis-linked", "collision-avoiding"),
        )

    @staticmethod
    def clean(symbol: str) -> str:
        return re.sub(r"[^A-Z0-9]", "", str(symbol).upper())[:10]
