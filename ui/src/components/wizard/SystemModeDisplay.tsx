/**
 * SystemModeDisplay Component
 * 
 * Shows the current system mode (LIMITED or FULL).
 * Follows BioDockify AI RULE 6: Never pretend full functionality.
 */

'use client';

import React from 'react';
import { AlertTriangle, Check, Zap, Cloud, Database, FileText, Brain, Search } from 'lucide-react';
import { SystemModeDeclaration } from '@/lib/system-rules';

interface SystemModeDisplayProps {
    mode: SystemModeDeclaration;
    compact?: boolean;
}

export default function SystemModeDisplay({ mode, compact = false }: SystemModeDisplayProps) {
    const isLimited = mode.mode === 'LIMITED';

    const getFeatureIcon = (feature: string) => {
        const icons: Record<string, React.ReactNode> = {
            'AI reasoning': <Brain className="w-4 h-4" />,
            'Memory persistence': <Database className="w-4 h-4" />,
            'File reading': <FileText className="w-4 h-4" />,
            'PDF processing': <FileText className="w-4 h-4" />,
            'Literature search': <Search className="w-4 h-4" />,
            'Research assistant': <Zap className="w-4 h-4" />
        };
        return icons[feature] || <Cloud className="w-4 h-4" />;
    };

    if (compact) {
        return (
            <div className={`inline-flex items-center space-x-2 px-3 py-1.5 rounded-full text-xs font-medium ${isLimited
                ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                : 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                }`}>
                {isLimited ? (
                    <AlertTriangle className="w-3 h-3" />
                ) : (
                    <Check className="w-3 h-3" />
                )}
                <span>{mode.title}</span>
            </div>
        );
    }

    return (
        <div className={`p-6 rounded-xl border ${isLimited
            ? 'bg-amber-500/5 border-amber-500/20'
            : 'bg-emerald-500/5 border-emerald-500/20'
            }`}>
            {/* Header */}
            <div className="flex items-center space-x-3 mb-4">
                {isLimited ? (
                    <div className="w-10 h-10 bg-amber-500/20 rounded-lg flex items-center justify-center">
                        <AlertTriangle className="w-5 h-5 text-amber-400" />
                    </div>
                ) : (
                    <div className="w-10 h-10 bg-emerald-500/20 rounded-lg flex items-center justify-center">
                        <Zap className="w-5 h-5 text-emerald-400" />
                    </div>
                )}
                <div>
                    <h3 className={`font-bold ${isLimited ? 'text-amber-400' : 'text-emerald-400'}`}>
                        System Mode: {mode.mode}
                    </h3>
                    <p className="text-sm text-slate-400">{mode.title}</p>
                </div>
            </div>

            {/* Capabilities Grid */}
            <div className="grid grid-cols-2 gap-2">
                {mode.capabilities.map((cap, idx) => (
                    <div
                        key={idx}
                        className={`flex items-center space-x-2 p-2 rounded-lg ${cap.enabled
                            ? 'bg-slate-800/50 text-slate-300'
                            : 'bg-slate-900/50 text-slate-500'
                            }`}
                    >
                        <div className={cap.enabled ? 'text-emerald-400' : 'text-slate-600'}>
                            {cap.enabled ? (
                                <Check className="w-4 h-4" />
                            ) : (
                                <AlertTriangle className="w-4 h-4" />
                            )}
                        </div>
                        <span className="text-sm">{cap.feature}</span>
                    </div>
                ))}
            </div>

            {/* Limited Mode Notice */}
            {isLimited && (
                <p className="mt-4 text-xs text-slate-500">
                    Some features are unavailable because required services are not running.
                    You can install and start them later from Settings.
                </p>
            )}
        </div>
    );
}
