from __future__ import annotations


def assess_candles(candles: list[dict]) -> dict:
    timestamps = [int(x.get("open_time", 0)) for x in candles]
    closes = [float(x.get("close", 0)) for x in candles]
    ordered = timestamps == sorted(timestamps)
    positive = all(x > 0 for x in closes)
    unique = len(timestamps) == len(set(timestamps))
    return {
        "samples": len(candles),
        "ordered": ordered,
        "unique_timestamps": unique,
        "positive_closes": positive,
        "usable": bool(candles) and ordered and unique and positive,
    }
