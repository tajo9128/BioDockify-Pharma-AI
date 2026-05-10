/**
 * BackendInitializer Component
 * 
 * Automatically starts and monitors backend services when the app loads.
 * Shows a loading screen until all services are ready.
 */

import React, { useEffect, useState, useCallback } from 'react';
import { Loader2, Server, CheckCircle2, AlertCircle, RefreshCw } from 'lucide-react';

interface ServiceStatus {
    backend: 'checking' | 'starting' | 'running' | 'error';
    ollama: 'checking' | 'running' | 'not_configured' | 'error';
    message: string;
}

interface BackendInitializerProps {
    children: React.ReactNode;
    /** Skip initialization (for testing/dev) */
    skipInit?: boolean;
    /** Timeout in ms before giving up */
    timeout?: number;
}

const API_BASE = '';
const MAX_RETRIES = 30; // 30 retries * 2s = 60s max wait
const RETRY_INTERVAL = 2000; // 2 seconds

/**
 * Check if backend API is running
 */
async function checkBackendHealth(): Promise<boolean> {
    try {
        const res = await fetch(`${API_BASE}/api/health`, {
            method: 'GET',
            signal: AbortSignal.timeout(3000)
        });
        return res.ok;
    } catch {
        return false;
    }
}

/**
 * Check if Ollama is available
 */
async function checkOllama(): Promise<boolean> {
    try {
        const res = await fetch('http://localhost:11434/api/tags', {
            method: 'GET',
            signal: AbortSignal.timeout(3000)
        });
        if (res.ok) {
            const data = await res.json();
            return (data.models || []).length > 0;
        }
        return false;
    } catch {
        return false;
    }
}

/**
 * Try to start backend using Tauri shell (only works in Tauri context)
 * [DEPRECATED] - Docker manages services now.
 */
async function tryStartBackend(): Promise<boolean> {
    console.log('[BackendInitializer] Service management is handled by Docker container.');
    return false;
}

