
import sys
import os
import logging
from unittest.mock import MagicMock

# Setup paths
sys.path.append(os.path.join(os.getcwd()))

# Mock litellm to avoid API calls during test
sys.modules["litellm"] = MagicMock()

from agent_zero.skills.achademio.wrapper import get_achademio
from agent_zero.skills.latte_review.wrapper import get_latte_review
from agent_zero.skills.email_messenger import get_email_messenger

def test_skills():
    print("[-] Testing Skill Integration...")
    
    # 1. Achademio
    try:
        achademio = get_achademio()
        print("[+] Achademio Logic Loaded.")
        # Mock the internal LLM call to verifying wiring
        achademio._call_llm = MagicMock(return_value="Rewritten text")
        res = achademio.rewrite_academic("Test text")
        if res == "Rewritten text":
            print("[+] Achademio.rewrite_academic passed.")
        else:
            print(f"[!] Achademio unexpected result: {res}")
    except Exception as e:
        print(f"[!] Achademio Failed: {e}")

    # 2. LatteReview (Just check import and init)
    try:
        latte = get_latte_review()
        print("[+] LatteReview Logic Loaded.")
        if latte:
             print("[+] LatteReview initialization passed.")
    except ImportError:
         print("[!] LatteReview dependencies missing (Expected if submodules not pulled)")
    except Exception as e:
        print(f"[!] LatteReview Failed: {e}")

    # 3. EmailMessenger
    try:
        messenger = get_email_messenger()
        print("[+] EmailMessenger Logic Loaded.")
    except Exception as e:
        print(f"[!] EmailMessenger Failed: {e}")

if __name__ == "__main__":
    test_skills()
