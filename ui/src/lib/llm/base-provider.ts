/**
 * LLM Provider Interface
 * Base interface for all LLM providers (LM Studio, z-ai, etc.)
 */

export interface Message {
  role: 'system' | 'user' | 'assistant';
  content: string;
}

export interface LLMProvider {
  /** Provider name */
  name: string;

  /** Provider type */
  type: 'cloud' | 'local';

  /** Check if provider is available */
  available(): Promise<boolean>;

  /** Complete a single prompt */
  complete(prompt: string, options?: CompleteOptions): Promise<string>;

  /** Complete a chat conversation */
  chat(messages: Message[], options?: ChatOptions): Promise<string>;

  /** Get list of available models */
  getModels?(): Promise<string[]>;
}

export interface CompleteOptions {
  model?: string;
  temperature?: number;
  maxTokens?: number;
  stream?: boolean;
}

export interface ChatOptions extends CompleteOptions {
  systemPrompt?: string;
}

export interface ProviderConfig {
  name: string;
  type: 'cloud' | 'local';
  enabled: boolean;
  priority: number; // Lower = higher priority
  defaultModel?: string;
}

export class LLMError extends Error {
  constructor(
    message: string,
    public provider: string,
    public code?: string
  ) {
    super(message);
    this.name = 'LLMError';
  }
}

export class ProviderUnavailableError extends LLMError {
  constructor(provider: string) {
    super(`Provider ${provider} is not available`, provider, 'UNAVAILABLE');
    this.name = 'ProviderUnavailableError';
  }
}

export class TimeoutError extends LLMError {
  constructor(provider: string, timeout: number) {
    super(
      `Provider ${provider} timed out after ${timeout}ms`,
      provider,
      'TIMEOUT'
    );
    this.name = 'TimeoutError';
  }
}
