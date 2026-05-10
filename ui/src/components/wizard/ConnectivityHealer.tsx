/**
 * ConnectivityHealer Component
 * 
 * Smart connectivity repair UI for the First-Run Wizard.
 * Automatically detects and attempts to resolve connection issues:
 * - Internet connectivity
 * - LM Studio (with auto-start)
 * - Backend health
 * 
 * Note: API keys are configured later in Settings.
 */

'use client';

import React, { useState, useEffect, useCallback } from 'react';
import {
    Wifi, WifiOff, Brain, Server,
    RefreshCcw, Check, XCircle, AlertTriangle,
    Loader2, Play, ExternalLink
} from 'lucide-react';

interface ConnectionCheck {
    name: string;
    status: 'pending' | 'checking' | 'success' | 'warning' | 'error';
    message: string;
    details?: Record<string, any>;
    can_auto_repair?: boolean;
    repair_action?: string;
}

interface DiagnosisResult {
    status: 'healthy' | 'degraded' | 'offline';
    checks: ConnectionCheck[];
    repair_actions: string[];
    can_proceed: boolean;
}

interface ConnectivityHealerProps {
    onComplete: (result: DiagnosisResult) => void;
    onSkip: () => void;
}

export default function ConnectivityHealer({ onComplete, onSkip }: ConnectivityHealerProps) {
    const [checks, setChecks] = useState<ConnectionCheck[]>([
        { name: 'Internet Connectivity', status: 'pending', message: 'Waiting...' },
        { name: 'LM Studio', status: 'pending', message: 'Waiting...' },
    ]);
    const [overallStatus, setOverallStatus] = useState<'healthy' | 'degraded' | 'offline' | null>(null);
    const [canProceed, setCanProceed] = useState(false);
    const [isRepairing, setIsRepairing] = useState(false);
    const [repairLog, setRepairLog] = useState<string[]>([]);
    const [isStartingOllama, setIsStartingOllama] = useState(false);

    // Run diagnosis on mount
    useEffect(() => {
        runDiagnosis();
    }, []);

    const addLog = (message: string) => {
        setRepairLog(prev => [...prev.slice(-4), `[${new Date().toLocaleTimeString()}] ${message}`]);
    };

    const runDiagnosis = async () => {
        addLog('Starting connectivity diagnosis...');
        setChecks(prev => prev.map(c => ({ ...c, status: 'checking' as const, message: 'Checking...' })));

        try {
            // Priority 1: Backend-driven diagnosis
            const res = await fetch('/api/diagnose/connectivity', {
                signal: AbortSignal.timeout(10000)
            });

            if (res.ok) {
                const report = await res.json();
                addLog(`Backend report: ${report.status}`);

                setChecks(report.checks);
                setOverallStatus(report.status);
                setCanProceed(report.can_proceed);

                if (report.status === 'healthy') {
                    addLog('All systems healthy via backend');
                } else {
                    addLog(`Systems ${report.status}. Issues: ${report.repair_actions.join(', ')}`);
                }
                return;
            }
        } catch (e) {
            addLog('Backend diagnosis unavailable, falling back to client-side checks');
        }

        // Fallback: Client-side checks (mostly for internet/LM local)
        await runClientSideChecks();
    };

    const runClientSideChecks = async () => {
        const newChecks: ConnectionCheck[] = [];

        // 1. Internet check
        try {
            addLog('Checking internet...');
            await fetch('https://www.google.com/favicon.ico', {
                mode: 'no-cors',
                signal: AbortSignal.timeout(5000)
            });
            newChecks.push({
                name: 'Internet Connectivity',
                status: 'success',
                message: 'Connected'
            });
        } catch {
            newChecks.push({
                name: 'Internet Connectivity',
                status: 'error',
                message: 'No internet connection',
                repair_action: 'Check your network connection'
            });
        }

        // 2. LM Studio check
        addLog('Checking LM Studio local probe...');
        const lmPorts = [1234, 1235, 8080];
        let lmFound = false;
        let lmDetails: Record<string, any> = {};

        for (const port of lmPorts) {
            try {
                const res = await fetch(`http://localhost:${port}/v1/models`, {
                    signal: AbortSignal.timeout(3000)
                });
                if (res.ok) {
                    const data = await res.json();
                    if (data.data?.length > 0) {
                        lmFound = true;
                        lmDetails = { port, model: data.data[0]?.id };
                        break;
                    }
                }
            } catch { /* Continue */ }
        }

        if (lmFound) {
            newChecks.push({
                name: 'LM Studio',
                status: 'success',
                message: `Connected (Port ${lmDetails.port})`,
                details: lmDetails
            });
        } else {
            newChecks.push({
                name: 'LM Studio',
                status: 'warning',
                message: 'Not detected locally',
                can_auto_repair: true,
                repair_action: 'Start LM Studio and Enable CORS'
            });
        }

        setChecks(newChecks);
        const hasError = newChecks.some(c => c.status === 'error');
        const hasWarning = newChecks.some(c => c.status === 'warning');

        setOverallStatus(hasError ? 'offline' : hasWarning ? 'degraded' : 'healthy');
        setCanProceed(!hasError);
        addLog('Client-side fallback diagnosis complete');
    };

    const handleStartOllama = async () => {
        setIsStartingOllama(true);
        addLog('Requesting backend to check Ollama...');

        try {
            const res = await fetch('/api/diagnose/ollama', {
                method: 'POST',
                signal: AbortSignal.timeout(15000)
            });

            const result = await res.json();

            if (result.success) {
                addLog('Ollama check acknowledged');

                // Update specific check status
                setChecks(prev => prev.map(c =>
                    c.name === 'Ollama' ? { ...c, status: 'checking', message: 'Checking...' } : c
                ));

                // Wait and verify
                for (let i = 1; i <= 8; i++) {
                    addLog(`Verifying Ollama... (${i * 5}s)`);
                    await new Promise(r => setTimeout(r, 5000));

                    const ollamaRes = await fetch('http://localhost:11434/api/tags').catch(() => null);
                    if (ollamaRes && ollamaRes.ok) {
                        addLog('Ollama responded!');
                        await runDiagnosis(); // Refresh everything
                        setIsStartingOllama(false);
                        return;
                    }
                }

                addLog('Ollama check complete, but no models found.');
            } else {
                addLog(`Check failed: ${result.message}`);
            }
        } catch (error) {
            addLog('Could not reach backend for check');
        }

        setIsStartingOllama(false);
        await runDiagnosis();
    };

    const handleRetry = async () => {
        setIsRepairing(true);
        addLog('Retrying all checks...');
        await runDiagnosis();
        setIsRepairing(false);
    };

    const handleProceed = () => {
        const result: DiagnosisResult = {
            status: overallStatus || 'degraded',
            checks,
            repair_actions: checks.filter(c => c.repair_action).map(c => c.repair_action!),
            can_proceed: canProceed
        };
        onComplete(result);
    };

    const getStatusIcon = (status: ConnectionCheck['status']) => {
        switch (status) {
            case 'pending':
                return <div className="w-5 h-5 rounded-full bg-slate-700" />;
            case 'checking':
                return <Loader2 className="w-5 h-5 text-sky-400 animate-spin" />;
            case 'success':
                return <Check className="w-5 h-5 text-emerald-400" />;
            case 'warning':
                return <AlertTriangle className="w-5 h-5 text-amber-400" />;
            case 'error':
                return <XCircle className="w-5 h-5 text-red-400" />;
        }
    };

    const getCheckIcon = (name: string) => {
        switch (name) {
            case 'Internet Connectivity':
                return <Wifi className="w-5 h-5 text-slate-400" />;
            case 'LM Studio':
                return <Brain className="w-5 h-5 text-slate-400" />;
            case 'Backend API':
                return <Server className="w-5 h-5 text-slate-400" />;
            default:
                return null;
        }
    };

    const allChecksComplete = checks.every(c => c.status !== 'pending' && c.status !== 'checking');
    const hasErrors = checks.some(c => c.status === 'error');
    const ollamaCheck = checks.find(c => c.name === 'Ollama');
    const showStartOllama = ollamaCheck &&
        (ollamaCheck.status === 'warning' || ollamaCheck.status === 'error') &&
        !isStartingOllama;

    return (
        <div className="space-y-6 animate-in slide-in-from-bottom-4 duration-500">
            <div className="text-center">
                <h2 className="text-xl font-bold text-white mb-2">
                    Establishing Connections
                </h2>
                <p className="text-slate-400 text-sm">
                    Verifying and repairing connectivity issues...
                </p>
            </div>

            {/* Check List */}
            <div className="space-y-3">
                {checks.map((check, idx) => (
                    <div
                        key={idx}
                        className="flex items-center justify-between p-4 bg-slate-900/50 border border-slate-800 rounded-lg transition-all"
                    >
                        <div className="flex items-center space-x-3">
                            {getCheckIcon(check.name)}
                            <div>
                                <span className="text-slate-200 font-medium block">
                                    {check.name}
                                </span>
                                <span className="text-sm text-slate-500">
                                    {check.message}
                                </span>
                            </div>
                        </div>
                        <div className="flex items-center space-x-2">
                            {check.details?.model && (
                                <span className="text-xs font-mono text-slate-500 bg-slate-800 px-2 py-1 rounded">
                                    {String(check.details.model).split('/').pop()}
                                </span>
                            )}
                            {getStatusIcon(check.status)}
                        </div>
                    </div>
                ))}
            </div>

            {/* Ollama Start Button */}
            {showStartOllama && (
                <div className="flex items-center justify-center space-x-3 p-4 bg-amber-500/10 border border-amber-500/30 rounded-lg">
                    <AlertTriangle className="w-5 h-5 text-amber-400" />
                    <span className="text-amber-300 text-sm">Ollama not running</span>
                    <button
                        onClick={handleStartOllama}
                        disabled={isStartingOllama}
                        className="flex items-center space-x-1 px-3 py-1.5 bg-amber-500 hover:bg-amber-400 text-slate-900 rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
                    >
                        <Play className="w-4 h-4" />
                        <span>Start Ollama</span>
                    </button>
                </div>
            )}

            {isStartingOllama && (
                <div className="flex items-center justify-center space-x-3 p-4 bg-sky-500/10 border border-sky-500/30 rounded-lg">
                    <Loader2 className="w-5 h-5 text-sky-400 animate-spin" />
                    <span className="text-sky-300 text-sm">Starting LM Studio...</span>
                </div>
            )}

            {/* Repair Log */}
            {repairLog.length > 0 && (
                <div className="p-3 bg-slate-900/30 border border-slate-800 rounded-lg">
                    <div className="text-xs font-mono text-slate-500 space-y-1 max-h-24 overflow-y-auto">
                        {repairLog.map((log, i) => (
                            <div key={i}>{log}</div>
                        ))}
                    </div>
                </div>
            )}

            {/* Overall Status */}
            {overallStatus && allChecksComplete && (
                <div className={`flex items-center justify-center space-x-2 p-3 rounded-lg ${overallStatus === 'healthy'
                    ? 'bg-emerald-500/10 border border-emerald-500/30'
                    : overallStatus === 'degraded'
                        ? 'bg-amber-500/10 border border-amber-500/30'
                        : 'bg-red-500/10 border border-red-500/30'
                    }`}>
                    {overallStatus === 'healthy' && <Check className="w-5 h-5 text-emerald-400" />}
                    {overallStatus === 'degraded' && <AlertTriangle className="w-5 h-5 text-amber-400" />}
                    {overallStatus === 'offline' && <XCircle className="w-5 h-5 text-red-400" />}
                    <span className={`font-medium ${overallStatus === 'healthy'
                        ? 'text-emerald-300'
                        : overallStatus === 'degraded'
                            ? 'text-amber-300'
                            : 'text-red-300'
                        }`}>
                        {overallStatus === 'healthy' && 'All systems operational'}
                        {overallStatus === 'degraded' && 'System operational with warnings'}
                        {overallStatus === 'offline' && 'Critical issues detected'}
                    </span>
                </div>
            )}

            {/* Action Buttons */}
            <div className="flex items-center justify-center space-x-4 pt-2">
                <button
                    onClick={handleRetry}
                    disabled={isRepairing || isStartingOllama}
                    className="flex items-center space-x-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg transition-colors disabled:opacity-50"
                >
                    <RefreshCcw className={`w-4 h-4 ${isRepairing ? 'animate-spin' : ''}`} />
                    <span>Retry All</span>
                </button>

                <button
                    onClick={handleProceed}
                    disabled={isStartingOllama /* Always allow proceed unless busy starting */}
                    className={`flex items-center space-x-2 px-6 py-2 rounded-lg font-semibold transition-colors disabled:opacity-50 ${hasErrors
                        ? 'bg-amber-600 hover:bg-amber-500 text-white'
                        : 'bg-teal-500 hover:bg-teal-400 text-slate-900'
                        }`}
                >
                    <Check className="w-4 h-4" />
                    <span>
                        {hasErrors ? 'Continue to Settings' : 'Continue'}
                    </span>
                </button>

                {hasErrors && !canProceed && (
                    <button
                        onClick={onSkip}
                        className="text-slate-500 hover:text-slate-300 text-sm transition-colors"
                    >
                        Skip (Offline Mode)
                    </button>
                )}
            </div>
        </div>
    );
}
