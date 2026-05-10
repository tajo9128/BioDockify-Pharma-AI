"""
BioDockify Runtime Monitoring & Observability.
Starts Prometheus metrics server and configures structured logging for Loki.
"""

import logging
import os
import time
from logging.handlers import RotatingFileHandler
from prometheus_client import Counter, Histogram, Gauge, start_http_server
from typing import Dict, Any

def _define_metrics():
    """Defines and returns Prometheus metrics, avoiding duplicate registration errors."""
    try:
        return {
            'http_requests_total': Counter(
                'biodockify_http_requests_total',
                'Total HTTP requests processed',
                ['method', 'endpoint', 'status']
            ),
            
            'http_request_duration_seconds': Histogram(
                'biodockify_http_request_duration_seconds',
                'HTTP request duration',
                ['method', 'endpoint']
            ),
            
            'active_users': Gauge(
                'biodockify_active_users',
                'Number of active users/sessions'
            ),
            
            'research_tasks_total': Counter(
                'biodockify_research_tasks_total',
                'Total research tasks executed',
                ['mode', 'status']
            )
        }
    except ValueError:
        # Metrics already registered, this should not happen with a global METRICS but good for robustness
        from prometheus_client import REGISTRY
        return {
            'http_requests_total': REGISTRY._names_to_collectors.get('biodockify_http_requests_total'),
            'http_request_duration_seconds': REGISTRY._names_to_collectors.get('biodockify_http_request_duration_seconds'),
            'active_users': REGISTRY._names_to_collectors.get('biodockify_active_users'),
            'research_tasks_total': REGISTRY._names_to_collectors.get('biodockify_research_tasks_total')
        }

# Global metrics definitions
METRICS = _define_metrics()

def setup_structured_logging(log_file: str = "logs/app.log"):
    """
    Setup logging that outputs JSON for easy ingestion by Loki.
    """
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    
    logger = logging.getLogger("BioDockify")
    logger.setLevel(logging.INFO)
    
    # Avoid duplicate handlers if re-called
    if logger.handlers:
        return logger
        
    # Console Handler
    console = logging.StreamHandler()
    
    # File Handler
    file_handler = RotatingFileHandler(
        log_file, 
        maxBytes=10*1024*1024, # 10MB
        backupCount=5
    )
    
    # JSON-like formatter (simple string but structured)
    # For a real implementation, we might use python-json-logger
    class JSONFormatter(logging.Formatter):
        def format(self, record):
            import json
            log_data = {
                "timestamp": self.formatTime(record, self.datefmt),
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
                "module": record.module,
                "line": record.lineno
            }
            # Add extra fields if they exist
            if hasattr(record, "extra"):
                log_data.update(record.extra)
            return json.dumps(log_data)

    formatter = JSONFormatter()
    console.setFormatter(formatter)
    file_handler.setFormatter(formatter)
    
    logger.addHandler(console)
    logger.addHandler(file_handler)
    
    return logger

def start_monitoring_server(port: int = 8000):
    """
    Start the Prometheus metrics server.
    """
    try:
        logger = logging.getLogger("BioDockify.Monitoring")
        logger.info(f"Starting Prometheus metrics server on port {port}")
        start_http_server(port)
    except Exception as e:
        logger.error(f"Failed to start Prometheus server: {e}")

# Initialize logging on import
logger = setup_structured_logging()
