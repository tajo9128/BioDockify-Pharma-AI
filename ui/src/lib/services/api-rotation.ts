/**
 * API Rotation Service
 * Automatically switches between API providers when rate limits are hit (429 errors)
 * Implements cooldown tracking and priority-based fallback chain
 */

// Provider configuration with priority order
export interface RotatableProvider {
    name: string;
    type: 'local' | 'free' | 'paid';
    priority: number; // Lower = higher priority (1 = first)
    baseUrl: string;
    keyPath: string; // Path in settings to get API key
    modelPath: string; // Path in settings to get model
    defaultModel: string;
    rateLimit: number; // Requests per minute (0 = unlimited)
}

// Default provider chain (priority order)
// LOCAL (1) → FREE (2-4) → PAID (5-10)
export const PROVIDER_CHAIN: RotatableProvider[] = [
    // === LOCAL (Priority 1) ===
    {
        name: 'ollama',
        type: 'local',
        priority: 1,
        baseUrl: '/api',
        keyPath: '', // No key needed for local
        modelPath: 'ai_provider.ollama_model',
        defaultModel: 'auto',
        rateLimit: 0 // Unlimited
    },
    // === FREE APIs (Priority 2-4) ===
    {
        name: 'groq',
        type: 'free',
        priority: 2,
        baseUrl: 'https://api.groq.com/openai/v1',
        keyPath: 'ai_provider.groq_key',
        modelPath: 'ai_provider.groq_model',
        defaultModel: 'llama-3.3-70b-versatile',
        rateLimit: 30
    },
    {
        name: 'huggingface',
        type: 'free',
        priority: 3,
        baseUrl: 'https://api-inference.huggingface.co',
        keyPath: 'ai_provider.huggingface_key',
        modelPath: 'ai_provider.huggingface_model',
        defaultModel: 'meta-llama/Llama-3-8B-Instruct',
        rateLimit: 10
    },
    {
        name: 'google',
        type: 'free',
        priority: 4,
        baseUrl: 'https://generativelanguage.googleapis.com/v1beta',
        keyPath: 'ai_provider.google_key',
        modelPath: 'ai_provider.google_model',
        defaultModel: 'gemini-1.5-flash',
        rateLimit: 15
    },
    // === PAID APIs (Priority 5-10) ===
    {
        name: 'openrouter',
        type: 'paid',
        priority: 5,
        baseUrl: 'https://openrouter.ai/api/v1',
        keyPath: 'ai_provider.openrouter_key',
        modelPath: 'ai_provider.openrouter_model',
        defaultModel: 'meta-llama/llama-3.1-8b-instruct:free',
        rateLimit: 200
    },
    {
        name: 'deepseek',
        type: 'paid',
        priority: 6,
        baseUrl: 'https://api.deepseek.com/v1',
        keyPath: 'ai_provider.deepseek_key',
        modelPath: 'ai_provider.deepseek_model',
        defaultModel: 'deepseek-chat',
        rateLimit: 60
    },
    {
        name: 'glm',
        type: 'paid',
        priority: 7,
        baseUrl: 'https://open.bigmodel.cn/api/paas/v4',
        keyPath: 'ai_provider.glm_key',
        modelPath: 'ai_provider.glm_model',
        defaultModel: 'glm-4-flash',
        rateLimit: 60
    },
    {
        name: 'kimi',
        type: 'paid',
        priority: 8,
        baseUrl: 'https://api.moonshot.cn/v1',
        keyPath: 'ai_provider.kimi_key',
        modelPath: 'ai_provider.kimi_model',
        defaultModel: 'moonshot-v1-8k',
        rateLimit: 30
    },
    {
        name: 'openai',
        type: 'paid',
        priority: 9,
        baseUrl: 'https://api.openai.com/v1',
        keyPath: 'ai_provider.openai_key',
        modelPath: 'ai_provider.openai_model',
        defaultModel: 'gpt-4o-mini',
        rateLimit: 500
    },
    {
        name: 'custom',
        type: 'paid',
        priority: 10,
        baseUrl: '', // User-defined
        keyPath: 'ai_provider.custom_key',
        modelPath: 'ai_provider.custom_model',
        defaultModel: '',
        rateLimit: 60
    }
];

// Track rate-limited providers with cooldown timestamps
const rateLimitedProviders: Map<string, number> = new Map();

// Cooldown duration in milliseconds (60 seconds)
const COOLDOWN_MS = 60000;

/**
 * Check if a provider is currently in cooldown from rate limiting
 */
export function isProviderInCooldown(providerName: string): boolean {
    const cooldownUntil = rateLimitedProviders.get(providerName);
    if (!cooldownUntil) return false;

    if (Date.now() > cooldownUntil) {
        // Cooldown expired, remove from map
        rateLimitedProviders.delete(providerName);
        console.log(`[APIRotation] ${providerName} cooldown expired, now available`);
        return false;
    }

    return true;
}

/**
 * Mark a provider as rate-limited (start cooldown)
 */
export function markProviderRateLimited(providerName: string): void {
    const cooldownUntil = Date.now() + COOLDOWN_MS;
    rateLimitedProviders.set(providerName, cooldownUntil);
    console.log(`[APIRotation] ${providerName} marked as rate-limited until ${new Date(cooldownUntil).toLocaleTimeString()}`);
}

