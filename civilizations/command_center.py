from __future__ import annotations

from .inbox import Inbox
from .treasury import Treasury


class CommandCenter:
    """Human interface for the local simulation."""

    def __init__(self, inbox: Inbox, treasury: Treasury, minimum_balance: float = 10_000.0):
        self.inbox = inbox
        self.treasury = treasury
        self.minimum_balance = minimum_balance

    def send_to_all(self, text: str, tick: int) -> dict:
        return self.inbox.send("OWNER", "ALL", text, tick).__dict__

    def send_to_agent(self, agent_id: str, text: str, tick: int) -> dict:
        return self.inbox.send("OWNER", agent_id, text, tick).__dict__

    def status(self) -> dict:
        balance = self.treasury.balance
        return {
            "treasury_balance": round(balance, 2),
            "minimum_balance": round(self.minimum_balance, 2),
            "top_up_needed": balance < self.minimum_balance,
            "owner_inbox_messages": len(self.inbox.for_recipient("OWNER")),
        }

    def monthly_reminder(self, month: int, tick: int) -> dict | None:
        if self.treasury.balance < self.minimum_balance:
            return self.inbox.send(
                "TREASURY",
                "OWNER",
                f"Month {month}: simulated treasury is below the operating reserve. "
                "Top-up required before the next monthly cycle.",
                tick,
            ).__dict__
        return None
