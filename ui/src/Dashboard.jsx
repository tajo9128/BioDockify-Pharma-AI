import React, { useState, useEffect, useRef } from 'react';

// Status Badge Component
const StatusBadge = ({ status }) => {
    const colors = {
        pending: 'bg-gray-800 text-gray-400 border-gray-700',
        running: 'bg-cyan-900/30 text-cyan-400 border-cyan-800 animate-pulse',
        completed: 'bg-emerald-900/30 text-emerald-400 border-emerald-800',
        failed: 'bg-red-900/30 text-red-400 border-red-800'
    };

    return (
        <span className={`px-2 py-1 rounded-md text-xs font-mono border ${colors[status] || colors.pending}`}>
            {status.toUpperCase()}
        </span>
    );
};

// Step Indicator Component
const StepIndicator = ({ step, currentStep, label }) => {
    const isCompleted = currentStep > step;
    const isActive = currentStep === step;
    const isPending = currentStep < step;

    return (
        <div className="flex flex-col items-center z-10">
            <div
                className={`w-10 h-10 rounded-full flex items-center justify-center border-2 transition-all duration-500
        ${isCompleted ? 'bg-emerald-500 border-emerald-500 shadow-[0_0_15px_rgba(16,185,129,0.4)]' : ''}
        ${isActive ? 'bg-cyan-900/80 border-cyan-400 text-cyan-100 shadow-[0_0_15px_rgba(34,211,238,0.3)]' : ''}
        ${isPending ? 'bg-gray-900 border-gray-700 text-gray-600' : ''}
        `}
            >
                {isCompleted ? (
                    <svg className="w-6 h-6 text-black" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                    </svg>
                ) : (
                    <span className="font-bold font-mono">{step + 1}</span>
                )}
            </div>
            <span className={`mt-3 text-xs font-medium tracking-wider uppercase transition-colors duration-300
        ${isActive ? 'text-cyan-400' : isCompleted ? 'text-emerald-400' : 'text-gray-600'}
      `}>
                {label}
            </span>
        </div>
    );
};