/**
 * Get the next available provider in the chain
 * Skips providers that are in cooldown or missing keys
 */
export function getNextAvailableProvider(
    settings: any,
    skipProvider?: string
): RotatableProvider | null {
    // Sort by priority
    const sortedProviders = [...PROVIDER_CHAIN].sort((a, b) => a.priority - b.priority);

    for (const provider of sortedProviders) {
        // Skip the provider we're rotating away from
        if (skipProvider && provider.name === skipProvider) continue;

        // Skip if in cooldown
        if (isProviderInCooldown(provider.name)) {
            console.log(`[APIRotation] Skipping ${provider.name} - in cooldown`);
            continue;
        }

        // Check if API key exists (except for local providers)
        if (provider.type !== 'local' && provider.keyPath) {
            const key = getNestedValue(settings, provider.keyPath);
            if (!key) {
                console.log(`[APIRotation] Skipping ${provider.name} - no API key configured`);
                continue;
            }
        }

        console.log(`[APIRotation] Selected ${provider.name} as next provider`);
        return provider;
    }

    console.warn('[APIRotation] No available providers found!');
    return null;
}

/**
 * Handle 429 rate limit error - rotates to next provider
 * Returns the new provider to use, or null if no alternatives
 */
export function handleRateLimitError(
    currentProvider: string,
    settings: any
): RotatableProvider | null {
    console.log(`[APIRotation] Rate limit hit on ${currentProvider}, rotating...`);

    // Mark current provider as rate-limited
    markProviderRateLimited(currentProvider);

    // Get next available provider
    return getNextAvailableProvider(settings, currentProvider);
}

/**
 * Check if an error is a rate limit error (429)
 */
export function isRateLimitError(error: any): boolean {
    if (!error) return false;

    // Check status code
    if (error.status === 429) return true;
    if (error.statusCode === 429) return true;

    // Check error message
    const message = error.message?.toLowerCase() || '';
    if (message.includes('rate limit')) return true;
    if (message.includes('too many requests')) return true;
    if (message.includes('429')) return true;
    if (message.includes('quota exceeded')) return true;

    return false;
}

/**
 * Get the current active provider based on settings and availability
 */
export function getCurrentActiveProvider(settings: any): RotatableProvider | null {
    const mode = settings?.ai_provider?.mode;

    // If specific mode is set, try that first
    if (mode && mode !== 'auto') {
        const provider = PROVIDER_CHAIN.find(p => p.name === mode);
        if (provider && !isProviderInCooldown(mode)) {
            return provider;
        }
    }

    // Otherwise, get next available
    return getNextAvailableProvider(settings);
}

/**
 * Utility: Get nested value from object using dot notation
 */
function getNestedValue(obj: any, path: string): any {
    if (!path) return undefined;
    return path.split('.').reduce((current, key) => current?.[key], obj);
}

/**
 * Get cooldown status for all providers
 */
export function getCooldownStatus(): Array<{ name: string; inCooldown: boolean; cooldownUntil?: Date }> {
    return PROVIDER_CHAIN.map(provider => ({
        name: provider.name,
        inCooldown: isProviderInCooldown(provider.name),
        cooldownUntil: rateLimitedProviders.has(provider.name)
            ? new Date(rateLimitedProviders.get(provider.name)!)
            : undefined
    }));
}

/**
 * Clear all cooldowns (for testing or manual reset)
 */
export function clearAllCooldowns(): void {
    rateLimitedProviders.clear();
    console.log('[APIRotation] All cooldowns cleared');
}

/**
 * Make an API call with automatic rotation on rate limit
 * This is the main entry point for API calls
 */
export async function callWithRotation(
    settings: any,
    requestFn: (provider: RotatableProvider) => Promise<Response>,
    maxRetries: number = 3
): Promise<Response> {
    let currentProvider = getCurrentActiveProvider(settings);
    let lastError: Error | null = null;

    for (let attempt = 0; attempt < maxRetries; attempt++) {
        if (!currentProvider) {
            throw new Error('No API providers available. Please configure at least one API key or start LM Studio.');
        }

        try {
            console.log(`[APIRotation] Attempt ${attempt + 1}/${maxRetries} with ${currentProvider.name}`);
            const response = await requestFn(currentProvider);

            // Check for rate limit response
            if (response.status === 429) {
                console.log(`[APIRotation] Got 429 from ${currentProvider.name}`);
                markProviderRateLimited(currentProvider.name);
                currentProvider = getNextAvailableProvider(settings, currentProvider.name);
                continue;
            }

            return response;

        } catch (error: any) {
            lastError = error;

            if (isRateLimitError(error)) {
                console.log(`[APIRotation] Rate limit error from ${currentProvider?.name}:`, error.message);
                if (currentProvider) markProviderRateLimited(currentProvider.name);
                currentProvider = getNextAvailableProvider(settings, currentProvider?.name);
            } else {
                // Non-rate-limit error, still try next provider
                console.error(`[APIRotation] Error from ${currentProvider?.name}:`, error.message);
                currentProvider = getNextAvailableProvider(settings, currentProvider?.name);
            }
        }
    }

    throw lastError || new Error('All API providers failed or are rate-limited');
}
