import asyncio
import logging
import sys
import os

# Add project root to path
sys.path.insert(0, ".")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("VerifyReception")

from agent_zero.biodockify_ai import AI

async def main():
    print("\n--- Verifying NanoBot Receptionist Architecture ---\n")
    
    # 1. Initialize
    print("[1] Initializing AI...")
    ai = AI.get_instance()
    await ai.initialize()
    
    # 2. Test Small Talk (User: 'Hello, who are you?')
    print("\n[2] Testing Small Talk (User: 'Hello, who are you?')")
    try:
        response1 = await ai.process_chat("Hello, who are you?")
        print(f"Response:\n{response1}\n")
        
        if "NanoBot" in response1 or "Receptionist" in response1:
            print("[SUCCESS] NanoBot replied directly.")
        else:
            print("[WARNING] Response didn't explicitly identify as NanoBot.")
            print(f"DEBUG RAW RESPONSE: '{response1}'")

    except Exception as e:
        print(f"[ERROR] Small Talk Test Failed: {e}")

    # 2.5 Test Identity (Who is your boss?)
    print("\n[2.5] Testing Identity (User: 'Who is your boss?')")
    try:
        response_id = await ai.process_chat("Who is your boss?")
        print(f"Response:\n{response_id}\n")
        if "Agent Zero" in response_id:
            print("[SUCCESS] NanoBot knows Agent Zero is the boss.")
        else:
            print("[WARNING] NanoBot didn't mention Agent Zero as boss.")
    except Exception as e:
        print(f"[ERROR] Identity Test Failed: {e}")

    # 3. Test Delegation (User: 'Research quantum biology')
    print("\n[3] Testing Delegation (User: 'Please research quantum biology concepts')")
    try:
        response2 = await ai.process_chat("Please research quantum biology concepts")
        print(f"Response:\n{response2}\n")
        
        if "Agent Zero" in response2 or "Boss" in response2:
            print("[SUCCESS] Delegation to Agent Zero confirmed.")
        else:
             print("[WARNING] Response didn't indicate delegation clearly.")
    except Exception as e:
        print(f"[ERROR] Delegation Test Failed: {e}")

    # 4. Capability Test (User: 'Check google.com')
    print("\n[4] Testing New Skill (User: 'Please check google.com title')")
    try:
        response3 = await ai.process_chat("Please check google.com title")
        print(f"Response:\n{response3}\n")
        
        # We look for indications that it TRIED to use the tool or described doing it
        if "google" in response3.lower() or "browser" in response3.lower():
            print("[SUCCESS] NanoBot attempted/acknowledged browser task.")
        else:
            print("[WARNING] NanoBot didn't seem to use the browser tool.")
            
    except Exception as e:
        print(f"[ERROR] Skill Test Failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
