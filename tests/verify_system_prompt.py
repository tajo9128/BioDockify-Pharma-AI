
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from nanobot.agent.context import ContextBuilder

def verify_system_prompt():
    workspace = Path(".")
    builder = ContextBuilder(workspace)
    # We mock the _load_bootstrap_files to avoid needing real files
    builder._load_bootstrap_files = lambda: ""
    
    # Handle Windows encoding
    if sys.platform == 'win32':
        sys.stdout.reconfigure(encoding='utf-8')

    prompt = builder._get_identity()
    print("--- SYSTEM PROMPT IDENTITY ---")
    # print(prompt) # Commented out to reduce noise, just check
    
    if "Receptionist" in prompt:
        print("✅ Receptionist persona detected.")
    else:
        print("❌ Receptionist persona NOT detected.")

if __name__ == "__main__":
    verify_system_prompt()
