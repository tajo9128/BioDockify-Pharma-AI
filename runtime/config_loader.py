"""
BioDockify Configuration Engine
Handles loading, saving, and validation of the application's runtime configuration.
Implements the 'BioDockify v2 Settings Contract'.
"""

import os
import platform
import yaml
import shutil
from pathlib import Path
from typing import Dict, Any, Optional

import sys

import base64
import uuid

# Define paths
BASE_DIR = Path(__file__).parent.parent


class SecurityManager:
    """
    Handles encryption of sensitive configuration values at rest.
    Uses cryptography.fernet for robust encryption with a machine-specific key.
    """

    def __init__(self):
        self.sensitive_suffices = ("_key", "password", "secret", "token", "email")
        self._key = self._get_or_create_key()
        self._fernet = None
        if self._key:
            try:
                from cryptography.fernet import Fernet

                self._fernet = Fernet(self._key)
            except ImportError:
                logger.warning(
                    "cryptography not found. Falling back to basic obfuscation."
                )

        # Legacy node info for backward compatibility fallback
        self.node = str(uuid.getnode())

    def _get_or_create_key(self) -> Optional[bytes]:
        """Load or generate a machine-specific encryption key."""
        try:
            from cryptography.fernet import Fernet

            # Path for the key: ~/.biodockify/encryption.key
            key_dir = Path.home() / ".biodockify"
            key_path = key_dir / "encryption.key"

            if key_path.exists():
                return key_path.read_bytes()

            # Create new key
            key_dir.mkdir(parents=True, exist_ok=True)
            key = Fernet.generate_key()
            key_path.write_bytes(key)
            # Try to set permissions (owner only)
            try:
                key_path.chmod(0o600)
            except:
                pass
            return key
        except Exception as e:
            logger.error(f"Failed to manage encryption key: {e}")
            return None

    def _xor_cipher(self, text: str) -> str:
        """Legacy XOR cipher for backward compatibility."""
        if not text:
            return text
        return "".join(
            chr(ord(c) ^ ord(self.node[i % len(self.node)])) for i, c in enumerate(text)
        )

    def encrypt_value(self, value: str) -> str:
        """Encrypts a string value using Fernet."""
        if not value or value.startswith("ENC:"):
            return value
        if not self._fernet:
            # Fallback to XOR obfuscation if Fernet is unavailable
            try:
                xored = self._xor_cipher(value)
                b64 = base64.b64encode(xored.encode("utf-8")).decode("utf-8")
                return f"ENC:XOR:{b64}"
            except:
                return value

        try:
            encrypted = self._fernet.encrypt(value.encode("utf-8")).decode("utf-8")
            return f"ENC:FRN:{encrypted}"
        except Exception as e:
            logger.error(f"Fernet encryption failed: {e}")
            return value

    def decrypt_value(self, value: str) -> str:
        """Decrypts a string value with backward compatibility fallback."""
        if not value or not isinstance(value, str) or not value.startswith("ENC:"):
            return value

        try:
            # New format checks
            if value.startswith("ENC:FRN:") and self._fernet:
                payload = value[8:]
                return self._fernet.decrypt(payload.encode("utf-8")).decode("utf-8")

            if value.startswith("ENC:XOR:"):
                payload = value[8:]
                xored = base64.b64decode(payload).decode("utf-8")
                return self._xor_cipher(xored)

            # Legacy format (no type prefix)
            payload = value[4:]
            try:
                # Try Fernet first if it looks like it (unlikely but safe)
                if self._fernet:
                    try:
                        return self._fernet.decrypt(payload.encode("utf-8")).decode(
                            "utf-8"
                        )
                    except:
                        pass

                # Fallback to XOR
                xored = base64.b64decode(payload).decode("utf-8")
                return self._xor_cipher(xored)
            except:
                return value

        except Exception as e:
            logger.warning(f"Config Decryption Error: {e}. Returning raw value.")
            return value

    def process_config(self, config: Dict, mode: str) -> Dict:
        """
        Recursively encrypts or decrypts sensitive keys in a config dict.
        mode: 'encrypt' or 'decrypt'
        """
        processed = config.copy()
        for k, v in processed.items():
            if isinstance(v, dict):
                processed[k] = self.process_config(v, mode)
            elif isinstance(v, str) and any(
                k.endswith(s) for s in self.sensitive_suffices
            ):
                if mode == "encrypt":
                    processed[k] = self.encrypt_value(v)
                elif mode == "decrypt":
                    processed[k] = self.decrypt_value(v)
        return processed


