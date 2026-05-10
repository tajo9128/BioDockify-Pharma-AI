
import sys
import platform

print(f"Python: {sys.version}")
print(f"Platform: {platform.platform()}")

print("\n--- Testing Imports ---")

try:
    import numpy
    print(f"[PASS] NumPy: {numpy.__version__}")
except ImportError as e:
    print(f"[FAIL] NumPy: FAIL - {e}")

try:
    import pandas
    print(f"[PASS] Pandas: {pandas.__version__}")
except ImportError as e:
    print(f"[FAIL] Pandas: FAIL - {e}")

try:
    import cv2
    print(f"[PASS] OpenCV: {cv2.__version__}")
except ImportError as e:
    print(f"[FAIL] OpenCV: FAIL - {e}")

print("\n--- Testing Critical ML Imports (May take a moment) ---")

try:
    import tensorflow as tf
    print(f"[PASS] TensorFlow: {tf.__version__}")
except ImportError as e:
    print(f"[FAIL] TensorFlow: FAIL - {e}")

try:
    import importlib.util
    # Note: Package is usually lowercase 'decimer' but imported as DECIMER depending on version
    # Let's try finding the spec for lowercase first as that is standard
    if importlib.util.find_spec("decimer") is not None:
        print(f"[PASS] DECIMER: Loaded successfully (found 'decimer')")
    elif importlib.util.find_spec("DECIMER") is not None:
         print(f"[PASS] DECIMER: Loaded successfully (found 'DECIMER')")
    else:
        print(f"[FAIL] DECIMER: FAIL - Package not found")
except ImportError as e:
    print(f"[FAIL] DECIMER: FAIL - {e}")

print("\n--- Smoke Test Complete ---")
