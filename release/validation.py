from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
from typing import Iterable

from markets.paper_reliability import PaperFill, PaperTradingLedger


@dataclass(frozen=True)
class ValidationReport:
    healthy: bool
    ledger_valid: bool
    duplicate_trade_ids: int
    malformed_records: int
    paper_trades: int
    message: str


def validate_paper_ledger(path: str = "data/paper_trades.jsonl") -> ValidationReport:
    ledger = PaperTradingLedger(path)
    raw_lines = Path(path).read_text(encoding="utf-8").splitlines() if Path(path).exists() else []
    parsed = ledger.read()
    malformed = 0
    for line in raw_lines:
        try:
            json.loads(line)
        except json.JSONDecodeError:
            malformed += 1
    result = ledger.validate(parsed)
    healthy = bool(result["valid"] and malformed == 0)
    return ValidationReport(
        healthy=healthy,
        ledger_valid=bool(result["valid"]),
        duplicate_trade_ids=int(result["duplicate_trade_ids"]),
        malformed_records=malformed,
        paper_trades=len(parsed),
        message="paper ledger healthy" if healthy else "paper ledger requires repair",
    )


def validate_fills(fills: Iterable[PaperFill]) -> ValidationReport:
    values = list(fills)
    ids = [fill.trade_id for fill in values]
    duplicates = len(ids) - len(set(ids))
    valid = duplicates == 0 and all(
        fill.quantity > 0
        and fill.requested_price > 0
        and fill.fill_price > 0
        and fill.fees >= 0
        and fill.slippage >= 0
        for fill in values
    )
    return ValidationReport(
        healthy=valid,
        ledger_valid=valid,
        duplicate_trade_ids=duplicates,
        malformed_records=0,
        paper_trades=len(values),
        message="paper fills healthy" if valid else "paper fills require repair",
    )
