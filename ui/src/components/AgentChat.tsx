'use client';
import React, { useState, useRef, useEffect, useCallback } from 'react';
import { Send, Bot, User, Sparkles, Terminal, Play, Globe, ShieldAlert, Brain, Wrench, Power, CheckCircle2, AlertCircle, Loader2, RefreshCw } from 'lucide-react';
import { ScrollArea } from "@/components/ui/scroll-area";
import { api } from '@/lib/api';
import { searchWeb, fetchWebPage } from '@/lib/web_fetcher';
import { getPersonaById } from '@/lib/personas';
import DiagnosisDialog from '@/components/DiagnosisDialog';
import DeepResearchPanel from '@/components/DeepResearchPanel';

interface Message {
    role: 'user' | 'assistant' | 'system';
    content: string;
    timestamp: Date;
    source?: string;
    thoughts?: string[];
    action?: any;
}

interface ServiceHealth {
    backend: 'checking' | 'online' | 'offline';
    ollama: 'checking' | 'online' | 'offline' | 'no_model';
}

const REPAIR_TRIGGERS = [
    'fix the system',
    'repair agent zero',
    'repair biodockify',
    'diagnose and repair',
    'recover ai services',
    'chat not working',
    'fix chat',
    'system health',
    'repair system'
];

export default function AgentChat() {
    // Import introduction dynamically to support first-time vs returning user logic
    const [messages, setMessages] = useState<Message[]>([
        {
            role: 'assistant',
            content: `**Hello.**

I am **BioDockify**, your intelligent research assistant for pharmaceutical and life-science research.

I help with:
• Deep Literature Analysis (comparative analysis, gap detection)
• Automatic Literature Review Workflow
• Evidence-Driven Research Analysis  
• Project Memory & Research Continuity
• Academic Writing Support
• Multi-channel Integration (Telegram, WhatsApp, Email, Discord)

**How to Start:**
• Upload research papers
• State your research topic
• Ask me to search literature

*Powered by BioDockify*

How can I assist your research today?`,
            timestamp: new Date()
        }
    ]);
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [status, setStatus] = useState(''); // "Searching...", "Reading..."
    const [isDiagnosisOpen, setIsDiagnosisOpen] = useState(false);
    const [deepResearchQuery, setDeepResearchQuery] = useState<string | null>(null);
    const scrollRef = useRef<HTMLDivElement>(null);

    // Health monitoring state
    const [health, setHealth] = useState<ServiceHealth>({
        backend: 'checking',
        ollama: 'checking'
    });
    const [isStartingServices, setIsStartingServices] = useState(false);

    // Health check function
    const checkHealth = useCallback(async () => {
        // Check backend via API proxy (works in both dev and production)
        try {
            const res = await fetch('/api/health', {
                method: 'GET',
                signal: AbortSignal.timeout(3000)
            });
            setHealth(h => ({ ...h, backend: res.ok ? 'online' : 'offline' }));
        } catch {
            setHealth(h => ({ ...h, backend: 'offline' }));
        }

        // Check Ollama (local only - keep direct URL)
        try {
            const res = await fetch('http://localhost:11434/api/tags', {
                method: 'GET',
                signal: AbortSignal.timeout(3000)
            });
            if (res.ok) {
                const data = await res.json();
                const hasModels = (data.models || []).length > 0;
                setHealth(h => ({ ...h, ollama: hasModels ? 'online' : 'no_model' }));
            } else {
                setHealth(h => ({ ...h, ollama: 'offline' }));
            }
        } catch {
            setHealth(h => ({ ...h, ollama: 'offline' }));
        }
    }, []);

    // Start services manually
    const handleStartServices = async () => {
        setIsStartingServices(true);

        // If in Tauri, try to start backend
        // (Removed for Docker-only build)
        console.log("Service startup is managed by Docker.");

        // Wait and recheck
        await new Promise(r => setTimeout(r, 5000));
        await checkHealth();
        setIsStartingServices(false);
    };

    // Initial health check and periodic monitoring
    useEffect(() => {
        checkHealth();
        const interval = setInterval(checkHealth, 30000); // Every 30 seconds
        return () => clearInterval(interval);
    }, [checkHealth]);

    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollIntoView({ behavior: "smooth" });
        }
    }, [messages]);

    // Check if we should prompt for API keys on first use
    const checkFirstTimeApiPrompt = async () => {
        if (typeof window === 'undefined') return;

        const hasPrompted = localStorage.getItem('biodockify_api_prompt_shown');
        if (hasPrompted) return;

        try {
            const settings = await api.getSettings();
            const providerConfig = settings?.ai_provider || {};

            // Check if any CLOUD provider is configured
            const hasCloudProvider = !!(
                providerConfig.google_key ||
                providerConfig.openrouter_key ||
                providerConfig.huggingface_key ||
                providerConfig.custom_key ||
                providerConfig.glm_key ||
                providerConfig.groq_key ||
                providerConfig.openai_key ||
                providerConfig.deepseek_key ||
                providerConfig.anthropic_key ||
                providerConfig.kimi_key ||
                providerConfig.elsevier_key
            );

            // If no cloud provider, suggest adding one for full potential
            if (!hasCloudProvider) {
                setMessages(prev => [...prev, {
                    role: 'system',
                    content: `🚀 **Unlock Full Research Potential**
                    
While you can run locally, adding a **Free or Paid API Key** unlocks:
• **Deep Research Mode** (Analyze 100+ papers)
• **Academic Writing Assistant** (Higher quality drafts)
• **Complex Reasoning** (Better gap detection)

**Recommended Free Options:**
• **Google Gemini** (High capacity, great for research)
• **Groq** (Extremely fast)

*Go to Settings → AI & Brain to configure.*`,
                    timestamp: new Date()
                }]);
            }

            localStorage.setItem('biodockify_api_prompt_shown', 'true');
        } catch (e) {
            console.error('Failed to check API settings:', e);
        }
    };

    // Single Agent Zero mode (v1.9)
    const agentMode = 'agent0' as const;

    const handleSend = async () => {
        if (!input.trim()) return;

        // Check for first-time API prompt
        await checkFirstTimeApiPrompt();

        const userMsg: Message = { role: 'user', content: input, timestamp: new Date() };
        setMessages(prev => [...prev, userMsg]);
        setInput('');

        setIsLoading(true);
        setStatus('BioDockify Pharma AI v1.60 Processing...');

        try {
            // Use single Agent Zero v1.9 endpoint
            setStatus('Generating Answer...');
            const data = await api.agentChat(userMsg.content);

            // BioDockify AI JSON Parsing Logic
            let replyContent = data.reply;
            let thoughts: string[] | undefined;
            let action: any | undefined;

            try {
                // Try to parse the response as BioDockify AI JSON Structure
                // The prompt enforces: { "thoughts": [], "headline": "", "action": {} }
                if (data.reply.trim().startsWith('{')) {
                    const parsed = JSON.parse(data.reply);
                    if (parsed.thoughts || parsed.headline) {
                        thoughts = parsed.thoughts;
                        replyContent = parsed.headline || parsed.action?.name || "Action executed.";
                        action = parsed.action;
                    }
                }
            } catch (e) {
                // Fallback to raw text if not JSON
                console.log("Response was not JSON, using raw text", e);
            }

            setMessages(prev => {
                const updated: Message[] = [...prev, {
                    role: 'assistant' as const,
                    content: replyContent,
                    thoughts: thoughts,
                    action: action,
                    timestamp: new Date()
                }];
                return updated.slice(-100);
            });

        } catch (error: any) {
            console.error("Chat error:", error);
            setMessages(prev => [...prev, {
                role: 'system',
                content: `⚠️ **Connection Error**\n\nFailed to reach BioDockify Backend: ${error.message}`,
                timestamp: new Date()
            }]);
        } finally {
            setIsLoading(false);
            setStatus('');
        }
    };

    return (
        <div className="flex flex-col h-full bg-slate-950 text-slate-100 font-sans relative">
            <DiagnosisDialog
                isOpen={isDiagnosisOpen}
                onClose={() => setIsDiagnosisOpen(false)}
            />

            {/* Header */}
            <div className="h-16 border-b border-slate-800 flex items-center justify-between px-6 bg-slate-900/50 backdrop-blur-sm">

                <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl flex items-center justify-center shadow-lg bg-gradient-to-br from-indigo-600 to-purple-700 shadow-indigo-500/20">
                        <Bot className="w-6 h-6 text-white" />
                    </div>
                    <div>
                        <h2 className="font-bold text-lg tracking-tight">BioDockify</h2>
                    </div>
                </div>
                {/* Actions */}
                <div className="flex items-center gap-2">
                    {/* Simplified Status - Just the dot */}
                    <div className={`w-2 h-2 rounded-full ${health.backend === 'online' ? 'bg-emerald-500 animate-pulse' : 'bg-red-500'}`} />
                </div>
            </div>

            {/* Chat Area */}
            <div className="flex-1 overflow-y-auto p-6 space-y-6">
                {messages.map((msg, idx) => (
                    <div key={idx} className={`flex gap-4 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                        {msg.role !== 'user' && (
                            <div className="w-8 h-8 rounded-full bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center flex-shrink-0 mt-1">
                                {msg.role === 'system' ? <Terminal className="w-4 h-4 text-red-400" /> : <Sparkles className="w-4 h-4 text-indigo-400" />}
                            </div>
                        )}

                        <div className={`max-w-[75%] space-y-1`}>
                            <div className={`p-4 rounded-2xl ${msg.role === 'user'
                                ? 'bg-indigo-600 text-white rounded-tr-sm'
                                : msg.role === 'system'
                                    ? 'bg-red-900/20 border border-red-900/50 text-red-200'
                                    : 'bg-slate-900 border border-slate-800 text-slate-300 rounded-tl-sm'
                                }`}>
                                {/* BioDockify AI: Thoughts Section */}
                                {msg.thoughts && msg.thoughts.length > 0 && (
                                    <div className="mb-3 p-3 bg-black/20 rounded-lg border border-white/5">
                                        <div className="flex items-center gap-2 mb-2 text-xs font-bold text-indigo-400 uppercase tracking-wider">
                                            <Brain className="w-3 h-3" /> Thinking
                                        </div>
                                        <ul className="list-disc list-outside ml-4 space-y-1 text-xs font-mono text-slate-400">
                                            {msg.thoughts.map((t, i) => (
                                                <li key={i}>{t}</li>
                                            ))}
                                        </ul>
                                    </div>
                                )}

                                <h1 className="text-xl font-bold text-white tracking-tight flex items-center mb-2">
                                    <Bot className={`w-6 h-6 mr-3 animate-pulse-soft ${msg.thoughts ? 'text-indigo-400' : 'text-teal-400'}`} />
                                    BioDockify
                                </h1>
                                <p className="leading-relaxed whitespace-pre-wrap text-sm">{msg.content}</p>

                                {/* Action Section */}
                                {msg.action && (
                                    <div className="mt-3 text-xs bg-indigo-500/10 text-indigo-200 p-2 rounded border border-indigo-500/20 flex items-center gap-2">
                                        <Terminal className="w-3 h-3" />
                                        <span className="font-mono">Executed: {msg.action.name}</span>
                                    </div>
                                )}
                            </div>
                            <span className="text-[10px] text-slate-600 px-1 opacity-100">
                                {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                            </span>
                        </div>

                        {msg.role === 'user' && (
                            <div className="w-8 h-8 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center flex-shrink-0 mt-1">
                                <User className="w-4 h-4 text-slate-400" />
                            </div>
                        )}
                    </div>
                ))}

                {deepResearchQuery && (
                    <div className="mb-6">
                        <DeepResearchPanel
                            query={deepResearchQuery}
                            onClose={() => setDeepResearchQuery(null)}
                        />
                    </div>
                )}

                {isLoading && (
                    <div className="flex gap-4">
                        <div className="w-8 h-8 rounded-full bg-indigo-500/10 flex items-center justify-center flex-shrink-0">
                            <Sparkles className="w-4 h-4 text-indigo-400 animate-pulse" />
                        </div>
                        <div className="flex items-center gap-1 h-10 px-4 bg-slate-900 border border-slate-800 rounded-2xl rounded-tl-sm">
                            <span className="w-1.5 h-1.5 bg-slate-500 rounded-full animate-bounce [animation-delay:-0.3s]" />
                            <span className="w-1.5 h-1.5 bg-slate-500 rounded-full animate-bounce [animation-delay:-0.15s]" />
                            <span className="w-1.5 h-1.5 bg-slate-500 rounded-full animate-bounce" />
                        </div>
                    </div>
                )}
                <div ref={scrollRef} />
            </div>

            {/* Input */}
            <div className="p-6 pt-2 bg-slate-950">
                <div className="relative">
                    <input
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                        placeholder="Message BioDockify..."
                        className="w-full bg-slate-900/50 border border-slate-800 rounded-xl py-4 pl-5 pr-14 text-slate-200 placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500/50 transition-all shadow-xl"
                        disabled={isLoading}
                    />
                    <button
                        onClick={handleSend}
                        disabled={!input.trim() || isLoading}
                        className="absolute right-2 top-2 p-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        <Send className="w-4 h-4" />
                    </button>
                </div>
                <div className="mt-2 flex justify-center gap-4 text-[10px] text-slate-600 font-medium uppercase tracking-wider">
                    <span className="text-indigo-400">
                        BioDockify
                    </span>
                    <span>•</span>
                    <span>Tools: Enabled</span>
                </div>
            </div>
        </div>
    );
}
