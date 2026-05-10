import asyncio
import logging
import sys
import os

# Ensure we can import from root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agent_zero.biodockify_ai import BioDockifyAI

# Configure logging to see our retry logic
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def verify_startup():
    print("--- Starting Agent Zero Verification ---")
    ai = BioDockifyAI.get_instance()
    
    try:
        # This will trigger our new robust initialize() method
        await ai.initialize()
        print("\n✅ Verification SUCCESS: Agent initialized without crashing.")
    except Exception as e:
        print(f"\n❌ Verification FAILED: Agent crashed with error: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(verify_startup())
    except KeyboardInterrupt:
        print("\nVerification interrupted by user.")
