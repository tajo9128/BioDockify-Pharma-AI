import React from 'react';
import { Settings } from '@/lib/api';
import { UserCircle, Building2, FlaskConical, Bot, Check } from 'lucide-react';

interface GeneralSettingsProps {
    settings: Settings;
    onSettingChange: (section: keyof Settings, value: any) => void;
}

export const GeneralSettings: React.FC<GeneralSettingsProps> = ({ settings, onSettingChange }) => {

    const updateProject = (key: string, value: string) => {
        onSettingChange('project', { ...settings.project, [key]: value });
    };

    const updatePersona = (key: string, value: string) => {
        onSettingChange('persona', { ...settings.persona, [key]: value });
    };

    return (
        <div className="space-y-6 animate-in fade-in duration-300">
            {/* Project Context */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
                <h3 className="text-lg font-semibold text-white mb-4 flex items-center">
                    <FlaskConical className="w-5 h-5 mr-2 text-teal-400" /> Current Project Context
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                        <label className="text-xs text-slate-500 uppercase block mb-1">Project Name</label>
                        <input
                            type="text"
                            value={settings.project?.name || ''}
                            onChange={(e) => updateProject('name', e.target.value)}
                            className="w-full bg-slate-950 border border-slate-800 rounded p-2 text-sm text-white focus:border-teal-500/50 focus:outline-none"
                            placeholder="New Project"
                        />
                    </div>
                    <div>
                        <label className="text-xs text-slate-500 uppercase block mb-1">Disease Context</label>
                        <input
                            type="text"
                            value={settings.project?.disease_context || ''}
                            onChange={(e) => updateProject('disease_context', e.target.value)}
                            className="w-full bg-slate-950 border border-slate-800 rounded p-2 text-sm text-white focus:border-teal-500/50 focus:outline-none"
                            placeholder="e.g. Alzheimer's, Oncology"
                        />
                    </div>
                    <div>
                        <label className="text-xs text-slate-500 uppercase block mb-1">Research Stage</label>
                        <select
                            value={settings.project?.stage || 'Early Discovery'}
                            onChange={(e) => updateProject('stage', e.target.value)}
                            className="w-full bg-slate-950 border border-slate-800 rounded p-2 text-sm text-white focus:border-teal-500/50 focus:outline-none"
                        >
                            <option value="Early Discovery">Early Discovery</option>
                            <option value="Target Validation">Target Validation</option>
                            <option value="Lead Optimization">Lead Optimization</option>
                            <option value="Preclinical">Preclinical</option>
                            <option value="Clinical">Clinical</option>
                        </select>
                    </div>
                    <div>
                        <label className="text-xs text-slate-500 uppercase block mb-1">Project Type</label>
                        <input
                            type="text"
                            value={settings.project?.type || ''}
                            onChange={(e) => updateProject('type', e.target.value)}
                            className="w-full bg-slate-950 border border-slate-800 rounded p-2 text-sm text-white focus:border-teal-500/50 focus:outline-none"
                            placeholder="e.g. Drug Discovery"
                        />
                    </div>
                </div>
            </div>

            {/* Researcher Persona */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
                <h3 className="text-lg font-semibold text-white mb-4 flex items-center">
                    <UserCircle className="w-5 h-5 mr-2 text-indigo-400" /> Researcher Profile
                </h3>
                <div className="space-y-4">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div>
                            <label className="text-xs text-slate-500 uppercase block mb-1">Full Name</label>
                            <input
                                type="text"
                                value={settings.persona?.name || ''}
                                onChange={(e) => updatePersona('name', e.target.value)}
                                className="w-full bg-slate-950 border border-slate-800 rounded p-2 text-sm text-white focus:border-indigo-500/50 focus:outline-none"
                                placeholder="Dr. Jane Doe"
                            />
                        </div>
                        <div>
                            <label className="text-xs text-slate-500 uppercase block mb-1">Email Address</label>
                            <input
                                type="email"
                                value={settings.persona?.email || ''}
                                onChange={(e) => updatePersona('email', e.target.value)}
                                className="w-full bg-slate-950 border border-slate-800 rounded p-2 text-sm text-white focus:border-indigo-500/50 focus:outline-none"
                                placeholder="jane.doe@university.edu"
                            />
                        </div>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div>
                            <label className="text-xs text-slate-500 uppercase block mb-1">Organization</label>
                            <div className="relative">
                                <Building2 className="absolute left-2 top-2.5 w-4 h-4 text-slate-500" />
                                <input
                                    type="text"
                                    value={settings.persona?.organization || ''}
                                    onChange={(e) => updatePersona('organization', e.target.value)}
                                    className="w-full bg-slate-950 border border-slate-800 rounded p-2 pl-8 text-sm text-white focus:border-indigo-500/50 focus:outline-none"
                                    placeholder="BioDockify Research Institute"
                                />
                            </div>
                        </div>
                        <div>
                            <label className="text-xs text-slate-500 uppercase block mb-1">Department</label>
                            <input
                                type="text"
                                value={settings.persona?.department || ''}
                                onChange={(e) => updatePersona('department', e.target.value)}
                                className="w-full bg-slate-950 border border-slate-800 rounded p-2 text-sm text-white focus:border-indigo-500/50 focus:outline-none"
                                placeholder="Molecular Biology"
                            />
                        </div>
                    </div>
                    <div>
                        <label className="text-xs text-slate-500 uppercase block mb-3 pl-1">Professional Roles (Select all that apply)</label>
                        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                            {[
                                { id: 'PhD Student', label: 'PhD Student' },
                                { id: 'PG Student', label: 'PG Student' },
                                { id: 'Faculty', label: 'Faculty' },
                                { id: 'Industry Scientist', label: 'Industry Scientist' },
                                { id: 'Senior Researcher', label: 'Senior Researcher' },
                                { id: 'Receptionist', label: 'Receptionist' }
                            ].map(role => {
                                const isSelected = settings.persona?.roles?.includes(role.id as any);
                                return (
                                    <button
                                        key={role.id}
                                        type="button"
                                        onClick={() => {
                                            const currentRoles = settings.persona?.roles || [];
                                            const newRoles = isSelected
                                                ? currentRoles.filter(r => r !== role.id)
                                                : [...currentRoles, role.id];
                                            onSettingChange('persona', { ...settings.persona, roles: newRoles });
                                        }}
                                        className={`flex items-center p-3 rounded-lg border transition-all ${isSelected
                                            ? 'bg-indigo-500/10 border-indigo-500 text-white ring-1 ring-indigo-500/30'
                                            : 'bg-slate-950 border-slate-800 text-slate-500 hover:border-slate-700'
                                            }`}
                                    >
                                        <div className={`w-4 h-4 rounded border mr-3 flex items-center justify-center transition-colors ${isSelected ? 'bg-indigo-500 border-indigo-500' : 'bg-slate-900 border-slate-700'}`}>
                                            {isSelected && <Check className="w-3 h-3 text-white" />}
                                        </div>
                                        <span className="text-sm font-medium">{role.label}</span>
                                    </button>
                                );
                            })}
                        </div>
                    </div>
                    <div>
                        <label className="text-xs text-slate-500 uppercase block mb-1">Introduction (Context for AI)</label>
                        <textarea
                            value={settings.persona?.introduction || ''}
                            onChange={(e) => updatePersona('introduction', e.target.value)}
                            className="w-full bg-slate-950 border border-slate-800 rounded p-2 text-sm text-white h-20 focus:border-indigo-500/50 focus:outline-none resize-none"
                            placeholder="I am a senior researcher focusing on protein folding simulations..."
                        />
                    </div>
                </div>
            </div>

            {/* AI Bot Identity */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
                <h3 className="text-lg font-semibold text-white mb-4 flex items-center">
                    <Bot className="w-5 h-5 mr-2 text-purple-400" /> AI Assistant Identity
                </h3>
                <div className="space-y-4">
                    <div>
                        <label className="text-xs text-slate-500 uppercase block mb-1">Assistant Name</label>
                        <input
                            type="text"
                            value={settings.persona?.bot_name || ''}
                            onChange={(e) => updatePersona('bot_name', e.target.value)}
                            className="w-full bg-slate-950 border border-slate-800 rounded p-2 text-sm text-white focus:border-purple-500/50 focus:outline-none"
                            placeholder="e.g. Helix"
                        />
                    </div>
                    <div>
                        <label className="text-xs text-slate-500 uppercase block mb-1">System Instructions / Persona</label>
                        <textarea
                            value={settings.persona?.bot_instructions || ''}
                            onChange={(e) => updatePersona('bot_instructions', e.target.value)}
                            className="w-full bg-slate-950 border border-slate-800 rounded p-2 text-sm text-white h-24 focus:border-purple-500/50 focus:outline-none resize-none"
                            placeholder="You are an expert pharmaceutical research assistant..."
                        />
                        <p className="text-[10px] text-slate-500 mt-1">These instructions steer the AI&apos;s high-level behavior and tone.</p>
                    </div>
                </div>
            </div>
        </div>
    );
};
