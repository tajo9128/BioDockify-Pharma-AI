import React from 'react';
import { Settings } from '@/lib/api';
import { AGENT_PERSONAS } from '@/lib/personas';
import { UserCog, Shield, Zap, Clock, CheckCircle } from 'lucide-react';

interface AgentSettingsProps {
    settings: Settings;
    onSettingChange: (section: keyof Settings, value: any) => void;
}

export const AgentSettings: React.FC<AgentSettingsProps> = ({ settings, onSettingChange }) => {

    const updateAgent = (key: string, value: string | number | boolean) => {
        onSettingChange('agent', { ...settings.agent, [key]: value });
    };

    const updateNanobot = (key: string, value: string | number | boolean) => {
        onSettingChange('nanobot', { ...settings.nanobot, [key]: value });
    };

    return (
        <div className="space-y-6 animate-in fade-in duration-300">
            {/* Agent Persona Selection */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
                <h3 className="text-lg font-semibold text-white mb-4 flex items-center">
                    <UserCog className="w-5 h-5 mr-2 text-indigo-400" /> Agent Persona & Reasoning Mode
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {AGENT_PERSONAS.map(persona => (
                        <div
                            key={persona.id}
                            onClick={() => updateAgent('mode', persona.id)} // Assuming 'mode' maps to persona id in backend logic
                            className={`cursor-pointer p-4 rounded-lg border transition-all ${settings.agent?.mode === persona.id ? 'bg-indigo-500/10 border-indigo-500 ring-1 ring-indigo-500/50' : 'bg-slate-950 border-slate-800 hover:border-slate-600'}`}
                        >
                            <div className="flex items-center justify-between mb-2">
                                <span className={`font-semibold ${settings.agent?.mode === persona.id ? 'text-indigo-400' : 'text-slate-200'}`}>{persona.label}</span>
                                {settings.agent?.mode === persona.id && <CheckCircle className="w-4 h-4 text-indigo-500" />}
                            </div>
                            <p className="text-xs text-slate-400 leading-relaxed">{persona.description}</p>
                        </div>
                    ))}
                </div>
            </div>

            {/* Safety & Execution */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
                <h3 className="text-lg font-semibold text-white mb-4 flex items-center">
                    <Shield className="w-5 h-5 mr-2 text-teal-400" /> Operational Safety & Limits
                </h3>
                <div className="space-y-4">
                    {/* Human Approval */}
                    <div className="flex items-center justify-between p-4 bg-slate-950 rounded-lg border border-slate-800">
                        <div className="flex-1 pr-4">
                            <h4 className="text-sm font-bold text-white mb-1">Human Approval Gates</h4>
                            <p className="text-xs text-slate-500">Require explicit user permission before the agent executes critical actions (e.g. file deletion, system commands).</p>
                        </div>
                        <button
                            onClick={() => updateAgent('human_approval_gates', !settings.agent?.human_approval_gates)}
                            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${settings.agent?.human_approval_gates ? 'bg-teal-600' : 'bg-slate-700'}`}
                        >
                            <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${settings.agent?.human_approval_gates ? 'translate-x-6' : 'translate-x-1'}`} />
                        </button>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {/* Nanobot Configuration */}
                        <div className="p-4 bg-slate-950 rounded-lg border border-slate-800">
                            <div className="flex items-center gap-2 mb-3">
                                <Zap className="w-4 h-4 text-yellow-400" />
                                <h4 className="text-sm font-bold text-slate-300">Nanobot Browser</h4>
                            </div>

                            <div className="space-y-3">
                                <div className="flex items-center justify-between">
                                    <span className="text-xs text-slate-400">Headless Mode</span>
                                    <button onClick={() => updateNanobot('headless_browser', !settings.nanobot?.headless_browser)} className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${settings.nanobot?.headless_browser ? 'bg-emerald-600' : 'bg-slate-700'}`}><span className={`inline-block h-3 w-3 transform rounded-full bg-white transition-transform ${settings.nanobot?.headless_browser ? 'translate-x-5' : 'translate-x-1'}`} /></button>
                                </div>
                                <div className="flex items-center justify-between">
                                    <span className="text-xs text-slate-400">Stealth Mode</span>
                                    <button onClick={() => updateNanobot('stealth_mode', !settings.nanobot?.stealth_mode)} className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${settings.nanobot?.stealth_mode ? 'bg-emerald-600' : 'bg-slate-700'}`}><span className={`inline-block h-3 w-3 transform rounded-full bg-white transition-transform ${settings.nanobot?.stealth_mode ? 'translate-x-5' : 'translate-x-1'}`} /></button>
                                </div>
                                <div className="flex items-center justify-between">
                                    <span className="text-xs text-slate-400">Timeout (sec)</span>
                                    <input type="number" value={settings.nanobot?.browser_timeout || 30} onChange={(e) => updateNanobot('browser_timeout', parseInt(e.target.value))} className="w-16 bg-slate-900 border border-slate-700 rounded px-1 py-0.5 text-xs text-white text-center" />
                                </div>
                            </div>
                        </div>

                        {/* Execution Limits */}
                        <div className="p-4 bg-slate-950 rounded-lg border border-slate-800">
                            <div className="flex items-center gap-2 mb-3">
                                <Clock className="w-4 h-4 text-blue-400" />
                                <h4 className="text-sm font-bold text-slate-300">Execution Limits</h4>
                            </div>
                            <div className="space-y-4">
                                <div className="flex items-center justify-between">
                                    <span className="text-xs text-slate-400">Max Runtime (Min)</span>
                                    <input type="number" value={settings.agent?.max_runtime_minutes || 45} onChange={(e) => updateAgent('max_runtime_minutes', parseInt(e.target.value))} className="w-16 bg-slate-900 border border-slate-700 rounded px-1 py-0.5 text-xs text-white text-center" />
                                </div>
                                <div className="flex items-center justify-between">
                                    <span className="text-xs text-slate-400">Max Retries</span>
                                    <input type="number" value={settings.agent?.max_retries || 3} onChange={(e) => updateAgent('max_retries', parseInt(e.target.value))} className="w-16 bg-slate-900 border border-slate-700 rounded px-1 py-0.5 text-xs text-white text-center" />
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};