security_manager = SecurityManager()


def get_config_path():
    """
    Determines the appropriate config path based on environment.
    Prioritizes %APPDATA% in production (frozen/installed), falls back to local dev.
    """
    app_name = "BioDockify"

    # Check if running as compiled executable (PyInstaller)
    if getattr(sys, "frozen", False):
        # Production: Use User AppData
        app_data = os.getenv("APPDATA")
        if app_data:
            config_dir = Path(app_data) / app_name
            config_dir.mkdir(parents=True, exist_ok=True)
            return config_dir / "config.yaml"

    # Development: Use local source directory
    # Support BIO_ENV for specific configs (dev/prod/staging)
    # Support explicit path override
    explicit_path = os.getenv("BIO_CONFIG_PATH")
    if explicit_path:
        return Path(explicit_path)

    env = os.getenv("BIO_ENV", "").lower()
    filename = f"config.{env}.yaml" if env else "config.yaml"

    # Fallback to standard config if env-specific doesn't exist
    target = BASE_DIR / "runtime" / filename
    if env and not target.exists():
        print(f"[*] {filename} not found, falling back to config.yaml")
        return BASE_DIR / "runtime" / "config.yaml"

    return target


CONFIG_PATH = get_config_path()

# -----------------------------------------------------------------------------
# DEFAULT CONFIGURATION (The "Safe Contract")
# -----------------------------------------------------------------------------
DEFAULT_CONFIG = {
    # SECTION A: PROJECT & RESEARCH CONTEXT
    "project": {
        "name": "My PhD Research",
        "type": "PhD Thesis",
        "disease_context": "Alzheimer's Disease",
        "stage": "Literature Review",
    },
    # SECTION B: AGENT ZERO BEHAVIOR
    "agent": {
        "mode": "semi-autonomous",
        "reasoning_depth": "standard",
        "self_correction": True,
        "max_retries": 3,
        "failure_policy": "ask_user",
    },
    # SECTION C: LITERATURE & EVIDENCE
    "literature": {
        "sources": ["pubmed"],
        "enable_crossref": True,
        "year_range": 10,
        "novelty_strictness": "medium",
        "grobid_url": "http://localhost:8070",
    },
    # NEW: Pharma Pipeline Controls
    "pharma": {
        "enable_pubtator": True,
        "enable_semantic_scholar": True,
        "enable_unpaywall": True,
        "citation_threshold": "high",
        "sources": {
            "pubmed": True,
            "pmc": True,
            "biorxiv": False,
            "chemrxiv": False,
            "clinicaltrials": True,
            "google_scholar": False,
            "openalex": True,
            "semantic_scholar": True,
            "ieee": False,
            "elsevier": False,
            "scopus": False,
            "wos": False,
            "science_index": False,
        },
    },
    # SECTION D: NANOBOT & CHANNELS
    "nanobot": {"headless_browser": True, "stealth_mode": False, "browser_timeout": 30},
    "channels": {
        "telegram": {"enabled": False, "token": "", "allow_from": []},
        "whatsapp": {
            "enabled": False,
            "bridge_url": "ws://localhost:3001",
            "auth_token": "",
            "allow_from": [],
        },
        "discord": {
            "enabled": False,
            "token": "",
            "allow_from": [],
            "gateway_url": "wss://gateway.discord.gg/?v=10&encoding=json",
        },
        "email": {
            "enabled": False,
            "smtp_host": "",
            "smtp_port": 587,
            "smtp_user": "",
            "smtp_password": "",
            "from_email": "",
            "to_emails": "",
        },
    },
    # SECTION E: API & AI SETTINGS
    "ai_provider": {
        "mode": "ollama",  # Default to Ollama (local)
        "primary_model": "ollama",  # Default to Ollama
        "cloud_fallback": True,
        # Ollama - use host.docker.internal for Docker, localhost for local dev
        "ollama_url": "http://host.docker.internal:11434/v1" if os.path.exists("/.dockerenv") else "http://localhost:11434/v1",
        "ollama_model": "",
        "openrouter_key": "",
        "huggingface_key": "",
        "glm_key": "",
        "elsevier_key": "",
        "pubmed_email": "",
        "item_key": "",  # Generic Item Key (not used but reserved)
        # Specific Providers
        "mistral_key": "",
        "mistral_model": "mistral-large-latest",
        "venice_key": "",
        "venice_model": "llama-3-70b",
        "kimi_key": "",
        "kimi_model": "moonshot-v1-8k",
        "deepseek_key": "",  # Already exists but grouping related keys
        "deepseek_model": "deepseek-chat",
        # Azure OpenAI
        "azure_endpoint": "",
        "azure_deployment": "",
        "azure_key": "",
        "azure_api_version": "2024-02-15-preview",
        # AWS Bedrock
        "aws_access_key": "",
        "aws_secret_key": "",
        "aws_region_name": "us-east-1",
        "aws_model_id": "anthropic.claude-3-sonnet-20240229-v1:0",
        # Custom / Universal
        "custom_key": "",
        "custom_base_url": "",
        "custom_model": "gpt-3.5-turbo",
        # Web Research Keys
        "serper_key": "",  # For Google Search (search.serper.dev)
        "jina_key": "",  # For Content Scraping (r.jina.ai)
        "brave_key": "",  # For Brave Search API
    },
    # NEW: Advanced Hardware Controls
    "ai_advanced": {
        "performance_profile": "high",  # "high", "moderate", "low"
        "context_window": 8192,
        "gpu_layers": -1,
        "thread_count": 8,
    },
    # NEW: User Persona
    "persona": {
        "roles": ["PhD Student"],  # Updated from 'role' to 'roles'
        "strictness": "conservative",
        "introduction": "",
        "research_focus": "",
    },
    # NEW: Output Config
    "output": {
        "format": "markdown",
        "citation_style": "apa",
        "include_disclosure": True,
        "output_dir": "",
    },
    # SECTION I: EXECUTION & SAFETY
    "execution": {
        "mode": "research",
        "max_runtime_minutes": 45,
        "use_knowledge_graph": True,
        "human_approval_gates": True,
    },
    # SYSTEM INTERNALS
    "system": {
        "auto_update": True,
        "pause_on_battery": True,
        "max_cpu_percent": 80,
        "log_level": "INFO",
        "version": "2.6.2",  # Bumped version for config migration
    },
}


