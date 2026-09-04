from __future__ import annotations

import argparse
import json
import tempfile

from release.paper_fixture import build_paper_release_fixture


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the deterministic paper-only release fixture")
    parser.add_argument("--data-dir", default=None, help="Directory for fixture ledger and audit files")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory() if args.data_dir is None else _existing_dir(args.data_dir) as data_dir:
        report = build_paper_release_fixture(data_dir)
        print(json.dumps(report.__dict__, indent=2, sort_keys=True))
    return 0


class _existing_dir:
    def __init__(self, path: str):
        self.path = path

    def __enter__(self):
        return self.path

    def __exit__(self, exc_type, exc, tb):
        return False


if __name__ == "__main__":
    raise SystemExit(main())
