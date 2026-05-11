/**
 * Agent Zero Self-Configuration System
 * 
 * Once Agent Zero has access to ANY AI provider (Ollama, Free API, Paid API, Internet),
 * it automatically configures all required settings without user intervention.
 * 
 * Priority Order:
 * 1. Local Ollama (best for privacy, offline)
 * 2. Free API (GLM-4, etc.)
 * 3. Paid API (OpenAI, Anthropic)
 * 4. Internet fallback (web-based)
 */

import { getSystemController } from './system-controller';
import { getServiceLifecycleManager } from './service-lifecycle';

// ============================================================================
// Types
// ============================================================================

export interface AIProvider {
    type: 'ollama' | 'glm' | 'openai' | 'anthropic' | 'internet';
    name: string;
    available: boolean;
    url?: string;
    apiKey?: string;
    models?: string[];
    priority: number;
}

export interface SelfConfigResult {
    success: boolean;
    provider: AIProvider | null;
    configuredSettings: string[];
    message: string;
}

// ============================================================================
// Provider Detection
// ============================================================================

const PROVIDERS: AIProvider[] = [
    { type: 'ollama', name: 'Ollama (Local)', available: false, url: '/api', priority: 1 },
    { type: 'glm', name: 'GLM-4 (Free)', available: false, url: 'https://open.bigmodel.cn/api/paas/v4', priority: 2 },
    { type: 'openai', name: 'OpenAI', available: false, url: 'https://api.openai.com/v1', priority: 3 },
    { type: 'anthropic', name: 'Anthropic Claude', available: false, url: 'https://api.anthropic.com', priority: 4 },
    { type: 'internet', name: 'Internet Fallback', available: false, priority: 5 }
];

/**
 * Detect all available AI providers
 */
export async function detectAIProviders(): Promise<AIProvider[]> {
    const detected: AIProvider[] = [];
    const storedConfig = getStoredConfig();

    // 1. Check Ollama (Priority 1)
    // First check if we have saved Ollama config from first-run
    const savedOllamaUrl = typeof window !== 'undefined' ? localStorage.getItem('biodockify_ollama_url') : null;
    const savedOllamaModel = typeof window !== 'undefined' ? localStorage.getItem('biodockify_ollama_model') : null;

    if (savedOllamaUrl) {
        // We have saved config from first-run, trust it
        detected.push({
            type: 'ollama',
            name: 'Ollama (Local)',
            available: true,
            url: savedOllamaUrl,
            models: savedOllamaModel ? [savedOllamaModel] : [],
            priority: 1
        });
        console.log('[SelfConfig] Ollama detected from saved config:', savedOllamaUrl, savedOllamaModel);
    } else {
        // Try to detect Ollama - use relative URL (proxied via Next.js)
        try {
            const res = await fetch('/api/tags', {
                signal: AbortSignal.timeout(5000)
            });
            if (res.ok) {
                const data = await res.json();
                const models = (data.models || []).map((m: any) => m.name);
if (models.length > 0) {
                    detected.push({
                        type: 'ollama',
                        name: 'Ollama (Local)',
                        available: true,
                        url: '/api',
                        models,
                        priority: 1
                    });
                    console.log('[SelfConfig] Ollama detected with models:', models);
                }
            }
        } catch {
            // Ollama not available
        }
    }

    // 2. Check for stored API keys (storedConfig already retrieved at top)

    // GLM API
    if (storedConfig.glm_api_key) {
        detected.push({
            type: 'glm',
            name: 'GLM-4 (Free)',
            available: true,
            url: 'https://open.bigmodel.cn/api/paas/v4',
            apiKey: storedConfig.glm_api_key,
            priority: 2
        });
        console.log('[SelfConfig] GLM API key found');
    }

    // OpenAI
    if (storedConfig.openai_api_key) {
        detected.push({
            type: 'openai',
            name: 'OpenAI',
            available: true,
            url: 'https://api.openai.com/v1',
            apiKey: storedConfig.openai_api_key,
            priority: 3
        });
        console.log('[SelfConfig] OpenAI API key found');
    }

    // 3. Check internet connectivity
    try {
        const internetRes = await fetch('https://www.google.com/favicon.ico', {
            signal: AbortSignal.timeout(3000),
            mode: 'no-cors'
        });
        detected.push({
            type: 'internet',
            name: 'Internet Available',
            available: true,
            priority: 5
        });
        console.log('[SelfConfig] Internet available');
    } catch {
        console.log('[SelfConfig] Internet not available');
    }

    // Sort by priority
    return detected.sort((a, b) => a.priority - b.priority);
}

