from __future__ import annotations

import argparse
import json
import time

from civilizations import Civilization


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the AI civilization simulation")
    parser.add_argument("--agents", type=int, default=100)
    parser.add_argument("--ticks", type=int, default=0, help="0 means run continuously")
    parser.add_argument("--delay", type=float, default=1.0)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    civilization = Civilization(size=args.agents, seed=args.seed)
    print("AI CIVILIZATION ONLINE")
    print("======================")
    print(f"Population: {args.agents}")
    print("Press Ctrl+C to stop.\n")

    completed = 0
    try:
        while args.ticks == 0 or completed < args.ticks:
            state = civilization.step()
            completed += 1
            print(json.dumps(state, indent=2))
            if args.ticks == 0 or completed < args.ticks:
                time.sleep(max(0.0, args.delay))
    except KeyboardInterrupt:
        print("\nCivilization paused.")


if __name__ == "__main__":
    main()