class ConfigLoader:
    def __init__(self):
        self._ensure_config_exists()

    def _ensure_config_exists(self):
        """Create default config if missing."""
        if not CONFIG_PATH.exists():
            self._save_to_disk(DEFAULT_CONFIG)
            print(f"[+] Created default config at {CONFIG_PATH}")

    def load_config(self) -> Dict[str, Any]:
        """Load configuration from disk with fail-safe defaults and env var overrides."""
        try:
            print(f"[*] Loading config from: {CONFIG_PATH}")
            with open(CONFIG_PATH, "r") as f:
                user_config = yaml.safe_load(f)

            if not user_config:
                user_config = DEFAULT_CONFIG

            # Merit: Deep merge with defaults to ensure new keys exist
            merged = self._merge_defaults(DEFAULT_CONFIG, user_config)

            # Environment Variable Overrides (Runtime Overlay)
            merged = self._apply_env_overrides(merged)

            # Migration Check
            final_config = self._migrate_config(merged)

            # Decrypt sensitive values for Runtime usage
            decrypted = security_manager.process_config(final_config, "decrypt")

            # Resolve Auto Mode
            self._resolve_auto_mode(decrypted)

            return decrypted

        except Exception as e:
            print(f"[!] Error loading config: {e}")
            return DEFAULT_CONFIG

    def _apply_env_overrides(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Overlays environment variables onto the config."""
        # AI Provider Keys
        if os.getenv("BIO_GOOGLE_KEY"):
            config["ai_provider"]["google_key"] = os.getenv("BIO_GOOGLE_KEY")
        if os.getenv("BIO_OPENROUTER_KEY"):
            config["ai_provider"]["openrouter_key"] = os.getenv("BIO_OPENROUTER_KEY")
        if os.getenv("BIO_OLLAMA_URL"):
            config["ai_provider"]["ollama_url"] = os.getenv("BIO_OLLAMA_URL")
        elif os.getenv("OLLAMA_URL"):
            config["ai_provider"]["ollama_url"] = os.getenv("OLLAMA_URL")
        
        # Force Ollama mode if OLLAMA_URL is set
        if os.getenv("OLLAMA_URL"):
            config["ai_provider"]["mode"] = "ollama"
        
        # System Overrides
        if os.getenv("BIO_MODE"):
            config["execution"]["mode"] = os.getenv("BIO_MODE")

        return config

    def _resolve_auto_mode(self, config: Dict[str, Any]):
        """
        Resolves 'auto' mode to a specific provider based on available keys.
        Logic: Google -> OpenRouter -> HuggingFace -> Custom -> OpenAI (Fallback)
        """
        ai = config.get("ai_provider", {})
        if ai.get("mode") == "auto":
            if ai.get("google_key"):
                config["ai_provider"]["mode"] = "google"
                print("[*] Auto-Mode: Selected 'google' (Key detected)")
            elif ai.get("openrouter_key"):
                config["ai_provider"]["mode"] = "openrouter"
                print("[*] Auto-Mode: Selected 'openrouter' (Key detected)")
            elif ai.get("huggingface_key"):
                config["ai_provider"]["mode"] = "huggingface"
                print("[*] Auto-Mode: Selected 'huggingface' (Key detected)")
            elif ai.get("custom_key") and ai.get("custom_base_url"):
                config["ai_provider"]["mode"] = "custom"
                print("[*] Auto-Mode: Selected 'custom' (Key + URL detected)")
            else:
                # Fallback to OpenAI (standard Paid API)
                # This ensures we don't default to specific vendor unless configured
                config["ai_provider"]["mode"] = "openai"
                print(
                    "[*] Auto-Mode: Defaulting to 'openai'. Please configure API keys."
                )

    def save_config(self, new_config: Dict[str, Any]) -> bool:
        """Save new configuration to disk (Legacy Wrapper)."""
        success, _ = self.save_config_detailed(new_config)
        return success

    def save_config_detailed(self, new_config: Dict[str, Any]) -> (bool, str):
        """Save new configuration to disk with detailed error reporting."""
        print(f"[*] Saving configuration to: {CONFIG_PATH}")
        try:
            # 1. Validate
            is_valid, error_msg = self._validate_config(new_config)
            if not is_valid:
                print(f"[!] Config validation failed: {error_msg}")
                return False, error_msg

            # 2. Backup existing
            self.backup_config()

            # 3. Encrypt sensitive values before saving to Disk
            secure_config = security_manager.process_config(new_config, "encrypt")
            self._save_to_disk(secure_config)
            return True, "Settings saved successfully"
        except Exception as e:
            print(f"[!] Failed to save config: {e}")
            return False, str(e)

    def reset_to_defaults(self) -> Dict[str, Any]:
        """Reset configuration to factory defaults."""
        self._save_to_disk(DEFAULT_CONFIG)
        return DEFAULT_CONFIG

    def _save_to_disk(self, config_data: Dict[str, Any]):
        """Helper to write YAML to disk atomically."""
        if not CONFIG_PATH.parent.exists():
            CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)

        # Write to temp file first
        tmp_path = CONFIG_PATH.with_suffix(".tmp")
        try:
            with open(tmp_path, "w") as f:
                yaml.dump(config_data, f, default_flow_style=False, sort_keys=False)

            # Atomic rename/replace
            if list(platform.uname()).count("Windows") > 0:
                # Windows can't atomic replace if dest exists, need remove first
                if CONFIG_PATH.exists():
                    try:
                        os.remove(CONFIG_PATH)
                    except Exception as e:
                        print(
                            f"[!] Warning: Could not remove old config ({e}). Attempting direct overwrite fallback."
                        )
                        # Fallback: direct write to target, ignoring temp file
                        with open(CONFIG_PATH, "w") as f:
                            yaml.dump(
                                config_data,
                                f,
                                default_flow_style=False,
                                sort_keys=False,
                            )
                        if tmp_path.exists():
                            os.remove(tmp_path)
                        return

            os.replace(tmp_path, CONFIG_PATH)
        except Exception as e:
            print(f"[!] Atomic save failed: {e}")
            if tmp_path.exists():
                os.remove(tmp_path)
            raise e

    def _merge_defaults(self, defaults: Dict, user: Dict) -> Dict:
        """
        Recursive merge to ensure user config has all required keys from defaults.
        Preserves user values where they exist.
        """
        result = defaults.copy()
        for key, value in user.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                result[key] = self._merge_defaults(result[key], value)
            else:
                result[key] = value
        return result

    def backup_config(self):
        """Creates a backup of the current config file."""
        if CONFIG_PATH.exists():
            backup_path = CONFIG_PATH.with_suffix(".bak")
            try:
                shutil.copy2(CONFIG_PATH, backup_path)
            except Exception as e:
                print(f"[!] Backup failed: {e}")

    def _migrate_config(self, config: Dict) -> Dict:
        """
        Handles version migration and schema updates.
        """
        # Migrate persona.role -> persona.roles
        persona = config.get("persona", {})
        if "role" in persona and "roles" not in persona:
            role = persona.get("role")
            if role:
                persona["roles"] = [role]
            else:
                persona["roles"] = ["PhD Student"]
            # Remove old key
            persona.pop("role", None)
            print(f"[*] Migrated legacy persona role '{role}' to roles list.")

        current_version = config.get("system", {}).get("version", "0.0.0")
        target_version = DEFAULT_CONFIG["system"]["version"]

        if current_version != target_version:
            print(f"[*] Migrating Config: {current_version} -> {target_version}")
            # Logic for specific version upgrades could go here
            # For now, we just update the version tag since _merge_defaults handles structure
            config["system"]["version"] = target_version
            # Auto-save migrated config (encrypted)
            secure = security_manager.process_config(config, "encrypt")
            self._save_to_disk(secure)

        return config

    def _validate_config(self, config: Dict) -> (bool, str):
        """
        Basic Schema Validation.
        Returns (True, "OK") if valid, (False, "Error Message") otherwise.
        """
        required_sections = ["project", "agent", "ai_provider", "system"]
        for section in required_sections:
            if section not in config:
                msg = f"Missing required section: {section}"
                print(f"[!] {msg}")
                return False, msg

        # Validate critical numeric ranges
        try:
            ctx = config.get("ai_advanced", {}).get("context_window", 8192)
            # Ensure it's an integer and within reasonable bounds
            if not isinstance(ctx, int) and not str(ctx).isdigit():
                return False, f"Invalid context_window: {ctx} is not a number"

            if int(ctx) < 1024:
                return False, f"Invalid context_window: {ctx} must be >= 1024"
        except Exception as e:
            return False, f"Validation Logic Error: {e}"

        return True, "OK"


# Singleton instance
_loader = ConfigLoader()


def load_config() -> Dict[str, Any]:
    return _loader.load_config()


def save_config(config: Dict[str, Any]) -> bool:
    return _loader.save_config(config)


def save_config_detailed(config: Dict[str, Any]) -> (bool, str):
    return _loader.save_config_detailed(config)


def reset_config() -> Dict[str, Any]:
    return _loader.reset_to_defaults()


if __name__ == "__main__":
    # Test run
    print(f"Config Path: {CONFIG_PATH}")
    cfg = load_config()
    print(f"Loaded Config Mode: {cfg['ai_provider']['mode']}")
