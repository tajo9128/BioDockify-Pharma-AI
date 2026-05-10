"""
LLM Adapters
Encapsulates API interaction logic for various AI providers.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import requests
import json
import litellm
import asyncio
from runtime.robust_connection import with_retry, async_with_retry, get_circuit_breaker
from runtime.cache import cache_llm_call

class BaseLLMAdapter(ABC):
    """Abstract base class for LLM providers."""
    
    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> str:
        """Generate text from prompt synchronously."""
        pass

    async def async_generate(self, prompt: str, **kwargs) -> str:
        """Generate text from prompt asynchronously. Default implementation runs in thread."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: self.generate(prompt, **kwargs))

class GoogleGeminiAdapter(BaseLLMAdapter):
    """Adapter for Google Gemini API (REST)."""
    
    def __init__(self, api_key: str, model: str = "gemini-pro"):
        self.api_key = api_key
        self.model = model
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models"

    @cache_llm_call
    @with_retry(max_retries=3, circuit_name="google_gemini")
    def generate(self, prompt: str, **kwargs) -> str:
        url = f"{self.base_url}/{self.model}:generateContent?key={self.api_key}"
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        
        resp = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]

class OpenRouterAdapter(BaseLLMAdapter):
    """Adapter for OpenRouter API."""
    
    def __init__(self, api_key: str, model: str = "mistralai/mistral-7b-instruct"):
        self.api_key = api_key
        self.model = model
        self.url = "https://openrouter.ai/api/v1/chat/completions"

    @cache_llm_call
    @with_retry(max_retries=3, circuit_name="openrouter")
    def generate(self, prompt: str, **kwargs) -> str:
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}]
        }
        
        resp = requests.post(
            self.url, 
            json=payload, 
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }, 
            timeout=30
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]

class HuggingFaceAdapter(BaseLLMAdapter):
    """Adapter for HuggingFace Inference API."""
    
    def __init__(self, api_key: str, model: str = "mistralai/Mixtral-8x7B-Instruct-v0.1"):
        self.api_key = api_key
        self.model = model
        # Note: HF URL format depends on model
        self.url = f"https://api-inference.huggingface.co/models/{self.model}"

    @cache_llm_call
    @with_retry(max_retries=3, circuit_name="huggingface")
    def generate(self, prompt: str, **kwargs) -> str:
        # HF Inference API parameters
        payload = {
            "inputs": prompt, 
            "parameters": {
                "max_new_tokens": kwargs.get("max_new_tokens", 1024), 
                "return_full_text": False
            }
        }
        
        resp = requests.post(
            self.url, 
            json=payload, 
            headers={"Authorization": f"Bearer {self.api_key}"}, 
            timeout=30
        )
        resp.raise_for_status()
        data = resp.json()
        # HF returns a list of result objects
        if isinstance(data, list) and len(data) > 0:
            return data[0].get("generated_text", "")
        elif isinstance(data, dict) and "generated_text" in data:
             return data["generated_text"]
        else:
            raise ValueError(f"Unexpected HF Response: {data}")

class CustomAdapter(BaseLLMAdapter):
    """Generic OpenAI-Compatible Adapter."""
    
    def __init__(self, api_key: str, base_url: str, model: str):
        self.api_key = api_key
        # Robustly handle URLs ending in /models
        base_url = base_url.rstrip('/')
        if base_url.endswith('/models'):
             base_url = base_url[:-7]
        self.base_url = base_url
        self.model = model
        # Robustly handle Bearer prefix if user accidentally included it
        if api_key and api_key.startswith("Bearer "):
            api_key = api_key.replace("Bearer ", "")
        self.api_key = api_key

    @cache_llm_call
    @with_retry(max_retries=3, circuit_name="custom_llm")
    def generate(self, prompt: str, **kwargs) -> str:
        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": kwargs.get("temperature", 0.7)
        }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        resp = requests.post(url, json=payload, headers=headers, timeout=60)
        
        if resp.status_code == 401:
            raise ValueError("Invalid API Key (401 Unauthorized)")
        elif resp.status_code == 404:
            raise ValueError(f"Endpoint not found (404). Check Base URL: {url}")
        elif resp.status_code == 403:
            raise ValueError("Access Denied (403 Forbidden)")
            
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]

class AnthropicAdapter(BaseLLMAdapter):
    """Adapter for Anthropic API."""
    
    def __init__(self, api_key: str, model: str = "claude-3-opus-20240229"):
        self.api_key = api_key
        self.model = model
        self.url = "https://api.anthropic.com/v1/messages"

    @cache_llm_call
    @with_retry(max_retries=3, circuit_name="anthropic")
    def generate(self, prompt: str, **kwargs) -> str:
        payload = {
            "model": self.model,
            "max_tokens": kwargs.get("max_tokens", 4096),
            "messages": [{"role": "user", "content": prompt}]
        }
        
        resp = requests.post(
            self.url, 
            json=payload, 
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json"
            }, 
            timeout=60
        )
        resp.raise_for_status()
        data = resp.json()
        return data["content"][0]["text"]

