from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
import json, time

@dataclass
class PaperFill:
    fill_id: str
    opportunity_id: str
    agent: str
    asset: str
    buy_venue: str
    sell_venue: str
    entry_buy: float
    entry_sell: float
    exit_buy: float = 0.0
    exit_sell: float = 0.0
    quantity: float = 1.0
    fees: float = 0.0
    status: str = "open"
    realized_pnl: float = 0.0
    opened_at: float = 0.0
    closed_at: float = 0.0

class PaperExecutionEngine:
    """Simulated fills only, with restart-safe lifecycle persistence."""
    def __init__(self, path="data/paper_fills.jsonl"):
        self.path=Path(path); self.path.parent.mkdir(parents=True, exist_ok=True)
        self.open_fills={}; self.closed=[]
        self._restore()

    def open(self, opportunity, agent="SYSTEM", quantity=1.0):
        fid=f"fill-{opportunity.opportunity_id}-{int(time.time()*1000)}"
        while fid in self.open_fills or any(x.fill_id == fid for x in self.closed):
            fid += "-1"
        fill=PaperFill(fid,opportunity.opportunity_id,agent,opportunity.asset,opportunity.buy_venue,opportunity.sell_venue,opportunity.buy_price,opportunity.sell_price,quantity=quantity,fees=opportunity.fees+opportunity.slippage,opened_at=time.time())
        self.open_fills[fid]=fill; self._write("opened",fill); return fill

    def mark(self, fill_id, buy_price, sell_price):
        fill=self.open_fills[fill_id]; fill.exit_buy=float(buy_price); fill.exit_sell=float(sell_price)
        entry_spread=fill.entry_sell-fill.entry_buy
        exit_spread=fill.exit_sell-fill.exit_buy
        gross=(entry_spread-exit_spread)*fill.quantity
        fill.realized_pnl=gross-fill.fees*fill.quantity
        return fill

    def close(self, fill_id, buy_price, sell_price):
        fill=self.mark(fill_id,buy_price,sell_price); fill.status="closed"; fill.closed_at=time.time()
        self.open_fills.pop(fill_id,None); self.closed.append(fill); self._write("closed",fill); return fill

    def observe(self, quote_by_venue):
        results=[]
        for fid,fill in list(self.open_fills.items()):
            if fill.buy_venue in quote_by_venue and fill.sell_venue in quote_by_venue:
                q1,q2=quote_by_venue[fill.buy_venue],quote_by_venue[fill.sell_venue]
                results.append(self.mark(fid,float(q1.ask),float(q2.bid)))
        return results

    def snapshot(self):
        pnl=sum(x.realized_pnl for x in self.closed); wins=sum(x.realized_pnl>0 for x in self.closed)
        return {"open":len(self.open_fills),"closed":len(self.closed),"realized_pnl":round(pnl,8),"win_rate":wins/len(self.closed) if self.closed else 0.0}

    def _write(self,event,fill):
        with self.path.open("a",encoding="utf-8") as f: f.write(json.dumps({"event":event,"timestamp":time.time(),"fill":asdict(fill)})+"\n")

    def _restore(self):
        try:
            with self.path.open(encoding="utf-8") as handle:
                for line in handle:
                    try: record=json.loads(line); fill_data=record["fill"]; fill=PaperFill(**fill_data)
                    except (json.JSONDecodeError, KeyError, TypeError): continue
                    if record.get("event") == "opened" and fill.status == "open":
                        self.open_fills[fill.fill_id]=fill
                    elif record.get("event") == "closed" or fill.status == "closed":
                        self.open_fills.pop(fill.fill_id,None)
                        if not any(x.fill_id == fill.fill_id for x in self.closed): self.closed.append(fill)
        except OSError:
            return
