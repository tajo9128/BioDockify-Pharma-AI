import React, { useState } from 'react';
import { api } from '@/lib/api';
import { FileText, Download, Code, CheckCircle2 } from 'lucide-react';

export default function PublicationView() {
    // Report Metadata
    const [title, setTitle] = useState('');
    const [author, setAuthor] = useState('BioDockify AI');
    const [affiliation, setAffiliation] = useState('Virtual Research Lab');
    const [abstract, setAbstract] = useState('');
    const [body, setBody] = useState('# Introduction\n\nWrite your report here using Markdown...');

    // State
    const [generating, setGenerating] = useState(false);
    const [latexSource, setLatexSource] = useState('');
    const [activeTab, setActiveTab] = useState<'edit' | 'latex'>('edit');

    const handleGenerate = async () => {
        if (!title) return;
        setGenerating(true);
        try {
            const res = await api.exportToLatex({
                title,
                author,
                affiliation,
                abstract,
                content_markdown: body
            });
            setLatexSource(res.latex_source);
            setActiveTab('latex');
        } catch (e) {
            console.error("Export failed", e);
        } finally {
            setGenerating(false);
        }
    };

    const copyToClipboard = () => {
        navigator.clipboard.writeText(latexSource);
        // Could add toast here
    };

    return (
        <div className="h-full flex flex-col bg-slate-950 text-slate-100 p-6 overflow-hidden">
            {/* Header */}
            <div className="flex justify-between items-center mb-6">
                <div>
                    <h1 className="text-3xl font-light tracking-tight text-white flex items-center gap-3">
                        <FileText className="h-8 w-8 text-indigo-500" />
                        Publication Manager
                    </h1>
                    <p className="text-slate-400 mt-1">Draft reports and export to LaTeX for publication.</p>
                </div>
                <div className="flex gap-2">
                    <button
                        onClick={() => setActiveTab('edit')}
                        className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${activeTab === 'edit' ? 'bg-slate-800 text-white' : 'text-slate-400 hover:text-white'}`}
                    >
                        Edit Draft
                    </button>
                    <button
                        onClick={() => setActiveTab('latex')}
                        className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${activeTab === 'latex' ? 'bg-slate-800 text-white' : 'text-slate-400 hover:text-white'}`}
                    >
                        LaTeX Source
                    </button>
                </div>
            </div>

            <div className="flex-1 flex gap-6 overflow-hidden">
                {activeTab === 'edit' ? (
                    // Edit View
                    <div className="flex-1 flex flex-col gap-4 overflow-y-auto pr-2 animate-in fade-in">
                        <div className="grid grid-cols-2 gap-4">
                            <div className="space-y-2">
                                <label className="text-xs text-slate-500 uppercase tracking-wider font-semibold">Title</label>
                                <input className="w-full bg-slate-900/50 border border-slate-800 rounded p-2 text-white focus:ring-1 focus:ring-indigo-500 outline-none"
                                    placeholder="Research Title" value={title} onChange={e => setTitle(e.target.value)} />
                            </div>
                            <div className="space-y-2">
                                <label className="text-xs text-slate-500 uppercase tracking-wider font-semibold">Author</label>
                                <input className="w-full bg-slate-900/50 border border-slate-800 rounded p-2 text-white focus:ring-1 focus:ring-indigo-500 outline-none"
                                    placeholder="Author Name" value={author} onChange={e => setAuthor(e.target.value)} />
                            </div>
                        </div>

                        <div className="space-y-2">
                            <label className="text-xs text-slate-500 uppercase tracking-wider font-semibold">Affiliation</label>
                            <input className="w-full bg-slate-900/50 border border-slate-800 rounded p-2 text-white focus:ring-1 focus:ring-indigo-500 outline-none"
                                placeholder="Lab / University" value={affiliation} onChange={e => setAffiliation(e.target.value)} />
                        </div>

                        <div className="space-y-2">
                            <label className="text-xs text-slate-500 uppercase tracking-wider font-semibold">Abstract</label>
                            <textarea className="w-full bg-slate-900/50 border border-slate-800 rounded p-2 text-white focus:ring-1 focus:ring-indigo-500 outline-none h-24 resize-none"
                                placeholder="Abstract..." value={abstract} onChange={e => setAbstract(e.target.value)} />
                        </div>

                        <div className="space-y-2 flex-1 flex flex-col">
                            <label className="text-xs text-slate-500 uppercase tracking-wider font-semibold">Report Body (Markdown)</label>
                            <textarea className="flex-1 bg-slate-900/50 border border-slate-800 rounded p-4 text-white font-mono text-sm focus:ring-1 focus:ring-indigo-500 outline-none resize-none"
                                value={body} onChange={e => setBody(e.target.value)} />
                        </div>

                        <div className="flex justify-end pt-2">
                            <button
                                onClick={handleGenerate}
                                disabled={generating || !title}
                                className="bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed text-white px-6 py-2 rounded-md flex items-center gap-2 transition-all shadow-lg shadow-indigo-500/20"
                            >
                                {generating ? 'Generating...' : <><Code className="h-4 w-4" /> Generate LaTeX</>}
                            </button>
                        </div>
                    </div>
                ) : (
                    // LaTeX View
                    <div className="flex-1 flex flex-col gap-4 animate-in fade-in slide-in-from-right-4">
                        {latexSource ? (
                            <>
                                <div className="bg-slate-900 rounded-lg border border-slate-800 flex flex-col h-full overflow-hidden relative group">
                                    <div className="absolute top-4 right-4 z-10 opacity-0 group-hover:opacity-100 transition-opacity">
                                        <button onClick={copyToClipboard} className="bg-slate-800 hover:bg-slate-700 text-slate-200 px-3 py-1.5 rounded text-xs border border-slate-700 shadow-xl flex gap-2 items-center">
                                            <Download className="h-3 w-3" /> Copy Source
                                        </button>
                                    </div>
                                    <pre className="p-6 overflow-auto text-xs font-mono text-slate-300 leading-relaxed selection:bg-indigo-500/30">
                                        {latexSource}
                                    </pre>
                                </div>
                                <div className="text-center text-slate-500 text-xs mt-2">
                                    Copy this source code and paste it into Overleaf to compile your PDF.
                                </div>
                            </>
                        ) : (
                            <div className="flex-1 flex flex-col items-center justify-center text-slate-500 border border-dashed border-slate-800 rounded-lg m-4">
                                <FileText className="h-12 w-12 opacity-20 mb-4" />
                                <p>No LaTeX generated yet.</p>
                                <button onClick={() => setActiveTab('edit')} className="text-indigo-400 hover:text-indigo-300 text-sm mt-2">Go to Editor</button>
                            </div>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
}
