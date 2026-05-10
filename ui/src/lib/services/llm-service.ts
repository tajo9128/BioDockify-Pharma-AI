/**
 * Unified LLM Service
 * 
 * Central service for ALL LLM calls across BioDockify.
 * Uses api-rotation for automatic fallback on rate limits.
 * 
 * Features:
 * - Deep Research
 * - Academic Writing
 * - Podcast Generation (script)
 * - Video Script Generation
 * - General Chat
 */

import {
    callWithRotation,
    getCurrentActiveProvider,
    RotatableProvider,
    PROVIDER_CHAIN
} from './api-rotation';

// Get settings from localStorage
function getSettings(): any {
    if (typeof window === 'undefined') return {};
    try {
        const cached = localStorage.getItem('biodockify_settings');
        return cached ? JSON.parse(cached) : {};
    } catch {
        return {};
    }
}

// Get API key for a provider
function getProviderApiKey(provider: RotatableProvider, settings: any): string {
    if (!provider.keyPath) return '';
    const parts = provider.keyPath.split('.');
    let value = settings;
    for (const part of parts) {
        value = value?.[part];
    }
    return value || '';
}

// Build URL for a provider
function getProviderUrl(provider: RotatableProvider, settings: any): string {
    if (provider.name === 'custom' && settings?.ai_provider?.custom_base_url) {
        return settings.ai_provider.custom_base_url;
    }
    if (provider.name === 'ollama' && settings?.ai_provider?.ollama_url) {
        return settings.ai_provider.ollama_url;
    }
    return provider.baseUrl;
}

// Get model for a provider
function getProviderModel(provider: RotatableProvider, settings: any): string {
    if (!provider.modelPath) return provider.defaultModel;
    const parts = provider.modelPath.split('.');
    let value = settings;
    for (const part of parts) {
        value = value?.[part];
    }
    return value || provider.defaultModel;
}

export interface LLMMessage {
    role: 'system' | 'user' | 'assistant';
    content: string;
}

export interface LLMOptions {
    temperature?: number;
    maxTokens?: number;
    stream?: boolean;
}

/**
 * Core LLM Chat function - uses rotation for fallback
 */
