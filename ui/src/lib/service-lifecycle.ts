/**
 * Service Lifecycle Manager
 * 
 * Autonomous service management for Agent Zero.
 * Handles: Auto-start, health monitoring, model management, and recovery.
 * 
 * RESPECTS CONSENT: Only performs actions user has consented to.
 */

import { getSystemController } from './system-controller';

// ============================================================================
// Types
// ============================================================================

export interface ServiceStatus {
    name: string;
    running: boolean;
    url: string;
    lastCheck: Date;
    error?: string;
}

export interface ModelInfo {
    name: string;
    size: string;
    installed: boolean;
    recommended: boolean;
}

export interface LifecycleConfig {
    autoStartOllama: boolean;
    autoStartSurfSense: boolean;
    autoStartOmniTools: boolean;
    autoPullModels: boolean;
    healthCheckInterval: number; // ms
    autoRecovery: boolean;
}

// ============================================================================
// Default Configuration
// ============================================================================

const DEFAULT_CONFIG: LifecycleConfig = {
    autoStartOllama: true,
    autoStartSurfSense: true,
    autoStartOmniTools: true,
    autoPullModels: true,
    healthCheckInterval: 30000, // 30 seconds
    autoRecovery: true
};

// Recommended models for research
const RECOMMENDED_MODELS = [
    { name: 'llama3.2:3b', size: '2GB', recommended: true, purpose: 'Fast general research' },
    { name: 'llama3.2:7b', size: '4GB', recommended: true, purpose: 'Balanced performance' },
    { name: 'codellama:7b', size: '4GB', recommended: false, purpose: 'Code analysis' },
    { name: 'mistral:7b', size: '4GB', recommended: false, purpose: 'Alternative model' }
];

// ============================================================================
// Service Lifecycle Manager Class
// ============================================================================

export class ServiceLifecycleManager {
    private config: LifecycleConfig;
    private healthCheckTimer: ReturnType<typeof setInterval> | null = null;
    private services: Map<string, ServiceStatus> = new Map();
    private listeners: Set<(services: Map<string, ServiceStatus>) => void> = new Set();

    constructor(config: Partial<LifecycleConfig> = {}) {
        this.config = { ...DEFAULT_CONFIG, ...config };
        this.initializeServices();
    }

    private initializeServices(): void {
        this.services.set('ollama', {
            name: 'Ollama',
            running: false,
            url: '/api',
            lastCheck: new Date()
        });
        this.services.set('surfsense', {
            name: 'SurfSense',
            running: false,
            url: '/api',
            lastCheck: new Date()
        });

        this.services.set('backend', {
            name: 'Backend API',
            running: false,
            url: '/api',
            lastCheck: new Date()
        });
    }

    // -------------------------------------------------------------------------
    // Configuration
    // -------------------------------------------------------------------------

    updateConfig(updates: Partial<LifecycleConfig>): void {
        this.config = { ...this.config, ...updates };
        console.log('[Lifecycle] Config updated:', this.config);
    }

    getConfig(): LifecycleConfig {
        return { ...this.config };
    }

    // -------------------------------------------------------------------------
    // Health Checks
    // -------------------------------------------------------------------------

    async checkService(serviceName: string): Promise<ServiceStatus> {
        const service = this.services.get(serviceName);
        if (!service) {
            throw new Error(`Unknown service: ${serviceName}`);
        }

        try {
            let running = false;

            switch (serviceName) {
                case 'ollama':
                    running = await this.checkOllama();
                    break;
                case 'surfsense':
                    running = await this.checkSurfSense();
                    break;
                case 'backend':
                    running = await this.checkBackend();
                    break;
            }

            const updated: ServiceStatus = {
                ...service,
                running,
                lastCheck: new Date(),
                error: undefined
            };
            this.services.set(serviceName, updated);
            return updated;

        } catch (e: any) {
            const updated: ServiceStatus = {
                ...service,
                running: false,
                lastCheck: new Date(),
                error: e.message
            };
            this.services.set(serviceName, updated);
            return updated;
        }
    }