/**
 * Get stored configuration from localStorage
 */
function getStoredConfig(): Record<string, string> {
    if (typeof window === 'undefined') return {};

    try {
        const stored = localStorage.getItem('biodockify_ai_config');
        return stored ? JSON.parse(stored) : {};
    } catch {
        return {};
    }
}

/**
 * Save configuration to localStorage
 */
function saveConfig(config: Record<string, any>): void {
    if (typeof window === 'undefined') return;

    try {
        localStorage.setItem('biodockify_ai_config', JSON.stringify(config));
        localStorage.setItem('biodockify_first_run_complete', 'true');
    } catch (e) {
        console.error('[SelfConfig] Failed to save config:', e);
    }
}

// ============================================================================
// Self-Configuration Logic
// ============================================================================

/**
 * Configure Agent Zero using the best available AI provider
 */
export async function selfConfigure(): Promise<SelfConfigResult> {
    console.log('[SelfConfig] Starting self-configuration...');

    const providers = await detectAIProviders();

    if (providers.length === 0) {
        return {
            success: false,
            provider: null,
            configuredSettings: [],
            message: 'No AI providers available. Please install Ollama or provide an API key.'
        };
    }

    // Get the best provider (highest priority = lowest number)
    const bestProvider = providers[0];
    console.log('[SelfConfig] Best provider:', bestProvider.name);

    // Configure based on provider type
    const configuredSettings: string[] = [];

    switch (bestProvider.type) {
        case 'ollama':
            await configureForOllama(bestProvider, configuredSettings);
            break;
        case 'glm':
            await configureForGLM(bestProvider, configuredSettings);
            break;
        case 'openai':
            await configureForOpenAI(bestProvider, configuredSettings);
            break;
        case 'internet':
            await configureForInternet(configuredSettings);
            break;
    }

    // Save the configuration
    const config = {
        ai_provider: {
            type: bestProvider.type,
            name: bestProvider.name,
            url: bestProvider.url,
            model: bestProvider.models?.[0] || getDefaultModel(bestProvider.type)
        },
        configured_at: new Date().toISOString(),
        auto_configured: true
    };

    saveConfig(config);

    // Update SystemController
    const controller = getSystemController();
    controller.getState().mode = 'FULL';

    console.log('[SelfConfig] Configuration complete:', configuredSettings);

    return {
        success: true,
        provider: bestProvider,
        configuredSettings,
        message: `BioDockify Pharma AI configured with ${bestProvider.name}`
    };
}

/**
 * Configure for Ollama
 */
async function configureForOllama(provider: AIProvider, settings: string[]): Promise<void> {
    // Set Ollama as primary
    settings.push('ai_provider=ollama');
    settings.push(`ollama_url=${provider.url}`);

    // Select best model
    if (provider.models && provider.models.length > 0) {
        const preferredModels = ['llama3.2:7b', 'llama3.2:3b', 'llama3.2', 'mistral:7b', 'codellama:7b'];
        const selectedModel = preferredModels.find(m => provider.models!.some(pm => pm.includes(m))) || provider.models[0];
        settings.push(`ollama_model=${selectedModel}`);
    }

    // Auto-pull recommended model if none available
    if (!provider.models || provider.models.length === 0) {
        console.log('[SelfConfig] No models found, attempting to pull llama3.2:3b...');
        try {
            await fetch('/api/tags', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name: 'llama3.2:3b', stream: false })
            });
            settings.push('auto_pulled_model=llama3.2:3b');
        } catch (e) {
            console.log('[SelfConfig] Failed to pull model:', e);
        }
    }

    // Configure optimal settings for local Ollama
    settings.push('context_length=8192');
    settings.push('temperature=0.7');
    settings.push('privacy_mode=local');
}

/**
 * Configure for GLM-4 (Free API)
 */
async function configureForGLM(provider: AIProvider, settings: string[]): Promise<void> {
    settings.push('ai_provider=glm');
    settings.push(`glm_url=${provider.url}`);
    settings.push('glm_model=glm-4-flash');
    settings.push('context_length=128000'); // GLM-4 supports 128k
    settings.push('temperature=0.7');
    settings.push('privacy_mode=cloud');
}

/**
 * Configure for OpenAI
 */
