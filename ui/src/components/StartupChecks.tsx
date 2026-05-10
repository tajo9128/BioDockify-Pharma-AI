'use client';

import React, { useState, useEffect } from 'react';
import { Wifi, Brain, Check, X, Loader2, AlertTriangle, ArrowRight } from 'lucide-react';

interface StartupChecksProps {
    onComplete: () => void;
}

type CheckStatus = 'pending' | 'checking' | 'success' | 'warning' | 'error';

export default function StartupChecks({ onComplete }: StartupChecksProps) {
    const [internetStatus, setInternetStatus] = useState<CheckStatus>('pending');
    const [aiStatus, setAiStatus] = useState<CheckStatus>('pending');
    const [showWelcome, setShowWelcome] = useState(false);

    useEffect(() => {
        runChecks();
    }, []);

    const runChecks = async () => {
        // 1. Check Internet
        setInternetStatus('checking');
        try {
            await fetch('https://www.google.com/favicon.ico', {
                mode: 'no-cors',
                signal: AbortSignal.timeout(3000)
            });
            setInternetStatus('success');
        } catch {
            setInternetStatus('warning'); // Soft fail for offline mode
        }

        // 2. Check LM Studio
        setAiStatus('checking');
        let aiFound = false;
        const ports = [1234, 8080];
        for (const port of ports) {
            try {
                const res = await fetch(`http://localhost:${port}/v1/models`, {
                    signal: AbortSignal.timeout(2000)
                });
                if (res.ok) {
                    aiFound = true;
                    break;
                }
            } catch { /* continue */ }
        }
        setAiStatus(aiFound ? 'success' : 'warning');

        // 3. Complete
        setTimeout(() => {
            setShowWelcome(true);
        }, 1000);
    };

    const handleEnter = () => {
        // Save flag to skip this next time if desired, or just session-based
        // For now, we just proceed
        localStorage.setItem('biodockify_onboarding_optimized', 'true');
        onComplete();
    };

    if (showWelcome) {
        return (
            <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950 text-slate-100 animate-in fade-in duration-500">
                <div className="text-center space-y-6 max-w-md p-8">
                    <div className="w-20 h-20 bg-teal-500/10 rounded-full flex items-center justify-center mx-auto mb-6 ring-1 ring-teal-500/30">
                        <span className="text-4xl">🧬</span>
                    </div>

                    <h1 className="text-4xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-teal-400 to-indigo-500">
                        BioDockify
                    </h1>

                    <div className="space-y-2 text-slate-400">
                        <p className="flex items-center justify-center gap-2">
                            {internetStatus === 'success' ? <Wifi className="w-4 h-4 text-emerald-400" /> : <Wifi className="w-4 h-4 text-amber-400" />}
                            Internet: {internetStatus === 'success' ? 'Connected' : 'Offline Mode'}
                        </p>
                        <p className="flex items-center justify-center gap-2">
                            {aiStatus === 'success' ? <Brain className="w-4 h-4 text-emerald-400" /> : <Brain className="w-4 h-4 text-amber-400" />}
                            AI Engine: {aiStatus === 'success' ? 'Ready' : 'Not Detected'}
                        </p>
                    </div>

                    <button
                        onClick={handleEnter}
                        className="group relative inline-flex items-center justify-center px-8 py-3 font-semibold text-white transition-all duration-200 bg-teal-600 rounded-full hover:bg-teal-500 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-teal-600"
                    >
                        Enter Workstation
                        <ArrowRight className="w-5 h-5 ml-2 -mr-1 transition-transform group-hover:translate-x-1" />
                    </button>

                    <p className="text-xs text-slate-600 mt-8">v2.5.9 • Pharma Research AI</p>
                </div>
            </div>
        );
    }

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950 text-slate-100">
            <div className="text-center space-y-4">
                <Loader2 className="w-10 h-10 text-teal-500 animate-spin mx-auto" />
                <p className="text-slate-400 font-medium tracking-wide">INITIALIZING SYSTEMS...</p>

                <div className="flex gap-4 justify-center text-xs text-slate-600 uppercase tracking-widest mt-4">
                    <span className={internetStatus === 'checking' ? 'text-teal-400 animate-pulse' : internetStatus === 'success' ? 'text-emerald-500' : ''}>
                        Network
                    </span>
                    <span className="text-slate-800">•</span>
                    <span className={aiStatus === 'checking' ? 'text-teal-400 animate-pulse' : aiStatus === 'success' ? 'text-emerald-500' : ''}>
                        Cognitive Core
                    </span>
                </div>
            </div>
        </div>
    );
}
