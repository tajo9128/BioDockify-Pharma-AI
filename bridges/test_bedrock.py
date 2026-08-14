"""Quick end-to-end test for Bedrock bridge.

Run: python -m bridges.test_bedrock
Expects AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY in env or ~/.aws/credentials
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bridges.bedrock_bridge import (
    is_bedrock_available,
    get_bedrock_status,
    invoke_bedrock_model,
)


def main():
    print("=" * 50)
    print("Bedrock Bridge — End-to-End Test")
    print("=" * 50)

    # Step 1: Check availability
    status = get_bedrock_status()
    print(f"\n[1] Status: {status}")

    if not is_bedrock_available():
        print("\n FAIL: Bedrock not available.")
        print("   - Is boto3 installed? pip install boto3")
        print("   - Does ~/.claude/bedrock_config.json exist?")
        return False

    print("   OK: boto3 + config loaded")

    # Step 2: Test invocation with a simple prompt
    print("\n[2] Invoking claude_haiku with test prompt...")
    result = invoke_bedrock_model(
        prompt="What is aspirin's chemical formula? Reply in one line.",
        model_key="claude_haiku",
        max_tokens=50,
        temperature=0.0,
    )

    if result["success"]:
        print(f"   OK: {result['response'][:100]}")
        print(f"   Model: {result['model']}")
        print(f"   Usage: {result.get('usage', {})}")
    else:
        print(f"   FAIL: {result['error']}")
        return False

    # Step 3: Test with Sonnet 5
    print("\n[3] Invoking claude_sonnet_5 with pharma prompt...")
    result = invoke_bedrock_model(
        prompt="List the pharmacophore features of ibuprofen in JSON format. Keep it under 5 features.",
        model_key="claude_sonnet_5",
        system_prompt="You are a computational chemistry expert. Be concise.",
        max_tokens=300,
        temperature=0.0,
    )

    if result["success"]:
        print(f"   OK: Response length = {len(result['response'])} chars")
        print(f"   Preview: {result['response'][:150]}...")
        print(f"   Usage: {result.get('usage', {})}")
    else:
        print(f"   FAIL: {result['error']}")
        return False

    print("\n" + "=" * 50)
    print("ALL TESTS PASSED")
    print("=" * 50)
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
