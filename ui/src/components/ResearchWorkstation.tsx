// --- Imports ---
import React, { useState, useEffect, useRef } from 'react';
import { api } from '@/lib/api';
import { useOnlineStatus } from '@/hooks/useOnlineStatus';
import { useAutoSave } from '@/hooks/useAutoSave';
import { Search, PenTool, Layout, Play, Pause, Square, AlertCircle, FileText, Globe, Cpu, ChevronRight, Maximize2, Beaker, Save, RotateCcw, Database, X, Plus, Settings, Terminal, Network, Share2, Activity, Zap, Link as LinkIcon, WifiOff, Loader2, ShieldCheck } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import ExternalInsightImporter, { ExternalAIInsight } from './ExternalInsightImporter';
import { DeepResearchView } from './deep-research/DeepResearchView';
import { ThesisWriterView } from './thesis/ThesisWriterView';
import { cn } from '@/lib/utils';
import DiagnosisDialog from '@/components/DiagnosisDialog';
import AgentStatusPanel from '@/components/AgentStatusPanel';

// Types (Micro-definitions to be self-contained)
type WorkMode = 'search' | 'synthesize' | 'write' | 'thesis_writer' | 'review_writer' | 'research_writer';
interface LogEntry { id: string; type: 'info' | 'thought' | 'result' | 'action' | 'error'; content: string; timestamp: Date; description?: string; }

// ... (inside component)
interface Evidence { id: string; title: string; score: number; year: number; }
interface Insight { id: string; title: string; content: string; source: string; type: 'internal' | 'external'; }

interface ResearchWorkstationProps {
    view?: string;
    // Agent Props
    goal?: string;
    onGoalChange?: (g: string) => void;
    onExecute?: () => void;
    onStop?: () => void;
    isExecuting?: boolean;
    thinkingSteps?: any[];
    error?: string | null;
    // New Props for Lifted State
    mode?: WorkMode;
    onModeChange?: (m: WorkMode) => void;
}

