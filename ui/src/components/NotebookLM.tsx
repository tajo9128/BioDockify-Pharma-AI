
import React, { useState, useRef } from 'react';
import {
    BookOpen, Upload, Globe, Trash2, Send, Plus, FileText,
    MoreHorizontal, PlayCircle, Mic, Sparkles, MessageSquare, Headphones
} from 'lucide-react';
import { api } from '@/lib/api';

interface Message {
    role: 'user' | 'assistant';
    content: string;
    context?: string;
}

export default function NotebookLM() {
    const [messages, setMessages] = useState<Message[]>([
        { role: 'assistant', content: 'Ready to answer questions based on your sources.' }
    ]);
    const [input, setInput] = useState('');
    const [sources, setSources] = useState<string[]>([]);
    const [loading, setLoading] = useState(false);
    const [uploading, setUploading] = useState(false);

    // File Input
    const fileInputRef = useRef<HTMLInputElement>(null);

    // --- HANDLERS ---

    const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        if (!e.target.files?.length) return;
        const file = e.target.files[0];
        setUploading(true);
        try {
            const formData = new FormData();
            formData.append('file', file);
            const res = await fetch('http://localhost:3000/api/rag/upload', { method: 'POST', body: formData });
            if (!res.ok) throw new Error('Upload failed');
            setSources(prev => [...prev, file.name]);
        } catch (err) {
            console.error(err);
            alert("Upload failed");
        } finally {
            setUploading(false);
        }
    };

    const handleLinkUpload = async () => {
        const url = prompt("Enter Google NotebookLM Share Link or data URL:");
        if (!url) return;
        setUploading(true);
        try {
            const res = await fetch('http://localhost:3000/api/rag/link', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url })
            });
            if (!res.ok) throw new Error('Link failed');
            setSources(prev => [...prev, url]);
        } catch (err) {
            console.error(err);
            alert("Link ingestion failed");
        } finally {
            setUploading(false);
        }
    };

    const handleSend = async () => {
        if (!input.trim()) return;
        const q = input;
        setInput('');
        setMessages(prev => [...prev, { role: 'user', content: q }]);
        setLoading(true);

        try {
            const res = await fetch('http://localhost:3000/api/rag/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query: q })
            });
            const data = await res.json();
            setMessages(prev => [...prev, { role: 'assistant', content: data.answer, context: data.context }]);
        } catch (err) {
            setMessages(prev => [...prev, { role: 'assistant', content: "Error retrieving answer." }]);
        } finally {
            setLoading(false);
        }
    };

    // --- RENDER ---

    return (
        <div className="flex h-screen bg-slate-50 dark:bg-slate-950 font-sans text-slate-900 dark:text-slate-100 overflow-hidden">

            {/* LEFT SIDEBAR: SOURCES */}
            <div className="w-80 border-r border-slate-200 dark:border-slate-800 flex flex-col bg-white dark:bg-slate-900">
                <div className="p-4 border-b border-slate-100 dark:border-slate-800 flex items-center justify-between">
                    <h2 className="font-semibold text-lg tracking-tight flex items-center gap-2">
                        <BookOpen className="w-5 h-5 text-teal-600" />
                        Sources
                    </h2>
                    <button onClick={handleLinkUpload} className="p-2 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg transition-colors text-slate-500" title="Add Link">
                        <Plus className="w-5 h-5" />
                    </button>
                </div>

                <div className="flex-1 overflow-y-auto p-4 space-y-3">
                    {/* Source List */}
                    {sources.map((src, i) => (
                        <div key={i} className="flex items-start gap-3 p-3 bg-slate-50 dark:bg-slate-800/50 rounded-lg border border-slate-100 dark:border-slate-800">
                            <div className="mt-1">
                                {src.startsWith('http') ? <Globe className="w-4 h-4 text-blue-500" /> : <FileText className="w-4 h-4 text-orange-500" />}
                            </div>
                            <div className="min-w-0 flex-1">
                                <p className="text-sm font-medium truncate">{src}</p>
                                <p className="text-xs text-slate-400">Indexed</p>
                            </div>
                        </div>
                    ))}

                    {/* Add Source Card */}
                    <div
                        onClick={() => fileInputRef.current?.click()}
                        className="mt-2 border-2 border-dashed border-slate-200 dark:border-slate-800 rounded-xl p-6 flex flex-col items-center justify-center text-slate-400 hover:border-teal-500/50 hover:text-teal-600 cursor-pointer transition-all gap-2"
                    >
                        <Upload className="w-6 h-6" />
                        <span className="text-sm font-medium">Upload File</span>
                        <input type="file" ref={fileInputRef} className="hidden" onChange={handleFileUpload} accept=".pdf,.txt,.md,.ipynb" />
                    </div>
                </div>
            </div>

            {/* MAIN CONTENT Area */}
            <div className="flex-1 flex flex-col relative bg-slate-50 dark:bg-slate-950">

                {/* Header: Notebook Guide */}
                <div className="px-8 py-6 pb-2">
                    <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 shadow-sm flex items-center justify-between">
                        <div className="flex items-center gap-4">
                            <div className="w-10 h-10 rounded-full bg-indigo-100 dark:bg-indigo-900/30 flex items-center justify-center">
                                <Headphones className="w-5 h-5 text-indigo-600 dark:text-indigo-400" />
                            </div>
                            <div>
                                <h3 className="font-semibold text-base">Audio Overview</h3>
                                <p className="text-sm text-slate-500">Listen to a deep dive discussion of your sources.</p>
                            </div>
                        </div>
                        <button className="px-4 py-2 bg-slate-900 dark:bg-white text-white dark:text-black rounded-full font-medium text-sm flex items-center gap-2 hover:opacity-90 transition-opacity">
                            <PlayCircle className="w-4 h-4" /> Play
                        </button>
                    </div>
                </div>

                {/* Chat Area */}
                <div className="flex-1 overflow-y-auto px-8 max-w-4xl mx-auto w-full pb-32 pt-4">
                    {messages.map((msg, idx) => (
                        <div key={idx} className={`mb-6 flex gap-4 ${msg.role === 'user' ? 'justify-end' : ''}`}>
                            {msg.role === 'assistant' && (
                                <div className="w-8 h-8 rounded-full bg-teal-100 dark:bg-teal-900/30 flex items-center justify-center flex-shrink-0">
                                    <Sparkles className="w-4 h-4 text-teal-600 dark:text-teal-400" />
                                </div>
                            )}

                            <div className={`max-w-[80%] space-y-2 ${msg.role === 'user' ? 'bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-2xl rounded-tr-sm px-5 py-3 shadow-sm' : ''}`}>
                                <div className="text-slate-800 dark:text-slate-200 leading-relaxed text-[15px]">
                                    {msg.content}
                                </div>
                                {/* Context Expander */}
                                {msg.context && (
                                    <details className="text-xs">
                                        <summary className="cursor-pointer text-slate-400 hover:text-teal-500 font-medium transition-colors list-none flex items-center gap-1 mt-2">
                                            <BookOpen className="w-3 h-3" /> View Source Context
                                        </summary>
                                        <div className="mt-2 p-3 bg-slate-100 dark:bg-slate-900/50 rounded-lg border border-slate-200 dark:border-slate-800 font-mono text-slate-600 dark:text-slate-400 text-[11px] leading-normal max-h-40 overflow-y-auto">
                                            {msg.context}
                                        </div>
                                    </details>
                                )}
                            </div>
                        </div>
                    ))}
                    {loading && (
                        <div className="flex gap-4">
                            <div className="w-8 h-8 rounded-full bg-slate-200 dark:bg-slate-800 animate-pulse" />
                            <div className="h-10 w-32 bg-slate-200 dark:bg-slate-800 rounded-xl animate-pulse" />
                        </div>
                    )}
                </div>

                {/* Input Area (Centered Floating) */}
                <div className="absolute bottom-6 left-0 right-0 px-8 flex justify-center pointer-events-none">
                    <div className="w-full max-w-3xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xl rounded-full p-2 pl-6 flex items-center gap-2 pointer-events-auto ring-1 ring-slate-900/5">
                        <input
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                            placeholder="Ask me anything..."
                            className="flex-1 bg-transparent border-none outline-none text-slate-900 dark:text-white placeholder:text-slate-400 h-10"
                        />
                        <button
                            onClick={handleSend}
                            disabled={!input.trim() || loading}
                            className="w-10 h-10 rounded-full bg-teal-600 text-white flex items-center justify-center hover:bg-teal-500 transition-colors disabled:opacity-50"
                        >
                            <Send className="w-4 h-4 ml-0.5" />
                        </button>
                    </div>
                </div>

            </div>
        </div>
    );
}
