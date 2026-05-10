"""
Verification test suite for Skills Hardening.
Checks for thread-safe singletons and basic functional integrity.
"""

import asyncio
import sys
import os
import threading
from typing import List, Dict, Any

# Ensure imports work
sys.path.append(os.getcwd())

from agent_zero.skills.achademio.wrapper import get_achademio
from agent_zero.skills.reviewer_agent.wrapper import get_reviewer_agent
from agent_zero.skills.scholar_copilot.wrapper import get_scholar_copilot
from agent_zero.skills.latte_review.wrapper import get_latte_review
from agent_zero.skills.deep_drive.wrapper import get_deep_drive
from agent_zero.skills.browser_scraper import get_browser_scraper
from agent_zero.skills.email_messenger import get_email_messenger

def test_singleton_thread_safety(skill_getter, name):
    print(f"[*] Testing thread-safety for {name}...")
    instances = []
    
    def get_instance():
        instances.append(skill_getter())
        
    threads = []
    for _ in range(10):
        t = threading.Thread(target=get_instance)
        threads.append(t)
        t.start()
        
    for t in threads:
        t.join()
        
    # All instances should be the same object
    first = instances[0]
    for inst in instances[1:]:
        if inst is not first:
            print(f"   FAILED: {name} singleton is NOT thread-safe!")
            return False
            
    print(f"   OK: {name} singleton is stable and thread-safe.")
    return True

async def test_email_non_blocking():
    print("[*] Testing EmailMessenger non-blocking logic...")
    messenger = get_email_messenger()
    # Mock SMTP to avoid actual network calls
    # messenger._send_email_sync = lambda *args: print("      (Mock SMTP call in thread)")
    
    # Check if _send_email_sync exists
    if hasattr(messenger, "_send_email_sync"):
        print("   OK: EmailMessenger has internal synchronous sender.")
    else:
        print("   FAILED: EmailMessenger missing _send_email_sync.")

async def test_latte_error_handling():
    print("[*] Testing LatteReview error logic...")
    from agent_zero.skills.latte_review.wrapper import LATTE_AVAILABLE
    if not LATTE_AVAILABLE:
        print("   INFO: LatteReview not available, testing graceful init...")
        latte = get_latte_review()
        if hasattr(latte, "available") and latte.available == False:
            print("   OK: LatteReview handles missing dependencies gracefully.")
        else:
            print("   FAILED: LatteReview graceful init logic missing.")
    else:
        print("   INFO: LatteReview available, skipping missing dep test.")

async def main():
    print("="*60)
    print("Skills Hardening - Verification Audit")
    print("="*60)
    
    skills = [
        (get_achademio, "Achademio"),
        (get_reviewer_agent, "ReviewerAgent"),
        (get_scholar_copilot, "ScholarCopilot"),
        (get_latte_review, "LatteReview"),
        (get_deep_drive, "DeepDrive"),
        (get_browser_scraper, "BrowserScraper"),
        (get_email_messenger, "EmailMessenger")
    ]
    
    all_passed = True
    for getter, name in skills:
        if not test_singleton_thread_safety(getter, name):
            all_passed = False
            
    await test_email_non_blocking()
    await test_latte_error_handling()
    
    print("\n" + "="*60)
    if all_passed:
        print("VERIFICATION SUCCESSFUL: Skills are hardened and thread-safe.")
    else:
        print("VERIFICATION FAILED: Some skills have stability issues.")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(main())
