from __future__ import annotations
import gc
import os
import resource

# Mobile/Voroa profile: favor bounded object retention and predictable collection.
MOBILE_GC = os.getenv('AEON_MOBILE_GC', '1') != '0'
if MOBILE_GC:
    gc.set_threshold(700, 10, 10)


def collect() -> int:
    """Run a full collection at explicit civilization checkpoints."""
    if not MOBILE_GC:
        return 0
    return gc.collect()


def rss_mb() -> float:
    """Return process peak RSS where supported (MiB)."""
    value = float(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    # Linux/Android reports KiB; macOS reports bytes.
    return value / (1024.0 if value > 1024 * 1024 else (1024.0 * 1024.0))


def snapshot() -> dict:
    return {'rss_peak_mb': round(rss_mb(), 2), 'gc_objects': len(gc.get_objects())}
