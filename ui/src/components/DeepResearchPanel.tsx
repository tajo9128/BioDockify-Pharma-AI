/**
 * Deep Research Panel
 * 
 * UI for SurfSense-inspired features:
 * 1. Deep Research Progress (Steps)
 * 2. Audio Briefing Player (Podcast)
 */

'use client';

import React, { useState, useEffect } from 'react';
import {
    Brain,
    CheckCircle,
    Circle,
    Play,
    Pause,
    Headphones,
    FileText,
    Loader2
} from 'lucide-react';
import { DeepResearchAgent, ResearchPlan, AudioBriefing } from '@/lib/deep-research';

interface DeepResearchPanelProps {
    query: string;
    onClose: () => void;
}

export default function DeepResearchPanel({ query, onClose }: DeepResearchPanelProps) {
    const [plan, setPlan] = useState<ResearchPlan | null>(null);
    const [briefing, setBriefing] = useState<AudioBriefing | null>(null);
    const [isPlaying, setIsPlaying] = useState(false);
    const [status, setStatus] = useState('Initializing Deep Research...');

    // Web Speech API for demo
    const [synthesis, setSynthesis] = useState<SpeechSynthesisUtterance | null>(null);

    useEffect(() => {
        startResearch();
    }, [query]);

    const startResearch = async () => {
        const agent = DeepResearchAgent.getInstance();

        // 1. Create Plan
        setStatus('Creating Research Plan...');
        await new Promise(r => setTimeout(r, 1000));
        const newPlan = await agent.createPlan(query);
        setPlan(newPlan);

        // 2. Execute Steps (Simulated)
        setStatus('Executing Research Steps...');
        for (let i = 0; i < newPlan.steps.length; i++) {
            setPlan(prev => prev ? { ...prev, currentStep: i } : null);
            await new Promise(r => setTimeout(r, 1500)); // Simulate work
        }

        setPlan(prev => prev ? { ...prev, currentStep: newPlan.steps.length, status: 'complete' } : null);
        setStatus('Synthesizing Audio Briefing...');

        // 3. Generate Audio
        const audio = await agent.generateAudioBriefing(
            `Here is your research briefing for: ${query}. We successfully analyzed multiple sources and found key insights...`
        );
        setBriefing(audio);
        setStatus('Research Complete');
    };

    const toggleAudio = () => {
        if (!briefing) return;

        if (isPlaying) {
            window.speechSynthesis.cancel();
            setIsPlaying(false);
        } else {
            const utter = new SpeechSynthesisUtterance(briefing.transcript);
            utter.onend = () => setIsPlaying(false);
            window.speechSynthesis.speak(utter);
            setSynthesis(utter);
            setIsPlaying(true);
        }
    };

    return (
        <div className="bg-slate-900 border border-slate-700 rounded-xl p-6 space-y-6 max-w-2xl mx-auto shadow-2xl">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                    <div className="w-10 h-10 rounded-xl bg-indigo-500/10 flex items-center justify-center">
                        <Brain className="w-6 h-6 text-indigo-400" />
                    </div>
                    <div>
                        <h3 className="text-lg font-bold text-white">Deep Research Agent</h3>
                        <p className="text-xs text-slate-400">Powered by SurfSense Architecture</p>
                    </div>
                </div>
                <button onClick={onClose} className="text-slate-500 hover:text-white">Close</button>
            </div>

            {/* Progress Steps */}
            {plan && (
                <div className="bg-slate-800/50 rounded-lg p-4 space-y-3">
                    <h4 className="text-sm font-semibold text-slate-300 uppercase tracking-wide mb-2">
                        Research Plan
                    </h4>
                    {plan.steps.map((step, idx) => (
                        <div key={idx} className="flex items-center space-x-3">
                            {idx < plan.currentStep ? (
                                <CheckCircle className="w-5 h-5 text-emerald-400" />
                            ) : idx === plan.currentStep ? (
                                <Loader2 className="w-5 h-5 text-indigo-400 animate-spin" />
                            ) : (
                                <Circle className="w-5 h-5 text-slate-600" />
                            )}
                            <span className={`text-sm ${idx <= plan.currentStep ? 'text-slate-200' : 'text-slate-500'
                                }`}>
                                {step}
                            </span>
                        </div>
                    ))}
                </div>
            )}

            {/* Audio Player (Podcast) */}
            {briefing && (
                <div className="bg-indigo-600/10 border border-indigo-500/30 rounded-xl p-4 flex items-center justify-between">
                    <div className="flex items-center space-x-4">
                        <div className="w-12 h-12 rounded-full bg-indigo-600 flex items-center justify-center shadow-lg">
                            <Headphones className="w-6 h-6 text-white" />
                        </div>
                        <div>
                            <h4 className="font-bold text-white">Audio Briefing</h4>
                            <p className="text-xs text-indigo-300">Generated Podcast • 3 mins</p>
                        </div>
                    </div>

                    <button
                        onClick={toggleAudio}
                        className="w-10 h-10 rounded-full bg-white text-indigo-600 flex items-center justify-center hover:bg-slate-200 transition-colors"
                    >
                        {isPlaying ? <Pause className="w-5 h-5" /> : <Play className="w-5 h-5 ml-1" />}
                    </button>
                </div>
            )}

            {!briefing && (
                <div className="flex items-center justify-center py-4 text-slate-500 text-sm animate-pulse">
                    {status}
                </div>
            )}
        </div>
    );
}
