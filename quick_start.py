#!/usr/bin/env python3
"""
BioDockify Quick Start Script
Guides students through initial setup and opens the application in browser.
"""

import os
import sys
import time
import socket
import subprocess
import webbrowser
import platform
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("quickstart")

# Configuration
BACKEND_PORT = 3000
FRONTEND_PORT = 3001
OLLAMA_PORT = 11434
STARTUP_TIMEOUT = 60  # seconds

BANNER = """
╔══════════════════════════════════════════════════════════════════╗
║                                                                  ║
║   🧬 BioDockify AI v3.1.0 - Pharma Research Assistant            ║
║   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   ║
║   Quick Start Setup Wizard                                       ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
"""


def clear_screen():
    """Clear the terminal screen."""
    os.system("cls" if platform.system() == "Windows" else "clear")


def print_header():
    """Print the application banner."""
    print(BANNER)


def check_port_open(port: int, host: str = "127.0.0.1") -> bool:
    """Check if a port is open (service running)."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(2)
            result = s.connect_ex((host, port))
            return result == 0
    except Exception:
        return False


def wait_for_port(
    port: int, timeout: int = STARTUP_TIMEOUT, name: str = "Service"
) -> bool:
    """Wait for a port to become available."""
    logger.info(f"⏳ Waiting for {name} on port {port}...")
    start_time = time.time()

    while time.time() - start_time < timeout:
        if check_port_open(port):
            logger.info(f"✅ {name} is ready on port {port}")
            return True
        time.sleep(1)

    logger.warning(f"⚠️  {name} did not start within {timeout} seconds")
    return False


def detect_ollama() -> dict:
    """Detect if Ollama is installed and running."""
    result = {
        "installed": False,
        "running": False,
        "models": [],
        "path": None,
        "url": f"http://localhost:{OLLAMA_PORT}",
        "docker_url": f"http://host.docker.internal:{OLLAMA_PORT}",
    }

    # Check if Ollama is in PATH
    ollama_path = shutil.which("ollama")
    if ollama_path:
        result["installed"] = True
        result["path"] = ollama_path

    # Check if Ollama is running on localhost
    if check_port_open(OLLAMA_PORT):
        result["running"] = True
        # Try to list models
        try:
            proc = subprocess.run(
                ["ollama", "list"], capture_output=True, text=True, timeout=10
            )
            if proc.returncode == 0:
                lines = proc.stdout.strip().split("\n")[1:]  # Skip header
                result["models"] = [line.split()[0] for line in lines if line.strip()]
        except Exception:
            pass
    # Check Docker host URL if localhost not running
    elif check_port_open(OLLAMA_PORT, "host.docker.internal"):
        result["running"] = True
        result["url"] = result["docker_url"]

    return result


def detect_lm_studio() -> dict:
    """Detect if LM Studio is running."""
    # Try localhost first, then host.docker.internal for Docker
    urls_to_try = [
        f"http://localhost:{LM_STUDIO_PORT}/v1",
        f"http://host.docker.internal:{LM_STUDIO_PORT}/v1",
    ]

    result = {"running": False, "url": urls_to_try[0], "docker_url": urls_to_try[1]}

    for url in urls_to_try:
        try:
            import urllib.request
            import json

            with urllib.request.urlopen(f"{url}/models", timeout=5) as response:
                data = json.loads(response.read().decode())
                if data.get("data"):
                    result["running"] = True
                    result["url"] = url
                    result["model"] = data["data"][0].get("id", "unknown")
                    break
        except Exception:
            continue

    return result


def check_api_keys() -> dict:
    """Check for configured API keys."""
    keys = {"google": False, "openrouter": False, "deepseek": False, "custom": False}

    try:
        from runtime.config_loader import load_config

        config = load_config()
        ai_config = config.get("ai_provider", {})

        if ai_config.get("google_key"):
            keys["google"] = True
        if ai_config.get("openrouter_key"):
            keys["openrouter"] = True
        if ai_config.get("deepseek_key"):
            keys["deepseek"] = True
        if ai_config.get("custom_key") and ai_config.get("custom_base_url"):
            keys["custom"] = True
    except Exception:
        pass

    return keys


def print_detection_results():
    """Print the detection results for all services."""
    print("\n" + "=" * 60)
    print("🔍 SERVICE DETECTION")
    print("=" * 60)

    # Ollama
    ollama = detect_ollama()
    print(f"\n📦 Ollama:")
    if ollama["installed"]:
        print(f"   ✅ Installed: {ollama['path']}")
    else:
        print("   ❌ Not installed")
        print("   📥 Install from: https://ollama.ai")

    if ollama["running"]:
        print(f"   ✅ Running on port {OLLAMA_PORT}")
        if ollama["models"]:
            print(f"   📋 Models: {', '.join(ollama['models'])}")
        else:
            print("   ⚠️  No models installed. Run: ollama pull llama3.2")
    else:
        print(f"   ❌ Not running")
        if ollama["installed"]:
            print("   🚀 Start with: ollama serve")

    # API Keys
    keys = check_api_keys()
    print(f"\n🔑 API Keys:")
    any_key = False
    if keys["google"]:
        print("   ✅ Google AI (Gemini)")
        any_key = True
    if keys["openrouter"]:
        print("   ✅ OpenRouter")
        any_key = True
    if keys["deepseek"]:
        print("   ✅ DeepSeek")
        any_key = True
    if keys["custom"]:
        print("   ✅ Custom API")
        any_key = True

    if not any_key:
        print("   ⚠️  No API keys configured")
        print("   📝 Configure in Settings or edit runtime/config.yaml")

    print("\n" + "=" * 60)

    # Determine AI mode
    if ollama["running"]:
        return "ollama"
    elif any_key:
        return "cloud"
    else:
        return "none"


def open_browser(url: str):
    """Open URL in default browser."""
    try:
        webbrowser.open(url)
        logger.info(f"🌐 Opening browser: {url}")
    except Exception as e:
        logger.warning(f"⚠️  Could not open browser: {e}")
        logger.info(f"   Please open manually: {url}")


def start_backend():
    """Start the backend server."""
    logger.info("🚀 Starting BioDockify Backend...")

    # Check if already running
    if check_port_open(BACKEND_PORT):
        logger.info(f"✅ Backend already running on port {BACKEND_PORT}")
        return True

    # Start server
    try:
        if platform.system() == "Windows":
            # Windows: Use pythonw for background process
            subprocess.Popen(
                [sys.executable, "server.py"],
                creationflags=subprocess.CREATE_NEW_CONSOLE,
                cwd=os.getcwd(),
            )
        else:
            # Unix: Use nohup
            subprocess.Popen(
                [sys.executable, "server.py"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
                cwd=os.getcwd(),
            )

        # Wait for backend to start
        return wait_for_port(BACKEND_PORT, name="Backend")
    except Exception as e:
        logger.error(f"❌ Failed to start backend: {e}")
        return False


def create_default_config():
    """Create default configuration if not exists."""
    try:
        from runtime.config_loader import ConfigLoader

        loader = ConfigLoader()
        config = loader.load_config()

        # Auto-detect and configure local AI providers
        ollama = detect_ollama()

        # Get current AI provider settings
        ai_provider = config.get("ai_provider", {})

        # If no provider is configured, auto-configure Ollama
        current_mode = ai_provider.get("mode", ai_provider.get("primary_model", ""))

        if not current_mode or current_mode == "google":
            if ollama["running"]:
                logger.info(
                    f"🔧 Auto-configuring Ollama (detected at {ollama['url']})..."
                )
                ai_provider["mode"] = "ollama"
                ai_provider["ollama_url"] = ollama["url"]
                if ollama.get("models"):
                    ai_provider["ollama_model"] = ollama["models"][0]
                config["ai_provider"] = ai_provider
                try:
                    loader.save_config(config)
                    logger.info("✅ Ollama auto-configured!")
                except Exception as e:
                    logger.warning(f"⚠️  Could not save config: {e}")

        logger.info("✅ Configuration loaded")
        return config
    except Exception as e:
        logger.warning(f"⚠️  Could not load config: {e}")
        return None


def print_quick_start_guide():
    """Print the quick start guide."""
    guide = """
