import smtplib

from civilizations.email_alerts import AlertCandidate, EmailAlertGateway


def candidate():
    return AlertCandidate(
        title="ARB opportunity",
        category="arbitrage",
        summary="Validated public-market price dislocation; execute manually.",
        confidence=0.95,
        edge=0.02,
        risk=0.2,
        sources=("dex-a", "dex-b"),
        agent="A001",
        buy_venue="dex-a",
        sell_venue="dex-b",
        buy_price=1.0,
        sell_price=1.03,
    )


def test_email_retries_transient_smtp_failure(monkeypatch):
    gateway = EmailAlertGateway(recipient="alerts@example.com")
    gateway.smtp_host = "smtp.example.com"
    gateway.smtp_user = "user"
    gateway.smtp_password = "secret"
    gateway.max_retries = 3
    attempts = []

    class SMTP:
        def __init__(self, *args, **kwargs):
            attempts.append(1)
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def starttls(self):
            if len(attempts) < 3:
                raise smtplib.SMTPException("temporary failure")
        def login(self, *args):
            pass
        def send_message(self, message):
            pass

    monkeypatch.setattr(smtplib, "SMTP", SMTP)
    monkeypatch.setattr("civilizations.email_alerts.time", lambda: 1000.0)

    assert gateway.send(candidate()) is True
    assert len(attempts) == 3
    assert gateway.sent == 1
    assert gateway.failed == 0


def test_email_failure_does_not_raise_or_mark_as_sent(monkeypatch):
    gateway = EmailAlertGateway(recipient="alerts@example.com")
    gateway.smtp_host = "smtp.example.com"
    gateway.smtp_user = "user"
    gateway.smtp_password = "secret"
    gateway.max_retries = 2

    class SMTP:
        def __init__(self, *args, **kwargs):
            pass
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def starttls(self):
            raise OSError("network down")

    monkeypatch.setattr(smtplib, "SMTP", SMTP)
    monkeypatch.setattr("civilizations.email_alerts.time", lambda: 1000.0)

    assert gateway.send(candidate()) is False
    assert gateway.sent == 0
    assert gateway.failed == 1
    assert "network down" in gateway.last_error
