"""
Robust Connection Module
Provides resilient API connections with retries, circuit breaker, and graceful fallbacks.
"""

import time
import logging
import functools
from typing import Callable, Any, Optional, Dict
from enum import Enum
import requests

logger = logging.getLogger("robust_connection")


class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery


class CircuitBreaker:
    """
    Circuit breaker pattern to prevent cascading failures.
    
    States:
    - CLOSED: Normal operation, requests go through
    - OPEN: Too many failures, requests are rejected
    - HALF_OPEN: Testing if service recovered
    """
    
    def __init__(
        self, 
        failure_threshold: int = 5, 
        recovery_timeout: int = 30,
        name: str = "service"
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.name = name
        self.state = CircuitState.CLOSED
        self.failures = 0
        self.last_failure_time = 0
        self.success_count = 0
    
    def can_execute(self) -> bool:
        """Check if request can be executed."""
        if self.state == CircuitState.CLOSED:
            return True
        
        if self.state == CircuitState.OPEN:
            # Check if recovery timeout has passed
            if time.time() - self.last_failure_time >= self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                logger.info(f"[{self.name}] Circuit entering HALF_OPEN state")
                return True
            return False
        
        # HALF_OPEN - allow one request through
        return True
    
    def record_success(self):
        """Record a successful request."""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= 3:  # Need 3 successes to close
                self.state = CircuitState.CLOSED
                self.failures = 0
                self.success_count = 0
                logger.info(f"[{self.name}] Circuit CLOSED - service recovered")
        else:
            self.failures = max(0, self.failures - 1)
    
    def record_failure(self):
        """Record a failed request."""
        self.failures += 1
        self.last_failure_time = time.time()
        self.success_count = 0
        
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
            logger.warning(f"[{self.name}] Circuit OPEN - service still failing")
        elif self.failures >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning(f"[{self.name}] Circuit OPEN - {self.failures} consecutive failures")


# Global circuit breakers for different services
_circuit_breakers: Dict[str, CircuitBreaker] = {}


def get_circuit_breaker(name: str) -> CircuitBreaker:
    """Get or create a circuit breaker for a service."""
    if name not in _circuit_breakers:
        _circuit_breakers[name] = CircuitBreaker(name=name)
    return _circuit_breakers[name]


def with_retry(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    exponential: bool = True,
    circuit_name: Optional[str] = None
):
    """
    Decorator for functions that need retry logic.
    
    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay between retries (seconds)
        max_delay: Maximum delay between retries (seconds)
        exponential: Use exponential backoff
        circuit_name: Name of circuit breaker to use
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            circuit = get_circuit_breaker(circuit_name or func.__name__) if circuit_name else None
            
            # Check circuit breaker
            if circuit and not circuit.can_execute():
                logger.warning(f"[{circuit_name}] Circuit OPEN - returning fallback")
                raise ConnectionError(f"Service '{circuit_name}' is temporarily unavailable")
            
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    result = func(*args, **kwargs)
                    if circuit:
                        circuit.record_success()
                    return result
                    
                except (requests.exceptions.ConnectionError, 
                        requests.exceptions.Timeout,
                        ConnectionError) as e:
                    last_exception = e
                    
                    if circuit:
                        circuit.record_failure()
                    
                    if attempt < max_retries:
                        delay = base_delay * (2 ** attempt) if exponential else base_delay
                        delay = min(delay, max_delay)
                        logger.warning(
                            f"[{func.__name__}] Attempt {attempt + 1}/{max_retries + 1} failed: {e}. "
                            f"Retrying in {delay:.1f}s..."
                        )
                        time.sleep(delay)
                    else:
                        logger.error(f"[{func.__name__}] All {max_retries + 1} attempts failed")
                        
                except Exception as e:
                    # Non-retriable errors
                    if circuit:
                        circuit.record_failure()
                    raise
            
            raise last_exception
        
        return wrapper
    return decorator


def async_with_retry(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    exponential: bool = True,
    circuit_name: Optional[str] = None
):
    """
    Async decorator for functions that need retry logic.
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            import asyncio
            import aiohttp
            
            circuit = get_circuit_breaker(circuit_name or func.__name__) if circuit_name else None
            
            # Check circuit breaker
            if circuit and not circuit.can_execute():
                logger.warning(f"[{circuit_name}] Circuit OPEN - service temporarily unavailable")
                raise ConnectionError(f"Service '{circuit_name}' is temporarily unavailable")
            
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    result = await func(*args, **kwargs)
                    if circuit:
                        circuit.record_success()
                    return result
                    
                except (aiohttp.ClientError, asyncio.TimeoutError, ConnectionError) as e:
                    last_exception = e
                    
                    if circuit:
                        circuit.record_failure()
                    
                    if attempt < max_retries:
                        delay = base_delay * (2 ** attempt) if exponential else base_delay
                        delay = min(delay, max_delay)
                        logger.warning(
                            f"[{func.__name__}] Async Attempt {attempt + 1}/{max_retries + 1} failed: {e}. "
                            f"Retrying in {delay:.1f}s..."
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(f"[{func.__name__}] All {max_retries + 1} async attempts failed")
                
                except Exception as e:
                    if circuit:
                        circuit.record_failure()
                    raise
            
            raise last_exception
        
        return wrapper
    return decorator


def graceful_request(
    url: str,
    method: str = "GET",
    timeout: int = 30,
    fallback: Any = None,
    circuit_name: str = "http",
    **kwargs
) -> Optional[requests.Response]:
    """
    Make an HTTP request with graceful error handling.
    
    Returns fallback value on failure instead of raising exception.
    """
    circuit = get_circuit_breaker(circuit_name)
    
    if not circuit.can_execute():
        logger.warning(f"[{circuit_name}] Circuit OPEN - returning fallback")
        return fallback
    
    try:
        response = requests.request(method, url, timeout=timeout, **kwargs)
        circuit.record_success()
        return response
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
        circuit.record_failure()
        logger.warning(f"Request to {url} failed: {e}")
        return fallback
    except Exception as e:
        circuit.record_failure()
        logger.error(f"Unexpected error requesting {url}: {e}")
        return fallback


class RobustServiceClient:
    """
    Base class for robust service clients with built-in resilience.
    """
    
    def __init__(self, base_url: str, service_name: str, timeout: int = 30):
        self.base_url = base_url.rstrip('/')
        self.service_name = service_name
        self.timeout = timeout
        self.circuit = get_circuit_breaker(service_name)
        self._is_available = None
        self._last_check = 0
        self._check_interval = 30  # Check availability every 30 seconds
    
    def is_available(self, force_check: bool = False) -> bool:
        """Check if service is available with caching."""
        now = time.time()
        
        if not force_check and self._is_available is not None:
            if now - self._last_check < self._check_interval:
                return self._is_available
        
        try:
            resp = requests.get(f"{self.base_url}/", timeout=5)
            self._is_available = resp.status_code < 500
        except:
            self._is_available = False
        
        self._last_check = now
        return self._is_available
    
    @with_retry(max_retries=2, circuit_name="service")
    def get(self, endpoint: str, **kwargs) -> requests.Response:
        """Make a GET request with retry."""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        return requests.get(url, timeout=self.timeout, **kwargs)
    
    @with_retry(max_retries=2, circuit_name="service")
    def post(self, endpoint: str, **kwargs) -> requests.Response:
        """Make a POST request with retry."""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        return requests.post(url, timeout=self.timeout, **kwargs)


class RobustOllamaClient(RobustServiceClient):
    """
    Robust Ollama client with automatic fallback behavior.
    """
    
    def __init__(self, base_url: str = "http://localhost:11434"):
        super().__init__(base_url, "ollama", timeout=120)
        self.model = ""
    
    def is_available(self, force_check: bool = False) -> bool:
        """Check if Ollama is running."""
        now = time.time()
        
        if not force_check and self._is_available is not None:
            if now - self._last_check < self._check_interval:
                return self._is_available
        
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=5)
            self._is_available = resp.status_code == 200
        except:
            self._is_available = False
        
        self._last_check = now
        return self._is_available
    
    def generate(self, prompt: str, model: str = None, **kwargs) -> str:
        """Generate text with Ollama, with graceful fallback."""
        if not self.circuit.can_execute():
            return self._fallback_response("Service temporarily unavailable")
        
        try:
            resp = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": model or self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": kwargs.get("temperature", 0.7),
                        "num_predict": kwargs.get("max_tokens", 1024)
                    }
                },
                timeout=self.timeout
            )
            resp.raise_for_status()
            self.circuit.record_success()
            return resp.json().get("response", "")
            
        except requests.exceptions.ConnectionError:
            self.circuit.record_failure()
            return self._fallback_response("Ollama not reachable - is it running?")
        except requests.exceptions.Timeout:
            self.circuit.record_failure()
            return self._fallback_response("Ollama request timed out")
        except Exception as e:
            self.circuit.record_failure()
            return self._fallback_response(f"Ollama error: {str(e)}")
    
    def _fallback_response(self, error_msg: str) -> str:
        """Return a graceful fallback response instead of crashing."""
        logger.warning(f"[Ollama] Fallback triggered: {error_msg}")
        return f"[AI Unavailable] {error_msg}. Please check Ollama status or configure a cloud API."


# Singleton instances
_ollama_client: Optional[RobustOllamaClient] = None


def get_ollama_client(base_url: str = "http://localhost:11434") -> RobustOllamaClient:
    """Get the robust Ollama client singleton."""
    global _ollama_client
    if _ollama_client is None or _ollama_client.base_url != base_url:
        _ollama_client = RobustOllamaClient(base_url)
    return _ollama_client
