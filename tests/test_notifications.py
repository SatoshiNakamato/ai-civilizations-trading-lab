import smtplib

from civilizations.notifications import NotificationGovernor, NotificationGovernorConfig, SMTPEmailSender


class Clock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


def test_governor_deduplicates_and_rate_limits():
    sent = []
    clock = Clock()
    governor = NotificationGovernor(
        lambda notification: sent.append(notification),
        NotificationGovernorConfig(max_notifications=2, window_seconds=60, dedupe_seconds=300),
        clock=clock,
    )
    assert governor.notify("critical", "Alpha", "BTC spread").sent
    assert governor.notify("critical", "Alpha", "BTC spread").reason == "deduplicated"
    clock.now = 1
    assert governor.notify("high", "Second", "ETH spread").sent
    clock.now = 2
    assert governor.notify("high", "Third", "SOL spread").reason == "rate_limited"
    assert len(sent) == 2


def test_provider_failure_degrades_without_raising():
    clock = Clock()

    def fail(_notification):
        raise RuntimeError("SMTP 550 5.4.5")

    governor = NotificationGovernor(fail, clock=clock)
    result = governor.notify("critical", "Alpha", "BTC spread")
    assert result.sent is False
    assert result.reason == "delivery_degraded:RuntimeError"


def test_daily_smtp_quota_opens_circuit():
    clock = Clock()

    class QuotaFailure:
        def __call__(self, _notification):
            raise smtplib.SMTPDataError(550, b"5.4.5 Daily user sending limit exceeded")

    governor = NotificationGovernor(
        QuotaFailure(),
        NotificationGovernorConfig(cooldown_seconds=0),
        clock=clock,
    )
    first = governor.notify("critical", "Alpha", "BTC spread")
    second = governor.notify("critical", "Other", "ETH spread")
    assert first.reason == "smtp_quota"
    assert second.reason == "smtp_circuit_open"
    assert governor.snapshot()["circuit_open"] is True


def test_fingerprint_is_deterministic():
    assert NotificationGovernor.fingerprint("CRITICAL", "A", "B") == NotificationGovernor.fingerprint("critical", "A", "B")


def test_governor_reads_voroa_environment(monkeypatch):
    monkeypatch.setenv("AEON_NOTIFICATION_MAX_PER_CYCLE", "2")
    monkeypatch.setenv("AEON_NOTIFICATION_MAX_PER_DAY", "7")
    monkeypatch.setenv("AEON_NOTIFICATION_COOLDOWN_SECONDS", "11")
    monkeypatch.setenv("AEON_NOTIFICATION_DEDUP_WINDOW_SECONDS", "22")
    monkeypatch.setenv("AEON_NOTIFICATION_MIN_SEVERITY", "CRITICAL")
    monkeypatch.setenv("AEON_NOTIFICATION_ENABLED", "true")
    monkeypatch.setenv("AEON_NOTIFICATION_EMAIL_ENABLED", "true")
    config = NotificationGovernorConfig.from_env()
    assert config.max_notifications == 2
    assert config.max_per_day == 7
    assert config.cooldown_seconds == 11
    assert config.dedupe_seconds == 22
    assert config.min_severity == "CRITICAL"


def test_smtp_sender_reads_delivery_variables(monkeypatch):
    monkeypatch.setenv("CIVILIZATION_SMTP_HOST", "smtp.example.test")
    monkeypatch.setenv("CIVILIZATION_SMTP_PORT", "587")
    monkeypatch.setenv("CIVILIZATION_SMTP_USER", "bot@example.test")
    monkeypatch.setenv("CIVILIZATION_SMTP_PASSWORD", "secret")
    monkeypatch.setenv("CIVILIZATION_ALERT_FROM", "alerts@example.test")
    monkeypatch.setenv("CIVILIZATION_ALERT_EMAIL", "owner@example.test")
    sender = SMTPEmailSender()
    assert (sender.host, sender.port, sender.user, sender.sender, sender.recipient) == (
        "smtp.example.test", 587, "bot@example.test", "alerts@example.test", "owner@example.test"
    )
