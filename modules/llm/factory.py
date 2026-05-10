from modules.llm.adapters import (
    BaseLLMAdapter,
    GoogleGeminiAdapter,
    OpenRouterAdapter,
    HuggingFaceAdapter,
    CustomAdapter,
    ZhipuAdapter,
    LMStudioAdapter,
    OllamaAdapter,
    AnthropicAdapter,
    AzureAdapter,
    AWSAdapter,
)
from typing import Optional


class LLMFactory:
    """Factory to create LLM Adapters based on configuration."""

    @staticmethod
    def get_adapter(
        provider: str, config: "OrchestratorConfig"
    ) -> Optional[BaseLLMAdapter]:
        """
        Returns the appropriate adapter instance.

        Args:
            provider: 'google', 'openrouter', 'huggingface', 'custom', 'zhipu', 'lm_studio', 'anthropic', 'groq', 'deepseek', 'ollama'
            config: OrchestratorConfig object with keys

        Returns:
            Initialized adapter or None if key missing
        """
        if provider == "google":
            if not config.google_key:
                print(f"Warning: Google API key missing. Falling back to LM Studio.")
                return LLMFactory._get_fallback_adapter()
            return GoogleGeminiAdapter(config.google_key)

        elif provider == "openrouter":
            if not config.openrouter_key:
                print(
                    f"Warning: OpenRouter API key missing. Falling back to LM Studio."
                )
                return LLMFactory._get_fallback_adapter()
            model = (
                config.primary_model
                if "mistral" in config.primary_model or "gpt" in config.primary_model
                else "mistralai/mistral-7b-instruct"
            )
            return OpenRouterAdapter(config.openrouter_key, model=model)

        elif provider == "huggingface":
            if not config.huggingface_key:
                print(
                    f"Warning: HuggingFace API key missing. Falling back to LM Studio."
                )
                return LLMFactory._get_fallback_adapter()
            return HuggingFaceAdapter(config.huggingface_key)

        elif provider == "custom":
            if not config.custom_key or not config.custom_base_url:
                print(
                    f"Warning: Custom Provider config missing. Falling back to LM Studio."
                )
                return LLMFactory._get_fallback_adapter()
            return CustomAdapter(
                config.custom_key, config.custom_base_url, config.custom_model
            )

        elif provider == "zhipu":
            if not config.glm_key:
                print(f"Warning: Zhipu API key missing. Falling back to LM Studio.")
                return LLMFactory._get_fallback_adapter()
            return ZhipuAdapter(config.glm_key)

        elif provider == "anthropic":
            if not config.anthropic_key:
                print(f"Warning: Anthropic API key missing. Falling back to LM Studio.")
                return LLMFactory._get_fallback_adapter()
            return AnthropicAdapter(config.anthropic_key)

        elif provider == "groq":
            if not config.groq_key:
                print(f"Warning: Groq API key missing. Falling back to LM Studio.")
                return LLMFactory._get_fallback_adapter()
            base_url = (
                getattr(config, "groq_base_url", None)
                or "https://api.groq.com/openai/v1"
            )
            model = getattr(config, "groq_model", None) or "llama3-70b-8192"
            return CustomAdapter(config.groq_key, base_url, model)

        elif provider == "deepseek":
            if not config.deepseek_key:
                print(f"Warning: DeepSeek API key missing. Falling back to LM Studio.")
                return LLMFactory._get_fallback_adapter()
            base_url = (
                getattr(config, "deepseek_base_url", None) or "https://api.deepseek.com"
            )
            model = getattr(config, "deepseek_model", None) or "deepseek-chat"
            return CustomAdapter(config.deepseek_key, base_url, model)
            base_url = (
                getattr(config, "deepseek_base_url", None) or "https://api.deepseek.com"
            )
            model = getattr(config, "deepseek_model", None) or "deepseek-chat"
            return CustomAdapter(config.deepseek_key, base_url, model)

        elif provider == "ollama":
            # Auto-detect model if not specified
            model = getattr(config, "ollama_model", "") or ""
            if not model:
                try:
                    from modules.llm.adapters import OllamaAdapter
                    temp = OllamaAdapter(base_url=getattr(config, "ollama_host", None) or "http://localhost:11434", model="")
                    available = temp.list_models()
                    if available:
                        model = available[0]
                        print(f"[Auto-detect] Using Ollama model: {model}")
                except:
                    pass
            return OllamaAdapter(
                config.ollama_host or "http://localhost:11434",
                model,
            )

        elif provider == "azure":
            if not config.azure_key or not config.azure_endpoint:
                print(f"Warning: Azure config missing. Falling back to LM Studio.")
                return LLMFactory._get_fallback_adapter()
            return AzureAdapter(
                api_key=config.azure_key,
                endpoint=config.azure_endpoint,
                deployment_name=config.azure_deployment,
                api_version=config.azure_api_version,
            )

        elif provider == "aws":
            if not config.aws_access_key or not config.aws_secret_key:
                print(f"Warning: AWS config missing. Falling back to LM Studio.")
                return LLMFactory._get_fallback_adapter()
            return AWSAdapter(
                access_key=config.aws_access_key,
                secret_key=config.aws_secret_key,
                region_name=config.aws_region_name,
                model_id=config.aws_model_id,
            )

        elif provider == "mistral":
            key = config.mistral_key or config.custom_key
            if not key:
                print(f"Warning: Mistral API key missing. Falling back to LM Studio.")
                return LLMFactory._get_fallback_adapter()
            return CustomAdapter(
                key,
                "https://api.mistral.ai/v1",
                config.mistral_model or "mistral-large-latest",
            )

        elif provider == "venice":
            key = config.venice_key or config.custom_key
            if not key:
                print(f"Warning: Venice API key missing. Falling back to LM Studio.")
                return LLMFactory._get_fallback_adapter()
            return CustomAdapter(
                key,
                "https://api.venice.ai/api/v1",
                config.venice_model or "llama-3-70b",
            )

        elif provider == "kimi":
            key = config.kimi_key or config.custom_key
            if not key:
                print(
                    f"Warning: Kimi/Moonshot API key missing. Falling back to LM Studio."
                )
                return LLMFactory._get_fallback_adapter()
            return CustomAdapter(
                key, "https://api.moonshot.cn/v1", config.kimi_model or "moonshot-v1-8k"
            )

        elif provider == "ollama":
            # Use Ollama adapter - use host.docker.internal for Docker, localhost for local dev
            import os
            default_url = "http://host.docker.internal:11434" if os.path.exists("/.dockerenv") else "http://localhost:11434"
            ollama_url = getattr(config, "ollama_url", default_url)
            model = getattr(config, "ollama_model", "")
            
            # Auto-detect model if not specified
            if not model:
                try:
                    from modules.llm.adapters import OllamaAdapter
                    temp_adapter = OllamaAdapter(base_url=ollama_url, model="")
                    available = temp_adapter.list_models()
                    if available:
                        model = available[0]
                        print(f"[Auto-detect] Using Ollama model: {model}")
                except Exception as e:
                    print(f"[Auto-detect] Failed to list models: {e}")
            
            return OllamaAdapter(base_url=ollama_url, model=model)

        print(f"Warning: Unknown provider '{provider}'. Falling back to Ollama.")
        return LLMFactory._get_fallback_adapter()

    @staticmethod
    def _get_fallback_adapter() -> BaseLLMAdapter:
        """Returns a default Ollama adapter with auto-detected model."""
        try:
            from modules.llm.adapters import OllamaAdapter
            adapter = OllamaAdapter(base_url="http://localhost:11434", model="")
            available = adapter.list_models()
            if available:
                adapter.model = available[0]
                print(f"[Fallback] Using auto-detected model: {adapter.model}")
                return adapter
        except Exception as e:
            print(f"[Fallback] Failed to auto-detect: {e}")
        
        return OllamaAdapter(base_url="http://localhost:11434", model="")
