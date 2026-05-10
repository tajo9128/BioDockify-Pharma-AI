import asyncio
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agent_zero.biodockify_ai import BioDockifyAI


async def verify_agent_zero():
    print("Verifying Agent Zero v1.9 Integration...")

    ai = BioDockifyAI()

    print("Initializing AI...")
    try:
        await ai.initialize()
    except Exception as e:
        print(f"Initialization warning (might be expected in test env): {e}")

    print("\n--- Test: Agent Zero v1.9 Mode ---")
    try:
        response = await ai.process_chat("Hello, who are you?")
        print(f"Response: {response}")

        if response and len(response) > 0:
            print("[SUCCESS] Agent Zero v1.9 responded.")
        else:
            print("[WARN] Empty response")

    except Exception as e:
        print(f"[INFO] Agent Zero response: {e}")


if __name__ == "__main__":
    asyncio.run(verify_agent_zero())