export const BackendInitializer: React.FC<BackendInitializerProps> = ({
    children,
    skipInit = false,
    timeout = 60000
}) => {
    const [status, setStatus] = useState<ServiceStatus>({
        backend: 'checking',
        ollama: 'checking',
        message: 'Checking services...'
    });
    const [isReady, setIsReady] = useState(skipInit);
    const [retryCount, setRetryCount] = useState(0);
    const [startAttempted, setStartAttempted] = useState(false);

    const initializeServices = useCallback(async () => {
        console.log('[BackendInitializer] Starting initialization...');

        // Check backend health
        const backendRunning = await checkBackendHealth();

        if (backendRunning) {
            console.log('[BackendInitializer] Backend is running!');

            // Check LM Studio 
            const ollamaRunning = await checkOllama();

            setStatus({
                backend: 'running',
                ollama: ollamaRunning ? 'running' : 'not_configured',
                message: 'All services ready!'
            });

            // Check if First-Run is needed
            const firstRunDone = localStorage.getItem('biodockify_first_run_complete') === 'true';
            if (!firstRunDone) {
                console.log('[BackendInitializer] First-run setup required.');
                // We'll let the App component handle showing the wizard based on this state
            }

            setIsReady(true);
            return;
        }

        // Backend not running - we wait for the sidecar (started by Rust/Tauri)
        if (!startAttempted) {
            setStatus(s => ({
                ...s,
                backend: 'starting',
                message: 'Waiting for BioDockify Engine...'
            }));
            setStartAttempted(true);

            // In production, the Rust sidecar handles the launch.
            // We just wait and retry health checks.
            console.log('[BackendInitializer] Waiting for Tauri Sidecar to initialize...');
        }

        // Retry after interval
        if (retryCount < MAX_RETRIES) {
            setRetryCount(c => c + 1);
            setStatus(s => ({
                ...s,
                message: `Waiting for backend... (${retryCount + 1}/${MAX_RETRIES})`
            }));
        } else {
            setStatus({
                backend: 'error',
                ollama: 'not_configured',
                message: 'Backend startup timeout. Please start manually.'
            });
        }
    }, [retryCount, startAttempted]);

    useEffect(() => {
        if (skipInit || isReady) return;

        initializeServices();

        // Retry timer
        const timer = setInterval(() => {
            if (!isReady && retryCount < MAX_RETRIES) {
                initializeServices();
            }
        }, RETRY_INTERVAL);

        return () => clearInterval(timer);
    }, [skipInit, isReady, retryCount, initializeServices]);

    // Manual retry
    const handleRetry = () => {
        setRetryCount(0);
        setStartAttempted(false);
        setStatus({
            backend: 'checking',
            ollama: 'checking',
            message: 'Retrying...'
        });
    };

    // If ready, render children
    if (isReady) {
        return <>{children}</>;
    }

    // Loading/startup screen
    return (
        <div className="min-h-screen bg-slate-900 flex flex-col items-center justify-center p-4 text-white">
            <div className="max-w-md w-full space-y-6 text-center">
                {/* Logo */}
                <div className="space-y-3">
                    <div className="flex justify-center mb-4">
                        <div className="relative w-16 h-16 rounded-2xl overflow-hidden shadow-lg border border-white/10">
                            {/* @ts-ignore */}
                            <img src="/logo.png" alt="BioDockify" className="w-full h-full object-cover" />
                        </div>
                    </div>
                    <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent">
                        BioDockify
                    </h1>
                    <p className="text-slate-400">
                        Initializing Research Platform...
                    </p>
                </div>

                {/* Status Card */}
                <div className="bg-slate-800 p-6 rounded-2xl border border-slate-700">
                    <div className="space-y-4">
                        {/* Backend Status */}
                        <div className="flex items-center justify-between">
                            <span className="text-slate-300">Backend API</span>
                            <StatusIcon status={status.backend} />
                        </div>

                        {/* LM Studio Status */}
                        <div className="flex items-center justify-between">
                            <span className="text-slate-300">LM Studio</span>
                            <StatusIcon status={status.ollama} />
                        </div>

                        {/* Divider */}
                        <div className="border-t border-slate-700" />

                        {/* Message */}
                        <p className="text-sm text-slate-400">
                            {status.message}
                        </p>

                        {/* Progress or Retry */}
                        {status.backend === 'error' ? (
                            <button
                                onClick={handleRetry}
                                className="w-full py-2 px-4 bg-blue-600 hover:bg-blue-500 rounded-lg flex items-center justify-center gap-2 transition"
                            >
                                <RefreshCw size={16} />
                                Retry
                            </button>
                        ) : (
                            <div className="flex items-center justify-center gap-2 text-blue-400">
                                <Loader2 className="animate-spin" size={20} />
                                <span className="text-sm">Please wait...</span>
                            </div>
                        )}
                    </div>
                </div>

                {/* Manual Instructions */}
                {status.backend === 'error' && (
                    <div className="text-left bg-amber-900/20 border border-amber-700/50 p-4 rounded-lg">
                        <p className="text-amber-400 text-sm font-medium mb-2">
                            Manual Start Instructions:
                        </p>
                        <code className="block text-xs text-slate-300 bg-slate-950 p-2 rounded">
                            cd &quot;BioDockify- Pharma Research AI&quot;<br />
                            .venv\Scripts\python.exe server.py
                        </code>
                    </div>
                )}
            </div>
        </div>
    );
};

// Helper component for status icons
const StatusIcon: React.FC<{ status: string }> = ({ status }) => {
    switch (status) {
        case 'running':
            return <CheckCircle2 className="text-emerald-400" size={20} />;
        case 'checking':
        case 'starting':
            return <Loader2 className="text-blue-400 animate-spin" size={20} />;
        case 'not_configured':
            return <span className="text-slate-500 text-sm">Optional</span>;
        case 'error':
            return <AlertCircle className="text-red-400" size={20} />;
        default:
            return <span className="text-slate-500">-</span>;
    }
};

export default BackendInitializer;
