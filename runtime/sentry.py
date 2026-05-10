import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.redis import RedisIntegration
import os
import logging

logger = logging.getLogger(__name__)

def setup_sentry():
    """Setup Sentry for BioDockify with PII filtering and performance monitoring."""
    
    # In a real app, this would be an environment variable
    # For now, we allow it to be skipped if not provided
    dsn = os.getenv('SENTRY_DSN')
    
    if dsn:
        try:
            sentry_sdk.init(
                dsn=dsn,
                integrations=[
                    FastApiIntegration(),
                    SqlalchemyIntegration(),
                    RedisIntegration(),
                ],
                
                # Performance monitoring
                traces_sample_rate=0.1,  # Sample 10% for free tier safety
                
                # Environment
                environment=os.getenv('ENVIRONMENT', 'development'),
                
                # Filter sensitive data
                before_send=filter_sensitive_data,
                before_send_transaction=filter_transaction_data,
                
                # Session tracking
                auto_session_tracking=True,
            )
            logger.info("✅ Sentry initialized and protected.")
        except Exception as e:
            logger.error(f"Failed to initialize Sentry: {e}")
    else:
        logger.warning("⚠️ SENTRY_DSN not found. Error tracking disabled.")

def filter_sensitive_data(event, hint):
    """Redact PII and secrets from Sentry events."""
    if 'request' not in event:
        return event
    
    # Redact Authorization and Cookie headers
    request = event.get('request', {})
    headers = request.get('headers', {})
    sensitive_headers = ['authorization', 'x-api-key', 'cookie', 'set-cookie']
    for header in sensitive_headers:
        if header in headers:
            headers[header] = '[REDACTED]'
    
    # Ensure updated headers are in the event
    if 'request' in event and 'headers' in event['request']:
        event['request']['headers'] = headers
            
    # Redact potential secrets in request body
    data = request.get('data')
    if isinstance(data, dict):
        for key in ['password', 'api_key', 'secret', 'token']:
            if key in data:
                data[key] = '[REDACTED]'
        event['request']['data'] = data
                
    # Redact user email
    if 'user' in event and 'email' in event['user']:
        email = event['user']['email']
        event['user']['email'] = f"{email[0]}***@{email.split('@')[-1]}" if '@' in email else '[REDACTED]'
        
    return event

def filter_transaction_data(event, hint):
    """Filter transactions to avoid noise (e.g., health checks)."""
    transaction = event.get('transaction', '')
    if any(k in transaction.lower() for k in ['health', 'metrics', 'static']):
        return None
    return event
