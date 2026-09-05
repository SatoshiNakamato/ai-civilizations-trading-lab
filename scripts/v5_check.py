"""Run the V5 twelve-capability release gate."""
from __future__ import annotations

import json
import sys
from pathlib import Path

# Make the repository root importable when this file is executed directly
# from the repository root (``python scripts/v5_check.py``).
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from civilizations.v5_frontier import V5Frontier


def main() -> int:
    report = V5Frontier(ROOT).check()
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
