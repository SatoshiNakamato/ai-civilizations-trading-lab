"""One-shot SMTP delivery test for the hosted worker environment.

This script deliberately bypasses the notification governor so it tests the
SMTP credentials and transport directly. It never places an order or calls an
exchange. Run it inside the same environment where the CIVILIZATION_* SMTP
variables are configured (for example, the hosted worker).
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone

from civilizations.notifications import Notification, SMTPEmailSender


def _configured(value: str | None) -> str:
    return "set" if value else "MISSING"


def main() -> int:
    print("=== AEON SMTP DELIVERY TEST ===", flush=True)
    print(f"CIVILIZATION_SMTP_HOST = {_configured(os.getenv('CIVILIZATION_SMTP_HOST'))}", flush=True)
    print(f"CIVILIZATION_SMTP_PORT = {os.getenv('CIVILIZATION_SMTP_PORT', '587')}", flush=True)
    print(f"CIVILIZATION_SMTP_USER = {_configured(os.getenv('CIVILIZATION_SMTP_USER'))}", flush=True)
    print(f"CIVILIZATION_SMTP_PASSWORD = {_configured(os.getenv('CIVILIZATION_SMTP_PASSWORD'))}", flush=True)
    print(f"CIVILIZATION_ALERT_FROM = {_configured(os.getenv('CIVILIZATION_ALERT_FROM'))}", flush=True)
    print(f"CIVILIZATION_ALERT_EMAIL = {_configured(os.getenv('CIVILIZATION_ALERT_EMAIL'))}", flush=True)

    missing = [
        name for name in (
            "CIVILIZATION_SMTP_HOST",
            "CIVILIZATION_SMTP_USER",
            "CIVILIZATION_SMTP_PASSWORD",
            "CIVILIZATION_ALERT_EMAIL",
        ) if not os.getenv(name)
    ]
    if missing:
        print(f"RESULT: NOT RUN; missing required variables: {', '.join(missing)}", flush=True)
        return 2

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
        return 1

    print("RESULT: SENT; SMTP accepted the test message.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
