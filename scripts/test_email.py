"""One-shot SMTP delivery test for the hosted worker environment.

This script deliberately bypasses the notification governor so it tests the
SMTP credentials and transport directly. It never places an order or calls an
exchange. Run it inside the same environment where the CIVILIZATION_* SMTP
variables are configured (for example, the hosted worker).

Use ``--dry-run`` to validate configuration without sending an email.
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Allow direct execution from the repository root with:
#     python scripts/test_email.py
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from civilizations.notifications import Notification, SMTPEmailSender


def _configured(value: str | None) -> str:
    return "set" if value else "MISSING"


def main() -> int:
    parser = argparse.ArgumentParser(description="Test AEON SMTP configuration and delivery")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="validate SMTP configuration without sending an email",
    )
    args = parser.parse_args()

    print("=== AEON SMTP DELIVERY TEST ===", flush=True)
    print(f"CIVILIZATION_SMTP_HOST = {_configured(os.getenv('CIVILIZATION_SMTP_HOST'))}", flush=True)
    print(f"CIVILIZATION_SMTP_PORT = {os.getenv('CIVILIZATION_SMTP_PORT', '587')}", flush=True)
    print(f"CIVILIZATION_SMTP_USER = {_configured(os.getenv('CIVILIZATION_SMTP_USER'))}", flush=True)
    print(f"CIVILIZATION_SMTP_PASSWORD = {_configured(os.getenv('CIVILIZATION_SMTP_PASSWORD'))}", flush=True)
    print(f"CIVILIZATION_ALERT_FROM = {_configured(os.getenv('CIVILIZATION_ALERT_FROM'))}", flush=True)
    print(f"CIVILIZATION_ALERT_EMAIL = {_configured(os.getenv('CIVILIZATION_ALERT_EMAIL'))}", flush=True)

    required = (
        "CIVILIZATION_SMTP_HOST",
        "CIVILIZATION_SMTP_USER",
        "CIVILIZATION_SMTP_PASSWORD",
        "CIVILIZATION_ALERT_EMAIL",
    )
    missing = [name for name in required if not os.getenv(name)]
    if missing:
        print(f"RESULT: NOT RUN; missing required variables: {', '.join(missing)}", flush=True)
        return 2

    password = os.getenv("CIVILIZATION_SMTP_PASSWORD", "")
    if not password.strip():
        print("RESULT: NOT RUN; SMTP password is empty", flush=True)
        return 2

    if args.dry_run:
        print("RESULT: CONFIGURATION OK; no email sent (--dry-run).", flush=True)
        return 0

    now = datetime.now(timezone.utc).isoformat()
    notification = Notification(
        severity="high",
        subject="[AEON TEST] SMTP delivery verified",
        body=(
            "This is a one-shot SMTP delivery test from the AI Civilizations Trading Lab.\n\n"
            f"UTC time: {now}\n"
            "No trade was executed.\n"
            "No exchange order was submitted.\n"
            "This message verifies the configured SMTP transport only.\n"
        ),
        fingerprint="smtp-test",
    )

    try:
        SMTPEmailSender()(notification)
    except Exception as exc:
        print(f"RESULT: FAILED; {type(exc).__name__}: {exc}", flush=True)
        if type(exc).__name__ == "SMTPDataError" and "5.4.5" in str(exc):
            print("ACTION: Gmail has rejected delivery because its sending quota is exhausted. No code change can bypass that server-side quota.", flush=True)
            print("ACTION: Do not repeatedly rerun this smoke test; wait for the quota window to reset before the next live delivery test.", flush=True)
        return 1

    print("RESULT: SENT; SMTP accepted the test message.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
