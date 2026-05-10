/**
 * z-ai Provider
 * Cloud LLM provider using z-ai-web-dev-sdk
 */

import ZAI from 'z-ai-web-dev-sdk';
import { LLMProvider, Message, CompleteOptions, ChatOptions, LLMError, TimeoutError } from './base-provider';

export class ZAIProvider implements LLMProvider {
  name = 'z-ai';
  type = 'cloud' as const;

  private timeout: number;
  private defaultModel: string;

  constructor(config: { timeout?: number; defaultModel?: string } = {}) {
    this.timeout = config.timeout || 120000; // 2 minutes
    this.defaultModel = config.defaultModel || 'gpt-4';
  }

  /**
   * Check if z-ai provider is available
   * Always returns true for cloud provider
   */
  async available(): Promise<boolean> {
    try {
      const zai = await ZAI.create();
      // Try a simple completion to verify connectivity
      const completion = await zai.chat.completions.create({
        messages: [
          {
            role: 'assistant',
            content: 'You are a helpful assistant.'
          },
          {
            role: 'user',
            content: 'Hi'
          }
        ],
        thinking: { type: 'disabled' }
      });
      return !!completion;
    } catch {
      // Even if fails, we'll treat as available (cloud service)
      return true;
    }
  }

  /**
   * Complete a single prompt
   */
  async complete(prompt: string, options: CompleteOptions = {}): Promise<string> {
    let timerId: any;
    let chatTimerId: any;
    try {
      const zai = await Promise.race([
        ZAI.create(),
        new Promise((_, reject) =>
          timerId = setTimeout(() => reject(new Error('Timeout')), this.timeout)
        )
      ]) as any;
      if (timerId) clearTimeout(timerId);

      const completion = await Promise.race([
        zai.chat.completions.create({
          messages: [
            {
              role: 'assistant',
              content: 'You are a helpful assistant.'
            },
            {
              role: 'user',
              content: prompt
            }
          ],
          thinking: { type: 'disabled' }
        }),
        new Promise((_, reject) =>
          chatTimerId = setTimeout(() => reject(new Error('Timeout')), this.timeout)
        )
      ]) as any;
      if (chatTimerId) clearTimeout(chatTimerId);

      const response = completion.choices[0]?.message?.content;

      if (!response || response.trim().length === 0) {
        throw new LLMError('Empty response from z-ai', this.name);
      }

      return response;
    } catch (error) {
      if (error instanceof Error && error.message === 'Timeout') {
        throw new TimeoutError(this.name, this.timeout);
      }
      if (error instanceof LLMError) throw error;
      throw new LLMError(`Failed to complete: ${error}`, this.name);
    } finally {
      if (timerId) clearTimeout(timerId);
      if (chatTimerId) clearTimeout(chatTimerId);
    }
  }

  /**
   * Complete a chat conversation
   */
  async chat(messages: Message[], options: ChatOptions = {}): Promise<string> {
    let timerId: any;
    let chatTimerId: any;
    try {
      const zai = await Promise.race([
        ZAI.create(),
        new Promise((_, reject) =>
          timerId = setTimeout(() => reject(new Error('Timeout')), this.timeout)
        )
      ]) as any;
      if (timerId) clearTimeout(timerId);

      // Add system prompt if provided
      const apiMessages = options.systemPrompt
        ? [
          { role: 'assistant' as const, content: options.systemPrompt },
          ...messages
        ]
        : messages;

      const completion = await Promise.race([
        zai.chat.completions.create({
          messages: apiMessages,
          thinking: { type: 'disabled' }
        }),
        new Promise((_, reject) =>
          chatTimerId = setTimeout(() => reject(new Error('Timeout')), this.timeout)
        )
      ]) as any;
      if (chatTimerId) clearTimeout(chatTimerId);

      const response = completion.choices[0]?.message?.content;

      if (!response || response.trim().length === 0) {
        throw new LLMError('Empty response from z-ai', this.name);
      }

      return response;
    } catch (error) {
      if (error instanceof Error && error.message === 'Timeout') {
        throw new TimeoutError(this.name, this.timeout);
      }
      if (error instanceof LLMError) throw error;
      throw new LLMError(`Failed to chat: ${error}`, this.name);
    } finally {
      if (timerId) clearTimeout(timerId);
      if (chatTimerId) clearTimeout(chatTimerId);
    }
  }

  /**
   * Get default model
   */
  getDefaultModel(): string {
    return this.defaultModel;
  }

  /**
   * Set default model
   */
  setDefaultModel(model: string) {
    this.defaultModel = model;
  }
}

// Singleton instance
let zaiInstance: ZAIProvider | null = null;

export function getZAIProvider(): ZAIProvider {
  if (!zaiInstance) {
    zaiInstance = new ZAIProvider();
  }
  return zaiInstance;
}
