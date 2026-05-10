import React, { useState } from 'react';
import { Settings } from '@/lib/api';
import { Settings as SettingsIcon, RotateCcw, Cpu, Download } from 'lucide-react';

interface SystemSettingsProps {
    settings: Settings;
    onSettingChange: (section: keyof Settings, value: any) => void;
    onReset: () => void;
}

export const SystemSettings: React.FC<SystemSettingsProps> = ({ settings, onSettingChange, onReset }) => {
    const [resetting, setResetting] = useState(false);

    const updateSystem = (key: string, value: string | number | boolean) => {
        onSettingChange('system', { ...settings.system, [key]: value });
    };

    const handleReset = async () => {
        if (!confirm('Are you sure you want to reset ALL settings to defaults? This cannot be undone.')) return;
        setResetting(true);
        try {
            await onReset();
            // toast handled by parent usually, but we can do it here too
        } finally {
            setResetting(false);
        }
    };

    return (
        <div className="space-y-6 animate-in fade-in duration-300">
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
                <h3 className="text-lg font-semibold text-white mb-4 flex items-center">
                    <SettingsIcon className="w-5 h-5 mr-2 text-slate-400" /> System Configuration
                </h3>

                <div className="space-y-6">
                    {/* Hardware Limits */}
                    <div className="p-4 bg-slate-950 rounded-lg border border-slate-800">
                        <div className="flex items-center gap-2 mb-3">
                            <Cpu className="w-4 h-4 text-blue-400" />
                            <h4 className="text-sm font-bold text-slate-300">Hardware Resource Limits</h4>
                        </div>

                        {/* Performance Profile */}
                        <div className="mb-4 pb-4 border-b border-slate-800">
                            <div className="flex items-center justify-between mb-2">
                                <label className="text-sm font-medium text-slate-300">Performance Profile</label>
                                <select
                                    value={settings.ai_advanced?.performance_profile || 'high'}
                                    onChange={(e) => onSettingChange && onSettingChange('ai_advanced', { ...settings.ai_advanced, performance_profile: e.target.value })}
                                    className="bg-slate-900 border border-slate-700 rounded px-3 py-1 text-xs text-white focus:outline-none focus:border-blue-500"
                                >
                                    <option value="low">Low (2k Context - 8GB RAM)</option>
                                    <option value="moderate">Moderate (4k Context - 16GB RAM)</option>
                                    <option value="high">High (8k Context - 32GB+ RAM)</option>
                                </select>
                            </div>
                            <p className="text-xs text-slate-500">
                                Adjusts memory optimization strategy. Lower profiles prune conversation history more aggressively.
                            </p>
                        </div>

                        <div className="flex items-center justify-between">
                            <span className="text-sm text-slate-400">Max CPU Usage (%)</span>
                            <div className="flex items-center gap-3">
                                <input
                                    type="range"
                                    min="10"
                                    max="100"
                                    step="10"
                                    value={settings.system?.max_cpu_percent || 80}
                                    onChange={(e) => updateSystem('max_cpu_percent', parseInt(e.target.value))}
                                    className="w-32 accent-blue-500"
                                />
                                <span className="text-sm font-mono text-white w-8 text-right">{settings.system?.max_cpu_percent || 80}%</span>
                            </div>
                        </div>
                        <p className="text-xs text-slate-500 mt-2">Limit the CPU resources available to local LLMs and heavy compute tasks.</p>
                    </div>

                    {/* Updates */}
                    <div className="flex items-center justify-between p-4 bg-slate-950 rounded-lg border border-slate-800">
                        <div className="flex items-center gap-2">
                            <Download className="w-4 h-4 text-emerald-400" />
                            <span className="text-sm text-slate-300">Automatic Updates</span>
                        </div>
                        <button
                            onClick={() => updateSystem('auto_update', !settings.system?.auto_update)}
                            className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${settings.system?.auto_update ? 'bg-emerald-600' : 'bg-slate-700'}`}
                        >
                            <span className={`inline-block h-3 w-3 transform rounded-full bg-white transition-transform ${settings.system?.auto_update ? 'translate-x-5' : 'translate-x-1'}`} />
                        </button>
                    </div>

                    {/* Danger Zone */}
                    <div className="pt-6 border-t border-slate-800">
                        <h4 className="text-sm font-bold text-red-400 mb-3 uppercase tracking-wider">Danger Zone</h4>
                        <button
                            onClick={handleReset}
                            disabled={resetting}
                            className="flex items-center justify-center w-full p-3 border border-red-900/50 bg-red-950/20 text-red-500 hover:bg-red-900/40 rounded-lg transition-colors text-sm font-medium"
                        >
                            <RotateCcw className={`w-4 h-4 mr-2 ${resetting ? 'animate-spin' : ''}`} />
                            {resetting ? 'Resetting...' : 'Reset All Settings to Defaults'}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
};