export default function ResearchWorkstation({
    view = 'home',
    goal = '',
    onGoalChange = () => { },
    onExecute = () => { },
    onStop = () => { },
    isExecuting = false,
    thinkingSteps = [],
    error = null,
    mode = 'search', // Default if not provided
    onModeChange
}: ResearchWorkstationProps) {
    // State
    // Internal state only if onModeChange is NOT provided (fallback for backward compat)
    const [internalMode, setInternalMode] = useState<WorkMode>('search');

    // Derived state: use prop if available, else internal
    const activeMode = onModeChange ? mode : internalMode;
    const setActiveMode = (m: WorkMode) => {
        if (onModeChange) onModeChange(m);
        else setInternalMode(m);
    };

    // Remove local query/isRunning state in favor of props
    const [evidence, setEvidence] = useState<Evidence[]>([]);
    const [externalInsights, setExternalInsights] = useState<ExternalAIInsight[]>([]);
    const [showImporter, setShowImporter] = useState(false);
    const [isFocusMode, setIsFocusMode] = useState(false);

    // Reviewer Agent State
    const [isReviewing, setIsReviewing] = useState(false);
    const [reviewResult, setReviewResult] = useState<any>(null);

    // Auto-Save Integration
    useAutoSave('biodockify_research_goal', goal);
    useAutoSave('biodockify_work_mode', mode);

    // Auto-scroll logic
    const logEndRef = useRef<HTMLDivElement>(null);
    useEffect(() => { logEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [thinkingSteps]); // Scroll on thinking steps

    const handleImportInsight = (insight: ExternalAIInsight) => {
        setExternalInsights(prev => [...prev, insight]);
        setShowImporter(false);
    };

    const handleReviewStream = async () => {
        if (thinkingSteps.length === 0) return;
        setIsReviewing(true);
        try {
            const allText = thinkingSteps.map(s => s.content || s.description || '').join('\n\n');
            const result = await api.literature.verifyCitations(allText);
            setReviewResult(result);
        } catch (e) {
            console.error("Stream review failed", e);
        } finally {
            setIsReviewing(false);
        }
    };

    // --- VIEW: RESULTS MANAGER ---
    if (view === 'results') {
        return (
            <div className="h-screen bg-slate-950 text-slate-200 p-8 overflow-y-auto">
                <header className="mb-8 border-b border-slate-800 pb-4">
                    <h1 className="text-2xl font-bold text-white flex items-center gap-3">
                        <FileText className="w-8 h-8 text-teal-400" />
                        Research Results & History
                    </h1>
                </header>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {/* Placeholder Cards for History */}
                    {['Alzheimer Target ID', 'CRISPR Off-Target Analysis', 'PD-L1 Pathway Review'].map((project, i) => (
                        <div key={i} className="bg-slate-900 border border-slate-800 rounded-xl p-6 hover:border-teal-500/50 transition-colors cursor-pointer group">
                            <div className="flex justify-between items-start mb-4">
                                <div className="p-3 bg-teal-500/10 rounded-lg text-teal-400 group-hover:text-teal-300">
                                    <FileText className="w-6 h-6" />
                                </div>
                                <span className="text-xs font-mono text-slate-500">2d ago</span>
                            </div>
                            <h3 className="text-lg font-bold text-slate-200 mb-2 group-hover:text-white">{project}</h3>
                            <p className="text-sm text-slate-400 mb-4">Completed analysis with 45 verified citations.</p>
                            <div className="flex items-center gap-2 text-xs font-medium text-slate-500">
                                <span className="px-2 py-1 bg-slate-800 rounded">PDF</span>
                                <span className="px-2 py-1 bg-slate-800 rounded">DOCX</span>
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        );
    }

    // --- VIEW: LAB INTERFACE ---
    if (view === 'lab') {
        return (
            <div className="h-screen bg-slate-950 text-slate-200 flex items-center justify-center">
                <div className="text-center space-y-6 max-w-lg">
                    <div className="w-24 h-24 bg-slate-900 rounded-full flex items-center justify-center mx-auto border-2 border-slate-800 animate-pulse">
                        <Beaker className="w-10 h-10 text-purple-400" />
                    </div>
                    <div>
                        <h1 className="text-2xl font-bold text-white mb-2">Virtual Lab Interface</h1>
                        <p className="text-slate-400">
                            Simulations for Molecular Docking (AutoDock Vina) and Protein Folding (AlphaFold adapter) are currently initializing.
                        </p>
                    </div>
                    <a
                        href="https://www.biodockify.com"
                        target="_blank"
                        rel="noopener noreferrer"
                        className="px-6 py-2 bg-purple-600/20 text-purple-400 border border-purple-600/50 rounded-lg hover:bg-purple-600/30 transition-colors inline-block"
                    >
                        Connect to BioDockify Cloud Lab
                    </a>
                </div>
            </div>
        );
    }

    // --- VIEW: AUTONOMOUS DEEP RESEARCH ---
    if (view === 'autonomous') {
        return (
            <div className="h-screen bg-slate-950 text-slate-200 overflow-y-auto">
                <DeepResearchView />
            </div>
        );
    }

    // --- MODE: PHD THESIS WRITER (Full Screen Overlay) ---
    if (mode === 'thesis_writer') {
        return (
            <div className="h-screen bg-slate-950 text-slate-200 overflow-hidden relative">
                <button
                    onClick={() => setActiveMode('search')}
                    className="absolute top-5 right-6 z-50 px-3 py-1 bg-slate-800 text-slate-400 text-xs rounded hover:bg-slate-700 border border-slate-700"
                >
                    Exit Thesis Mode
                </button>
                <ThesisWriterView />
            </div>
        );
    }

    // --- VIEW: STANDARD WORKSTATION (Home/Research) ---
    return (
        <div className="h-screen flex flex-col bg-slate-950 text-slate-200 overflow-hidden font-sans">
            {/* Header */}
            <header className="h-14 border-b border-slate-800 flex items-center justify-between px-6 bg-slate-950/80 backdrop-blur flex-shrink-0">
                <div className="flex items-center space-x-3">
                    <Layout className="w-5 h-5 text-teal-400" />
                    <span className="font-bold text-white tracking-wide hidden md:inline">BioDockify <span className="text-slate-600 font-normal">Workstation</span></span>
                </div>
                <div className="flex items-center space-x-4">
                    <span className={`flex items-center text-xs font-mono px-2 py-1 rounded bg-slate-900 border border-slate-700 ${isExecuting ? 'text-green-400 animate-pulse' : 'text-slate-500'} `}>
                        <Cpu className="w-3 h-3 mr-2" />
                        {isExecuting ? 'AGENT ACTIVE' : 'IDLE'}
                    </span>
                    <button
                        onClick={() => setIsFocusMode(!isFocusMode)}
                        className={`p-2 rounded-lg transition-colors ${isFocusMode ? 'bg-teal-500/20 text-teal-400' : 'hover:bg-slate-800 text-slate-400'} `}
                        title="Toggle Focus Mode"
                    >
                        <Maximize2 className="w-4 h-4" />
                    </button>
                </div>
            </header>

            {/* Main Layout (Responsive) */}
            <div className="flex-1 flex overflow-hidden relative">

                {/* COL 1: CONTROL PANEL (Hidden in Focus Mode or Small Screens) */}
                <div className={`border-r border-slate-800 bg-slate-950 flex flex-col transition-all duration-300 ease-in-out
                    ${isFocusMode ? 'w-0 opacity-0 overflow-hidden' : 'w-80 opacity-100'}
                    ${/* Mobile: Hide by default if streaming - simplistic responsive logic */ ''}
                    hidden md:flex flex-shrink-0
    `}>
                    <div className="p-6 space-y-6 w-80">
                        {/* Mode Selector */}
                        <div>
                            <label className="text-xs font-bold text-slate-500 uppercase tracking-widest mb-3 block">Operation Mode</label>
                            <div className="grid grid-cols-1 gap-2">
                                <ModeBtn id="search" label="Discovery" icon={Search} active={activeMode === 'search'} onClick={() => setActiveMode('search')} />
                                <ModeBtn id="synthesize" label="Synthesis" icon={FileText} active={activeMode === 'synthesize'} onClick={() => setActiveMode('synthesize')} />
                                <ModeBtn id="write" label="Drafting" icon={PenTool} active={activeMode === 'write'} onClick={() => setActiveMode('write')} />
                                <ModeBtn id="thesis_writer" label="PhD Thesis" icon={Globe} active={activeMode === 'thesis_writer'} onClick={() => setActiveMode('thesis_writer')} />
                                <ModeBtn id="review_writer" label="Intl. Review" icon={Beaker} active={activeMode === 'review_writer'} onClick={() => setActiveMode('review_writer')} />
                                <ModeBtn id="research_writer" label="Orig. Research" icon={FileText} active={activeMode === 'research_writer'} onClick={() => setActiveMode('research_writer')} />
                            </div>
                        </div>

                        {/* Input Area */}
                        <div className="flex-1 flex flex-col">
                            <label className="text-xs font-bold text-slate-500 uppercase tracking-widest mb-3 block">Research Goal</label>
                            <textarea
                                value={goal}
                                onChange={(e) => onGoalChange(e.target.value)}
                                placeholder="Describe your research objective..."
                                className="w-full h-32 bg-slate-900 border border-slate-700 rounded-xl p-4 text-sm text-white resize-none focus:ring-1 focus:ring-teal-500 outline-none"
                            />
                        </div>

                        {/* Actions */}
                        <div className="grid grid-cols-3 gap-2">
                            <button
                                onClick={onExecute}
                                disabled={isExecuting || !goal.trim()}
                                className="col-span-2 bg-teal-600 hover:bg-teal-500 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg py-3 font-bold flex items-center justify-center space-x-2 transition-all shadow-lg shadow-teal-900/20"
                                title={isExecuting ? "Agent is running..." : !goal.trim() ? "Please enter a research goal" : "Start Analysis"}
                            >
                                {isExecuting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4 fill-current" />}
                                <span>{isExecuting ? 'RUNNING' : 'START'}</span>
                            </button>
                            <button
                                onClick={onStop}
                                disabled={!isExecuting}
                                className="bg-slate-800 hover:bg-red-500/20 hover:text-red-400 text-slate-400 rounded-lg flex items-center justify-center transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                                <Square className="w-4 h-4 fill-current" />
                            </button>
                        </div>
                    </div>

                    {/* Status Footer */}
                    <div className="mt-auto p-4 border-t border-slate-800 bg-slate-900/50 w-80">
                        {/* Imported Insights List Mini-View */}
                        <div className="mb-4">
                            <div className="flex items-center justify-between mb-2">
                                <label className="text-xs font-bold text-slate-500 uppercase tracking-widest">External Context</label>
                                <button onClick={() => setShowImporter(!showImporter)} className="text-teal-500 hover:text-teal-400">
                                    <Plus className="w-3 h-3" />
                                </button>
                            </div>

                            {showImporter && (
                                <div className="absolute left-6 z-50 w-96 shadow-2xl animate-in slide-in-from-left-4 fade-in duration-200">
                                    <div className="relative">
                                        <button onClick={() => setShowImporter(false)} className="absolute right-2 top-2 text-slate-500 hover:text-white z-10">
                                            <X className="w-4 h-4" />
                                        </button>
                                        <ExternalInsightImporter onImport={handleImportInsight} />
                                    </div>
                                </div>
                            )}

                            <div className="space-y-2 max-h-32 overflow-y-auto pr-1">
                                {externalInsights.length === 0 ? (
                                    <p className="text-xs text-slate-600 italic">No external insights added.</p>
                                ) : (
                                    externalInsights.map(insight => (
                                        <div key={insight.id} className="bg-slate-900 p-2 rounded border border-slate-800 text-xs">
                                            <div className="flex justify-between text-slate-500 mb-1">
                                                <span className="font-bold">{insight.tool}</span>
                                                <span>{new Date(insight.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                                            </div>
                                            <p className="text-slate-300 line-clamp-2">{insight.summary}</p>
                                        </div>
                                    ))
                                )}
                            </div>
                        </div>

                        <div className="flex items-center justify-between text-xs text-slate-500 pt-2 border-t border-slate-800">
                            <span>Pharma Pipeline:</span>
                            <span className="text-green-400 font-bold">READY</span>
                        </div>
                    </div>
                </div>

                {/* COL 2: STREAM (Reasoning Engine) - Always Visible, Flex-1 */}
                <div className="flex-1 border-r border-slate-800 bg-slate-950 flex flex-col relative min-w-0">
                    {/* Agent Status Panel - Real-time Thinking Visualization */}
                    {isExecuting && (
                        <div className="p-4 border-b border-slate-800">
                            <AgentStatusPanel
                                useWebSocket={true}
                                apiBaseUrl={process.env.NEXT_PUBLIC_API_URL || "http://localhost:3000"}
                            />
                        </div>
                    )}

                    <div className="p-4 border-b border-slate-800 bg-slate-950/80 backdrop-blur sticky top-0 z-10 flex justify-between items-center">
                        <h2 className="text-sm font-bold text-slate-300">Reasoning Stream</h2>
                        <div className="flex items-center gap-2">
                            {reviewResult && (
                                <div className={`flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full border ${reviewResult.integrity_score > 80 ? 'bg-green-500/10 border-green-500/30 text-green-400' : 'bg-red-500/10 border-red-500/30 text-red-400'}`}>
                                    <ShieldCheck className="w-3 h-3" />
                                    <span>{reviewResult.integrity_score}% Integrity</span>
                                </div>
                            )}
                            <button
                                onClick={handleReviewStream}
                                disabled={isReviewing || thinkingSteps.length === 0}
                                className="text-xs text-teal-400 hover:underline disabled:opacity-50 disabled:no-underline flex items-center gap-1"
                            >
                                {isReviewing ? <Loader2 className="w-3 h-3 animate-spin" /> : <ShieldCheck className="w-3 h-3" />}
                                {isReviewing ? 'Verifying...' : 'Verify Citations'}
                            </button>
                            <button className="text-xs text-slate-500 hover:text-slate-300">Export Logs</button>
                        </div>
                    </div>

                    <div className="flex-1 overflow-y-auto p-6 space-y-6 scroll-smooth">
                        {thinkingSteps.length === 0 && (
                            <div className="h-full flex flex-col items-center justify-center text-slate-700 space-y-4">
                                <Cpu className="w-16 h-16 opacity-20" />
                                <p>Agent is awaiting instructions...</p>
                            </div>
                        )}
                        {thinkingSteps.map((step, idx) => (
                            <div key={idx} className="group animate-in fade-in slide-in-from-bottom-2 duration-300">
                                <div className="flex items-start space-x-3">
                                    <div className={`mt-1 w-2 h-2 rounded-full flex-shrink-0 ${step.type === 'thought' ? 'bg-purple-500' :
                                        step.type === 'result' ? 'bg-green-500' : 'bg-slate-500'
                                        } `} />
                                    <div className="space-y-1 min-w-0">
                                        <span className="text-xs text-slate-500 font-mono uppercase">{step.type}</span>
                                        <div className={`text-sm leading-relaxed ${step.type === 'thought' ? 'text-slate-400 italic' : 'text-slate-200'} break-words`}>
                                            <ReactMarkdown>{step.description || step.content}</ReactMarkdown>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        ))}
                        <div ref={logEndRef} />
                    </div>
                </div>

                {/* COL 3: KNOWLEDGE GRAPH (Evidence) - Hidden in Focus Mode, Stacked? */}
                <div className={`bg-slate-950 flex flex-col transition-all duration-300 ease-in-out
                     ${isFocusMode ? 'w-0 opacity-0 overflow-hidden' : 'w-96 opacity-100'}
border-l border-slate-800 hidden xl:flex flex-shrink-0
    `}>
                    <div className="p-4 border-b border-slate-800 bg-slate-950/80 backdrop-blur sticky top-0 z-10">
                        <h2 className="text-sm font-bold text-slate-300">Live Evidence</h2>
                    </div>

                    <div className="flex-1 overflow-y-auto p-4 space-y-3 w-96">
                        {evidence.length === 0 ? (
                            <div className="text-center py-12 text-slate-600 text-sm">
                                No evidence collected yet.
                            </div>
                        ) : (
                            evidence.map((ev) => (
                                <div key={ev.id} className="p-3 bg-slate-900 border border-slate-800 rounded-lg hover:border-slate-700 transition-colors group cursor-pointer">
                                    <h4 className="text-sm font-medium text-blue-400 group-hover:underline line-clamp-2">{ev.title}</h4>
                                    <div className="mt-2 flex items-center justify-between text-xs text-slate-500">
                                        <span>{ev.year}</span>
                                        <span className="flex items-center text-teal-500 font-mono">
                                            Inf: {ev.score}
                                        </span>
                                    </div>
                                </div>
                            ))
                        )}
                    </div>
                </div>

            </div>
        </div>
    );
}

const ModeBtn = ({ id, label, icon: Icon, active, onClick }: any) => (
    <button
        onClick={onClick}
        className={`w-full flex items-center p-3 rounded-lg transition-all border ${active
            ? 'bg-teal-500/10 border-teal-500/50 text-white'
            : 'bg-slate-900 border-transparent text-slate-500 hover:bg-slate-800 hover:text-slate-300'
            } `}
    >
        <div className={`p-2 rounded-md mr-3 ${active ? 'bg-teal-500 text-black' : 'bg-slate-800'} `}>
            <Icon className="w-4 h-4" />
        </div>
        <div className="text-left">
            <span className={`block text-sm font-bold ${active ? 'text-teal-400' : 'text-slate-400'} `}>{label}</span>
        </div>
        {active && <ChevronRight className="w-4 h-4 ml-auto text-teal-500" />}
    </button>
);
