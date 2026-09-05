import os
import smtplib

from civilizations.notification_governor import NotificationConfig, NotificationGovernor


def test_governor_reads_voroa_environment(monkeypatch):
    monkeypatch.setenv("AEON_NOTIFICATION_MAX_PER_CYCLE", "2")
    monkeypatch.setenv("AEON_NOTIFICATION_MAX_PER_DAY", "7")
    monkeypatch.setenv("AEON_NOTIFICATION_MIN_SEVERITY", "CRITICAL")
    config = NotificationConfig.from_env()
    assert config.max_per_cycle == 2
    assert config.max_per_day == 7
    assert config.min_severity == "CRITICAL"


def test_smtp_quota_error_is_governed_and_never_escapes(monkeypatch):
    for key, value in {
        "AEON_NOTIFICATION_ENABLED": "true",
        "AEON_NOTIFICATION_EMAIL_ENABLED": "true",
        "CIVILIZATION_SMTP_HOST": "smtp.example.test",
        "CIVILIZATION_SMTP_PORT": "587",
        "CIVILIZATION_SMTP_USER": "sender@example.test",
        "CIVILIZATION_SMTP_PASSWORD": "secret",
        "CIVILIZATION_ALERT_FROM": "sender@example.test",
        "CIVILIZATION_ALERT_EMAIL": "owner@example.test",
    }.items():
        monkeypatch.setenv(key, value)

    class FakeSMTP:
        def __init__(self, *args, **kwargs):
            pass
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def starttls(self):
            pass
        def login(self, *args):
            pass
        def send_message(self, message):
            raise smtplib.SMTPDataError(550, b"5.4.5 Daily user sending limit exceeded")

    monkeypatch.setattr(smtplib, "SMTP", FakeSMTP)
    governor = NotificationGovernor(NotificationConfig(cooldown_seconds=300, max_per_cycle=5, max_per_day=20))

    first = governor.notify(severity="CRITICAL", subject="Arbitrage", body="BTC opportunity")
    second = governor.notify(severity="CRITICAL", subject="Arbitrage", body="BTC opportunity")

    assert first["sent"] is False
    assert first["reason"] == "smtp_error"
    assert second["sent"] is False
    assert second["reason"] == "smtp_circuit_open"
    assert governor.snapshot()["circuit_open"] is True


def test_successful_notification_is_deduplicated(monkeypatch):
    for key, value in {
        "CIVILIZATION_SMTP_HOST": "smtp.example.test",
        "CIVILIZATION_SMTP_PORT": "587",
        "CIVILIZATION_SMTP_USER": "sender@example.test",
        "CIVILIZATION_SMTP_PASSWORD": "secret",
        "CIVILIZATION_ALERT_FROM": "sender@example.test",
        "CIVILIZATION_ALERT_EMAIL": "owner@example.test",
    }.items():
        monkeypatch.setenv(key, value)

    class FakeSMTP:
        def __init__(self, *args, **kwargs):
            pass
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def starttls(self):
            pass
        def login(self, *args):
            pass
        def send_message(self, message):
            return None

    monkeypatch.setattr(smtplib, "SMTP", FakeSMTP)
    governor = NotificationGovernor(NotificationConfig(cooldown_seconds=0, max_per_cycle=5, max_per_day=20))
    assert governor.notify(severity="CRITICAL", subject="A", body="B")["sent"] is True
    assert governor.notify(severity="CRITICAL", subject="A", body="B")["reason"] == "duplicate"