const Dashboard = () => {
    const [mode, setMode] = useState('local');
    const [researchTitle, setResearchTitle] = useState('');
    const [taskId, setTaskId] = useState(null);
    const [status, setStatus] = useState('idle'); // idle, pending, running, completed, failed
    const [progress, setProgress] = useState(0);
    const [logs, setLogs] = useState([]);
    const [currentStep, setCurrentStep] = useState(0);

    const consoleEndRef = useRef(null);

    // Auto-scroll logs
    useEffect(() => {
        consoleEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [logs]);

    // Connect to WebSocket when task starts
    useEffect(() => {
        if (status === 'running' || status === 'pending') {
            // In a real app, this connects to the backend
            // const ws = new WebSocket('ws://localhost:8234/ws/status');
            // For Zero-Cost MVP validation, we'll simulate the stream if API isn't present

            const timer = setInterval(() => {
                // Simulation logic
                setProgress(prev => {
                    if (prev >= 100) {
                        setStatus('completed');
                        clearInterval(timer);
                        return 100;
                    }
                    return prev + 1;
                });

                // Determine step based on progress
                const step = Math.floor(progress / 25);
                if (step !== currentStep) {
                    setCurrentStep(step);
                    addLog(`Starting Phase ${step + 1}: ${['Literature Search', 'Entity Extraction', 'Graph Build', 'Synthesis'][step]}...`);
                }
            }, 200);

            return () => clearInterval(timer);
        }
    }, [status, currentStep, progress]);

    const addLog = (message) => {
        const timestamp = new Date().toLocaleTimeString('en-US', { hour12: false });
        setLogs(prev => [...prev, `[${timestamp}] ${message}`]);
    };

    const handleStartResearch = async () => {
        if (!researchTitle.trim()) return;

        setStatus('running');
        setLogs([]);
        setProgress(0);
        setCurrentStep(0);
        addLog(`Initializing BioDockify Runtime...`);
        addLog(`Mode: ${mode.toUpperCase()} (Offline-First)`);
        addLog(`Task: ${researchTitle}`);

        // API Call would go here:
        // await fetch('http://localhost:8234/api/research/start', ...)
    };

    const steps = [
        { label: "Search" },
        { label: "Parse" },
        { label: "Graph" },
        { label: "Synthesize" }
    ];

    return (
        <div className="min-h-screen bg-[#0a0a0c] text-slate-200 font-sans selection:bg-cyan-500/30">
            {/* Background Decor */}
            <div className="fixed inset-0 z-0 pointer-events-none">
                <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-purple-900/10 rounded-full blur-[120px]"></div>
                <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-cyan-900/10 rounded-full blur-[120px]"></div>
            </div>

            <div className="relative z-10 max-w-6xl mx-auto px-6 py-8 flex flex-col h-screen">

                {/* Header */}
                <header className="flex items-center justify-between mb-12 border-b border-white/5 pb-6">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 bg-gradient-to-br from-cyan-500 to-blue-600 rounded-lg flex items-center justify-center shadow-lg shadow-cyan-500/20">
                            <span className="font-bold text-white text-xl">B</span>
                        </div>
                        <div>
                            <h1 className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-white to-slate-400">
                                BioDockify
                            </h1>
                            <p className="text-xs text-slate-500 font-medium tracking-wide">PHARMA RESEARCH AI</p>
                        </div>
                    </div>

                    <div className="flex items-center gap-6 bg-white/5 px-4 py-2 rounded-full border border-white/5 backdrop-blur-sm">
                        <div className="flex items-center gap-3">
                            <span className={`text-sm ${mode === 'local' ? 'text-emerald-400' : 'text-slate-500'}`}>Offline</span>
                            <button
                                onClick={() => setMode(mode === 'local' ? 'cloud' : 'local')}
                                className={`w-12 h-6 rounded-full relative transition-colors duration-300 ${mode === 'local' ? 'bg-emerald-900/50' : 'bg-blue-900/50'}`}
                            >
                                <div className={`absolute top-1 w-4 h-4 rounded-full bg-white transition-all duration-300 ${mode === 'local' ? 'left-1' : 'left-7'}`}></div>
                            </button>
                            <span className={`text-sm ${mode === 'cloud' ? 'text-blue-400' : 'text-slate-500'}`}>Cloud (BYOK)</span>
                        </div>
                    </div>
                </header>

                {/* Main Content Area */}
                <main className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-8">

                    {/* Left Column: Input and Progress (4 cols) */}
                    <div className="lg:col-span-4 space-y-8 flex flex-col">

                        {/* Input Card */}
                        <div className="bg-white/5 border border-white/10 rounded-2xl p-6 backdrop-blur-md shadow-xl">
                            <label className="block text-sm font-medium text-slate-400 mb-2">Research Target</label>
                            <input
                                type="text"
                                value={researchTitle}
                                onChange={(e) => setResearchTitle(e.target.value)}
                                placeholder="e.g. Kinase inhibitors for Alzheimer's"
                                className="w-full bg-black/20 border border-white/10 rounded-lg px-4 py-3 text-white placeholder-slate-600 focus:outline-none focus:border-cyan-500/50 focus:ring-1 focus:ring-cyan-500/50 transition-all mb-4"
                            />
                            <button
                                onClick={handleStartResearch}
                                disabled={status === 'running'}
                                className="w-full bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white font-bold py-3 rounded-lg shadow-lg shadow-cyan-900/20 disabled:opacity-50 disabled:cursor-not-allowed transition-all active:scale-[0.98] flex items-center justify-center gap-2"
                            >
                                {status === 'running' ? (
                                    <>
                                        <svg className="animate-spin h-5 w-5 text-white" fill="none" viewBox="0 0 24 24">
                                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                        </svg>
                                        Processing...
                                    </>
                                ) : 'Start Research'}
                            </button>
                        </div>

                        {/* Stepper */}
                        <div className="relative flex justify-between px-2 pt-4">
                            {/* Connecting Line */}
                            <div className="absolute top-5 left-0 w-full h-0.5 bg-gray-800 -z-0"></div>
                            <div
                                className="absolute top-5 left-0 h-0.5 bg-gradient-to-r from-cyan-500 to-emerald-500 -z-0 transition-all duration-700"
                                style={{ width: `${Math.max(0, (progress - 10))}%` }}
                            ></div>

                            {steps.map((s, idx) => (
                                <StepIndicator
                                    key={idx}
                                    step={idx}
                                    currentStep={currentStep}
                                    label={s.label}
                                />
                            ))}
                        </div>

                        {/* Info Cards */}
                        <div className="grid grid-cols-1 gap-4 mt-auto">
                            <div className="bg-white/5 border border-white/5 p-4 rounded-xl flex items-center gap-4">
                                <div className="p-2 bg-purple-500/20 rounded-lg text-purple-400">
                                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>
                                </div>
                                <div>
                                    <h3 className="text-sm font-bold text-white">Real-time Analysis</h3>
                                    <p className="text-xs text-slate-500">Live molecule validation</p>
                                </div>
                            </div>
                        </div>

                    </div>

                    {/* Right Column: Console/Results (8 cols) */}
                    <div className="lg:col-span-8 flex flex-col h-full min-h-[500px]">
                        {/* Console Window */}
                        <div className="flex-1 bg-[#0f1115] rounded-2xl border border-white/10 overflow-hidden flex flex-col shadow-2xl relative">

                            {/* Terminal Header */}
                            <div className="bg-[#1a1d24] px-4 py-3 flex items-center justify-between border-b border-white/5">
                                <div className="flex gap-2">
                                    <div className="w-3 h-3 rounded-full bg-red-500/20 border border-red-500/50"></div>
                                    <div className="w-3 h-3 rounded-full bg-yellow-500/20 border border-yellow-500/50"></div>
                                    <div className="w-3 h-3 rounded-full bg-green-500/20 border border-green-500/50"></div>
                                </div>
                                <div className="text-xs font-mono text-slate-500 flex items-center gap-2">
                                    <StatusBadge status={status === 'idle' ? 'pending' : status} />
                                    <span>runtime.log</span>
                                </div>
                            </div>

                            {/* Logs Area */}
                            <div className="flex-1 p-4 font-mono text-sm overflow-y-auto space-y-2 scrollbar-thin scrollbar-thumb-white/10 scrollbar-track-transparent">
                                {logs.length === 0 && (
                                    <div className="h-full flex flex-col items-center justify-center text-slate-600 opacity-50">
                                        <svg className="w-12 h-12 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                                        </svg>
                                        <p>Ready to initialize research sequence...</p>
                                    </div>
                                )}

                                {logs.map((log, i) => (
                                    <div key={i} className="flex gap-3 animate-in fade-in slide-in-from-left-2 duration-300">
                                        <span className="text-slate-600 select-none">{log.split(']')[0]}]</span>
                                        <span className={`${log.includes('Error') ? 'text-red-400' :
                                                log.includes('Success') ? 'text-emerald-400' :
                                                    log.includes('Phase') ? 'text-cyan-400' :
                                                        'text-slate-300'
                                            }`}>
                                            {log.split(']')[1]}
                                        </span>
                                    </div>
                                ))}
                                <div ref={consoleEndRef} />
                            </div>

                            {/* Progress Bar Footer */}
                            <div className="h-1 bg-gray-800 w-full">
                                <div className="h-full bg-cyan-500 transition-all duration-300" style={{ width: `${progress}%` }}></div>
                            </div>
                        </div>
                    </div>

                </main>
            </div>
        </div>
    );
};

export default Dashboard;
