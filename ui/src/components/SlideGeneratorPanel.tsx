'use client';

import React, { useState } from 'react';
import { Presentation, FileText, Search, MessageSquare, Folder, Download, Loader2, X } from 'lucide-react';
import api from '@/lib/api';

interface SlideGeneratorPanelProps {
    isOpen: boolean;
    onClose: () => void;
}

type SourceType = 'knowledge_base' | 'search' | 'prompt' | 'documents';

export default function SlideGeneratorPanel({ isOpen, onClose }: SlideGeneratorPanelProps) {
    const [source, setSource] = useState<SourceType>('knowledge_base');
    const [topic, setTopic] = useState('');
    const [searchQuery, setSearchQuery] = useState('');
    const [customPrompt, setCustomPrompt] = useState('');
    const [style, setStyle] = useState('academic');
    const [numSlides, setNumSlides] = useState(10);
    const [includeCitations, setIncludeCitations] = useState(true);
    const [isGenerating, setIsGenerating] = useState(false);
    const [generatedSlides, setGeneratedSlides] = useState<any[] | null>(null);
    const [error, setError] = useState<string | null>(null);

    const handleGenerate = async () => {
        setIsGenerating(true);
        setError(null);
        setGeneratedSlides(null);

        try {
            const result = await api.slides.generate({
                source,
                topic,
                searchQuery,
                customPrompt,
                style,
                numSlides,
                includeCitations
            });

            if (result.status === 'success') {
                setGeneratedSlides(result.slides);
            } else {
                setError('Failed to generate slides');
            }
        } catch (err: any) {
            setError(err.message || 'Failed to generate slides');
        } finally {
            setIsGenerating(false);
        }
    };

    const handleDownload = async () => {
        if (!generatedSlides) return;

        try {
            const result = await api.slides.render(generatedSlides, style, topic || 'Presentation');
            if (result.html) {
                const blob = new Blob([result.html], { type: 'text/html' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `${topic || 'presentation'}.html`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(url);
            }
        } catch (err: any) {
            setError('Failed to download slides');
        }
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <div className="bg-slate-900 rounded-xl border border-slate-700 w-full max-w-2xl max-h-[90vh] overflow-y-auto">
                {/* Header */}
                <div className="flex items-center justify-between p-4 border-b border-slate-700">
                    <div className="flex items-center gap-2">
                        <Presentation className="text-cyan-400" size={24} />
                        <h2 className="text-xl font-semibold text-white">Generate Presentation</h2>
                    </div>
                    <button onClick={onClose} className="text-slate-400 hover:text-white">
                        <X size={24} />
                    </button>
                </div>

                {/* Content */}
                <div className="p-6 space-y-6">
                    {/* Source Selection */}
                    <div>
                        <label className="block text-sm font-medium text-slate-300 mb-2">Source</label>
                        <div className="grid grid-cols-2 gap-2">
                            {[
                                { id: 'knowledge_base', label: 'Knowledge Base', icon: Folder },
                                { id: 'search', label: 'Search Results', icon: Search },
                                { id: 'prompt', label: 'Custom Prompt', icon: MessageSquare },
                                { id: 'documents', label: 'Documents', icon: FileText }
                            ].map(({ id, label, icon: Icon }) => (
                                <button
                                    key={id}
                                    onClick={() => setSource(id as SourceType)}
                                    className={`flex items-center gap-2 p-3 rounded-lg border transition-colors ${source === id
                                            ? 'bg-cyan-500/20 border-cyan-500 text-cyan-400'
                                            : 'bg-slate-800 border-slate-600 text-slate-300 hover:border-slate-500'
                                        }`}
                                >
                                    <Icon size={18} />
                                    <span>{label}</span>
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* Topic/Query Input */}
                    {source === 'knowledge_base' && (
                        <div>
                            <label className="block text-sm font-medium text-slate-300 mb-2">Topic</label>
                            <input
                                type="text"
                                value={topic}
                                onChange={(e) => setTopic(e.target.value)}
                                placeholder="e.g., Alzheimer's Disease Drug Targets"
                                className="w-full px-4 py-3 bg-slate-800 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:border-cyan-500 focus:outline-none"
                            />
                        </div>
                    )}

                    {source === 'search' && (
                        <div>
                            <label className="block text-sm font-medium text-slate-300 mb-2">Search Query</label>
                            <input
                                type="text"
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                                placeholder="e.g., CRISPR gene therapy applications"
                                className="w-full px-4 py-3 bg-slate-800 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:border-cyan-500 focus:outline-none"
                            />
                        </div>
                    )}

                    {source === 'prompt' && (
                        <div>
                            <label className="block text-sm font-medium text-slate-300 mb-2">Describe Your Presentation</label>
                            <textarea
                                value={customPrompt}
                                onChange={(e) => setCustomPrompt(e.target.value)}
                                placeholder="e.g., Create a 15-slide presentation comparing traditional vs. targeted cancer therapies, focusing on efficacy and side effects..."
                                rows={4}
                                className="w-full px-4 py-3 bg-slate-800 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:border-cyan-500 focus:outline-none resize-none"
                            />
                        </div>
                    )}

                    {/* Style & Options */}
                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <label className="block text-sm font-medium text-slate-300 mb-2">Style</label>
                            <select
                                value={style}
                                onChange={(e) => setStyle(e.target.value)}
                                className="w-full px-4 py-3 bg-slate-800 border border-slate-600 rounded-lg text-white focus:border-cyan-500 focus:outline-none"
                            >
                                <option value="academic">Academic</option>
                                <option value="modern">Modern</option>
                                <option value="minimal">Minimal</option>
                                <option value="pharma">Pharmaceutical</option>
                            </select>
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-slate-300 mb-2">Number of Slides</label>
                            <select
                                value={numSlides}
                                onChange={(e) => setNumSlides(Number(e.target.value))}
                                className="w-full px-4 py-3 bg-slate-800 border border-slate-600 rounded-lg text-white focus:border-cyan-500 focus:outline-none"
                            >
                                <option value={5}>5 (Brief)</option>
                                <option value={10}>10 (Standard)</option>
                                <option value={15}>15 (Detailed)</option>
                                <option value={20}>20 (Comprehensive)</option>
                            </select>
                        </div>
                    </div>

                    {/* Options */}
                    <div className="flex items-center gap-2">
                        <input
                            type="checkbox"
                            id="citations"
                            checked={includeCitations}
                            onChange={(e) => setIncludeCitations(e.target.checked)}
                            className="w-4 h-4 rounded border-slate-600 bg-slate-800 text-cyan-500 focus:ring-cyan-500"
                        />
                        <label htmlFor="citations" className="text-sm text-slate-300">Include source citations</label>
                    </div>

                    {/* Error */}
                    {error && (
                        <div className="p-3 bg-red-500/20 border border-red-500 rounded-lg text-red-400">
                            {error}
                        </div>
                    )}

                    {/* Results */}
                    {generatedSlides && (
                        <div className="p-4 bg-green-500/20 border border-green-500 rounded-lg">
                            <div className="flex items-center justify-between">
                                <div>
                                    <p className="text-green-400 font-medium">
                                        ✓ Generated {generatedSlides.length} slides!
                                    </p>
                                    <p className="text-sm text-slate-400 mt-1">
                                        Click Download to save as HTML
                                    </p>
                                </div>
                                <button
                                    onClick={handleDownload}
                                    className="flex items-center gap-2 px-4 py-2 bg-green-500 hover:bg-green-600 text-white rounded-lg transition-colors"
                                >
                                    <Download size={18} />
                                    Download
                                </button>
                            </div>
                        </div>
                    )}
                </div>

                {/* Footer */}
                <div className="flex items-center justify-end gap-3 p-4 border-t border-slate-700">
                    <button
                        onClick={onClose}
                        className="px-4 py-2 text-slate-400 hover:text-white transition-colors"
                    >
                        Cancel
                    </button>
                    <button
                        onClick={handleGenerate}
                        disabled={isGenerating}
                        className="flex items-center gap-2 px-6 py-2 bg-cyan-500 hover:bg-cyan-600 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        {isGenerating ? (
                            <>
                                <Loader2 className="animate-spin" size={18} />
                                Generating...
                            </>
                        ) : (
                            <>
                                <Presentation size={18} />
                                Generate Slides
                            </>
                        )}
                    </button>
                </div>
            </div>
        </div>
    );
}
