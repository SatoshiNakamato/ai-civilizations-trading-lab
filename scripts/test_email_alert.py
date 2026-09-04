import sys
from pathlib import Path

# Allow direct execution from the repository root with `python scripts/test_email_alert.py`.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from civilizations.email_alerts import AlertCandidate, EmailAlertGateway

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
    raise SystemExit("SMTP configuration is not loaded")

try:
    ok = gateway.send(candidate)
    print("EMAIL SENT:", ok)
except Exception as exc:
    print("EMAIL FAILED:", type(exc).__name__, str(exc))
    raise SystemExit(1)
