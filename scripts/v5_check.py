"""Run the V5 twelve-capability release gate."""
from __future__ import annotations

import json
import sys

from civilizations.v5_frontier import V5Frontier


def main() -> int:
    report = V5Frontier(".").check()
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
