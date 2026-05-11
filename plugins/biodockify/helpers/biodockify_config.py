import os
from pathlib import Path

PLUGIN_NAME = "biodockify"

def get_research_config():
    from helpers import settings
    config = settings.get_plugin_config(PLUGIN_NAME)
    return config or {}

def get_default_model():
    config = get_research_config()
    return config.get("research.default_model", "anthropic/claude-sonnet-4-20250514")

def get_literature_databases():
    config = get_research_config()
    return config.get("research.literature_databases", ["pubmed", "semantic_scholar"])

def is_subagent_enabled(agent_name: str) -> bool:
    config = get_research_config()
    key = f"subagents.{agent_name}_enabled"
    return config.get(key, True)

def get_statistics_method():
    config = get_research_config()
    return config.get("research.statistics_default", "ttest")