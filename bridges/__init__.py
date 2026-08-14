"""Bridges — external service integrations (AWS Bedrock, PharmacoNet, etc.)"""
from .bedrock_bridge import (
    is_bedrock_available,
    get_bedrock_status,
    invoke_bedrock_model,
    batch_invoke_bedrock,
)
