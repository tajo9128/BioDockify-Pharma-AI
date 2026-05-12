
import sys
import os
from pathlib import Path

# Add parent to path to allow imports
sys.path.append(str(Path(__file__).parent.parent))

from runtime.config_loader import load_config, save_config, CONFIG_PATH

print(f"Target Config Path: {CONFIG_PATH}")

# 1. Load
cfg = load_config()
print("Initial 'persona':", cfg.get("persona", "MISSING"))

# 2. Modify
if "persona" not in cfg:
    cfg["persona"] = {}
cfg["persona"]["introduction"] = "TEST_PERSISTENCE_VALUE_123"
cfg["pharma"] = {"enable_pubtator": True} # Ensure this section exists

# 3. Save
print("Saving modified config...")
success = save_config(cfg)
print(f"Save Success: {success}")

# 4. Verify from Disk raw
import yaml
with open(CONFIG_PATH, 'r') as f:
    disk_cfg = yaml.safe_load(f)

print("Disk 'persona':", disk_cfg.get("persona", "MISSING"))
print("Disk 'pharma':", disk_cfg.get("pharma", "MISSING"))

if disk_cfg.get("persona", {}).get("introduction") == "TEST_PERSISTENCE_VALUE_123":
    print("TEST PASSED: Value persisted.")
else:
    print("TEST FAILED: Value NOT persisted.")
