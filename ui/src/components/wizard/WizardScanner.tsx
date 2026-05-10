/**
 * WizardScanner Component
 * 
 * Displays environment scan results during First-Run Wizard.
 * Follows BioDockify AI RULE 3: Read-only, no auto-start/install.
 */

'use client';

import React, { useEffect, useState } from 'react';
import { Check, XCircle, AlertTriangle, RefreshCcw, ExternalLink } from 'lucide-react';
import { getSystemController } from '@/lib/system-controller';
import { ScanResult, SetupGuidance } from '@/lib/system-rules';

interface WizardScannerProps {
    onScanComplete: (results: ScanResult[]) => void;
    autoStart?: boolean;
}

export default function WizardScanner({ onScanComplete, autoStart = true }: WizardScannerProps) {
    const [isScanning, setIsScanning] = useState(false);
    const [scanResults, setScanResults] = useState<ScanResult[]>([]);
    const [setupGuidance, setSetupGuidance] = useState<SetupGuidance[]>([]);
    const [scanComplete, setScanComplete] = useState(false);

    const controller = getSystemController();

    useEffect(() => {
        if (autoStart && !scanComplete) {
            performScan();
        }
    }, [autoStart]);

    const performScan = async () => {
        setIsScanning(true);
        setScanComplete(false);

        // Visual pacing - show scanning state
        await new Promise(r => setTimeout(r, 500));

        const results = await controller.performEnvironmentScan();
        setScanResults(results);

        // Get setup guidance for missing components
        const guidance = controller.getSetupGuidance();
        setSetupGuidance(guidance);

        await new Promise(r => setTimeout(r, 300));

        setIsScanning(false);
        setScanComplete(true);
        onScanComplete(results);
    };

    const getStatusIcon = (status: ScanResult['status']) => {
        switch (status) {
            case 'ok':
                return <Check className="w-5 h-5 text-emerald-400" />;
            case 'warning':
                return <AlertTriangle className="w-5 h-5 text-amber-400" />;
            case 'error':
                return <XCircle className="w-5 h-5 text-red-400" />;
        }
    };

    const getStatusText = (status: ScanResult['status']) => {
        switch (status) {
            case 'ok':
                return 'text-emerald-400';
            case 'warning':
                return 'text-amber-400';
            case 'error':
                return 'text-red-400';
        }
    };

    return (
        <div className="space-y-6">
            {/* Scan Results */}
            <div className="space-y-3">
                <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider">
                    System Scan Results
                </h3>

                {scanResults.length === 0 && isScanning && (
                    <div className="flex items-center justify-center py-8">
                        <RefreshCcw className="w-6 h-6 text-sky-400 animate-spin mr-3" />
                        <span className="text-slate-400">Scanning environment...</span>
                    </div>
                )}

                {scanResults.map((result, idx) => (
                    <div
                        key={idx}
                        className="flex items-center justify-between p-4 bg-slate-900/50 border border-slate-800 rounded-lg"
                    >
                        <div className="flex items-center space-x-3">
                            {isScanning && scanResults.length <= idx ? (
                                <RefreshCcw className="w-5 h-5 text-slate-500 animate-spin" />
                            ) : (
                                getStatusIcon(result.status)
                            )}
                            <span className="text-slate-300 font-medium">{result.name}</span>
                        </div>
                        <span className={`text-sm font-mono ${getStatusText(result.status)}`}>
                            {result.message}
                        </span>
                    </div>
                ))}
            </div>

            {/* Setup Guidance (RULE 5: No autonomy, explain + links) */}
            {scanComplete && setupGuidance.length > 0 && (
                <div className="space-y-4 mt-6">
                    <h3 className="text-sm font-semibold text-amber-400 uppercase tracking-wider">
                        Optional Setup
                    </h3>

                    {setupGuidance.map((guidance, idx) => (
                        <div
                            key={idx}
                            className="p-4 bg-amber-500/5 border border-amber-500/20 rounded-lg space-y-3"
                        >
                            <div className="flex items-center justify-between">
                                <span className="text-white font-semibold">{guidance.component}</span>
                                {guidance.canSkip && (
                                    <span className="text-xs text-slate-500 bg-slate-800 px-2 py-1 rounded">
                                        Optional
                                    </span>
                                )}
                            </div>

                            <p className="text-sm text-slate-400">{guidance.reason}</p>

                            {guidance.skipConsequences.length > 0 && (
                                <div className="text-xs text-slate-500">
                                    <span className="font-medium">If skipped:</span>
                                    <ul className="list-disc list-inside mt-1 space-y-0.5">
                                        {guidance.skipConsequences.map((c, i) => (
                                            <li key={i}>{c}</li>
                                        ))}
                                    </ul>
                                </div>
                            )}

                            <a
                                href={guidance.downloadUrl}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="inline-flex items-center space-x-2 text-sm text-sky-400 hover:text-sky-300 transition-colors"
                            >
                                <ExternalLink className="w-4 h-4" />
                                <span>Download {guidance.component}</span>
                            </a>
                        </div>
                    ))}
                </div>
            )}

            {/* Rescan Button */}
            {scanComplete && (
                <button
                    onClick={performScan}
                    disabled={isScanning}
                    className="flex items-center justify-center space-x-2 w-full py-3 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg transition-colors disabled:opacity-50"
                >
                    <RefreshCcw className={`w-4 h-4 ${isScanning ? 'animate-spin' : ''}`} />
                    <span>Rescan Environment</span>
                </button>
            )}
        </div>
    );
}
