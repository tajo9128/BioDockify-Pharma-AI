/**
 * LLM Provider Selector
 * Manages multiple LLM providers with automatic fallback
 */

import { LLMProvider, Message, CompleteOptions, ChatOptions, ProviderConfig, LLMError, ProviderUnavailableError } from './base-provider';

import { getZAIProvider, ZAIProvider } from './z-ai-provider';

export interface ProviderSelectorConfig {
  preferredProvider?: string;
  providers?: ProviderConfig[];
}

export class ProviderSelector {
  private providers: Map<string, LLMProvider>;
  private config: Map<string, ProviderConfig>;
  private preferredProvider: string | null;

  constructor(config: ProviderSelectorConfig = {}) {
    this.providers = new Map();
    this.config = new Map();
    this.preferredProvider = config.preferredProvider || null;

    // Register default providers


    this.registerProvider(
      new ZAIProvider(),
      {
        name: 'z-ai',
        type: 'cloud',
        enabled: true,
        priority: 2, // Cloud as fallback
        defaultModel: 'gpt-4'
      }
    );
  }

  /**
   * Register a new provider
   */
  registerProvider(provider: LLMProvider, config: ProviderConfig) {
    this.providers.set(config.name, provider);
    this.config.set(config.name, config);
  }

  /**
   * Get a specific provider by name
   */
  getProvider(name: string): LLMProvider | undefined {
    return this.providers.get(name);
  }

  /**
   * Get all registered providers
   */
  getAllProviders(): LLMProvider[] {
    return Array.from(this.providers.values());
  }

  /**
   * Get all provider configs
   */
  getAllProviderConfigs(): ProviderConfig[] {
    return Array.from(this.config.values());
  }

  /**
   * Get the best available provider with fallback
   */
  async getBestProvider(): Promise<LLMProvider> {
    const enabledProviders = Array.from(this.config.values())
      .filter(c => c.enabled)
      .sort((a, b) => a.priority - b.priority);

    // Try preferred provider first
    if (this.preferredProvider) {
      const preferred = this.providers.get(this.preferredProvider);
      const preferredConfig = this.config.get(this.preferredProvider);

      if (preferred && preferredConfig && preferredConfig.enabled) {
        if (await preferred.available()) {
          console.log(`✅ Using preferred provider: ${this.preferredProvider}`);
          return preferred;
        }
      }
    }

    // Try all enabled providers in priority order
    for (const providerConfig of enabledProviders) {
      const provider = this.providers.get(providerConfig.name);

      if (!provider) continue;

      try {
        const available = await provider.available();
        if (available) {
          console.log(`✅ Selected provider: ${providerConfig.name} (${providerConfig.type})`);
          return provider;
        } else {
          console.log(`⚠️  Provider ${providerConfig.name} is not available`);
        }
      } catch (error) {
        console.error(`❌ Error checking provider ${providerConfig.name}:`, error);
      }
    }

    throw new ProviderUnavailableError('No LLM provider available');
  }

  /**
   * Set preferred provider
   */
  setPreferredProvider(providerName: string) {
    if (!this.providers.has(providerName)) {
      throw new Error(`Provider ${providerName} not registered`);
    }

    this.preferredProvider = providerName;
    console.log(`🎯 Preferred provider set to: ${providerName}`);
  }

  /**
   * Get current preferred provider
   */
  getPreferredProvider(): string | null {
    return this.preferredProvider;
  }

  /**
   * Enable/disable a provider
   */
  setProviderEnabled(providerName: string, enabled: boolean) {
    const config = this.config.get(providerName);
    if (config) {
      config.enabled = enabled;
      console.log(`🔧 Provider ${providerName} ${enabled ? 'enabled' : 'disabled'}`);
    }
  }

  /**
   * Check provider status
   */
  async checkProviderStatus(providerName: string): Promise<boolean> {
    const provider = this.providers.get(providerName);
    if (!provider) {
      return false;
    }

    try {
      return await provider.available();
    } catch {
      return false;
    }
  }

  /**
   * Get status of all providers
   */
  async getProvidersStatus(): Promise<
    Array<{ name: string; type: string; available: boolean; enabled: boolean }>
  > {
    const status = [];

    for (const [name, provider] of this.providers.entries()) {
      const config = this.config.get(name)!;

      status.push({
        name,
        type: provider.type,
        available: await provider.available(),
        enabled: config.enabled
      });
    }

    return status;
  }

  /**
   * Complete a prompt using best available provider
   */
  async complete(prompt: string, options: CompleteOptions = {}): Promise<string> {
    const provider = await this.getBestProvider();
    return await provider.complete(prompt, options);
  }

  /**
   * Chat using best available provider
   */
  async chat(messages: Message[], options: ChatOptions = {}): Promise<string> {
    const provider = await this.getBestProvider();
    return await provider.chat(messages, options);
  }
}

// Singleton instance
let providerSelectorInstance: ProviderSelector | null = null;

export function getProviderSelector(): ProviderSelector {
  if (!providerSelectorInstance) {
    providerSelectorInstance = new ProviderSelector();
  }
  return providerSelectorInstance;
}

export function createProviderSelector(config: ProviderSelectorConfig): ProviderSelector {
  return new ProviderSelector(config);
}
