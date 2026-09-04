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
    """Generate compact, pronounceable, meme-theme-linked token identities."""
    VOWELS = "AEIOU"
    BAD = {"TEST", "COIN", "TOKEN", "SCAM", "RUG", "MOON", "SAFE"}
    MEME_WORDS = ("VIRAL", "FROG", "CAT", "PEPE", "DOGE", "MOCHI", "BONGO", "PULSE", "MEME")

    def choose(self, *, thesis: str, agent: str, cycle: int, existing: set[str] | None = None) -> TickerChoice:
        existing = {self.clean(x) for x in (existing or set())}
        seed = hashlib.sha256(f"{agent}|{cycle}|{thesis}".encode()).hexdigest().upper()
        words = re.findall(r"[A-Za-z]{3,12}", thesis.upper())
        theme = next((w for w in words if w in self.MEME_WORDS), None) or next((w for w in words if w not in {"TOKEN", "RESEARCH", "HYPOTHESIS", "MOMENTUM", "LIQUIDITY", "CROSS", "MARKET", "EVENT", "DRIVEN"}), "NOVA")
        prefix = re.sub(r"[^A-Z]", "", theme)[:4]
        candidates = []
        for offset in range(16):
            chunk = seed[offset * 2: offset * 2 + 8]
            a = chr(65 + int(chunk[:2], 16) % 26); b = chr(65 + int(chunk[2:4], 16) % 26); c = chr(65 + int(chunk[4:6], 16) % 26)
            forms = [prefix[:3], prefix[:3] + a, prefix[:2] + a + b, a + b + c, prefix[:2] + a + b + c]
            for symbol in forms:
                symbol = self.clean(symbol)
                if 3 <= len(symbol) <= 6: candidates.append(symbol)
        scored = []
        for symbol in candidates:
            if symbol in existing or symbol in self.BAD: continue
            vowels = sum(ch in self.VOWELS for ch in symbol); unique = len(set(symbol)) / len(symbol)
            pronounceable = 1.0 if 1 <= vowels <= max(1, len(symbol) // 2) else 0.55
            short = 1.0 - abs(len(symbol) - 4) * 0.12
            theme_bonus = 0.10 if symbol.startswith(prefix[:2]) else 0.0
            score = max(0.0, min(1.0, 0.30 * unique + 0.30 * pronounceable + 0.25 * short + theme_bonus))
            scored.append((score, symbol))
        score, symbol = max(scored or [(0.5, "NOVA")])
        return TickerChoice(symbol=symbol, name=f"{theme.title()} Signal {cycle}", score=score, reasons=("short", "pronounceable", "meme-theme-aware", "collision-avoiding"))

    @staticmethod
    def clean(symbol: str) -> str:
        return re.sub(r"[^A-Z0-9]", "", str(symbol).upper())[:10]
