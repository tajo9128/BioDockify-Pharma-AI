import React, { useState } from 'react';
import { Settings, api } from '@/lib/api';
import { CloudKeyBox } from './CloudKeyBox';
import { Globe, Search, Database, Shield, BookOpen, Activity, FlaskConical } from 'lucide-react';

interface ResearchSettingsProps {
    settings: Settings;
    onSettingChange: (section: keyof Settings, value: any) => void;
}

interface ToggleCardProps {
    icon: React.ElementType;
    label: string;
    enabled: boolean;
    onClick: () => void;
    color?: string;
}

const ToggleCard = ({ icon: Icon, label, enabled, onClick, color = 'teal' }: ToggleCardProps) => (
    <button onClick={onClick} className={`flex items-center p-3 rounded-lg border transition-all ${enabled ? `bg-${color}-500/10 border-${color}-500/50 text-white` : 'bg-slate-950 border-slate-800 text-slate-500'} w-full`}>
        <div className={`p-2 rounded-md mr-3 ${enabled ? `bg-${color}-500 text-black` : 'bg-slate-900'}`}><Icon className="w-4 h-4" /></div>
        <span className="font-semibold text-sm">{label}</span>
    </button>
);

export const ResearchSettings: React.FC<ResearchSettingsProps> = ({ settings, onSettingChange }) => {

    // API Test State specifically for Search tools
    const [searchTestProgress, setSearchTestProgress] = useState<Record<string, {
        status: 'idle' | 'testing' | 'success' | 'error';
        progress: number;
        message: string;
        details: string;
    }>>({});

    const updatePharma = (key: string, value: any) => {
        onSettingChange('pharma', { ...settings.pharma, [key]: value });
    };

    const updatePharmaSource = (key: string, val: boolean) => {
        onSettingChange('pharma', {
            ...settings.pharma,
            sources: { ...(settings.pharma.sources || {}), [key]: val }
        });
    };

    const updateProvider = (key: string, value: string | boolean | number) => {
        onSettingChange('ai_provider', { ...settings.ai_provider, [key]: value });
    };

    const handleTestKey = async (provider: string, key?: string, serviceType: 'llm' | 'elsevier' | 'bohrium' | 'brave' = 'llm') => {
        if (!key && provider !== 'bohrium') return;

        const updateProgress = (updates: any) => {
            setSearchTestProgress(prev => ({ ...prev, [provider]: { ...prev[provider], ...updates } }));
        };

        updateProgress({ status: 'testing', progress: 20, message: 'Testing...', details: '' });

        try {
            // Construct the provider config
            const config: any = {
                ai_provider: {
                    mode: provider,
                }
            };

            // Map keys
            if (provider === 'brave') {
                config.ai_provider.brave_key = key;
            } else if (provider === 'serper') {
                config.ai_provider.serper_key = key;
            } else if (provider === 'bohrium') {
                config.ai_provider.bohrium_url = key; // key is used as URL for bohrium in this context based on usage
            }

            const result = await api.testConnection(config);
            if (result.status === 'success') {
                updateProgress({ status: 'success', progress: 100, message: 'PASSED', details: result.message });
            } else {
                throw new Error(result.message);
            }
        } catch (err: any) {
            updateProgress({ status: 'error', progress: 100, message: 'FAILED', details: err.message });
        }
    };

    return (
        <div className="space-y-6 animate-in fade-in duration-300">
            {/* SurfSense */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
                <h3 className="text-lg font-semibold text-white mb-4 flex items-center">
                    <Globe className="w-5 h-5 mr-2 text-indigo-400" /> SurfSense Knowledge Engine
                </h3>
                <div className="p-5 bg-slate-950 rounded-lg border border-slate-800">
                    <div className="flex items-center justify-between mb-4">
                        <div className="flex items-center gap-3">
                            <div className="p-2 bg-indigo-500/10 rounded-lg border border-indigo-500/20">
                                <Search className="w-5 h-5 text-indigo-400" />
                            </div>
                            <div>
                                <h4 className="font-bold text-slate-200">SurfSense Deep Research</h4>
                                <p className="text-xs text-slate-500">Autonomous web research and knowledge aggregation system.</p>
                            </div>
                        </div>
                        <div className="flex items-center gap-2">
                            <span className="text-xs text-slate-500">Auto-Start</span>
                            <button
                                onClick={() => updateProvider('surfsense_auto_start', !settings.ai_provider.surfsense_auto_start)}
                                className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${settings.ai_provider.surfsense_auto_start ? 'bg-indigo-600' : 'bg-slate-700'}`}
                            >
                                <span className={`inline-block h-3 w-3 transform rounded-full bg-white transition-transform ${settings.ai_provider.surfsense_auto_start ? 'translate-x-5' : 'translate-x-1'}`} />
                            </button>
                        </div>
                    </div>

                    <div className="space-y-3">
                        <div>
                            <label className="text-[10px] uppercase text-slate-500 font-bold mb-1 block">SurfSense API URL</label>
                            <input
                                type="text"
                                value={settings.ai_provider.surfsense_url || 'http://localhost:3003'}
                                onChange={(e) => updateProvider('surfsense_url', e.target.value)}
                                className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1.5 text-sm text-white focus:outline-none focus:border-indigo-500"
                                placeholder="http://localhost:3003"
                            />
                        </div>
                        <div>
                            <label className="text-[10px] uppercase text-slate-500 font-bold mb-1 block">Admin Key (Optional)</label>
                            <input
                                type="password"
                                value={settings.ai_provider.surfsense_key || ''}
                                onChange={(e) => updateProvider('surfsense_key', e.target.value)}
                                className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1.5 text-sm text-white focus:outline-none focus:border-indigo-500"
                                placeholder="Enter SurfSense API Key if configured..."
                            />
                        </div>
                    </div>
                </div>
            </div>

            {/* Search Engines */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
                <h3 className="text-lg font-semibold text-white mb-4 flex items-center">
                    <Search className="w-5 h-5 mr-2 text-purple-400" /> Search Engines & Swarms
                </h3>
                <div className="grid md:grid-cols-2 gap-4">
                    <CloudKeyBox name="Brave Search" icon="BR" value={settings.ai_provider.brave_key || ''} onChange={(v) => updateProvider('brave_key', v)} onTest={() => handleTestKey('brave', settings.ai_provider.brave_key, 'brave')} testStatus={searchTestProgress['brave']?.status} testProgress={searchTestProgress['brave']?.progress} testMessage={searchTestProgress['brave']?.message} testDetails={searchTestProgress['brave']?.details} modelPlaceholder="N/A" />
                    <CloudKeyBox name="Serper Dev" icon="SD" value={settings.ai_provider.serper_key || ''} onChange={(v) => updateProvider('serper_key', v)} onTest={() => handleTestKey('serper', settings.ai_provider.serper_key, 'brave')} testStatus={searchTestProgress['serper']?.status} testProgress={searchTestProgress['serper']?.progress} testMessage={searchTestProgress['serper']?.message} testDetails={searchTestProgress['serper']?.details} modelPlaceholder="N/A" />
                    {/* Bohrium */}
                    <div className="col-span-1 md:col-span-2 p-4 bg-slate-950 rounded-lg border border-slate-800">
                        <div className="flex items-center justify-between mb-3">
                            <div className="flex items-center space-x-2">
                                <span className="text-xs font-bold text-slate-400 font-mono bg-slate-900 px-2 py-1 rounded">BH</span>
                                <span className="text-sm font-medium text-slate-300">Bohrium Setup (Swarm Intelligence)</span>
                            </div>
                        </div>
                        <div className="flex space-x-2">
                            <input
                                type="text"
                                value={settings.ai_provider?.bohrium_url || ''}
                                onChange={(e) => updateProvider('bohrium_url', e.target.value)}
                                className="flex-1 bg-slate-900 border border-slate-700 rounded px-2 py-1 text-sm text-white placeholder-slate-600"
                                placeholder="http://localhost:8000"
                            />
                            <button
                                onClick={() => handleTestKey('bohrium', settings.ai_provider.bohrium_url, 'bohrium')}
                                disabled={searchTestProgress['bohrium']?.status === 'testing'}
                                className="px-3 bg-slate-800 text-xs text-white rounded hover:bg-slate-700 disabled:opacity-50"
                            >
                                Test
                            </button>
                        </div>
                        {/* Bohrium Status */}
                        {(searchTestProgress['bohrium']?.status && searchTestProgress['bohrium']?.status !== 'idle') && (
                            <div className="mt-2 text-xs text-slate-400">
                                Status: <span className={searchTestProgress['bohrium'].status === 'success' ? 'text-green-400' : 'text-red-400'}>{searchTestProgress['bohrium'].status.toUpperCase()}</span> - {searchTestProgress['bohrium'].message}
                            </div>
                        )}
                    </div>
                </div>
            </div>

            {/* Literature Sources */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
                <h3 className="text-lg font-semibold text-white mb-6 flex items-center">
                    <Database className="w-5 h-5 mr-2 text-cyan-400" /> Literature Sources
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <ToggleCard icon={Activity} label="PubMed" enabled={settings.pharma.sources?.pubmed} onClick={() => updatePharmaSource('pubmed', !settings.pharma.sources?.pubmed)} color="blue" />
                    <ToggleCard icon={Activity} label="PubMed Central" enabled={settings.pharma.sources?.pmc} onClick={() => updatePharmaSource('pmc', !settings.pharma.sources?.pmc)} color="emerald" />
                    <ToggleCard icon={Globe} label="Google Scholar" enabled={settings.pharma.sources?.google_scholar} onClick={() => updatePharmaSource('google_scholar', !settings.pharma.sources?.google_scholar)} color="sky" />
                    <ToggleCard icon={BookOpen} label="OpenAlex" enabled={settings.pharma.sources?.openalex} onClick={() => updatePharmaSource('openalex', !settings.pharma.sources?.openalex)} color="indigo" />
                    <ToggleCard icon={FlaskConical} label="BioRxiv (Preprints)" enabled={settings.pharma.sources?.biorxiv} onClick={() => updatePharmaSource('biorxiv', !settings.pharma.sources?.biorxiv)} color="red" />
                    <ToggleCard icon={FlaskConical} label="ChemRxiv" enabled={settings.pharma.sources?.chemrxiv} onClick={() => updatePharmaSource('chemrxiv', !settings.pharma.sources?.chemrxiv)} color="cyan" />
                    <ToggleCard icon={Activity} label="ClinicalTrials.gov" enabled={settings.pharma.sources?.clinicaltrials} onClick={() => updatePharmaSource('clinicaltrials', !settings.pharma.sources?.clinicaltrials)} color="teal" />
                    <ToggleCard icon={BookOpen} label="Semantic Scholar" enabled={settings.pharma.sources?.semantic_scholar} onClick={() => updatePharmaSource('semantic_scholar', !settings.pharma.sources?.semantic_scholar)} color="blue" />
                    <ToggleCard icon={Globe} label="IEEE Xplore" enabled={settings.pharma.sources?.ieee} onClick={() => updatePharmaSource('ieee', !settings.pharma.sources?.ieee)} color="slate" />
                    <ToggleCard icon={Database} label="Elsevier" enabled={settings.pharma.sources?.elsevier} onClick={() => updatePharmaSource('elsevier', !settings.pharma.sources?.elsevier)} color="orange" />
                </div>
            </div>

            {/* Compliance */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
                <h3 className="text-lg font-semibold text-white mb-4 flex items-center">
                    <Shield className="w-5 h-5 mr-2 text-emerald-400" /> Compliance & Safety
                </h3>
                <div className="flex items-center justify-between p-4 bg-slate-950 rounded-lg border border-slate-800">
                    <div>
                        <h4 className="text-sm font-semibold text-white">Citation Lock</h4>
                        <p className="text-xs text-slate-400">Lock outputs without sufficient sources.</p>
                    </div>
                    <select value={settings.pharma?.citation_threshold || 'medium'} onChange={(e) => updatePharma('citation_threshold', e.target.value)} className="bg-slate-900 border border-slate-700 text-white text-sm rounded px-2 py-1">
                        <option value="low">Low</option>
                        <option value="medium">Standard</option>
                        <option value="high">Strict</option>
                    </select>
                </div>
            </div>
        </div>
    );
};
