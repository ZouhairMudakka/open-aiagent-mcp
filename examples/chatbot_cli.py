from __future__ import annotations

import json

from src.agents.base_agent import Agent


def main():
    agent = Agent()
    print("Chatbot ready. Type /quit to exit. Examples:")
    print("  /echo Hello world")
    print("  /db {\"action\": \"list\"}")
    print("  /db {\"action\": \"add\", \"data\": \"hello\"}")

    while True:
        user_input = input("you> ").strip()
        if user_input.lower() in {"/quit", "quit", "exit"}:
            break

        # If starts with /db and followed by JSON, build payload
        if user_input.startswith("/db "):
            try:
                payload = json.loads(user_input[4:])
                response = agent.invoke_tool("db", payload)
            except Exception as exc:
                response = f"Error: {exc}"
        else:
            response = agent.chat(user_input)
        print("bot>", response)


if __name__ == "__main__":
    main() 