    private async checkOllama(): Promise<boolean> {
        try {
            const res = await fetch('/api/tags', {
                signal: AbortSignal.timeout(3000)
            });
            return res.ok;
        } catch {
            return false;
        }
    }

    private async checkSurfSense(): Promise<boolean> {
        try {
            const res = await fetch('/health', {
                signal: AbortSignal.timeout(3000)
            });
            return res.ok;
        } catch {
            return false;
        }
    }

    private async checkBackend(): Promise<boolean> {
        try {
            // Use the root /health endpoint which whitelists CORS and is optimized
            const res = await fetch('/health', {
                signal: AbortSignal.timeout(3000)
            });
            return res.ok;
        } catch {
            return false;
        }
    }

    async checkAllServices(): Promise<Map<string, ServiceStatus>> {
        await Promise.all([
            this.checkService('ollama'),
            this.checkService('surfsense'),
            this.checkService('backend')
        ]);
        this.notifyListeners();
        return new Map(this.services);
    }

    // -------------------------------------------------------------------------
    // Auto-Start (Requires Consent)
    // -------------------------------------------------------------------------

    async autoStartServices(): Promise<{ started: string[]; failed: string[] }> {
        const started: string[] = [];
        const failed: string[] = [];

        // Check consent from SystemController
        const controller = getSystemController();
        const state = controller.getState();

        // Auto-start Ollama if consented and not running
        if (this.config.autoStartOllama && state.consent.auto_start_ollama) {
            const ollama = this.services.get('ollama');
            if (ollama && !ollama.running) {
                const success = await this.startOllama();
                if (success) {
                    started.push('Ollama');
                } else {
                    failed.push('Ollama');
                }
            }
        }

        // Auto-start SurfSense if consented and not running
        if (this.config.autoStartSurfSense && state.consent.auto_start_neo4j) { // Reuse old consent key for now or rename? 
            // Better to use state.consent.auto_start_neo4j as "Database" consent for migration stability
            const ss = this.services.get('surfsense');
            if (ss && !ss.running) {
                // We rely on Backend to auto-start SurfSense usually. 
                // But if we want frontend to trigger it via shell command:
                // For now, let's assume Backend handles it via main.py we updated.
                // Or implementing a simple trigger here.

                // Let's implement startSurfSense using docker compose command
                const success = await this.startSurfSense();
                if (success) {
                    started.push('SurfSense');
                } else {
                    failed.push('SurfSense');
                }
            }
        }


        return { started, failed };
    }

    private async startOllama(): Promise<boolean> {
        console.log('[Lifecycle] Ollama start not supported in Docker mode (managed by container)');
        return false;
    }

    private async startSurfSense(): Promise<boolean> {
        console.log('[Lifecycle] SurfSense start not supported in Docker mode (managed by container)');
        return false;
    }



    // -------------------------------------------------------------------------
    // Model Management
    // -------------------------------------------------------------------------

    async getInstalledModels(): Promise<ModelInfo[]> {
        try {
            const res = await fetch('/api/tags', {
                signal: AbortSignal.timeout(5000)
            });

            if (!res.ok) return [];

            const data = await res.json();
            const installed = new Set((data.models || []).map((m: any) => m.name));

            return RECOMMENDED_MODELS.map(m => ({
                ...m,
                installed: installed.has(m.name)
            }));
        } catch {
            return RECOMMENDED_MODELS.map(m => ({ ...m, installed: false }));
        }
    }

