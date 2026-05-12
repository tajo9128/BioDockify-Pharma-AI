/**
 * BioDockify AI System Control Rules
 * 
 * Governs BioDockify AI's behavior during FIRST-RUN WIZARD MODE.
 * These rules are MANDATORY and override all other behaviors.
 * 
 * Authority: Highest (overrides convenience, speed, or verbosity)
 * Priority: Transparency → Safety → Stability → Intelligence
 */

// ============================================================================
// RULE 1: System State Detection
// ============================================================================

// ============================================================================
// RULE 1: System State Detection
// ============================================================================

export interface SystemState {
    first_run: boolean;
    config_missing: boolean;
    wizard_mode: boolean;
    services: {
        ollama_installed: boolean;
        ollama_running: boolean;
        ollama_models: string[];
        disk_space_ok: boolean;
        internet_available: boolean;
    };
    consent: {
        auto_start_ollama: boolean;
        auto_start_neo4j: boolean;
        remember_choice: boolean;
    };
    mode: 'LIMITED' | 'FULL';
}

export const DEFAULT_SYSTEM_STATE: SystemState = {
    first_run: true,
    config_missing: true,
    wizard_mode: false,
    services: {
        ollama_installed: false,
        ollama_running: false,
        ollama_models: [],
        disk_space_ok: true,
        internet_available: false
    },
    consent: {
        auto_start_ollama: true,
        auto_start_neo4j: true,
        remember_choice: false
    },
    mode: 'LIMITED'
};

// ============================================================================
// RULE 2: Mode Detection
// ============================================================================

export function shouldEnterWizardMode(state: SystemState): boolean {
    return state.first_run || state.config_missing;
}

export function isWizardMode(state: SystemState): boolean {
    return state.wizard_mode;
}

// ============================================================================
// RULE 3: Environment Scan Results (Read-Only)
// ============================================================================

export interface ScanResult {
    name: string;
    status: 'ok' | 'warning' | 'error';
    message: string;
    required: boolean;
}

export function formatScanResults(state: SystemState): ScanResult[] {
    return [
        {
            name: 'Ollama Installed',
            status: state.services.ollama_installed ? 'ok' : 'warning',
            message: state.services.ollama_installed ? 'Found' : 'Not installed',
            required: false
        },
        {
            name: 'LM Studio Running',
            status: state.services.ollama_running ? 'ok' : 'warning',
            message: state.services.ollama_running
                ? `Running (Port 1234)`
                : 'Not running',
            required: false
        },
        {
            name: 'Disk Space',
            status: state.services.disk_space_ok ? 'ok' : 'error',
            message: state.services.disk_space_ok ? 'Sufficient' : 'Low disk space',
            required: true
        }
    ];
}

// ============================================================================
// RULE 4: Consent Management
// ============================================================================

export interface ConsentRequest {
    id: keyof SystemState['consent'];
    label: string;
    description: string;
    granted: boolean;
}

export function getConsentRequests(state: SystemState): ConsentRequest[] {
    return [
        {
            id: 'auto_start_ollama',
            label: 'Allow BioDockify to check LM Studio availability',
            description: 'We will verify connection to local AI automatically.',
            granted: state.consent.auto_start_ollama
        },
        {
            id: 'auto_start_ollama',
            label: 'Auto-start Ollama (Local AI Engine)',
            description: 'Required for fast local reasoning without cloud APIs.',
            granted: state.consent.auto_start_ollama
        },
        {
            id: 'auto_start_neo4j',
            label: 'Auto-start Knowledge Engine (SurfSense)',
            description: 'Required for advanced pharma graph research.',
            granted: state.consent.auto_start_neo4j
        },
        {
            id: 'remember_choice',
            label: 'Remember my choice',
            description: 'Save these preferences for future sessions.',
            granted: state.consent.remember_choice
        }
    ];
}

// ============================================================================
// RULE 5: Guided Setup (No Autonomy)
// ============================================================================

export interface SetupGuidance {
    component: string;
    needed: boolean;
    reason: string;
    downloadUrl: string;
    canSkip: boolean;
    skipConsequences: string[];
}

export function getSetupGuidance(): SetupGuidance[] {
    return [
        {
            component: 'LM Studio',
            needed: true,
            reason: 'Required for local AI reasoning and research assistance.',
            downloadUrl: 'https://lmstudio.ai/download',
            canSkip: true,
            skipConsequences: [
                'AI reasoning will be disabled',
                'Research assistant features unavailable',
                'Document summarization disabled'
            ]
        }
    ];
}

// ============================================================================
// RULE 6: Safe-Mode Declaration
// ============================================================================

export interface SystemModeDeclaration {
    mode: 'LIMITED' | 'FULL';
    title: string;
    capabilities: {
        feature: string;
        enabled: boolean;
    }[];
}

export function getSystemModeDeclaration(state: SystemState): SystemModeDeclaration {
    // FULL MODE requires: LM Studio running + Internet available
    const hasOllama = state.services.ollama_running;
    const hasInternet = state.services.internet_available;
    const isFullMode = hasOllama && hasInternet;

    return {
        mode: isFullMode ? 'FULL' : 'LIMITED',
        title: isFullMode ? 'Full Mode Active - All Features Enabled' : 'Limited Mode Active',
        capabilities: [
            // AI Reasoning (requires LM Studio)
            { feature: 'AI reasoning', enabled: hasOllama },
            { feature: 'Research assistant', enabled: hasOllama },
            { feature: 'Document analysis', enabled: hasOllama },
            { feature: 'Experiment suggestions', enabled: hasOllama },

            // Internet Features (requires Internet)
            { feature: 'Literature search', enabled: hasInternet },
            { feature: 'PubMed integration', enabled: hasInternet },
            { feature: 'ChEMBL database', enabled: hasInternet },
            { feature: 'UniProt queries', enabled: hasInternet },

            // Core Features (always available)
            { feature: 'File reading', enabled: true },
            { feature: 'PDF processing', enabled: true },
            { feature: 'Local knowledge base', enabled: true },

            // Full Potential Features (requires both)
            { feature: 'Real-time research', enabled: isFullMode },
            { feature: 'Auto-citation', enabled: isFullMode },
            { feature: 'Cross-database analysis', enabled: isFullMode }
        ]
    };
}

