
"""API Rotation Provider - Cycles through multiple LLM providers with failover"""

import asyncio
from typing import Optional, Dict, Any
from loguru import logger

from nanobot.providers.litellm_provider import LiteLLMProvider, LLMResponse


class RotationProvider:
    """
    Multi-provider LLM rotation with automatic failover.

    Cycles through providers in order, automatically switching on failure.
    Tracks provider health and usage statistics.
    """

    def __init__(
        self,
        providers: Optional[Dict[str, Dict[str, Any]]] = None,
        default_providers: Optional[Dict[str, Dict[str, Any]]] = None,
    ):
        self.providers = providers or {}
        self.default_providers = default_providers or self._get_default_providers()
        self.current_provider_index = 0
        self.provider_instances: Dict[str, LiteLLMProvider] = {}
        self.provider_health: Dict[str, bool] = {}
        self.provider_failures: Dict[str, int] = {}
        self._initialize_providers()

    def _get_default_providers(self) -> Dict[str, Dict[str, Any]]:
        """Default provider configurations."""
        return {
            "deepseek_reasoner": {
                "api_key": os.getenv("DEEPSEEK_API_KEY", ""),
                "model": "deepseek-reasoner",
                "api_base": "https://api.deepseek.com",
                "priority": 1
            },
            "glm5_modal": {
                "api_key": "modalresearch_zPhZ66S5WbQ8pj6rqL2ukTq92rOt5JbUGBM1PU1euRo",  # Modal API key for GLM-5-FP8
                "model": "zai-org/GLM-5-FP8",
                "api_base": "https://api.us-west-2.modal.direct/v1",
                "priority": 2
            },
            "glm47_zhipu": {
                "api_key": "dd45abe0a64648fa8f4f9b7b2144e5c2.JHGdsrQhEBZbAdTx",
                "model": "GLM-4.7",
                "priority": 3
            }
        }

    def _initialize_providers(self):
        """Initialize LiteLLMProvider instances for each configured provider."""
        if not self.providers:
            self.providers = self.default_providers

        # Sort by priority
        sorted_providers = sorted(
            self.providers.items(), 
            key=lambda x: x[1].get('priority', 99)
        )
        self.provider_order = [name for name, _ in sorted_providers]

        for name, config in self.providers.items():
            try:
                provider = LiteLLMProvider(
                    api_key=config.get("api_key"),
                    api_base=config.get("api_base"),
                    default_model=config.get("model")
                )
                self.provider_instances[name] = provider
                self.provider_health[name] = True
                self.provider_failures[name] = 0
                logger.info(f"Initialized rotation provider: {name} with model {config.get('model')}")
            except Exception as e:
                logger.error(f"Failed to initialize provider {name}: {e}")
                self.provider_health[name] = False

        # Set initial provider
        if self.provider_order:
            self._set_current_provider(self.provider_order[0])

    def _set_current_provider(self, provider_name: str):
        """Set the current active provider."""
        if provider_name in self.provider_instances:
            self.current_provider = provider_name
            logger.info(f"Switched to provider: {provider_name}")

    def _get_next_provider(self) -> Optional[str]:
        """Get the next healthy provider in rotation."""
        for i, name in enumerate(self.provider_order):
            if name == self.current_provider:
                # Check remaining providers
                for next_name in self.provider_order[i+1:]:
                    if self.provider_health.get(next_name, True):
                        return next_name
                # Check from beginning
                for next_name in self.provider_order[:i]:
                    if self.provider_health.get(next_name, True):
                        return next_name
        return None

    async def chat(
        self,
        messages: list,
        tools: Optional[list] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Chat with automatic provider rotation on failure.

        Attempts up to 3 times total across all providers.
        """
        max_attempts = 3
        attempt = 0
        last_error = None

        while attempt < max_attempts:
            provider_name = self.current_provider
            provider = self.provider_instances.get(provider_name)

            if not provider:
                logger.warning(f"Provider {provider_name} not available, switching")
                next_provider = self._get_next_provider()
                if next_provider:
                    self._set_current_provider(next_provider)
                    continue
                else:
                    break

            try:
                logger.info(f"Using provider: {provider_name} (attempt {attempt + 1}/{max_attempts})")
                response = await provider.chat(messages=messages, tools=tools, **kwargs)

                # Reset failure count on success
                self.provider_failures[provider_name] = 0
                self.provider_health[provider_name] = True

                # Add provider info to response
                response.provider = provider_name
                return response

            except Exception as e:
                last_error = e
                attempt += 1
                self.provider_failures[provider_name] = self.provider_failures.get(provider_name, 0) + 1

                logger.warning(f"Provider {provider_name} failed: {e}")

                # Mark as unhealthy if multiple failures
                if self.provider_failures[provider_name] >= 2:
                    self.provider_health[provider_name] = False
                    logger.error(f"Marking provider {provider_name} as unhealthy")

                # Switch to next provider
                next_provider = self._get_next_provider()
                if next_provider:
                    self._set_current_provider(next_provider)
                else:
                    logger.error("No more healthy providers available")
                    break

        # All providers failed
        raise Exception(f"All providers failed. Last error: {last_error}")

    def get_status(self) -> Dict[str, Any]:
        """Get rotation provider status."""
        return {
            "current_provider": self.current_provider,
            "provider_order": self.provider_order,
            "provider_health": self.provider_health,
            "provider_failures": self.provider_failures,
            "available_providers": list(self.provider_instances.keys())
        }
