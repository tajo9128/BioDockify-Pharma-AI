"""AWS Bedrock bridge — invoke Claude models via Bedrock.

Config: ~/.claude/bedrock_config.json (not in repo for security)
Credentials: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY env vars or IAM role
"""
import json
import os
import logging

log = logging.getLogger("bedrock_bridge")

BEDROCK_AVAILABLE = False
BEDROCK_CONFIG = {}

try:
    import boto3
    from botocore.exceptions import BotoCoreError, ClientError
    BEDROCK_AVAILABLE = True
    log.info("boto3 imported successfully")

    # Load config from ~/.claude/bedrock_config.json
    config_path = os.path.expanduser("~/.claude/bedrock_config.json")
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            BEDROCK_CONFIG = json.load(f)
        log.info(f"Bedrock config loaded from {config_path}")
    else:
        log.debug(f"Bedrock config not found at {config_path} — Bedrock features disabled")
except ImportError:
    log.warning("boto3 not installed — Bedrock features unavailable. Install: pip install boto3")


def is_bedrock_available() -> bool:
    """Check if Bedrock is available and configured."""
    return BEDROCK_AVAILABLE and bool(BEDROCK_CONFIG)


def get_bedrock_status() -> dict:
    """Get Bedrock availability and config status."""
    return {
        "available": BEDROCK_AVAILABLE,
        "configured": bool(BEDROCK_CONFIG),
        "region": BEDROCK_CONFIG.get("region", "N/A"),
        "role_arn": BEDROCK_CONFIG.get("role_arn", "N/A")[:40] + "...",  # Truncate for safety
    }


def invoke_bedrock_model(
    prompt: str,
    model_key: str = "claude_sonnet_5",
    system_prompt: str = None,
    max_tokens: int = None,
    temperature: float = None,
) -> dict:
    """Invoke a Claude model via Bedrock.

    Args:
        prompt: User prompt/message
        model_key: Key from bedrock_config.json models dict (e.g., 'claude_sonnet_5')
        system_prompt: Optional system prompt
        max_tokens: Override config max_tokens
        temperature: Override config temperature

    Returns:
        dict with success status, response text, or error
    """
    if not is_bedrock_available():
        return {
            "success": False,
            "error": "Bedrock not available. Install boto3 and configure ~/.claude/bedrock_config.json",
        }

    try:
        # Get model ID
        models = BEDROCK_CONFIG.get("models", {})
        model_id = models.get(model_key)
        if not model_id:
            return {
                "success": False,
                "error": f"Model '{model_key}' not found in config. Available: {list(models.keys())}",
            }

        # Get client
        region = BEDROCK_CONFIG.get("region", "us-east-1")
        client = boto3.client("bedrock-runtime", region_name=region)

        # Build messages
        messages = [{"role": "user", "content": prompt}]

        # Build request body (Bedrock Messages API format)
        body = {
            "anthropic_version": "bedrock-2023-10-16",
            "messages": messages,
            "max_tokens": max_tokens or BEDROCK_CONFIG.get("max_tokens", 4096),
            "temperature": temperature if temperature is not None else BEDROCK_CONFIG.get("temperature", 0.7),
        }

        if system_prompt:
            body["system"] = system_prompt

        # Invoke model
        response = client.invoke_model(
            modelId=model_id,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(body),
        )

        # Parse response
        result_body = json.loads(response["body"].read())

        # Extract text from response
        text = ""
        if "content" in result_body:
            content = result_body["content"]
            if isinstance(content, list) and len(content) > 0:
                text = content[0].get("text", "")

        return {
            "success": True,
            "response": text,
            "model": model_id,
            "usage": result_body.get("usage", {}),
        }

    except (BotoCoreError, ClientError) as e:
        log.error(f"Bedrock API error: {e}")
        return {
            "success": False,
            "error": f"Bedrock API error: {str(e)}",
        }
    except Exception as e:
        log.error(f"Bedrock invocation failed: {e}")
        return {
            "success": False,
            "error": f"Bedrock invocation failed: {str(e)}",
        }


def batch_invoke_bedrock(
    prompts: list,
    model_key: str = "claude_sonnet_5",
    system_prompt: str = None,
) -> list:
    """Invoke multiple prompts sequentially.

    Args:
        prompts: List of prompt strings
        model_key: Model to use
        system_prompt: Optional system prompt

    Returns:
        List of dicts with success/response/error
    """
    results = []
    for prompt in prompts:
        result = invoke_bedrock_model(
            prompt=prompt,
            model_key=model_key,
            system_prompt=system_prompt,
        )
        results.append(result)
    return results
