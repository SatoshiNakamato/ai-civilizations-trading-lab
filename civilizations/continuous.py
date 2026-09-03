from __future__ import annotations

import signal
import threading
import time
from dataclasses import dataclass
from .core import Civilization

@dataclass
class RuntimeStats:
    cycles: int = 0
    started_at: float = 0.0
    last_cycle_at: float = 0.0
    errors: int = 0

class ContinuousCivilization:
    """Long-running research simulation. No trading or financial execution is performed."""
    def __init__(self, size: int = 100, interval_seconds: int = 60, seed: int = 42):
        self.civilization = Civilization(size=size, seed=seed)
        self.interval_seconds = max(5, int(interval_seconds))
        self.stats = RuntimeStats(started_at=time.time())
        self.stop_event = threading.Event()
        self.last_state = self.civilization.snapshot()

    def cycle(self):
        try:
            self.last_state = self.civilization.step()
            self.stats.cycles += 1
            self.stats.last_cycle_at = time.time()
            return self.last_state
        except Exception:
            self.stats.errors += 1
            raise

    def run_forever(self):
        print('CONTINUOUS AI CIVILIZATION ONLINE')
        print(f'Population: {len(self.civilization.agents)}')
        print(f'Cycle interval: {self.interval_seconds}s')
        print('Mode: research/validation only; no financial execution')
        while not self.stop_event.is_set():
            started = time.time()
            try:
                state = self.cycle()
                best = state.get('best_agents', [{}])[0]
                print(f"cycle={self.stats.cycles} generation={state['generation']} ideas={state['ideas']} predictions={state['evolution']['predictions']} resolved={state['evolution']['resolved_predictions']} top={best.get('id','-')} capability={best.get('capability','-')}", flush=True)
            except Exception as exc:
                print(f'cycle error: {type(exc).__name__}: {exc}', flush=True)
            remaining = max(0.0, self.interval_seconds - (time.time() - started))
            self.stop_event.wait(remaining)
        print('Civilization stopped.')

    def stop(self):
        self.stop_event.set()


def main():
    runtime = ContinuousCivilization()
    def handle_signal(signum, frame):
        print('\nShutdown requested...', flush=True)
        runtime.stop()
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)
    runtime.run_forever()

if __name__ == '__main__':
    main()
