#!/usr/bin/env python3
import uvicorn
import os
import sys
import logging
import traceback

# Configure immediate logging to stdout
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout)
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

logging.info("Server process started. Initializing...")

# Add the current directory to sys.path so imports work
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# --- PROTECTIVE STARTUP CHECKS ---
REQUIRED_ENV = [
    # "OLLAMA_HOST" # Uncomment if Ollama is critical
]

# Check for .env file and load it if python-dotenv is available (optional)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

missing = [v for v in REQUIRED_ENV if not os.getenv(v)]
if missing:
    logging.warning("⚠️  Startup Warning: Missing recommended environment variables: %s", ", ".join(missing))

# Check for critical dependencies before importing heavy libs
TF_AVAILABLE = False
try:
    import tensorflow
    TF_AVAILABLE = True
except ImportError:
    logging.warning("⚠️ TensorFlow not found. DECIMER/ML features will be disabled.")
    logging.warning("   Run 'pip install tensorflow' to enable full functionality.")
# ---------------------------------


# EXPLICIT IMPORTS FOR PYINSTALLER BUNDLING (graceful)
try:
    import tensorflow as tf
except ImportError:
    tf = None

try:
    import numpy as np
except ImportError:
    logging.warning("NumPy not found")
    np = None

try:
    import PIL
except ImportError:
    PIL = None

try:
    import pypdf
except ImportError:
    pypdf = None

try:
    import pdfminer
except ImportError:
    pdfminer = None

# Optional dependencies
# Safe Import of Main App
try:
    logging.info("Attempting to import api.main...")
    from api.main import app
    logging.info("✅ api.main imported successfully.")
except Exception as e:
    logging.critical("CRITICAL ERROR: Failed to import api.main!")
    traceback.print_exc()
    sys.exit(1)

def main():
    try:
        logging.info("Starting Uvicorn server...")
        # Bind to 0.0.0.0 (More robust for Windows/IPv6 resolution of localhost)
        uvicorn.run(app, host="0.0.0.0", port=3000, log_level="info")
    except Exception as e:
        logging.critical(f"Server crashed: {e}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
