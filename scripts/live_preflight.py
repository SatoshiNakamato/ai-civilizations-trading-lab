from __future__ import annotations

import os
import json


def main():
    required = ["TRADING_EXCHANGE", "TRADING_API_KEY", "TRADING_API_SECRET", "LIVE_TRADING_CONFIRMATION"]
    missing = [name for name in required if not os.getenv(name, "").strip()]
    confirmation_ok = os.getenv("LIVE_TRADING_CONFIRMATION") == "I_UNDERSTAND_LIVE_RISK"
    out = {
        "configured": not missing and confirmation_ok,
        "exchange": os.getenv("TRADING_EXCHANGE", "coinbase"),
        "missing": missing,
        "confirmation_ok": confirmation_ok,
        "live_orders_enabled": os.getenv("LIVE_TRADING", "0") == "1",
        "limits": {
            "max_order_quote": float(os.getenv("LIVE_MAX_ORDER_QUOTE", "25")),
            "max_position_quote": float(os.getenv("LIVE_MAX_POSITION_QUOTE", "100")),
            "max_daily_loss": float(os.getenv("LIVE_MAX_DAILY_LOSS", "25")),
            "max_daily_notional": float(os.getenv("LIVE_MAX_DAILY_NOTIONAL", "250")),
        },
    }
    print(json.dumps(out, sort_keys=True))
    return 0 if out["configured"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