// ============================================================================
// RULE 7: Configuration Commit (Atomic)
// ============================================================================

export interface ConfigCommitResult {
    success: boolean;
    error?: string;
}

export async function commitConfiguration(
    state: SystemState,
    saveConfig: (config: any) => Promise<boolean>
): Promise<ConfigCommitResult> {
    // Only commit after user confirmation
    const config = {
        first_run: false,
        consent: state.consent,
        services: {
            ollama_url: state.services.ollama_running ? 'http://localhost:11434' : '',
            ollama_enabled: state.consent.auto_start_ollama
        },
        mode: state.mode
    };

    try {
        const success = await saveConfig(config);
        if (!success) {
            return { success: false, error: 'Configuration save failed. Please try again.' };
        }
        return { success: true };
    } catch (e) {
        return {
            success: false,
            error: 'Unable to save configuration. Please check disk permissions.'
        };
    }
}

// ============================================================================
// RULE 8: Post-Wizard Verification
// ============================================================================

export interface VerificationResult {
    allPassed: boolean;
    checks: {
        name: string;
        passed: boolean;
        message: string;
    }[];
}

export async function verifyPostWizard(
    state: SystemState,
    checkOllama: () => Promise<boolean>
): Promise<VerificationResult> {
    const checks: { name: string; passed: boolean; message: string }[] = [];

    // Only verify services that were enabled
    if (state.consent.auto_start_ollama || state.services.ollama_running) {
        const ollamaOk = await checkOllama();
        checks.push({
            name: 'Ollama Connection',
            passed: ollamaOk,
            message: ollamaOk ? 'Reachable' : 'Not reachable'
        });
    }

    return {
        allPassed: checks.every(c => c.passed),
        checks
    };
}

// ============================================================================
// RULE 9: Handover Message
// ============================================================================

export function getHandoverMessage(state: SystemState): string {
    const mode = getSystemModeDeclaration(state);
    const hasOllama = state.services.ollama_running;
    const hasInternet = state.services.internet_available;

    if (mode.mode === 'FULL') {
        return 'BioDockify is now running at FULL POTENTIAL. All AI reasoning, research databases, and real-time features are active.';
    } else if (hasOllama && !hasInternet) {
        return 'BioDockify is ready with Local AI. Internet features (PubMed, ChEMBL, UniProt) are unavailable.';
    } else if (!hasOllama && hasInternet) {
        return 'BioDockify is ready with Internet access. AI reasoning features require LM Studio.';
    } else {
        const disabled = mode.capabilities
            .filter(c => !c.enabled)
            .map(c => c.feature)
            .slice(0, 5)
            .join(', ');
        return `BioDockify is in Limited Mode. Unavailable: ${disabled}`;
    }
}

// ============================================================================
// RULE 10: One-Time Execution Check
// ============================================================================

export function hasCompletedFirstRun(): boolean {
    if (typeof window === 'undefined') return false;
    return localStorage.getItem('biodockify_first_run_complete') === 'true';
}

export function markFirstRunComplete(): void {
    if (typeof window !== 'undefined') {
        localStorage.setItem('biodockify_first_run_complete', 'true');
    }
}

export function resetFirstRun(): void {
    if (typeof window !== 'undefined') {
        localStorage.removeItem('biodockify_first_run_complete');
    }
}

// ============================================================================
// RULE 11: Error Transparency (Plain Language)
// ============================================================================

export function formatErrorMessage(error: Error | string): string {
    const messages: Record<string, string> = {
        'ECONNREFUSED': 'Unable to connect. The service may not be running.',
        'ETIMEDOUT': 'Connection timed out. Please check your network.',
        'ENOTFOUND': 'Service not found. Please verify the address.',
        'NetworkError': 'Network issue detected. Please check your connection.',
    };

    const errorStr = typeof error === 'string' ? error : error.message;

    for (const [key, msg] of Object.entries(messages)) {
        if (errorStr.includes(key)) {
            return msg;
        }
    }

    return 'An unexpected issue occurred. Please try again.';
}

// ============================================================================
// RULE 12: Prohibited Actions Enforcement
// ============================================================================

export interface WizardModeRestrictions {
    allowAIReasoning: boolean;
    allowMemoryWrites: boolean;
    allowResearchQuestions: boolean;
    allowExperimentSuggestions: boolean;
    allowInternetWithoutConsent: boolean;
    allowUserDataStorage: boolean;
}

export function getWizardModeRestrictions(): WizardModeRestrictions {
    return {
        allowAIReasoning: false,
        allowMemoryWrites: false,
        allowResearchQuestions: false,
        allowExperimentSuggestions: false,
        allowInternetWithoutConsent: false,
        allowUserDataStorage: false
    };
}

// ============================================================================
// FINAL ANTIGRAVITY OVERRIDE
// ============================================================================

export const PRIORITY_ORDER = ['Transparency', 'Safety', 'Stability', 'Intelligence'] as const;

export function resolveConflict(
    options: { option: string; category: typeof PRIORITY_ORDER[number] }[]
): string {
    const sorted = [...options].sort((a, b) => {
        return PRIORITY_ORDER.indexOf(a.category) - PRIORITY_ORDER.indexOf(b.category);
    });
    return sorted[0].option;
}