class LMStudioAdapter(BaseLLMAdapter):
    """
    Dedicated Adapter for LM Studio Local Inference using LiteLLM.
    Enforces OpenAI compatibility and attempts to mandate JSON structure.
    Includes Automatic Model Detection.
    """
    
    PREFERRED_MODELS = [
        "openbiollm",
        "biomed",
        "mistral",
        "llama",
        "lfm",
        "phi",
        "gemma"
    ]

    def __init__(self, base_url: str = "http://localhost:1234/v1", model: str = "auto"):
        # Robustly handle URLs ending in /models by stripping it
        base_url = base_url.rstrip('/')
        if base_url.endswith('/models'):
             base_url = base_url[:-7] # Remove /models
             
        self.base_url = base_url.rstrip('/')
        self.config_model = model
        self.api_base = self.base_url
        self._detected_model = None
        
        # Try to detect immediately if possible, but don't crash if server down on init
        # (Lazy detection in generate is safer for startup)
        pass

    def _auto_select_model(self) -> str:
        """
        Automatically selects the best available model from LM Studio.
        """
        if self._detected_model:
            return self._detected_model
            
        try:
            url = f"{self.base_url}/models"
            # Fast timeout for detection
            r = requests.get(url, timeout=2)
            r.raise_for_status()
            
            data = r.json().get("data", [])
            available_ids = [m["id"] for m in data]
            
            if not available_ids:
                raise ValueError("LM Studio is running but No models are loaded.")
                
            # Selection Logic
            selected = None
            
            # 1. Try to find preferred models
            for pref in LMStudioAdapter.PREFERRED_MODELS:
                for m_id in available_ids:
                    if pref.lower() in m_id.lower():
                        selected = m_id
                        break
                if selected: break
            
            # 2. Fallback to first available
            if not selected:
                selected = available_ids[0]
                
            self._detected_model = selected
            print(f"[OK] LM Studio Model Auto-Selected: {selected}")
            return selected
            
        except requests.exceptions.RequestException:
             # If we can't connect, we can't auto-detect. 
             # Return configured defaults or raise error depending on context.
             # For now, return config model to let caller fail normally if down.
             return self.config_model if self.config_model != "auto" else "local-model"
             
        except Exception as e:
            print(f"[WARN] Model Auto-Detection Warning: {e}")
            return self.config_model if self.config_model != "auto" else "local-model"

    @cache_llm_call
    def generate(self, prompt: str, **kwargs) -> str:
        try:
            # Determine effective model
            if self.config_model == "auto" or self.config_model == "local-model":
                effective_model = self._auto_select_model()
            else:
                effective_model = self.config_model
            
            messages = [{"role": "user", "content": prompt}]
            
            # Check if we should enforce JSON mode
            response_format = None
            if "json" in prompt.lower():
                response_format = {"type": "json_object"}

            # LiteLLM call
            response = litellm.completion(
                model=f"openai/{effective_model}", 
                api_base=self.api_base,
                api_key="lm-studio", 
                messages=messages,
                temperature=kwargs.get("temperature", 0.7),
                max_tokens=kwargs.get("max_tokens", 2048),
                response_format=response_format,
                timeout=300 # 5 minutes for slow local hardware
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            msg = str(e)
            if "Connection" in msg or "refused" in msg:
                 raise ValueError(
                    f"LM Studio Connection Failed: Could not connect to {self.base_url}. "
                    "Please ensure LM Studio is running and the 'Local Server' is started."
                )
            if "formatted" in msg or "404" in msg:
                 # Likely model not found issue if auto-detect failed or wasn't used
                 raise ValueError(
                    f"LM Studio Error: Model '{self.config_model}' not found or server error. "
                    f"Ensure a model is loaded in LM Studio. Details: {e}"
                 )
            raise ValueError(f"LM Studio/LiteLLM Error: {e}")

class ZhipuAdapter(BaseLLMAdapter):
    """Adapter for Zhipu AI (GLM-4)."""
    
    def __init__(self, api_key: str, model: str = "glm-5"):
        self.api_key = api_key
        self.model = model
        self.url = "https://open.bigmodel.cn/api/paas/v4/chat/completions"

    @cache_llm_call
    @with_retry(max_retries=3, circuit_name="zhipu")
    def generate(self, prompt: str, **kwargs) -> str:
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7
        }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        resp = requests.post(self.url, json=payload, headers=headers, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]


