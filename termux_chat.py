from civilizations.command_center import CommandCenter
from civilizations.core import Civilization
from civilizations.inbox import Inbox
from civilizations.treasury import Treasury


def main():
    civilization = Civilization(100, 42)
    inbox = Inbox()
    treasury = Treasury()
    center = CommandCenter(inbox, treasury)

    print("CIVILIZATION COMMAND CENTER")
    print("Commands: all <message> | agent <ID> <message> | status | run | inbox | quit")

    while True:
        try:
            raw = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not raw:
            continue
        if raw == "quit":
            break
        if raw == "run":
            state = civilization.step()
            print(f"generation={state['generation']} ideas={state['ideas']} messages={state['messages']}")
            continue
        if raw == "status":
            print(center.status())
            continue
        if raw == "inbox":
            for message in inbox.for_recipient("OWNER")[-20:]:
                print(f"{message['sender']}> {message['text']}")
            continue
        if raw.startswith("all "):
            print(center.send_to_all(raw[4:], civilization.tick))
            continue
        if raw.startswith("agent "):
            parts = raw.split(" ", 2)
            if len(parts) < 3:
                print("usage: agent A037 your message")
                continue
            print(center.send_to_agent(parts[1], parts[2], civilization.tick))
            continue
        print("Unknown command. Try: all, agent, status, run, inbox, quit")


if __name__ == "__main__":
    main()
