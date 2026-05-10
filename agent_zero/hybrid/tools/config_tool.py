"""
Tool for Agent Zero to manage system configuration.
Allows the agent to read and update settings in config.yaml.
"""
import logging
from typing import Dict, Any, Union
from runtime.config_loader import load_config, save_config

logger = logging.getLogger(__name__)

class ConfigManagerTool:
    """
    A tool that allows the agent to read and modify its own configuration.
    """
    
    def get_config(self, params: Dict[str, Any] = None) -> Union[Dict[str, Any], str]:
        """
        Get the current system configuration.
        """
        try:
            config = load_config()
            # If a specific key path is requested, return just that
            if params and "key" in params:
                key_path = params["key"].split(".")
                value = config
                for k in key_path:
                    if isinstance(value, dict) and k in value:
                        value = value[k]
                    else:
                        return f"Key '{params['key']}' not found."
                return value
            
            return config
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            return f"Error loading config: {str(e)}"

    def update_config(self, params: Dict[str, Any]) -> str:
        """
        Update a configuration setting.
        Params:
            key (str): Dot-notation path to the setting (e.g., 'ai_provider.primary_model')
            value (Any): The new value to set.
        """
        key = params.get("key")
        value = params.get("value")
        
        if not key:
            return "Error: 'key' parameter is required."
        
        if value is None:
             return "Error: 'value' parameter is required."

        try:
            # 1. Load current config
            current_config = load_config()
            
            # 2. Deep copy for rollback (simple copy if not nested deeply enough for dict.copy issues)
            import copy
            backup_config = copy.deepcopy(current_config)
            
            # 3. Navigate and update
            keys = key.split(".")
            target = current_config
            
            # Traverse to the parent of the target key
            for k in keys[:-1]:
                if k not in target:
                     target[k] = {} # Create missing sections
                target = target[k]
                if not isinstance(target, dict):
                    return f"Error: '{k}' is not a dictionary container."
            
            # 4. Set the value
            last_key = keys[-1]
            old_value = target.get(last_key, "N/A")
            target[last_key] = value
            
            # 5. Save
            if save_config(current_config):
                return f"Successfully updated '{key}' from '{old_value}' to '{value}'."
            else:
                # Rollback - this tool doesn't keep a persistent live copy, 
                # but if it did, we'd restore here. For now, returning error is enough
                # since the local variable 'current_config' just dies.
                return "Failed to save configuration to disk. Settings remain unchanged."
                
        except Exception as e:
            logger.error(f"Config update failed: {e}")
            return f"Error updating config: {str(e)}"
