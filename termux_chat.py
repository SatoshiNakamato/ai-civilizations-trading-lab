from civilizations.command_center import CommandCenter
from civilizations.core import Civilization
from civilizations.inbox import Inbox
from civilizations.treasury import Treasury


def build_response(agent, message):
    focus = {
        "quant": "statistical validation and out-of-sample testing",
        "arb": "cross-market price discrepancies after fees, slippage and latency",
        "macro": "macro regimes and their effect on markets",
        "momentum": "price persistence, liquidity and trend behavior",
        "value": "valuation and fair-value estimation",
        "contrarian": "crowding, sentiment and asymmetric reversals",
        "risk": "position sizing, volatility and drawdown control",
        "probability": "forecast calibration and probability estimation",
        "microstructure": "spreads, liquidity and order-flow behavior",
        "explorer": "new falsifiable strategy combinations",
    }
    area = focus.get(agent.archetype, "research, experimentation and strategy discovery")
    best = max(agent.ideas, key=lambda idea: idea.fitness, default=None)
    if best is not None:
        return (f"I am {agent.agent_id}. My specialization is {agent.archetype}. "
                f"My current research focus is {area}. My strongest current hypothesis is "
                f"{best.title}, with fitness {best.fitness:.4f}. My capability score is "
                f"{agent.intelligence.capability_score:.3f}, and my experience is "
                f"{agent.intelligence.experience}. I received your message: {message}")
    return f"I am {agent.agent_id}, specializing in {agent.archetype}. My current focus is {area}. I received your message: {message}"


def main():
    civilization = Civilization(100, 42)
    inbox = Inbox()
    treasury = Treasury()
    center = CommandCenter(inbox, treasury)
    print("CIVILIZATION COMMAND CENTER")
    print("============================")
    print("Commands: all <message> | agent <ID> <message> | run | status | inbox | citizens | quit")
    while True:
        try:
            raw = input("\nyou> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nLeaving command center.")
            break
        if not raw:
            continue
        if raw.lower() == "quit":
            print("Command center offline.")
            break
        if raw.lower() == "status":
            print(center.status()); continue
        if raw.lower() == "inbox":
            messages = inbox.for_recipient("OWNER")
            if not messages:
                print("No messages.")
                continue
            for message in messages[-20:]:
                print(f"\n[{message['sender']}] {message['timestamp']}\n{message['text']}")
            continue
        if raw.lower() == "citizens":
            for agent_id, agent in civilization.agents.items():
                print(f"{agent_id} | {agent.archetype} | capability={agent.intelligence.capability_score:.3f} | experience={agent.intelligence.experience}")
            continue
        if raw.lower() == "run":
            state = civilization.step()
            print(f"\nGeneration {state['generation']}")
            print(f"Ideas: {state['ideas']}")
            print(f"Messages: {state['messages']}")
            continue
        if raw.startswith("agent "):
            parts = raw.split(" ", 2)
            if len(parts) < 3:
                print("Usage: agent A099 your message"); continue
            agent_id, message = parts[1].upper(), parts[2]
            agent = civilization.agents.get(agent_id)
            if agent is None:
                print(f"Unknown agent: {agent_id}"); continue
            inbox.send("OWNER", agent_id, message, civilization.tick)
            response = build_response(agent, message)
            inbox.send(agent_id, "OWNER", response, civilization.tick)
            print(f"\n{agent_id}> {response}")
            continue
        if raw.startswith("all "):
            message = raw[4:].strip()
            if not message:
                print("Usage: all your message"); continue
            center.send_to_all(message, civilization.tick)
            agents = list(civilization.agents.values())
            for agent in agents[:10]:
                inbox.send(agent.agent_id, "OWNER", build_response(agent, message), civilization.tick)
            print(f"Message delivered to {len(agents)} agents. 10 responses queued.")
            continue
        print("Unknown command. Try: all, agent, run, status, inbox, citizens, quit")


if __name__ == "__main__":
    main()
