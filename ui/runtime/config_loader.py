"""
Runtime configuration loader module for BioDockify
Loads configuration from config.yaml or creates default config
"""

import os
import yaml
from typing import Dict, Any


def load_config() -> Dict[str, Any]:
    """Load runtime configuration from config.yaml"""
    config_path = os.path.join(os.path.dirname(__file__), 'config.yaml')

    default_config = {
        'openai_key': '',
        'elsevier_key': '',
        'ollama_url': 'http://localhost:11434',
        'neo4j_host': 'bolt://localhost:7687',
        'neo4j_user': 'neo4j',
        'neo4j_password': 'password',
    }

    # Create default config if it doesn't exist
    if not os.path.exists(config_path):
        with open(config_path, 'w') as f:
            yaml.dump(default_config, f)
            f.flush()
        return default_config

    # Load existing config
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    # Use default values for missing keys
    if config is None:
        config = {}

    for key, value in default_config.items():
        if key not in config:
            config[key] = value

    return config


def save_config(config: Dict[str, Any]) -> None:
    """Save configuration to config.yaml"""
    config_path = os.path.join(os.path.dirname(__file__), 'config.yaml')

    with open(config_path, 'w') as f:
        yaml.dump(config, f)
        f.flush()


def get_config_value(key: str, default: Any = None) -> Any:
    """Get a specific configuration value"""
    config = load_config()
    return config.get(key, default)


def set_config_value(key: str, value: Any) -> None:
    """Set a specific configuration value"""
    config = load_config()
    config[key] = value
    save_config(config)
