import sys
import os

# Add project root to sys.path
sys.path.append(os.getcwd())

print("Checking imports for api.main...")

try:
    # Attempt to import the main application
    # This will trigger SyntaxErrors or immediate ImportErrors
    from api import main
    print("SUCCESS: api.main imported successfully.")
except ImportError as e:
    print(f"IMPORT ERROR: {e}")
    # We might expect some import errors if dependencies (like torch/tensorflow) aren't installed 
    # on the host environment exactly matches the container. 
    # But we are looking for SyntaxErrors or logical crashes at module level.
except SyntaxError as e:
    print(f"SYNTAX ERROR: {e}")
    sys.exit(1)
except Exception as e:
    print(f"RUNTIME ERROR during import: {e}")
    sys.exit(1)
