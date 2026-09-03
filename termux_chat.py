from civilizations.command_center import CommandCenter
from civilizations.core import Civilization
from civilizations.inbox import Inbox
from civilizations.llm_agent import CognitiveAgent
from civilizations.treasury import Treasury


def main():
    civilization = Civilization(100, 42)
    inbox = Inbox()
    treasury = Treasury()
    center = CommandCenter(inbox, treasury)
    minds = {agent_id: CognitiveAgent(agent) for agent_id, agent in civilization.agents.items()}

    print("CIVILIZATION COMMAND CENTER")
    print("============================")
    print("Commands: all <message> | agent <ID> <message> | run | status | inbox | citizens | quit")
    print("LLM mode: configured" if minds["A001"].model_call.api_key else "LLM mode: waiting for OPENAI_API_KEY")

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
            print(center.status())
            continue
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
                print("Usage: agent A099 your message")
                continue
            agent_id, message = parts[1].upper(), parts[2]
            agent = civilization.agents.get(agent_id)
            if agent is None:
                print(f"Unknown agent: {agent_id}")
                continue
            inbox.send("OWNER", agent_id, message, civilization.tick)
            response = minds[agent_id].respond(message)
            inbox.send(agent_id, "OWNER", response, civilization.tick)
            print(f"\n{agent_id}> {response}")
            continue
        if raw.startswith("all "):
            message = raw[4:].strip()
            if not message:
                print("Usage: all your message")
                continue
            center.send_to_all(message, civilization.tick)
            agents = list(civilization.agents.values())
            for agent in agents[:10]:
                response = minds[agent.agent_id].respond(message)
                inbox.send(agent.agent_id, "OWNER", response, civilization.tick)
            print(f"Message delivered to {len(agents)} agents. 10 cognitive responses generated.")
            continue
        print("Unknown command. Try: all, agent, run, status, inbox, citizens, quit")


if __name__ == "__main__":
    main()
