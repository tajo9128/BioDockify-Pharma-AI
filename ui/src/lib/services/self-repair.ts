/**
 * Agent Zero Self-Repair Service
 * Automatically detects and fixes configuration issues
 * Provides intelligent retry logic and alternative configurations
 */

// LM Studio default and alternative ports
const LM_STUDIO_PORTS = [1234, 1235, 8080, 8000];
const DEFAULT_TIMEOUT = 5000; // Increased from 3000ms

export interface RepairResult {
    success: boolean;
    action: string;
    details: string;
    newConfig?: Record<string, any>;
}

export interface ServiceStatus {
    name: string;
    available: boolean;
    url?: string;
    error?: string;
    model?: string;
}

/**
 * Enhanced LM Studio detection with multiple retry and port scanning
 */
export async function detectOllamaEnhanced(): Promise<ServiceStatus> {
    console.log('[SelfRepair] Starting enhanced LM Studio detection...');

    // Try each port
    for (const port of LM_STUDIO_PORTS) {
        const url = `http://localhost:${port}/v1`;
        console.log(`[SelfRepair] Trying LM Studio on port ${port}...`);

        try {
            const result = await fetchWithRetry(`${url}/models`, 3, DEFAULT_TIMEOUT);

            if (result.ok) {
                const data = await result.json();
                const models = data?.data || [];
                const model = models[0]?.id;

                console.log(`[SelfRepair] LM Studio found on port ${port}!`, { model });

                return {
                    name: 'LM Studio',
                    available: true,
                    url: url,
                    model: model || undefined
                };
            }
        } catch (e) {
            console.log(`[SelfRepair] Port ${port} failed:`, e);
        }
    }

    // All ports failed
    return {
        name: 'LM Studio',
        available: false,
        error: 'Could not connect on any port (1234, 1235, 8080, 8000)'
    };
}

/**
 * Fetch with automatic retry using universalFetch for CORS bypass
 */
async function fetchWithRetry(
    url: string,
    maxRetries: number = 3,
    timeout: number = DEFAULT_TIMEOUT
): Promise<{ ok: boolean; json: () => Promise<any>; data?: any }> {
    const { universalFetch } = await import('./universal-fetch');
    let lastError: Error | null = null;

    for (let attempt = 1; attempt <= maxRetries; attempt++) {
        try {
            console.log(`[SelfRepair] Fetch attempt ${attempt}/${maxRetries}: ${url}`);

            const response = await universalFetch(url, {
                method: 'GET',
                timeout
            });

            return response;

        } catch (e: any) {
            lastError = e;
            console.log(`[SelfRepair] Attempt ${attempt} failed: ${e.message}`);

            if (attempt < maxRetries) {
                // Exponential backoff
                const delay = Math.min(1000 * Math.pow(2, attempt - 1), 5000);
                await new Promise(r => setTimeout(r, delay));
            }
        }
    }

    throw lastError || new Error('All retries failed');
}

/**
 * Self-repair: Fix Ollama configuration issues
 */
export async function repairOllamaConfig(): Promise<RepairResult> {
    console.log('[SelfRepair] Starting Ollama repair...');

    // Step 1: Enhanced detection
    const status = await detectOllamaEnhanced();

    if (status.available) {
        return {
            success: true,
            action: 'auto_detected',
            details: `Ollama found at ${status.url}${status.model ? ` with model: ${status.model}` : ''}`,
            newConfig: {
                ollama_url: status.url,
                ollama_model: status.model
            }
        };
    }

    // Step 2: Check if Ollama is running
    const processCheck = await checkOllamaProcess();

    if (processCheck.running && !processCheck.serverReady) {
        return {
            success: false,
            action: 'server_not_ready',
            details: 'Ollama is running but the server is not responding.'
        };
    }

    if (!processCheck.running) {
        return {
            success: false,
            action: 'not_running',
            details: 'Ollama is not running. Please start Ollama and install a model.'
        };
    }

    return {
        success: false,
        action: 'unknown_error',
        details: 'Could not detect Ollama. Check if it\'s running on the default port (11434).'
    };
}

/**
 * Check if Ollama is running via backend
 */
async function checkOllamaProcess(): Promise<{ running: boolean; serverReady: boolean }> {
    try {
        const API_BASE = typeof window !== 'undefined'
            ? (window as any).__BIODOCKIFY_API_URL__ || 'http://localhost:3000'
            : 'http://localhost:3000';
        const res = await fetch(`${API_BASE}/api/system/check-process?name=Ollama`, {
            method: 'GET',
            signal: AbortSignal.timeout(3000)
        });

        if (res.ok) {
            return await res.json();
        }
    } catch (e) {
        console.log('[SelfRepair] Backend process check unavailable');
    }

    // Fallback: assume not running if we can't check
    return { running: false, serverReady: false };
}

/**
 * Run full self-repair diagnostics
 */
export async function runSelfRepairDiagnostics(): Promise<{
    ollama: RepairResult;
    backend: ServiceStatus;
    recommendations: string[];
}> {
    console.log('[SelfRepair] Running full diagnostics...');

    // Check Ollama
    const ollama = await repairOllamaConfig();

    // Check Backend
    const backend = await checkBackend();

    // Generate recommendations
    const recommendations: string[] = [];

    if (!ollama.success) {
        recommendations.push('Start Ollama and install a model (e.g., ollama pull llama3.2)');
    }

    if (!backend.available) {
        recommendations.push('The BioDockify backend is not running - some features may be limited');
    }

    return {
        ollama,
        backend,
        recommendations
    };
}

/**
 * Check backend API status
 */
async function checkBackend(): Promise<ServiceStatus> {
    try {
        const API_BASE = typeof window !== 'undefined'
            ? (window as any).__BIODOCKIFY_API_URL__ || 'http://localhost:3000'
            : 'http://localhost:3000';
        const res = await fetch(`${API_BASE}/api/health`, {
            method: 'GET',
            signal: AbortSignal.timeout(3000)
        });

        return {
            name: 'Backend API',
            available: res.ok,
            url: API_BASE
        };
    } catch {
        return {
            name: 'Backend API',
            available: false,
            error: 'Cannot connect to backend'
        };
    }
}

/**
 * Auto-fix configuration based on detected issues
 */
export async function autoFixConfiguration(): Promise<{
    fixed: boolean;
    changes: string[];
}> {
    const changes: string[] = [];

    // Try to detect and fix Ollama
    const ollamaResult = await detectOllamaEnhanced();

    if (ollamaResult.available && ollamaResult.url) {
        // Save to localStorage for persistence
        if (typeof window !== 'undefined') {
            localStorage.setItem('biodockify_ollama_url', ollamaResult.url);
            if (ollamaResult.model) {
                localStorage.setItem('biodockify_ollama_model', ollamaResult.model);
            }
            changes.push(`Auto-configured Ollama URL: ${ollamaResult.url}`);
        }
    }

    return {
        fixed: changes.length > 0,
        changes
    };
}
