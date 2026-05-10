
import React, { useState } from 'react';
import { Settings, Sparkles, CheckCircle, ArrowRight } from 'lucide-react';
import ConnectivityHealer from './wizard/ConnectivityHealer';

interface StartupProps {
    onComplete: (settings: any) => void;
}

export default function FirstRunWizard({ onComplete }: StartupProps) {
    const [isComplete, setIsComplete] = useState(false);

    const handleConnectivityComplete = (result: any) => {
        setIsComplete(true);
    };

    const finishSetup = () => {
        // Save minimal defaults
        const defaults = {
            theme: 'dark',
            ai_provider: { mode: 'ollama', ollama_url: 'http://localhost:11434' }
        };
        localStorage.setItem('biodockify_first_run_complete', 'true');
        onComplete(defaults);
    };

    if (isComplete) {
        return (
            <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-md p-4">
                <div className="max-w-md w-full bg-slate-900 border border-emerald-500/30 rounded-2xl shadow-2xl p-8 text-center animate-in zoom-in duration-300">
                    <div className="w-16 h-16 bg-emerald-500/10 rounded-full flex items-center justify-center mx-auto mb-6">
                        <CheckCircle className="w-8 h-8 text-emerald-400" />
                    </div>
                    <h2 className="text-2xl font-bold text-white mb-2">Systems Online</h2>
                    <p className="text-slate-400 mb-8">
                        BioDockify AI is ready. Please configure your specific AI preferences in Settings before starting your research.
                    </p>

                    <button
                        onClick={finishSetup}
                        className="w-full py-4 bg-emerald-600 hover:bg-emerald-500 text-white font-bold rounded-xl transition-all flex items-center justify-center gap-2 shadow-lg shadow-emerald-900/20"
                    >
                        <span>Go to Dashboard</span>
                        <ArrowRight className="w-5 h-5" />
                    </button>

                    <p className="mt-4 text-xs text-slate-500">
                        Tip: Open <Settings className="w-3 h-3 inline mx-1" /> <strong>Settings</strong> to connect generic or paid models.
                    </p>
                </div>
            </div>
        );
    }

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950 text-slate-100 overflow-y-auto p-4">
            <div className="w-full max-w-xl bg-slate-900/50 backdrop-blur-xl border border-slate-800 rounded-2xl shadow-2xl overflow-hidden animate-in fade-in zoom-in duration-300">
                <div className="p-8">
                    <div className="text-center mb-8">
                        <div className="w-12 h-12 bg-indigo-500/10 rounded-full flex items-center justify-center mx-auto mb-4">
                            <Sparkles className="w-6 h-6 text-indigo-400" />
                        </div>
                        <h2 className="text-2xl font-bold text-white">System Initialization</h2>
                        <p className="text-slate-400 text-sm mt-1">Verifying BioDockify research environment...</p>
                    </div>

                    <ConnectivityHealer
                        onComplete={handleConnectivityComplete}
                        onSkip={() => setIsComplete(true)}
                    />
                </div>
            </div>
        </div>
    );
}
