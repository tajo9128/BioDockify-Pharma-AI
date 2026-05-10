import React, { useState } from 'react';
import { RefreshCw, CheckCircle, AlertCircle } from 'lucide-react';

interface CloudKeyBoxProps {
    name: string;
    icon: React.ReactNode;
    value: string;
    onChange: (value: string) => void;
    onTest: () => void;
    testStatus?: 'idle' | 'testing' | 'success' | 'error';
    testProgress?: number;
    testMessage?: string;
    testDetails?: string;
    modelValue?: string;
    onModelChange?: (value: string) => void;
    modelPlaceholder?: string;
    baseUrlValue?: string;
    onBaseUrlChange?: (value: string) => void;
    showBaseUrl?: boolean;
    predefinedModels?: string[];
}

export const CloudKeyBox: React.FC<CloudKeyBoxProps> = ({
    name,
    icon,
    value,
    onChange,
    onTest,
    testStatus = 'idle',
    testProgress = 0,
    testMessage = '',
    testDetails = '',
    modelValue,
    onModelChange,
    modelPlaceholder,
    baseUrlValue,
    onBaseUrlChange,
    showBaseUrl = false,
    predefinedModels = []
}) => {
    const [isExpanded, setIsExpanded] = useState(false);

    const getStatusIcon = () => {
        if (testStatus === 'testing') return <RefreshCw className="w-3 h-3 animate-spin text-blue-400" />;
        if (testStatus === 'success') return <CheckCircle className="w-3 h-3 text-green-400" />;
        if (testStatus === 'error') return <AlertCircle className="w-3 h-3 text-red-400" />;
        return null;
    };

    return (
        <div className={`p-4 bg-slate-950 rounded-lg border transition-all ${testStatus === 'success' ? 'border-green-500/30' : testStatus === 'error' ? 'border-red-500/30' : 'border-slate-800'}`}>
            <div className="flex items-center justify-between mb-3">
                <div className="flex items-center space-x-2">
                    <span className="text-xs font-bold text-slate-400 font-mono bg-slate-900 px-2 py-1 rounded">{icon}</span>
                    <span className="text-sm font-medium text-slate-300">{name}</span>
                </div>
                <div className="flex items-center gap-2">
                    {getStatusIcon()}
                    {showBaseUrl && (
                        <button onClick={() => setIsExpanded(!isExpanded)} className="text-xs text-slate-500 hover:text-slate-300">
                            {isExpanded ? 'Simple' : 'Advanced'}
                        </button>
                    )}
                </div>
            </div>

            <div className="flex space-x-2 mb-2">
                <input
                    type="password"
                    value={value || ''}
                    onChange={(e) => onChange(e.target.value)}
                    className="flex-1 bg-slate-900 border border-slate-700 rounded px-2 py-1 text-sm text-white placeholder-slate-600"
                    placeholder="API Key..."
                />
                <button
                    onClick={onTest}
                    disabled={testStatus === 'testing' || !value}
                    className="px-3 bg-slate-800 text-xs text-white rounded hover:bg-slate-700 disabled:opacity-50"
                >
                    Test
                </button>
            </div>

            {/* Model Selection - ALWAYS VISIBLE */}
            <div className="mt-4">
                {predefinedModels.length > 0 ? (
                    <div>
                        <label className="text-[10px] uppercase text-slate-500 font-bold mb-1 block">Model ID</label>
                        <div className="flex gap-2">
                            <select
                                value={modelValue || ''}
                                onChange={(e) => onModelChange && onModelChange(e.target.value)}
                                className="flex-1 bg-slate-900 border border-slate-700 rounded px-2 py-1 text-xs text-white"
                            >
                                <option value="">Select a Model...</option>
                                {predefinedModels.map((m: string) => (
                                    <option key={m} value={m}>{m}</option>
                                ))}
                            </select>
                            {/* Allow custom input even with predefined models */}
                            <input
                                type="text"
                                value={modelValue || ''}
                                onChange={(e) => onModelChange && onModelChange(e.target.value)}
                                className="flex-1 bg-slate-900 border border-slate-700 rounded px-2 py-1 text-xs text-white placeholder-slate-600"
                                placeholder="Or type custom..."
                            />
                        </div>
                    </div>
                ) : (
                    <div>
                        <label className="text-[10px] uppercase text-slate-500 font-bold mb-1 block">Model ID</label>
                        <input
                            type="text"
                            value={modelValue || ''}
                            onChange={(e) => onModelChange && onModelChange(e.target.value)}
                            className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 text-xs text-white placeholder-slate-600"
                            placeholder={modelPlaceholder || "e.g. gpt-4o"}
                        />
                    </div>
                )}
            </div>

            {/* Progress Bar & Status Message */}
            {(testStatus !== 'idle' || testMessage) && (
                <div className="mt-3 mb-2 animate-in fade-in slide-in-from-top-1">
                    {testStatus === 'testing' && (
                        <div className="w-full bg-slate-900 rounded-full h-1 mb-2 overflow-hidden">
                            <div
                                className="bg-indigo-500 h-1 rounded-full transition-all duration-300"
                                style={{ width: `${testProgress}%` }}
                            />
                        </div>
                    )}
                    <div className="flex items-start gap-2">
                        <div className="flex-1">
                            <p className={`text-xs font-bold ${testStatus === 'error' ? 'text-red-400' : testStatus === 'success' ? 'text-emerald-400' : 'text-indigo-400'}`}>
                                {testMessage}
                            </p>
                            {testDetails && (
                                <p className="text-[10px] text-slate-500 mt-0.5 font-mono break-all">{testDetails}</p>
                            )}
                        </div>
                    </div>
                </div>
            )}

            {/* Advanced Options (Base URL) */}
            {isExpanded && showBaseUrl && (
                <div className="space-y-2 mt-2 pt-2 border-t border-slate-800/50 animate-in fade-in slide-in-from-top-1">
                    <div>
                        <label className="text-[10px] uppercase text-slate-500 font-bold mb-1 block">Base URL (Legacy/Proxy)</label>
                        <input
                            type="text"
                            value={baseUrlValue || ''}
                            onChange={(e) => onBaseUrlChange && onBaseUrlChange(e.target.value)}
                            className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 text-xs text-white placeholder-slate-600"
                            placeholder="https://api.openai.com/v1"
                        />
                    </div>
                </div>
            )}
        </div>
    );
};
