/**
 * Diagnosis & Repair Dialog
 * 
 * Implements the UI for BioDockify AI Self-Repair Workflow.
 * Enforces the strict "Ask First" protocol.
 * 
 * Flow:
 * 1. Intro (Consent to Diagnose)
 * 2. Scaning (Read-only)
 * 3. Report & Plan (Consent to Repair)
 * 4. Cleaning/Repairing
 * 5. Summary
 */

'use client';

import React, { useState } from 'react';
import {
    Activity,
    AlertTriangle,
    CheckCircle,
    Cpu,
    Database,
    Shield,
    XOctagon,
    ArrowRight,
    RefreshCw
} from 'lucide-react';
import { DiagnosticEngine, DiagnosticReport } from '@/lib/diagnostics';
import { RepairManager, RepairPlan, RepairResult } from '@/lib/repair-system';

interface DiagnosisDialogProps {
    isOpen: boolean;
    onClose: () => void;
}

type WizardStep = 'intro' | 'scanning' | 'report' | 'repairing' | 'summary';

interface ProgressItem {
    name: string;
    status: 'pending' | 'checking' | 'done' | 'error';
}

export default function DiagnosisDialog({ isOpen, onClose }: DiagnosisDialogProps) {
    const [step, setStep] = useState<WizardStep>('intro');
    const [report, setReport] = useState<DiagnosticReport | null>(null);
    const [plan, setPlan] = useState<RepairPlan | null>(null);
    const [result, setResult] = useState<RepairResult | null>(null);

    // Real-time progress tracking
    const [progressItems, setProgressItems] = useState<ProgressItem[]>([]);
    const [currentAction, setCurrentAction] = useState<string>('');
    const [repairProgress, setRepairProgress] = useState<{ current: number, total: number }>({ current: 0, total: 0 });

    // Services
    const diagnosticEngine = DiagnosticEngine.getInstance();
    const repairManager = RepairManager.getInstance();

    if (!isOpen) return null;

    // ------------------------------------------------------------------------
    // Step Actions
    // ------------------------------------------------------------------------

    const startDiagnosis = async () => {
        setStep('scanning');

        // 1. Determine active configuration
        let aiMode = 'auto';
        if (typeof window !== 'undefined') {
            try {
                const saved = localStorage.getItem('biodockify_ai_config');
                if (saved) {
                    const conf = JSON.parse(saved);
                    aiMode = conf.mode || 'auto';
                }
            } catch (e) { }
        }

        // 2. Define relevant services to check
        const services = [
            { name: 'Backend API', key: 'backend' },
            { name: 'System Integrity', key: 'system' }
        ];

        // Conditional Checks based on Mode
        const checkOllama = (aiMode === 'ollama' || aiMode === 'auto');
        const checkBackend = aiMode !== 'ollama' && aiMode !== 'z-ai';
        const checkSurfSense = aiMode !== 'ollama' && aiMode !== 'z-ai';
        
        if (checkOllama) services.push({ name: 'Ollama', key: 'ollama' });
        if (checkSurfSense) services.push({ name: 'Knowledge Engine', key: 'surfsense' });

        // Initialize progress items
        setProgressItems(services.map(s => ({ name: s.name, status: 'pending' })));

        // Simulate step-by-step checking with visual feedback
        for (let i = 0; i < services.length; i++) {
            setCurrentAction(`Checking ${services[i].name}...`);
            setProgressItems(prev => prev.map((item, idx) =>
                idx === i ? { ...item, status: 'checking' } : item
            ));

            // Wait a bit for visual feedback
            await new Promise(r => setTimeout(r, 600));

            // Provisional "done" (actual status comes from report)
            setProgressItems(prev => prev.map((item, idx) =>
                idx === i ? { ...item, status: 'done' } : item
            ));
        }

        setCurrentAction('Generating report...');

        // 3. Run ACTUAL Diagnosis with options
        const diagnosis = await diagnosticEngine.runDiagnosis({
            checkOllama,
            checkSurfSense
        });

        setReport(diagnosis);

        if (diagnosis.issuesFound) {
            const proposedPlan = repairManager.createRepairPlan(diagnosis);
            setPlan(proposedPlan);
        } else {
            setPlan(null);
        }

        // Brief pause before showing results
        await new Promise(r => setTimeout(r, 300));
        setStep('report');
    };

    const startRepair = async () => {
        if (!plan) return;
        setStep('repairing');

        // Track repair progress
        setRepairProgress({ current: 0, total: plan.actions.length });

        const results: { description: string; success: boolean }[] = [];

        for (let i = 0; i < plan.actions.length; i++) {
            const action = plan.actions[i];
            setCurrentAction(action.description);
            setRepairProgress({ current: i + 1, total: plan.actions.length });

            try {
                const success = await action.action();
                results.push({ description: action.description, success });
            } catch (e) {
                results.push({ description: action.description, success: false });
            }

            // Brief pause between actions
            await new Promise(r => setTimeout(r, 500));
        }

        setCurrentAction('Verifying repairs...');

        // Re-calculate options for verification
        let aiMode = 'auto';
        try {
            const conf = JSON.parse(localStorage.getItem('biodockify_ai_config') || '{}');
            aiMode = conf.mode || 'auto';
        } catch { }

        const options = {
            checkOllamaMode: (aiMode === 'ollama' || aiMode === 'auto'),
            checkBackendOnly: aiMode !== 'ollama' && aiMode !== 'z-ai',
            checkSurfSense: true
        };

        const finalDiagnosis = await diagnosticEngine.runDiagnosis(options);

        setResult({
            success: !finalDiagnosis.issuesFound,
            actionsTaken: results,
            verificationResult: finalDiagnosis
        });
        setStep('summary');
    };

    // ------------------------------------------------------------------------
    // UI Helpers
    // ------------------------------------------------------------------------

    const renderStatusIcon = (status: string) => {
        switch (status) {
            case 'ok': return <CheckCircle className="w-5 h-5 text-emerald-400" />;
            case 'warning': return <AlertTriangle className="w-5 h-5 text-amber-400" />;
            case 'error': return <XOctagon className="w-5 h-5 text-red-500" />;
            default: return <Activity className="w-5 h-5 text-slate-500" />;
        }
    };

    // ------------------------------------------------------------------------
    // Views
    // ------------------------------------------------------------------------

    const renderIntro = () => (
        <div className="space-y-6">
            <div className="flex items-center space-x-3 mb-4">
                <div className="w-12 h-12 rounded-full bg-sky-500/10 flex items-center justify-center">
                    <Activity className="w-6 h-6 text-sky-400" />
                </div>
                <div>
                    <h2 className="text-xl font-bold text-white">System Diagnostic</h2>
                    <p className="text-slate-400">BioDockify AI Self-Repair</p>
                </div>
            </div>

            <div className="bg-slate-800/50 p-4 rounded-lg border border-slate-700">
                <p className="text-slate-300 leading-relaxed">
                    I can diagnose local services (Ollama, Neo4j, Models) to identify connection issues.
                    I will not make any changes to your system without your explicit approval in the next step.
                </p>
            </div>

            <div className="flex space-x-3 pt-4">
                <button
                    onClick={onClose}
                    className="flex-1 py-3 px-4 rounded-lg bg-slate-800 text-slate-400 hover:bg-slate-700 transition-colors"
                >
                    Cancel
                </button>
                <button
                    onClick={startDiagnosis}
                    className="flex-1 py-3 px-4 rounded-lg bg-sky-600 text-white font-medium hover:bg-sky-500 transition-colors flex items-center justify-center space-x-2"
                >
                    <Activity className="w-4 h-4" />
                    <span>Start Diagnosis</span>
                </button>
            </div>
        </div>
    );

    const renderScanning = () => (
        <div className="space-y-6">
            <div className="flex items-center space-x-3 mb-4">
                <div className="w-12 h-12 rounded-full bg-sky-500/10 flex items-center justify-center">
                    <Activity className="w-6 h-6 text-sky-400 animate-pulse" />
                </div>
                <div>
                    <h2 className="text-xl font-bold text-white">Scanning System</h2>
                    <p className="text-slate-400 text-sm">{currentAction || 'Initializing...'}</p>
                </div>
            </div>

            {/* Progress Bar */}
            <div className="w-full bg-slate-800 rounded-full h-2 overflow-hidden">
                <div
                    className="bg-sky-500 h-full transition-all duration-500"
                    style={{ width: `${(progressItems.filter(p => p.status === 'done').length / Math.max(progressItems.length, 1)) * 100}%` }}
                />
            </div>

            {/* Service Check List */}
            <div className="space-y-2 bg-slate-900/50 rounded-lg p-3">
                {progressItems.map((item, idx) => (
                    <div key={idx} className="flex items-center justify-between p-2 bg-slate-800/50 rounded border border-slate-700/50">
                        <div className="flex items-center space-x-3">
                            {item.status === 'pending' && <div className="w-4 h-4 rounded-full bg-slate-600" />}
                            {item.status === 'checking' && <div className="w-4 h-4 rounded-full border-2 border-sky-400 border-t-transparent animate-spin" />}
                            {item.status === 'done' && <CheckCircle className="w-4 h-4 text-emerald-400" />}
                            {item.status === 'error' && <XOctagon className="w-4 h-4 text-red-400" />}
                            <span className={`text-sm ${item.status === 'checking' ? 'text-sky-400' : item.status === 'done' ? 'text-emerald-400' : 'text-slate-400'}`}>
                                {item.name}
                            </span>
                        </div>
                        <span className="text-xs text-slate-500">
                            {item.status === 'pending' ? 'Waiting' :
                                item.status === 'checking' ? 'Checking...' :
                                    item.status === 'done' ? '✓ Done' : 'Error'}
                        </span>
                    </div>
                ))}
            </div>

            {/* Estimated Time */}
            <div className="text-center text-xs text-slate-500">
                Estimated time: ~{Math.max(5, progressItems.filter(p => p.status === 'pending').length * 2)}s remaining
            </div>
        </div>
    );

    const renderReport = () => (
        <div className="space-y-6">
            <h3 className="text-lg font-bold text-white flex items-center">
                <Shield className="w-5 h-5 mr-2 text-sky-400" />
                Diagnosis Results
            </h3>

            {/* Check List */}
            <div className="space-y-2 bg-slate-900/50 rounded-lg p-2 max-h-[200px] overflow-y-auto">
                {report?.checks.map((check) => (
                    <div key={check.id} className="flex items-center justify-between p-3 bg-slate-800/30 rounded border border-slate-800">
                        <div className="flex items-center space-x-3">
                            {renderStatusIcon(check.status)}
                            <span className="text-slate-300 font-medium">{check.name}</span>
                        </div>
                        <span className="text-xs text-slate-500 font-mono">{check.message}</span>
                    </div>
                ))}
            </div>

            {/* Repair Plan Proposal */}
            {plan && plan.actions.length > 0 ? (
                <div className="bg-amber-500/10 border border-amber-500/20 rounded-lg p-4 space-y-3">
                    <div className="flex items-center justify-between">
                        <h4 className="text-amber-400 font-bold flex items-center">
                            <RefreshCw className="w-4 h-4 mr-2" />
                            Repair Plan Proposed
                        </h4>
                        <span className="text-xs text-amber-500/80 px-2 py-1 bg-amber-500/10 rounded uppercase">
                            Risk: {plan.estimatedRisk}
                        </span>
                    </div>

                    <p className="text-sm text-slate-300">{plan.explanation}</p>

                    <ul className="space-y-1">
                        {plan.actions.map(action => (
                            <li key={action.id} className="text-sm text-slate-400 flex items-start">
                                <span className="mr-2 text-amber-500">•</span>
                                {action.description}
                            </li>
                        ))}
                    </ul>
                </div>
            ) : (
                <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-lg p-4">
                    <p className="text-emerald-400 flex items-center">
                        <CheckCircle className="w-5 h-5 mr-2" />
                        System is healthy. No repairs needed.
                    </p>
                </div>
            )}

            <div className="flex space-x-3 pt-2">
                <button
                    onClick={onClose}
                    className="flex-1 py-3 px-4 rounded-lg bg-slate-800 text-slate-400 hover:bg-slate-700 transition-colors"
                >
                    {plan ? 'Cancel Repair' : 'Close'}
                </button>
                {plan && (
                    <button
                        onClick={startRepair}
                        className="flex-1 py-3 px-4 rounded-lg bg-amber-600 text-white font-medium hover:bg-amber-500 transition-colors flex items-center justify-center space-x-2"
                    >
                        <RefreshCw className="w-4 h-4" />
                        <span>Approve Repair</span>
                    </button>
                )}
            </div>
        </div>
    );

    const renderRepairing = () => (
        <div className="space-y-6">
            <div className="flex items-center space-x-3 mb-4">
                <div className="w-12 h-12 rounded-full bg-amber-500/10 flex items-center justify-center">
                    <RefreshCw className="w-6 h-6 text-amber-400 animate-spin" />
                </div>
                <div>
                    <h2 className="text-xl font-bold text-white">Repairing System</h2>
                    <p className="text-slate-400 text-sm">Step {repairProgress.current} of {repairProgress.total}</p>
                </div>
            </div>

            {/* Progress Bar */}
            <div className="w-full bg-slate-800 rounded-full h-3 overflow-hidden">
                <div
                    className="bg-gradient-to-r from-amber-500 to-orange-500 h-full transition-all duration-500"
                    style={{ width: `${(repairProgress.current / Math.max(repairProgress.total, 1)) * 100}%` }}
                />
            </div>

            {/* Current Action */}
            <div className="bg-slate-900/50 rounded-lg p-4 border border-slate-700">
                <div className="flex items-center space-x-3">
                    <div className="w-8 h-8 rounded-full border-2 border-amber-400 border-t-transparent animate-spin" />
                    <div>
                        <p className="text-amber-400 font-medium">{currentAction || 'Initializing...'}</p>
                        <p className="text-slate-500 text-sm">Please wait while the fix is applied</p>
                    </div>
                </div>
            </div>

            {/* Problems Being Fixed */}
            {plan && plan.actions.length > 0 && (
                <div className="bg-slate-900/50 rounded-lg p-3 border border-slate-700">
                    <h4 className="text-xs font-semibold text-slate-400 uppercase mb-2">Issues Being Fixed</h4>
                    <div className="space-y-1">
                        {plan.actions.map((action, idx) => (
                            <div key={action.id} className="flex items-center justify-between text-sm">
                                <span className="text-slate-300">{action.description}</span>
                                <span className={`text-xs px-2 py-0.5 rounded ${idx < repairProgress.current - 1 ? 'bg-emerald-500/20 text-emerald-400' :
                                    idx === repairProgress.current - 1 ? 'bg-amber-500/20 text-amber-400' :
                                        'bg-slate-700 text-slate-500'
                                    }`}>
                                    {idx < repairProgress.current - 1 ? '✓ Fixed' :
                                        idx === repairProgress.current - 1 ? 'In Progress' : 'Pending'}
                                </span>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Estimated Time */}
            <div className="text-center text-xs text-slate-500">
                Estimated time: ~{Math.max(10, (repairProgress.total - repairProgress.current) * 12)}s remaining
            </div>
        </div>
    );

    const renderSummary = () => (
        <div className="space-y-6">
            <div className="flex items-center space-x-3 mb-2">
                <div className={`w-12 h-12 rounded-full flex items-center justify-center ${result?.success ? 'bg-emerald-500/10' : 'bg-red-500/10'
                    }`}>
                    {result?.success ? (
                        <CheckCircle className="w-6 h-6 text-emerald-400" />
                    ) : (
                        <AlertTriangle className="w-6 h-6 text-red-400" />
                    )}
                </div>
                <div>
                    <h2 className="text-xl font-bold text-white">Repair Complete</h2>
                    <p className={result?.success ? 'text-emerald-400' : 'text-red-400'}>
                        {result?.success ? 'All systems verified' : 'Some issues persist'}
                    </p>
                </div>
            </div>

            <div className="bg-slate-900/50 rounded-lg p-4 border border-slate-800 space-y-3">
                <h4 className="text-sm font-semibold text-slate-400 uppercase">Actions Taken</h4>
                <div className="space-y-2">
                    {result?.actionsTaken.map((action, idx) => (
                        <div key={idx} className="flex items-center justify-between text-sm">
                            <span className="text-slate-300">{action.description}</span>
                            <span className={action.success ? 'text-emerald-500' : 'text-red-500'}>
                                {action.success ? 'Success' : 'Failed'}
                            </span>
                        </div>
                    ))}
                </div>
            </div>

            <div className="bg-slate-900/50 rounded-lg p-4 border border-slate-800 space-y-3">
                <h4 className="text-sm font-semibold text-slate-400 uppercase">Verification</h4>
                <div className="space-y-1">
                    {result?.verificationResult.checks.map(check => (
                        <div key={check.id} className="flex items-center text-sm">
                            {renderStatusIcon(check.status)}
                            <span className="ml-2 text-slate-400">{check.name}: {check.message}</span>
                        </div>
                    ))}
                </div>
            </div>

            <button
                onClick={onClose}
                className="w-full py-3 px-4 rounded-lg bg-slate-700 text-white font-medium hover:bg-slate-600 transition-colors"
            >
                Close & Return to Chat
            </button>
        </div>
    );

    // ------------------------------------------------------------------------
    // Main Render
    // ------------------------------------------------------------------------

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
            <div className="bg-slate-900 border border-slate-700 rounded-xl w-full max-w-lg shadow-2xl overflow-hidden">
                {/* Safe Mode Indicator (Header) */}
                <div className="bg-slate-800 px-6 py-2 flex items-center justify-between border-b border-slate-700">
                    <div className="flex items-center space-x-2">
                        <Shield className="w-4 h-4 text-emerald-400" />
                        <span className="text-xs font-semibold text-emerald-400 uppercase tracking-wide">
                            Safe Mode Active
                        </span>
                    </div>
                </div>

                <div className="p-6">
                    {step === 'intro' && renderIntro()}
                    {step === 'scanning' && renderScanning()}
                    {step === 'report' && renderReport()}
                    {step === 'repairing' && renderRepairing()}
                    {step === 'summary' && renderSummary()}
                </div>
            </div>
        </div>
    );
}
