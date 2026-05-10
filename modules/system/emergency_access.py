import hmac
import hashlib
import json
import base64
import time
import logging

logger = logging.getLogger("biodockify_api")

import os

# SECURITY WARNING: Ideally this should be an environment variable.
# For this hotfix/robust offline mode, we are embedding a default fallback key.
# Change this string to rotate keys (will invalidate old codes).
EMERGENCY_SECRET_KEY = os.environ.get(
    "BIODOCKIFY_EMERGENCY_SECRET"
)

def validate_emergency_token(email: str, token: str) -> bool:
    """
    Validates an emergency offline access token.
    Token Format: BASE64_PAYLOAD.SIGNATURE_HEX
    Payload: JSON {"email": "...", "exp": timestamp}
    """
    try:
        if not token or "." not in token:
            return False

        b64_payload, signature = token.rsplit(".", 1)
        
        # 1. Verify Signature
        expected_signature = hmac.new(
            EMERGENCY_SECRET_KEY.encode(), 
            b64_payload.encode(), 
            hashlib.sha256
        ).hexdigest()
        
        if not hmac.compare_digest(signature, expected_signature):
            logger.warning(f"Invalid emergency token signature for {email}")
            return False

        # 2. Decode Payload
        decoded_bytes = base64.urlsafe_b64decode(b64_payload + "==") # Padding safety
        payload = json.loads(decoded_bytes)

        # 3. Validate Context (Email & Expiry)
        if payload.get("email") != email:
            logger.warning(f"Token email mismatch: {payload.get('email')} vs {email}")
            return False
            
        if payload.get("exp", 0) < time.time():
            logger.warning(f"Emergency token expired for {email}")
            return False

        logger.info(f"Emergency Access Granted for {email}")
        return True

    except Exception as e:
        logger.error(f"Error validating emergency token: {e}")
        return False

def generate_emergency_token(email: str, hours_valid: int = 24) -> str:
    """
    Helper to generate tokens (Used by admin tools)
    """
    payload = {
        "email": email,
        "exp": int(time.time()) + (hours_valid * 3600)
    }
    json_str = json.dumps(payload)
    b64_payload = base64.urlsafe_b64encode(json_str.encode()).decode().rstrip("=")
    
    signature = hmac.new(
        EMERGENCY_SECRET_KEY.encode(), 
        b64_payload.encode(), 
        hashlib.sha256
    ).hexdigest()
    
    return f"{b64_payload}.{signature}"
