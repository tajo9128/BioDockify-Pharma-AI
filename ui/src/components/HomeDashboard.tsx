import React, { useEffect, useState } from 'react';
import api, { Project, EnhancedSystemStatus } from '@/lib/api';
import {
    FlaskConical, PenTool, Brain, Search,
    Database, Clock, ArrowRight, Zap,
    Target, Bot, Loader2, CheckCircle,
    AlertCircle, Activity
} from 'lucide-react';

interface HomeProps {
    onNavigate: (view: string) => void;
}

export default function HomeDashboard({ onNavigate }: HomeProps) {
    const [userName, setUserName] = useState<string>('Researcher');
    const [loading, setLoading] = useState(true);
    const [projects, setProjects] = useState<Project[]>([]);
    const [systemStatus, setSystemStatus] = useState<EnhancedSystemStatus | null>(null);

    useEffect(() => {
        const fetchData = async () => {
            try {
                // Try to get cached name first
                const localName = localStorage.getItem('biodockify_user_name');
                if (localName) setUserName(localName);

                // Parallel fetch
                const [settings, projectList, sysStatus] = await Promise.all([
                    api.getSettings().catch(() => null),
                    api.projects.list().catch(() => []),
                    api.projects.getSystemStatus().catch(() => null)
                ]);

                if (settings?.persona?.name) {
                    setUserName(settings.persona.name);
                    localStorage.setItem('biodockify_user_name', settings.persona.name);
                }

                setProjects(projectList || []);
                setSystemStatus(sysStatus);

            } catch (e) {
                console.error('Dashboard data fetch failed:', e);
            } finally {
                setLoading(false);
            }
        };

        fetchData();
        const poll = setInterval(fetchData, 30000); // Poll every 30s
        return () => clearInterval(poll);
    }, []);

    const RestrictedCard = ({ onClick, children, id }: { onClick: () => void, children: React.ReactNode, id: string }) => {
        // License check removed - Free for everyone
        const isLocked = false;

        return (
            <button
                onClick={onClick}
                className="group relative p-6 bg-gradient-to-br from-opacity-20 to-slate-900 border border-opacity-20 hover:border-opacity-50 from-slate-900 border-slate-800 rounded-2xl transition-all text-left overflow-hidden hover:border-slate-600"
            >
                {children}
            </button>
        );
    };

    return (
        <div className="h-full overflow-y-auto p-8 bg-slate-950">
            {/* Hero Section */}
            <div className="max-w-5xl mx-auto mb-12 animate-in fade-in slide-in-from-bottom-4 duration-500">
                <h1 className="text-4xl font-bold text-white mb-2">Welcome Back, {userName}</h1>
                <p className="text-slate-400 text-lg">BioDockify v2.4.9 Research Workstation. What shall we discover today?</p>

            </div>

            <div className="max-w-5xl mx-auto">
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-12">
                    {/* Main Action 1 - BioDockify AI Chat */}
                    <RestrictedCard id="agent-chat" onClick={() => onNavigate('agent-chat')}>
                        <div className="absolute top-0 right-0 p-4 opacity-50 group-hover:opacity-100 transition-opacity">
                            <ArrowRight className="w-5 h-5 text-teal-400" />
                        </div>
                        <div className="w-12 h-12 bg-teal-500/10 rounded-xl flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
                            <Bot className="w-6 h-6 text-teal-400" />
                        </div>
                        <h3 className="text-xl font-bold text-white mb-2">Chat</h3>
                        <p className="text-sm text-slate-400">Your AI research partner. Ask questions, plan experiments, and analyze data.</p>
                    </RestrictedCard>

                    {/* Main Action 2 - Research */}
                    <RestrictedCard id="research" onClick={() => onNavigate('research')}>
                        <div className="absolute top-0 right-0 p-4 opacity-50 group-hover:opacity-100 transition-opacity">
                            <ArrowRight className="w-5 h-5 text-indigo-400" />
                        </div>
                        <div className="w-12 h-12 bg-indigo-500/10 rounded-xl flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
                            <FlaskConical className="w-6 h-6 text-indigo-400" />
                        </div>
                        <h3 className="text-xl font-bold text-white mb-2">Research</h3>
                        <p className="text-sm text-slate-400">Advanced molecular analysis and simulation tools.</p>
                    </RestrictedCard>

                    {/* Main Action 3 - Academic Suite */}
                    <RestrictedCard id="writers" onClick={() => onNavigate('writers')}>
                        <div className="absolute top-0 right-0 p-4 opacity-50 group-hover:opacity-100 transition-opacity">
                            <ArrowRight className="w-5 h-5 text-purple-400" />
                        </div>
                        <div className="w-12 h-12 bg-purple-500/10 rounded-xl flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
                            <PenTool className="w-6 h-6 text-purple-400" />
                        </div>
                        <h3 className="text-xl font-bold text-white mb-2">Academic Writer</h3>
                        <p className="text-sm text-slate-400">Draft thesis chapters and review papers with AI assistance.</p>
                    </RestrictedCard>

                    {/* Main Action 4 (External) - ALWAYS UNLOCKED */}
                    <button
                        onClick={() => window.open('https://www.biodockify.com', '_blank')}
                        className="group relative p-6 bg-gradient-to-br from-cyan-900/30 to-slate-900 border border-cyan-500/20 rounded-2xl hover:border-cyan-500/50 transition-all text-left overflow-hidden"
                    >
                        <div className="absolute top-0 right-0 p-4 opacity-50 group-hover:opacity-100 transition-opacity">
                            <ArrowRight className="w-5 h-5 text-cyan-400" />
                        </div>
                        <div className="w-12 h-12 bg-cyan-500/10 rounded-xl flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
                            <FlaskConical className="w-6 h-6 text-cyan-400" />
                        </div>
                        <h3 className="text-xl font-bold text-white mb-2">Virtual Lab</h3>
                        <p className="text-sm text-slate-400">Access the full cloud-based Virtual Lab environment.</p>
                    </button>
                </div>

                {/* Status & Quick Stats */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="p-6 bg-slate-900/50 border border-slate-800 rounded-2xl">
                        <h3 className="text-lg font-semibold text-white mb-4 flex items-center">
                            <Zap className="w-5 h-5 mr-2 text-amber-400" /> System Health
                        </h3>
                        <div className="space-y-3">
                            <div className="flex items-center justify-between text-sm p-3 bg-slate-950 rounded-lg border border-slate-800">
                                <span className="text-slate-300">Project Scheduler</span>
                                <span className={`${systemStatus?.status === 'online' ? 'text-emerald-400' : 'text-amber-400'
                                    } flex items-center text-xs font-mono bg-slate-900 px-2 py-1 rounded`}>
                                    <span className={`w-2 h-2 ${systemStatus?.status === 'online' ? 'bg-emerald-400' : 'bg-amber-400'
                                        } rounded-full mr-2 ${systemStatus?.status === 'online' ? 'animate-pulse' : ''}`} />
                                    {systemStatus?.status?.toUpperCase() || 'UNKNOWN'}
                                </span>
                            </div>
                            <div className="grid grid-cols-2 gap-2 mt-4">
                                <div className="p-2 bg-slate-950 rounded-lg border border-slate-800/50 text-center">
                                    <div className="text-xs text-slate-500 uppercase">Active Devices</div>
                                    <div className="text-lg font-bold text-white">{systemStatus?.device_count || 0}</div>
                                </div>
                                <div className="p-2 bg-slate-950 rounded-lg border border-slate-800/50 text-center">
                                    <div className="text-xs text-slate-500 uppercase">Task Queue</div>
                                    <div className="text-lg font-bold text-white">{systemStatus?.queue_size || 0}</div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div className="p-6 bg-slate-900/50 border border-slate-800 rounded-2xl flex flex-col">
                        <h3 className="text-lg font-semibold text-white mb-4 flex items-center">
                            <Clock className="w-5 h-5 mr-2 text-sky-400" /> Active Projects
                        </h3>

                        <div className="flex-1 space-y-3 overflow-y-auto max-h-[220px] pr-2 custom-scrollbar">
                            {projects.length > 0 ? (
                                projects.map((p) => (
                                    <div key={p.id} className="p-3 bg-slate-950 rounded-xl border border-slate-800 hover:border-slate-700 transition-colors">
                                        <div className="flex justify-between items-start mb-2">
                                            <div className="font-medium text-white text-sm truncate pr-2">{p.title}</div>
                                            <div className={`text-[10px] px-1.5 py-0.5 rounded border ${p.status === 'executing' ? 'bg-indigo-500/10 border-indigo-500/30 text-indigo-400' :
                                                p.status === 'completed' ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400' :
                                                    'bg-slate-800 border-slate-700 text-slate-400'
                                                }`}>
                                                {p.status.toUpperCase()}
                                            </div>
                                        </div>
                                        <div className="w-full h-1 bg-slate-800 rounded-full overflow-hidden">
                                            <div
                                                className={`h-full transition-all duration-500 ${p.status === 'failed' ? 'bg-red-500' : 'bg-teal-500'
                                                    }`}
                                                style={{ width: `${p.progress}%` }}
                                            />
                                        </div>
                                        <div className="flex justify-between mt-1.5 text-[10px] text-slate-500 italic">
                                            <span>{p.type}</span>
                                            <span>{p.progress}% complete</span>
                                        </div>
                                    </div>
                                ))
                            ) : (
                                <div className="text-center py-8">
                                    <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-slate-800 mb-3">
                                        <Search className="w-5 h-5 text-slate-500" />
                                    </div>
                                    <p className="text-slate-400 text-sm">No active projects.</p>
                                    <button onClick={() => onNavigate('research')} className="mt-2 text-sky-400 hover:text-sky-300 text-sm font-medium">Create your first project</button>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}

