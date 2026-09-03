from __future__ import annotations

from statistics import mean, pstdev


def compute_features(candles: list[dict]) -> dict:
    closes = [float(x["close"]) for x in candles if float(x.get("close", 0)) > 0]
    volumes = [float(x.get("volume", 0)) for x in candles]
    if len(closes) < 2:
        return {"samples": len(closes), "return": 0.0, "volatility": 0.0, "trend": 0.0, "volume_ratio": 0.0}
    returns = [(closes[i] / closes[i - 1]) - 1 for i in range(1, len(closes))]
    trend = closes[-1] / closes[0] - 1
    return {
        "samples": len(closes),
        "return": trend,
        "volatility": pstdev(returns) if len(returns) > 1 else 0.0,
        "trend": trend,
        "volume_ratio": volumes[-1] / mean(volumes[:-1]) if len(volumes) > 1 and mean(volumes[:-1]) else 0.0,
    }
