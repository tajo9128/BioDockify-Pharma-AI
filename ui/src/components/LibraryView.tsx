'use client';

import React, { useState, useEffect } from 'react';
import { api } from '@/lib/api';
import { UploadZone } from '@/components/library/UploadZone';
import { FileText, Trash2, Search, Filter, BookOpen, Clock, FileType, BrainCircuit, Loader2 } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { cn } from '@/lib/utils';
import { toast } from 'sonner';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

interface LibraryFile {
    id: string;
    filename: string;
    size_bytes: number;
    added_at: string;
    processed: boolean;
    metadata: any;
}

interface SearchResult {
    score: number;
    metadata: {
        source: string;
        type?: string;
        page?: number;
    }
}

export default function LibraryPage() {
    const [files, setFiles] = useState<LibraryFile[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [searchQuery, setSearchQuery] = useState('');

    // RAG State
    const [isSearching, setIsSearching] = useState(false);
    const [ragResults, setRagResults] = useState<SearchResult[]>([]);
    const [showRag, setShowRag] = useState(false);

    useEffect(() => {
        loadFiles();
    }, []);

    const loadFiles = async () => {
        try {
            setIsLoading(true);
            const data = await api.getLibraryFiles();
            setFiles(data);
        } catch (error) {
            console.error('Failed to load library:', error);
            toast.error('Failed to load library files');
        } finally {
            setIsLoading(false);
        }
    };

    const handleSemanticSearch = async () => {
        if (!searchQuery.trim()) return;

        setIsSearching(true);
        setShowRag(true);
        try {
            const res = await fetch('http://localhost:3000/api/library/query', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query: searchQuery, top_k: 5 })
            });

            if (res.ok) {
                const data = await res.json();
                setRagResults(data.results || []);
                if (data.results?.length === 0) toast.info("No relevant excerpts found.");
            } else {
                toast.error("Search failed");
            }
        } catch (error) {
            console.error('Semantic search error:', error);
            toast.error('Semantic search failed');
        } finally {
            setIsSearching(false);
        }
    };

    const handleDelete = async (id: string, e: React.MouseEvent) => {
        e.stopPropagation();
        if (!confirm('Are you sure you want to delete this file?')) return;

        try {
            await api.deleteLibraryFile(id);
            toast.success('File deleted');
            loadFiles(); // Refresh
        } catch (error) {
            console.error('Delete failed:', error);
            toast.error('Failed to delete file');
        }
    };

    const formatSize = (bytes: number) => {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    };

    const filteredFiles = files.filter(f =>
        f.filename.toLowerCase().includes(searchQuery.toLowerCase())
    );

    return (
        <div className="h-full flex flex-col bg-slate-950 text-slate-200 font-sans">
            {/* Header */}
            <header className="h-16 border-b border-slate-800 flex items-center justify-between px-8 bg-slate-950/50 backdrop-blur shrink-0">
                <div className="flex items-center gap-3">
                    <div className="p-2 bg-indigo-500/10 rounded-lg text-indigo-400">
                        <BookOpen className="w-5 h-5" />
                    </div>
                    <div>
                        <h1 className="text-lg font-semibold text-white">Digital Library</h1>
                        <p className="text-xs text-slate-500">Manage your local research assets</p>
                    </div>
                </div>

                <div className="flex items-center gap-4">
                    <div className="relative flex gap-2">
                        <div className="relative">
                            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
                            <input
                                type="text"
                                placeholder="Search files or ask a question..."
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                                onKeyDown={(e) => e.key === 'Enter' && handleSemanticSearch()}
                                className="w-80 bg-slate-900 border border-slate-800 text-sm rounded-full pl-9 pr-4 py-1.5 focus:outline-none focus:border-indigo-500 transition-colors"
                            />
                        </div>
                        <button
                            onClick={handleSemanticSearch}
                            disabled={isSearching}
                            className="bg-indigo-600 hover:bg-indigo-700 text-white p-1.5 rounded-full transition-colors disabled:opacity-50"
                            title="Run Semantic Search"
                        >
                            {isSearching ? <Loader2 className="w-4 h-4 animate-spin" /> : <BrainCircuit className="w-4 h-4" />}
                        </button>
                    </div>
                </div>
            </header>

            {/* Content */}
            <div className="flex-1 overflow-y-auto p-8">
                <div className="max-w-5xl mx-auto space-y-8">

                    {/* RAG Results Area */}
                    {showRag && searchQuery && (
                        <section className="space-y-4 animate-in fade-in slide-in-from-top-4">
                            <div className="flex items-center justify-between">
                                <h2 className="text-sm font-medium text-indigo-400 uppercase tracking-wider flex items-center gap-2">
                                    <BrainCircuit className="w-4 h-4" />
                                    Semantic Search Results
                                </h2>
                                <button onClick={() => setShowRag(false)} className="text-xs text-slate-500 hover:text-white">Close Results</button>
                            </div>

                            <div className="grid grid-cols-1 gap-3">
                                {ragResults.length === 0 && !isSearching ? (
                                    <div className="p-4 text-slate-500 text-sm italic">No semantic matches found.</div>
                                ) : (
                                    ragResults.map((result, idx) => (
                                        <div key={idx} className="p-4 bg-slate-900/50 rounded-xl border border-indigo-500/20 hover:border-indigo-500/40 transition-colors">
                                            <div className="flex justify-between items-start mb-2">
                                                <span className="text-teal-400 font-medium text-xs flex items-center gap-1.5">
                                                    <FileText className="w-3.5 h-3.5" />
                                                    {result.metadata?.source || 'Unknown Source'}
                                                </span>
                                                <span className="text-indigo-400 text-xs font-mono">{(result.score * 100).toFixed(0)}% Relevance</span>
                                            </div>
                                            <p className="text-slate-300 text-sm leading-relaxed">
                                                {/* Visual placeholder for result content. In Phase 1 we verify metadata retrieval. */}
                                                Matched Metadata: {JSON.stringify(result.metadata)}
                                            </p>
                                        </div>
                                    ))
                                )}
                            </div>
                            <div className="h-px bg-slate-800 my-6" />
                        </section>
                    )}

                    {/* Upload Section */}
                    <section>
                        <UploadZone onUploadComplete={loadFiles} />
                    </section>

                    {/* Files List */}
                    <section className="space-y-4">
                        <div className="flex items-center justify-between">
                            <h2 className="text-sm font-medium text-slate-400 uppercase tracking-wider">
                                Library Content ({files.length})
                            </h2>
                        </div>

                        {isLoading ? (
                            <div className="text-center py-12 text-slate-500">Loading library...</div>
                        ) : filteredFiles.length === 0 ? (
                            <div className="text-center py-12 border border-dashed border-slate-800 rounded-xl">
                                <p className="text-slate-500">No files found. Upload some documents to get started.</p>
                            </div>
                        ) : (
                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                                {filteredFiles.map(file => (
                                    <div key={file.id} className="group relative bg-slate-900 border border-slate-800 hover:border-indigo-500/50 rounded-xl p-4 transition-all hover:shadow-lg hover:shadow-indigo-500/10">
                                        <div className="flex items-start justify-between mb-3">
                                            <div className="p-2 bg-slate-800 rounded-lg text-slate-400 group-hover:text-indigo-400 group-hover:bg-indigo-500/10 transition-colors">
                                                <FileText className="w-6 h-6" />
                                            </div>
                                            <button
                                                onClick={(e) => handleDelete(file.id, e)}
                                                className="p-1.5 text-slate-600 hover:text-red-400 hover:bg-red-500/10 rounded transition-colors opacity-0 group-hover:opacity-100"
                                                title="Delete File"
                                            >
                                                <Trash2 className="w-4 h-4" />
                                            </button>
                                        </div>

                                        <h3 className="font-medium text-slate-200 truncate mb-1" title={file.filename}>
                                            {file.filename}
                                        </h3>

                                        <div className="flex items-center gap-4 text-xs text-slate-500">
                                            <span className="flex items-center gap-1">
                                                <FileType className="w-3 h-3" />
                                                {formatSize(file.size_bytes)}
                                            </span>
                                            <span className="flex items-center gap-1">
                                                <Clock className="w-3 h-3" />
                                                {formatDistanceToNow(new Date(file.added_at), { addSuffix: true })}
                                            </span>
                                        </div>

                                        {file.processed && (
                                            <div className="absolute bottom-4 right-4">
                                                <div className="w-2 h-2 rounded-full bg-teal-500 shadow-[0_0_8px] shadow-teal-500" title="Processed & Indexed" />
                                            </div>
                                        )}
                                    </div>
                                ))}
                            </div>
                        )}
                    </section>
                </div>
            </div>
        </div>
    );
}
