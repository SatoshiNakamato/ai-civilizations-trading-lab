import os
import sys
from pathlib import Path

# Allow direct execution from the repository root with `python scripts/test_email_alert.py`.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from civilizations.email_alerts import AlertCandidate, EmailAlertGateway


def main() -> int:
    candidate = AlertCandidate(
        title="TEST — Civilization email gateway",
        category="breakthrough",
        summary="Controlled connectivity test. No trading action is requested.",
        confidence=0.95,
        risk=0.10,
        agent="SYSTEM-TEST",
    )

    gateway = EmailAlertGateway()
    print("Gateway enabled:", gateway.enabled())
    print("Recipient:", gateway.recipient)
    print("Severity:", candidate.severity)

    if not gateway.enabled():
        print("SMTP configuration is not loaded")
        return 2

    # Never send a real email from CI. Set CIVILIZATION_EMAIL_SMOKE_TEST=1
    # explicitly when a human wants this script to perform the SMTP smoke test.
    if os.getenv("CI") and os.getenv("CIVILIZATION_EMAIL_SMOKE_TEST") != "1":
        print("CI environment detected; SMTP smoke test skipped")
        return 0

    try:
        ok = gateway.send(candidate)
        print("EMAIL SENT:", ok)
        return 0 if ok else 1
    except Exception as exc:
        print("EMAIL FAILED:", type(exc).__name__, str(exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
