from __future__ import annotations
import argparse, json
from .background import submit


def main() -> None:
    parser = argparse.ArgumentParser(description="AEON Creator Command Center")
    parser.add_argument("--once")
    args = parser.parse_args()
    print("AEON COMMAND CENTER ONLINE", flush=True)
    print("The civilization continues running independently in the background.", flush=True)
    print("Close this console at any time; the background world remains active.", flush=True)
    if args.once:
        print(json.dumps(submit(args.once), indent=2, default=str))
        return
    while True:
        try:
            line = input("CREATOR> ")
        except (EOFError, KeyboardInterrupt):
            print("\nCommand center closed. Background civilization remains online.")
            break
        if line.strip().lower() in {"exit", "quit"}:
            print("Command center closed. Background civilization remains online.")
            break
        print(json.dumps(submit(line), indent=2, default=str), flush=True)


if __name__ == "__main__":
    main()
