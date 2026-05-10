
import React from 'react';
import { useSettings } from '../../hooks/useSettings';

interface Settings {
    agent_zero?: {
        autonomy_level?: string;
        force_persona?: string;
        internet_research?: boolean;
        // Add other properties as needed
    };
    // Add other setting groups
}

export default function BioDockifyResearchSettings() {
    const { settings, updateSettings } = useSettings();

    // Type assertion or check to avoid TS errors if useSettings is not fully typed
    const safeSettings = settings as Settings;

    const updateResearch = (key: string, value: any) => {
        updateSettings('agent_zero', {
            ...(safeSettings.agent_zero || {}),
            [key]: value
        });
    };

    const autonomyLevel = safeSettings.agent_zero?.autonomy_level || 'supervised';
    const forcePersona = safeSettings.agent_zero?.force_persona || 'Auto-Detect';
    const internetResearch = safeSettings.agent_zero?.internet_research ?? true;

    return (
        <div className="space-y-6">
            <div>
                <h2 className="text-2xl font-bold text-white mb-2">BioDockify AI (Research Engine)</h2>
                <p className="text-slate-400">Configure the Deep Reasoning Core. This engine handles the 40-Pillar Pharma Intelligence Framework.</p>
            </div>

            <div className="bg-slate-800 rounded-lg p-6 border border-slate-700 space-y-6">
                <h3 className="text-lg font-semibold text-purple-400">Cognitive Architecture</h3>

                <div className="flex items-center justify-between">
                    <div>
                        <label className="block text-slate-200 font-medium">Autonomy Level</label>
                        <p className="text-xs text-slate-500">Allow the agent to self-correct and retry without asking</p>
                    </div>
                    <select
                        value={autonomyLevel}
                        onChange={(e) => updateResearch('autonomy_level', e.target.value)}
                        className="bg-slate-900 border border-slate-600 rounded px-3 py-1 text-white text-sm"
                    >
                        <option value="supervised">Supervised (Ask often)</option>
                        <option value="semi-autonomous">Semi-Autonomous (Retry errors)</option>
                        <option value="autonomous">Fully Autonomous (God Mode)</option>
                    </select>
                </div>

                <div>
                    <label className="text-slate-200 font-medium block mb-2">Active Persona</label>
                    <p className="text-xs text-slate-500 mb-3">Manually override the Cognitive Router (Default: Auto-Detect)</p>
                    <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                        {['Auto-Detect', 'Pharma Faculty', 'PhD Researcher', 'Industrial Scientist', 'Biostatistician', 'Innovation Engine'].map((mode) => (
                            <button
                                key={mode}
                                onClick={() => updateResearch('force_persona', mode)}
                                className={`text-xs px-3 py-2 rounded border transition-colors ${forcePersona === mode ? 'bg-purple-900 border-purple-500 text-white' : 'bg-slate-900 border-slate-700 text-slate-400 hover:border-slate-500 hover:text-slate-200'}`}
                            >
                                {mode}
                            </button>
                        ))}
                    </div>
                </div>

                <div className="flex items-center justify-between pt-4 border-t border-slate-700">
                    <div>
                        <label className="text-slate-200 font-medium">Internet Research</label>
                        <p className="text-xs text-slate-500">Allow agent to access external live data</p>
                    </div>
                    <input
                        type="checkbox"
                        checked={internetResearch}
                        onChange={(e) => updateResearch('internet_research', e.target.checked)}
                        className="h-5 w-5 rounded border-slate-600 bg-slate-900 text-purple-600 focus:ring-purple-500"
                    />
                </div>
            </div>
        </div>
    );
}
