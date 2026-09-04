from civilizations.opportunities import Opportunity, OpportunityEngine
from civilizations.email_alerts import AlertCandidate, EmailAlertGateway


def test_critical_opportunity_routes_to_alert():
    engine = OpportunityEngine(cooldown_seconds=0)
    opportunity = Opportunity(
        opportunity_id="",
        category="arbitrage",
        asset="BTC",
        summary="BTC venue spread",
        confidence=0.98,
        risk=0.10,
        gross_edge=0.025,
        fees=0.002,
        slippage=0.001,
        liquidity=0.90,
        sources=["https://example.com/market"],
        buy_venue="venue-a",
        sell_venue="venue-b",
    )
    found = engine.discover(opportunity)
    validated = engine.validate(found)
    assert validated.status == "validated"
    assert engine.should_alert(validated) == "CRITICAL"


def test_email_gateway_suppresses_non_important_alerts():
    gateway = EmailAlertGateway(recipient="test@example.com")
    candidate = AlertCandidate(
        title="routine update",
        category="market",
        summary="routine research",
        confidence=0.70,
    )
    assert candidate.severity == "WATCH"
    assert gateway.should_alert(candidate) is False
