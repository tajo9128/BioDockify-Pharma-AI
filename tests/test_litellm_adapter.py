
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modules.llm.adapters import LMStudioAdapter

def test_litellm_connection():
    print("Testing LMStudioAdapter with LiteLLM...")
    
    # Initialize adapter
    # Assuming LM Studio is running on default port 1234
    adapter = LMStudioAdapter(base_url="http://localhost:1234/v1", model="local-model")
    
    try:
        # Test 1: Simple Generation
        print("\n[Test 1] Simple Generation:")
        response = adapter.generate("Hello, are you working?", max_tokens=50)
        print(f"Response: {response}")
        
        # Test 2: JSON Enforcement
        print("\n[Test 2] JSON Enforcement:")
        prompt = "Generate a JSON object with fields 'name' and 'role' for a pharma researcher."
        # The adapter should detect 'json' in prompt and force JSON mode
        json_response = adapter.generate(prompt, max_tokens=100)
        print(f"JSON Response: {json_response}")
        
        # Verify if it looks like JSON
        import json
        try:
            parsed = json.loads(json_response)
            print("✅ Valid JSON received.")
        except json.JSONDecodeError:
            print("❌ Invalid JSON received.")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("Ensure LM Studio is running and the Local Server is ON.")

if __name__ == "__main__":
    test_litellm_connection()