async function configureForOpenAI(provider: AIProvider, settings: string[]): Promise<void> {
    settings.push('ai_provider=openai');
    settings.push(`openai_url=${provider.url}`);
    settings.push('openai_model=gpt-4-turbo');
    settings.push('context_length=128000');
    settings.push('temperature=0.7');
    settings.push('privacy_mode=cloud');
}

/**
 * Configure for Internet fallback
 */
async function configureForInternet(settings: string[]): Promise<void> {
    settings.push('ai_provider=internet');
    settings.push('limited_mode=true');
    settings.push('web_search_enabled=true');
    settings.push('privacy_mode=public');
}

/**
 * Get default model for provider type
 */
function getDefaultModel(type: AIProvider['type']): string {
    switch (type) {
        case 'ollama': return 'local-model';
        case 'ollama': return 'llama3.2:3b';
        case 'glm': return 'glm-4-flash';
        case 'openai': return 'gpt-4-turbo';
        case 'anthropic': return 'claude-3-sonnet';
        default: return 'default';
    }
}

// ============================================================================
// AI-Powered Settings Optimization
// ============================================================================

/**
 * Use AI to optimize settings based on system capabilities
 */
export async function aiOptimizeSettings(): Promise<string[]> {
    const optimizations: string[] = [];

    // Get system info
    const lifecycleManager = getServiceLifecycleManager();
    const services = lifecycleManager.getAllStatuses();

    // Check if we have an AI available
    const providers = await detectAIProviders();
    const aiAvailable = providers.some(p => p.type === 'ollama' || p.type === 'glm' || p.type === 'openai');

    if (!aiAvailable) {
        console.log('[SelfConfig] No AI available for optimization');
        return optimizations;
    }

    // Auto-detect and configure Neo4j if available
    const neo4jService = services.find(s => s.name === 'Neo4j');
    if (neo4jService?.running) {
        optimizations.push('neo4j_enabled=true');
        optimizations.push('knowledge_graph=true');
        optimizations.push('neo4j_uri=bolt://localhost:7687');
    }

    // Configure based on available memory (if we can detect it)
    // For now, use sensible defaults
    optimizations.push('max_concurrent_requests=3');
    optimizations.push('cache_enabled=true');
    optimizations.push('auto_save=true');

    return optimizations;
}

// ============================================================================
// Main Entry Point
// ============================================================================

/**
 * Initialize Agent Zero with automatic self-configuration
 * Call this on app startup
 */
export async function initializeAgentZeroWithAI(): Promise<{
    provider: AIProvider | null;
    mode: 'FULL' | 'LIMITED';
    ready: boolean;
}> {
    console.log('[Agent Zero] Initializing with AI self-configuration...');

    // Step 1: Detect providers
    const providers = await detectAIProviders();

    if (providers.length === 0) {
        console.log('[Agent Zero] No AI providers found, running in LIMITED mode');
        return { provider: null, mode: 'LIMITED', ready: false };
    }

    // Step 2: Self-configure with best provider
    const result = await selfConfigure();

    if (!result.success) {
        console.log('[Agent Zero] Self-configuration failed:', result.message);
        return { provider: null, mode: 'LIMITED', ready: false };
    }

    // Step 3: AI-powered optimization
    await aiOptimizeSettings();

    // Step 4: Mark as ready
    console.log('[Agent Zero] Ready with provider:', result.provider?.name);

    return {
        provider: result.provider,
        mode: 'FULL',
        ready: true
    };
}

/**
 * Check if Agent Zero is already configured
 */
export function isConfigured(): boolean {
    if (typeof window === 'undefined') return false;

    // Check if first run is complete
    const firstRunComplete = localStorage.getItem('biodockify_first_run_complete') === 'true';

    // Check if LM Studio is configured (from first-run wizard or settings)
    const ollamaConfigured = localStorage.getItem('biodockify_ollama_url') !== null;

    // Check stored config
    const config = getStoredConfig();
    const autoConfigured = String(config.auto_configured) === 'true';

    return firstRunComplete || autoConfigured || ollamaConfigured;
}

/**
 * Reset configuration (for testing)
 */
export function resetConfiguration(): void {
    if (typeof window === 'undefined') return;

    localStorage.removeItem('biodockify_ai_config');
    localStorage.removeItem('biodockify_first_run_complete');
    localStorage.removeItem('biodockify_config');

    console.log('[SelfConfig] Configuration reset');
}