export async function llmChat(
    messages: LLMMessage[],
    options: LLMOptions = {}
): Promise<string> {
    const settings = getSettings();

    const response = await callWithRotation(settings, async (provider) => {
        const url = getProviderUrl(provider, settings);
        const apiKey = getProviderApiKey(provider, settings);
        const model = getProviderModel(provider, settings);

        // Special handling for Google Gemini API format
        if (provider.name === 'google') {
            return fetch(`${url}/models/${model}:generateContent?key=${apiKey}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    contents: messages.map(m => ({
                        role: m.role === 'assistant' ? 'model' : m.role,
                        parts: [{ text: m.content }]
                    }))
                })
            });
        }

        // Standard OpenAI-compatible format (works with most providers)
        const headers: Record<string, string> = {
            'Content-Type': 'application/json'
        };

        if (apiKey) {
            headers['Authorization'] = `Bearer ${apiKey}`;
        }

        return fetch(`${url}/chat/completions`, {
            method: 'POST',
            headers,
            body: JSON.stringify({
                model,
                messages,
                temperature: options.temperature ?? 0.7,
                max_tokens: options.maxTokens ?? 2048,
                stream: options.stream ?? false
            })
        });
    });

    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData?.error?.message || `LLM request failed: ${response.status}`);
    }

    const data = await response.json();

    // Handle Google Gemini response format
    if (data.candidates) {
        return data.candidates[0]?.content?.parts[0]?.text || '';
    }

    // Standard OpenAI format
    return data.choices?.[0]?.message?.content || '';
}

/**
 * Deep Research - Break down query into research plan
 */
export async function deepResearchPlan(query: string): Promise<string[]> {
    const response = await llmChat([
        {
            role: 'system',
            content: `You are a research planning assistant. Break down complex research queries into 4-6 clear, actionable research steps. Return ONLY a JSON array of strings.`
        },
        {
            role: 'user',
            content: `Create a research plan for: "${query}"`
        }
    ], { temperature: 0.3 });

    try {
        // Extract JSON from response
        const jsonMatch = response.match(/\[[\s\S]*\]/);
        return jsonMatch ? JSON.parse(jsonMatch[0]) : [
            `Analyze: "${query}"`,
            'Search recent literature',
            'Cross-reference findings',
            'Synthesize conclusions'
        ];
    } catch {
        return [
            `Analyze: "${query}"`,
            'Search recent literature',
            'Cross-reference findings',
            'Synthesize conclusions'
        ];
    }
}

/**
 * Deep Research - Execute a single research step
 */
export async function deepResearchStep(step: string, context: string): Promise<string> {
    const response = await llmChat([
        {
            role: 'system',
            content: `You are a pharmaceutical research assistant. Execute the given research step thoroughly, using the provided context. Be detailed and cite sources when possible.`
        },
        {
            role: 'user',
            content: `Research Step: ${step}\n\nContext: ${context}`
        }
    ], { maxTokens: 1500 });

    return response;
}

/**
 * Academic Writing - Generate structured academic text
 */
export async function academicWrite(
    topic: string,
    style: 'abstract' | 'introduction' | 'methods' | 'results' | 'discussion' | 'conclusion',
    context: string
): Promise<string> {
    const styleGuides: Record<string, string> = {
        abstract: 'Write a concise 250-word abstract following IMRaD structure.',
        introduction: 'Write an engaging introduction with context, problem statement, and objectives.',
        methods: 'Describe methodology clearly and reproducibly.',
        results: 'Present findings objectively with appropriate statistical descriptions.',
        discussion: 'Interpret results, compare with literature, discuss implications and limitations.',
        conclusion: 'Summarize key findings and suggest future directions.'
    };

    const response = await llmChat([
        {
            role: 'system',
            content: `You are an expert academic and scientific writer specializing in pharmaceutical and biomedical research. ${styleGuides[style]} Use formal academic language and cite sources appropriately.`
        },
        {
            role: 'user',
            content: `Topic: ${topic}\n\nContext/Notes: ${context}`
        }
    ], { temperature: 0.5, maxTokens: 2000 });

    return response;
}

/**
 * Podcast Script Generation - Create engaging audio briefing script
 */
export async function generatePodcastScript(
    topic: string,
    findings: string[],
    duration: 'short' | 'medium' | 'long' = 'medium'
): Promise<string> {
    const durations = { short: '2-3', medium: '5-7', long: '10-15' };

    const response = await llmChat([
        {
            role: 'system',
            content: `You are a science communicator creating an engaging audio briefing script. The script should be conversational, informative, and suitable for audio playback. Duration target: ${durations[duration]} minutes.`
        },
        {
            role: 'user',
            content: `Topic: ${topic}\n\nKey Findings:\n${findings.map((f, i) => `${i + 1}. ${f}`).join('\n')}`
        }
    ], { temperature: 0.7, maxTokens: 2500 });

    return response;
}

/**
 * Video Script Generation - Create structured video narration script
 */
export async function generateVideoScript(
    topic: string,
    keyPoints: string[],
    style: 'educational' | 'summary' | 'presentation' = 'educational'
): Promise<{ scenes: Array<{ narration: string; visualNotes: string }> }> {
    const response = await llmChat([
        {
            role: 'system',
            content: `You are creating a ${style} video script. Return a JSON object with "scenes" array, where each scene has "narration" (spoken text) and "visualNotes" (suggested visuals). Target 5-8 scenes.`
        },
        {
            role: 'user',
            content: `Topic: ${topic}\n\nKey Points:\n${keyPoints.map((p, i) => `${i + 1}. ${p}`).join('\n')}`
        }
    ], { temperature: 0.6, maxTokens: 3000 });

    try {
        const jsonMatch = response.match(/\{[\s\S]*\}/);
        return jsonMatch ? JSON.parse(jsonMatch[0]) : { scenes: [] };
    } catch {
        return { scenes: [{ narration: response, visualNotes: 'General topic visualization' }] };
    }
}

/**
 * Get current active provider info (for UI display)
 */
export function getActiveProviderInfo(): { name: string; type: string } | null {
    const settings = getSettings();
    const provider = getCurrentActiveProvider(settings);
    return provider ? { name: provider.name, type: provider.type } : null;
}

/**
 * Quick check if any LLM provider is available
 */
export async function checkLlmAvailability(): Promise<boolean> {
    const settings = getSettings();
    const provider = getCurrentActiveProvider(settings);
    return provider !== null;
}
