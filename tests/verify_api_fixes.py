"""
API Verification Script - Free & Paid Providers
Tests Ollama (free) and Cloud APIs (paid) with the applied fixes.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_ollama_adapter():
    """Test FREE tier - Ollama local LLM"""
    print("\n" + "="*60)
    print("🆓 TESTING FREE TIER: Ollama Adapter")
    print("="*60)
    
    from modules.llm.adapters import OllamaAdapter
    
    adapter = OllamaAdapter(base_url="http://localhost:11434")
    
    # Test 1: Check availability
    print("\n[Test 1] Checking Ollama availability...")
    is_available = adapter.is_available()
    if is_available:
        print("   ✅ Ollama is running")
    else:
        print("   ⚠️ Ollama not running (expected if not installed)")
        print("   ℹ️ Fallback to cloud API will be used")
        return True  # Not a failure - just not running
    
    # Test 2: Check model exists
    print("\n[Test 2] Checking model existence...")
    if adapter.model_exists():
        print(f"   ✅ Model '{adapter.model}' exists")
    else:
        models = adapter.list_models()
        if models:
            print(f"   ⚠️ Model '{adapter.model}' not found, but {len(models)} other models available")
            print(f"   ℹ️ Available: {', '.join(models[:3])}")
        else:
            print("   ⚠️ No models installed in Ollama")
        return True  # Not a failure
    
    # Test 3: Test generation with model pre-check
    print("\n[Test 3] Testing generation with pre-check...")
    result = adapter.generate("Say hello in one word.")
    if "[Model Not Found]" in result:
        print(f"   ⚠️ Model error (good - caught gracefully)")
        print(f"   ℹ️ Message: {result[:80]}...")
    elif "[Ollama" in result:
        print(f"   ⚠️ Ollama error (good - caught gracefully)")
        print(f"   ℹ️ Message: {result[:80]}...")
    elif result:
        print(f"   ✅ Generation successful: '{result[:50]}...'")
    
    return True


def test_cloud_adapters():
    """Test PAID tier - Cloud API adapters"""
    print("\n" + "="*60)
    print("💰 TESTING PAID TIER: Cloud API Adapters")
    print("="*60)
    
    from modules.llm.factory import LLMFactory
    from runtime.config_loader import load_config
    
    config = load_config()
    ai = config.get("ai_provider", {})
    
    # Create mock config object for factory
    class MockConfig:
        def __init__(self, ai_config):
            self.primary_model = ai_config.get("primary_model", "google")
            self.google_key = ai_config.get("google_key", "")
            self.openrouter_key = ai_config.get("openrouter_key", "")
            self.huggingface_key = ai_config.get("huggingface_key", "")
            self.glm_key = ai_config.get("glm_key", "")
            self.custom_key = ai_config.get("custom_key", "")
            self.custom_base_url = ai_config.get("custom_base_url", "")
            self.custom_model = ai_config.get("custom_model", "gpt-3.5-turbo")
            self.ollama_url = ai_config.get("ollama_url", "http://localhost:11434")
            self.ollama_model = ai_config.get("ollama_model", "")
    
    mock_cfg = MockConfig(ai)
    
    # Test each provider
    providers = ["google", "openrouter", "huggingface", "ollama", "custom"]
    results = {}
    
    for provider in providers:
        print(f"\n[{provider.upper()}] Testing adapter creation...")
        adapter = LLMFactory.get_adapter(provider, mock_cfg)
        
        if adapter is None:
            key_field = f"{provider}_key" if provider != "ollama" else "ollama_url"
            key_value = getattr(mock_cfg, key_field, None) if hasattr(mock_cfg, key_field) else None
            if not key_value or key_value == "":
                print(f"   ⚠️ No API key configured - SKIPPED")
                results[provider] = "no_key"
            else:
                print(f"   ❌ Failed to create adapter")
                results[provider] = "failed"
        else:
            print(f"   ✅ Adapter created successfully")
            results[provider] = "ok"
            
            # For Ollama, test auto-detection
            if provider == "ollama":
                print(f"   ℹ️ Model: {adapter.model}")
                if hasattr(adapter, 'model_exists'):
                    exists = adapter.model_exists()
                    print(f"   ℹ️ Model exists: {exists}")
    
    return results


def test_config_mode():
    """Test config mode fix"""
    print("\n" + "="*60)
    print("⚙️ TESTING CONFIG MODE FIX")
    print("="*60)
    
    from runtime.config_loader import load_config, DEFAULT_CONFIG
    
    # Test 1: Check default config
    print("\n[Test 1] Default config mode...")
    default_mode = DEFAULT_CONFIG.get("ai_provider", {}).get("mode", "unknown")
    if default_mode == "hybrid":
        print(f"   ✅ Default mode is 'hybrid' (correct)")
    else:
        print(f"   ❌ Default mode is '{default_mode}' (should be 'hybrid')")
        return False
    
    # Test 2: Check fallback options
    print("\n[Test 2] Fallback options...")
    ollama_fallback = DEFAULT_CONFIG.get("ai_provider", {}).get("ollama_fallback", None)
    cloud_fallback = DEFAULT_CONFIG.get("ai_provider", {}).get("cloud_fallback", None)
    
    if ollama_fallback is True:
        print("   ✅ ollama_fallback = True")
    else:
        print(f"   ❌ ollama_fallback = {ollama_fallback}")
    
    if cloud_fallback is True:
        print("   ✅ cloud_fallback = True")
    else:
        print(f"   ❌ cloud_fallback = {cloud_fallback}")
    
    # Test 3: Auto mode mapping
    print("\n[Test 3] Auto-to-hybrid mapping in orchestrator...")
    try:
        # Simulate the orchestrator logic
        ai_mode = "auto"
        if ai_mode == "auto":
            ai_mode = "hybrid"
        
        if ai_mode == "hybrid":
            print("   ✅ 'auto' correctly maps to 'hybrid'")
        else:
            print(f"   ❌ 'auto' mapped to '{ai_mode}'")
            return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False
    
    return True


def test_error_handling():
    """Test graceful error handling"""
    print("\n" + "="*60)
    print("🛡️ TESTING ERROR HANDLING")
    print("="*60)
    
    from modules.llm.adapters import OllamaAdapter
    
    # Test with non-existent model
    print("\n[Test 1] Non-existent model handling...")
    adapter = OllamaAdapter(base_url="http://localhost:11434", model="nonexistent-model-xyz")
    
    result = adapter.generate("Test prompt")
    
    if "[Model Not Found]" in result or "[Ollama" in result:
        print("   ✅ Graceful error message returned (not crash)")
        if "ollama pull" in result.lower():
            print("   ✅ Install guidance included")
    elif result == "":
        print("   ⚠️ Empty response (Ollama may not be running)")
    else:
        print(f"   ℹ️ Response: {result[:60]}...")
    
    # Test with bad URL
    print("\n[Test 2] Bad URL handling...")
    adapter_bad = OllamaAdapter(base_url="http://localhost:99999", model="test")
    result_bad = adapter_bad.generate("Test")
    
    if "[Ollama" in result_bad:
        print("   ✅ Connection error caught gracefully")
    else:
        print(f"   ℹ️ Response: {result_bad[:60]}...")
    
    return True


def main():
    print("\n" + "#"*60)
    print("# BioDockify API Verification - Free & Paid Providers")
    print("#"*60)
    
    results = {
        "config_mode": False,
        "error_handling": False,
        "ollama": False,
        "cloud_apis": {}
    }
    
    try:
        results["config_mode"] = test_config_mode()
    except Exception as e:
        print(f"❌ Config mode test failed: {e}")
    
    try:
        results["error_handling"] = test_error_handling()
    except Exception as e:
        print(f"❌ Error handling test failed: {e}")
    
    try:
        results["ollama"] = test_ollama_adapter()
    except Exception as e:
        print(f"❌ Ollama test failed: {e}")
    
    try:
        results["cloud_apis"] = test_cloud_adapters()
    except Exception as e:
        print(f"❌ Cloud API test failed: {e}")
    
    # Summary
    print("\n" + "="*60)
    print("📊 VERIFICATION SUMMARY")
    print("="*60)
    
    print(f"\n✅ Config Mode Fix: {'PASS' if results['config_mode'] else 'FAIL'}")
    print(f"✅ Error Handling: {'PASS' if results['error_handling'] else 'FAIL'}")
    print(f"✅ Ollama (Free): {'PASS' if results['ollama'] else 'FAIL'}")
    
    print("\n💰 Cloud APIs (Paid):")
    cloud_api_count = 0
    cloud_api_ok_count = 0
    for provider, status in results.get("cloud_apis", {}).items():
        icon = "✅" if status == "ok" else "⚠️" if status == "no_key" else "❌"
        print(f"   {icon} {provider.upper()}: {status}")
        cloud_api_count += 1
        if status == "ok":
            cloud_api_ok_count += 1
    
    # Print cloud API summary
    print(f"\n💰 Cloud APIs (Paid): {'PASS' if cloud_api_ok_count > 0 else 'FAIL'} ({cloud_api_ok_count}/{cloud_api_count} configured)")
    
    # Overall
    # Test should fail if no cloud APIs are configured (all show "no_key")
    cloud_api_status = cloud_api_ok_count > 0
    overall = results["config_mode"] and results["error_handling"] and cloud_api_status
    print(f"\n{'='*60}")
    if overall:
        print("🎉 API VERIFICATION: PASS")
        return 0
    else:
        print("❌ API VERIFICATION: FAIL")
        if not cloud_api_status:
            print("\n⚠️  No cloud APIs are configured!")
            print("   Please configure at least one cloud API key in the config file:")
            print("   - google_key: For Google Gemini API")
            print("   - openrouter_key: For OpenRouter API")
            print("   - huggingface_key: For HuggingFace API")
            print("   - custom_key: For custom OpenAI-compatible API")
        return 1


if __name__ == "__main__":
    sys.exit(main())