class OllamaAdapter(BaseLLMAdapter):
    """
    Robust adapter for local Ollama LLM with retry logic and graceful fallbacks.
    """
    
    MAX_RETRIES = 3
    RETRY_DELAY = 2.0
    
    def __init__(self, base_url: str = "http://localhost:11434", model: str = ""):
        self.base_url = base_url.rstrip('/')
        self.model = model
        self._failure_count = 0
        self._last_success = 0
        self._is_available_cache = None
        self._cache_time = 0
        self._available_models_cache = None
        self._models_cache_time = 0

    def model_exists(self, model_name: str = None) -> bool:
        """Check if a model exists in Ollama."""
        model_to_check = model_name or self.model
        available = self.list_models()
        
        # Check exact match or base model name match
        for m in available:
            if m == model_to_check or m.startswith(model_to_check.split(':')[0]):
                return True
        return False

    def _verify_model_or_fallback(self) -> str:
        """Verify model exists, try to find alternative, or return error message."""
        available = self.list_models()
        
        # Auto-select first model if none specified
        if not self.model and available:
            self.model = available[0]
            print(f"[Auto-select] Using model: {self.model}")
            return ""
        
        if self.model_exists():
            return ""  # Model exists, no error
        
        if not available:
            return (
                f"[Model Not Found] No models available in Ollama. "
                f"Please install a model:\n"
                f"  ollama pull llama3.2\n"
                f"  ollama pull mistral\n"
                f"  ollama pull gemma2"
            )
        
        return (
            f"[Model Not Found] Model '{self.model}' is not installed in Ollama.\n"
            f"Available models: {', '.join(available[:5])}\n"
            f"To install the model run: ollama pull {self.model}"
        )

    @cache_llm_call
    @with_retry(max_retries=3, circuit_name="ollama")
    def generate(self, prompt: str, **kwargs) -> str:
        """Generate text with automatic retries and model verification."""
        # Pre-check: Verify model exists
        model_error = self._verify_model_or_fallback()
        if model_error:
            return model_error
        
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": kwargs.get("temperature", 0.7),
                "num_predict": kwargs.get("max_tokens", 1024)
            }
        }
        
        resp = requests.post(url, json=payload, timeout=120)
        
        # Handle specific HTTP errors
        if resp.status_code == 404:
            return self._model_not_found_error()
        
        resp.raise_for_status()
        data = resp.json()
        
        # Check for Ollama-specific error in response
        if "error" in data:
            error_msg = data.get("error", "")
            if "not found" in error_msg.lower() or "doesn't exist" in error_msg.lower():
                return self._model_not_found_error()
            return f"[Ollama Error] {error_msg}"
        
        import time as t
        self._last_success = t.time()
        return data.get("response", "")
    
    def _model_not_found_error(self) -> str:
        """Return a helpful error message when model is not found."""
        available = self.list_models()
        if available:
            return (
                f"[Model Not Found] Model '{self.model}' is not installed.\n"
                f"Available models: {', '.join(available[:5])}\n"
                f"Install with: ollama pull {self.model}"
            )
        return (
            f"[Model Not Found] Model '{self.model}' is not installed.\n"
            f"Install with: ollama pull {self.model}\n"
            f"Or try: ollama pull llama3"
        )
    
    def chat(self, messages: list, **kwargs) -> str:
        """Chat completion with automatic retries."""
        url = f"{self.base_url}/api/chat"
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": kwargs.get("temperature", 0.7),
                "num_predict": kwargs.get("max_tokens", 1024)
            }
        }
        
        for attempt in range(self.MAX_RETRIES):
            try:
                resp = requests.post(url, json=payload, timeout=120)
                resp.raise_for_status()
                data = resp.json()
                self._failure_count = 0
                return data.get("message", {}).get("content", "")
                
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
                if attempt < self.MAX_RETRIES - 1:
                    import time as t
                    t.sleep(self.RETRY_DELAY * (attempt + 1))
                    continue
                    
            except Exception as e:
                return self._graceful_fallback(str(e))
        
        return self._graceful_fallback("Connection failed after retries")
    
    def is_available(self) -> bool:
        """Check if Ollama server is running with caching."""
        import time as t
        now = t.time()
        
        # Cache availability check for 30 seconds
        if self._is_available_cache is not None and now - self._cache_time < 30:
            return self._is_available_cache
        
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=10)
            self._is_available_cache = resp.status_code == 200
        except:
            self._is_available_cache = False
        
        self._cache_time = now
        return self._is_available_cache
    
    def list_models(self) -> list:
        """List available models in Ollama."""
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=10)
            resp.raise_for_status()
            data = resp.json()
            return [m.get("name", "") for m in data.get("models", [])]
        except:
            return []
    
    def _graceful_fallback(self, error: str) -> str:
        """Return a helpful message instead of crashing."""
        if "Connection" in error or "refused" in error.lower():
            return (
                "[Ollama Unavailable] Cannot connect to Ollama service. "
                "Please ensure Ollama is running with 'ollama serve' or "
                "configure a cloud API (Google/OpenRouter) in Settings."
            )
        elif "timeout" in error.lower():
            return (
                "[Ollama Timeout] Request timed out. Ollama may be overloaded "
                "or the model is too large. Try a smaller model or use a cloud API."
            )
        else:
            return f"[Ollama Error] {error}. Please check Ollama logs or use a cloud API."

