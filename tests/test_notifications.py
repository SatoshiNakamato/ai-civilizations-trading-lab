from civilizations.notifications import NotificationGovernor, NotificationGovernorConfig


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
    assert governor.notify("critical", "Alpha", "BTC spread") .sent
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


def test_fingerprint_is_deterministic():
    assert NotificationGovernor.fingerprint("CRITICAL", "A", "B") == NotificationGovernor.fingerprint("critical", "A", "B")
