/**
 * Auto-Configuration Service
 * Automatically detects and configures available services (Ollama, GROBID)
 */

const DEFAULT_OLLAMA_URL = '/api';
const DEFAULT_GROBID_URL = '/api';
const API_BASE = '';

export interface DetectedServices {
    backend: boolean;
    ollama: boolean;
    ollama_model?: string;
    grobid: boolean;
}

export interface ServiceConfig {
    ollamaUrl: string;
    grobidUrl: string;
}

/**
 * Check Ollama availability and detect loaded model
 * Returns { available: boolean, model?: string }
 */
export async function checkOllama(url: string = DEFAULT_OLLAMA_URL): Promise<{ available: boolean; model?: string }> {
    try {
        const { universalFetch } = await import('./universal-fetch');

        // Normalize URL: Strip /api/tags suffix if present to get base
        const baseUrl = url.replace(/\/api\/tags\/?$/, '');
        const targetUrl = `${baseUrl}/api/tags`;

        const res = await universalFetch(targetUrl, {
            method: 'GET',
            timeout: 5000
        });

        if (!res.ok) {
            return { available: false };
        }

        const data = res.data;
        const models = data?.models || [];

        if (models.length === 0) {
            // Ollama running but no model installed
            return { available: true, model: undefined };
        }

        // Return first installed model
        const modelName = models[0]?.name || 'unknown';
        console.log('[AutoConfig] Ollama model detected:', modelName);

        return { available: true, model: modelName };
    } catch (e) {
        console.log('[AutoConfig] Ollama check failed:', e);
        return { available: false };
    }
}

/**
 * Check if backend API is running
 */
export async function checkBackend(): Promise<boolean> {
    try {
        const res = await fetch(`${API_BASE}/api/health`, {
            method: 'GET',
            signal: AbortSignal.timeout(2000)
        });
        return res.ok;
    } catch {
        return false;
    }
}

export async function detectAllServices(): Promise<DetectedServices> {
    console.log('[AutoConfig] Starting service detection...');

    const [backend, ollamaResult] = await Promise.all([
        checkBackend(),
        checkOllama()
    ]);

    const result: DetectedServices = {
        backend,
        ollama: ollamaResult.available,
        ollama_model: ollamaResult.model,
        grobid: backend
    };

    console.log('[AutoConfig] Detection complete:', result);
    return result;
}

/**
 * Auto-configure services based on detection
 * Returns the recommended configuration
 */
export async function autoConfigureServices(): Promise<{
    detected: DetectedServices;
    config: ServiceConfig;
}> {
    const detected = await detectAllServices();

    // Build configuration based on detected services
    const config: ServiceConfig = {
        ollamaUrl: detected.ollama ? DEFAULT_OLLAMA_URL : '',
        grobidUrl: detected.grobid ? DEFAULT_GROBID_URL : ''
    };

    console.log('[AutoConfig] Recommended config:', config);

    return { detected, config };
}

/**
 * Save auto-detected configuration to settings
 */
export async function saveAutoConfig(config: ServiceConfig): Promise<boolean> {
    try {
        const res = await fetch(`${API_BASE}/api/settings`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                ai_provider: {
                    mode: config.ollamaUrl ? 'ollama' : 'auto',
                    ollama_url: config.ollamaUrl
                },
                // Send empty/disabled Neo4j config to keep backend happy/clean
                neo4j: {
                    uri: '',
                    user: 'neo4j',
                    password: ''
                }
            })
        });
        return res.ok;
    } catch (e) {
        console.error('[AutoConfig] Failed to save config:', e);
        return false;
    }
}