class AzureAdapter(BaseLLMAdapter):
    """Adapter for Azure OpenAI Service using LiteLLM."""
    
    def __init__(self, api_key: str, endpoint: str, deployment_name: str, api_version: str):
        self.api_key = api_key
        self.endpoint = endpoint
        self.deployment_name = deployment_name
        self.api_version = api_version
        
    @cache_llm_call
    @with_retry(max_retries=3, circuit_name="azure_openai")
    def generate(self, prompt: str, **kwargs) -> str:
        messages = [{"role": "user", "content": prompt}]
        
        # Azure requires: 
        # model="azure/<deployment_name>"
        # api_base=endpoint
        # api_key=key
        # api_version=ver
        
        response = litellm.completion(
            model=f"azure/{self.deployment_name}",
            api_key=self.api_key,
            api_base=self.endpoint,
            api_version=self.api_version,
            messages=messages,
            temperature=kwargs.get("temperature", 0.7),
            max_tokens=kwargs.get("max_tokens", 4096),
            timeout=60
        )
        return response.choices[0].message.content

class AWSAdapter(BaseLLMAdapter):
    """Adapter for AWS Bedrock using LiteLLM."""
    
    def __init__(self, access_key: str, secret_key: str, region_name: str, model_id: str):
        self.access_key = access_key
        self.secret_key = secret_key
        self.region_name = region_name
        self.model_id = model_id
        
        # Set environment variables for boto3/litellm implicitly or pass explicitly if litellm supports
        # LiteLLM supports passing aws_access_key_id etc. in some versions, or env vars.
        # Safest is to set env vars temporarily or use os.environ if safe.
        # But for thread safety, let's see if litellm accepts them in completion.
        # LiteLLM docs say: set os.environ['AWS_ACCESS_KEY_ID'] etc.
        # To avoid global side effects, we can try passing them or context manager.
        # For now, we'll set them in os.environ if not present, but this is a bit risky for concurrency if multiple keys.
        # Better: LiteLLM allows passing `aws_access_key_id` in `completion` in newer versions.
        # If not, we fall back to os.environ.
    
    @cache_llm_call
    @with_retry(max_retries=3, circuit_name="aws_bedrock")
    def generate(self, prompt: str, **kwargs) -> str:
        messages = [{"role": "user", "content": prompt}]
        
        response = litellm.completion(
            model=f"bedrock/{self.model_id}",
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            aws_region_name=self.region_name,
            messages=messages,
            temperature=kwargs.get("temperature", 0.7),
            max_tokens=kwargs.get("max_tokens", 4096),
            timeout=60
        )
        return response.choices[0].message.content


class MiniMaxAdapter(BaseLLMAdapter):
    """MiniMax API Adapter for Chinese LLM services."""

    def __init__(self, api_key: str, group_id: str = "", model: str = "abab6.5s-chat", **kwargs):
        self.api_key = api_key
        self.group_id = group_id
        self.model = model
        self.base_url = kwargs.get('api_base', 'https://api.minimax.chat/v1')

    def chat(self, messages: list, **kwargs) -> str:
        """Generate chat response using MiniMax API."""
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }

        payload = {
            'model': self.model,
            'messages': messages,
            'temperature': kwargs.get('temperature', 0.7),
            'max_tokens': kwargs.get('max_tokens', 2000)
        }

        if self.group_id:
            headers['GroupId'] = self.group_id

        import requests
        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )

        response.raise_for_status()
        return response.json()['choices'][0]['message']['content']

    def embed(self, text: str) -> list:
        """Generate embeddings using MiniMax API."""
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }

        if self.group_id:
            headers['GroupId'] = self.group_id

        import requests
        response = requests.post(
            f"{self.base_url}/embeddings",
            headers=headers,
            json={'model': self.model, 'input': text},
            timeout=30
        )

        response.raise_for_status()
        return response.json()['data'][0]['embedding']