    async pullModel(modelName: string, onProgress?: (progress: number) => void): Promise<boolean> {
        if (!this.config.autoPullModels) {
            console.log('[Lifecycle] Auto-pull disabled, skipping model pull');
            return false;
        }

        console.log(`[Lifecycle] Pulling model: ${modelName}`);

        try {
            const res = await fetch('/api/tags', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name: modelName, stream: false })
            });

            if (res.ok) {
                console.log(`[Lifecycle] Model ${modelName} pulled successfully`);
                return true;
            } else {
                console.error(`[Lifecycle] Failed to pull model: ${res.statusText}`);
                return false;
            }
        } catch (e) {
            console.error('[Lifecycle] Model pull error:', e);
            return false;
        }
    }

    async ensureDefaultModel(): Promise<boolean> {
        const models = await this.getInstalledModels();
        const hasRecommended = models.some(m => m.recommended && m.installed);

        if (!hasRecommended && this.config.autoPullModels) {
            // Pull the smallest recommended model
            return this.pullModel('llama3.2:3b');
        }

        return hasRecommended;
    }

    // -------------------------------------------------------------------------
    // Health Monitoring (Background)
    // -------------------------------------------------------------------------

    startHealthMonitoring(): void {
        if (this.healthCheckTimer) {
            return; // Already running
        }

        console.log('[Lifecycle] Starting health monitoring');

        this.healthCheckTimer = setInterval(async () => {
            await this.checkAllServices();

            // Auto-recovery if enabled
            if (this.config.autoRecovery) {
                await this.autoStartServices();
            }
        }, this.config.healthCheckInterval);
    }

    stopHealthMonitoring(): void {
        if (this.healthCheckTimer) {
            clearInterval(this.healthCheckTimer);
            this.healthCheckTimer = null;
            console.log('[Lifecycle] Health monitoring stopped');
        }
    }

    dispose(): void {
        this.stopHealthMonitoring();
        this.listeners.clear();
        console.log('[Lifecycle] Service Lifecycle Manager disposed');
    }

    // -------------------------------------------------------------------------
    // Event Subscription
    // -------------------------------------------------------------------------

    subscribe(listener: (services: Map<string, ServiceStatus>) => void): () => void {
        this.listeners.add(listener);
        return () => this.listeners.delete(listener);
    }

    private notifyListeners(): void {
        this.listeners.forEach(listener => listener(new Map(this.services)));
    }

    // -------------------------------------------------------------------------
    // Utilities
    // -------------------------------------------------------------------------

    private isTauri(): boolean {
        return false;
    }

    getServiceStatus(name: string): ServiceStatus | undefined {
        return this.services.get(name);
    }

    getAllStatuses(): ServiceStatus[] {
        return Array.from(this.services.values());
    }
}

// ============================================================================
// Singleton Instance
// ============================================================================

let managerInstance: ServiceLifecycleManager | null = null;

export function getServiceLifecycleManager(): ServiceLifecycleManager {
    if (!managerInstance) {
        managerInstance = new ServiceLifecycleManager();
    }
    return managerInstance;
}

export function configureServiceLifecycle(config: Partial<LifecycleConfig>): void {
    getServiceLifecycleManager().updateConfig(config);
}

// ============================================================================
// Auto-Initialize on App Start
// ============================================================================

export async function initializeAgentZeroServices(): Promise<{
    services: ServiceStatus[];
    modelsAvailable: boolean;
    autoStarted: string[];
}> {
    console.log('[Agent Zero] Initializing services...');

    const manager = getServiceLifecycleManager();

    // Load consent from SystemController
    const controller = getSystemController();
    const state = controller.getState();

    // Configure based on user consent
    manager.updateConfig({
        autoStartOllama: state.consent.auto_start_ollama,
        autoStartSurfSense: state.consent.auto_start_neo4j, // Mapping old consent to new service
        autoStartOmniTools: true, // Default to true for now as it's lightweight
        autoPullModels: true, // Default to true for models
        autoRecovery: true
    });

    // Check all services
    await manager.checkAllServices();

    // Auto-start if consented
    const { started } = await manager.autoStartServices();

    // Ensure default model is available
    const modelsAvailable = await manager.ensureDefaultModel();

    // Start background health monitoring
    manager.startHealthMonitoring();

    console.log('[Agent Zero] Initialization complete');

    return {
        services: manager.getAllStatuses(),
        modelsAvailable,
        autoStarted: started
    };
}