╔══════════════════════════════════════════════════════════════════╗
║                    📚 QUICK START GUIDE                          ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║  1️⃣  FIRST TIME SETUP                                           ║
║     • Configure your AI provider in Settings                    ║
║     • Choose: Ollama (free), LM Studio (free), or Cloud API     ║
║                                                                  ║
║  2️⃣  START RESEARCHING                                          ║
║     • Open the Chat interface                                   ║
║     • Ask questions about your research topic                   ║
║     • Use Agent Zero for deep research tasks                    ║
║                                                                  ║
║  3️⃣  KEYBOARD SHORTCUTS                                         ║
║     • Ctrl+K  - Quick command palette                           ║
║     • Ctrl+/  - Toggle help                                     ║
║     • Ctrl+S  - Save current work                               ║
║                                                                  ║
║  4️⃣  NEED HELP?                                                 ║
║     • Check STUDENT_SETUP_GUIDE.md                              ║
║     • Visit: github.com/tajo9128/BioDockify-pharma-research-ai  ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
"""
    print(guide)


def main():
    """Main entry point for quick start."""
    clear_screen()
    print_header()

    # Step 1: Check/Create configuration
    logger.info("\n📋 Step 1: Checking configuration...")
    config = create_default_config()

    # Step 2: Detect services
    logger.info("\n🔍 Step 2: Detecting AI services...")
    ai_mode = print_detection_results()

    # Step 3: Provide guidance if no AI available
    if ai_mode == "none":
        print("\n⚠️  WARNING: No AI provider detected!")
        print("\nTo use BioDockify, you need one of:")
        print("  1. Ollama (free, local) - https://ollama.ai")
        print("  2. LM Studio (free, local) - https://lmstudio.ai")
        print("  3. Cloud API key (Google, OpenRouter, DeepSeek, etc.)")
        print("\nConfigure in Settings after starting the application.")

        response = input("\nContinue anyway? (y/n): ").strip().lower()
        if response != "y":
            logger.info("Exiting. Please install an AI provider and try again.")
            sys.exit(0)

    # Step 4: Start backend
    logger.info("\n🚀 Step 3: Starting backend server...")
    if not start_backend():
        logger.error("❌ Failed to start backend. Check logs for details.")
        sys.exit(1)

    # Step 5: Print guide
    print_quick_start_guide()

    # Step 6: Open browser
    logger.info("\n🌐 Step 4: Opening application in browser...")
    time.sleep(2)  # Brief delay for server to fully initialize
    open_browser(f"http://localhost:{BACKEND_PORT}")

    # Final message
    print("\n" + "=" * 60)
    print("✅ BioDockify is ready!")
    print("=" * 60)
    print(f"\n🌐 Web Interface: http://localhost:{BACKEND_PORT}")
    print(f"📊 API Docs: http://localhost:{BACKEND_PORT}/docs")
    print(f"⚙️  Settings: http://localhost:{BACKEND_PORT}/settings")
    print("\nPress Ctrl+C to stop the server...")

    # Keep running
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("\n\n👋 Shutting down BioDockify...")
        logger.info("Thank you for using BioDockify!")


if __name__ == "__main__":
    import shutil  # Required for shutil.which

    main()
