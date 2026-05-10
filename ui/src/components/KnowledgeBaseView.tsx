'use client';

import React, { useState, useEffect, useCallback } from 'react';
import {
    Database, Upload, Search, FileText, Trash2, RefreshCcw,
    File, FileWarning, CheckCircle, Loader2, X, Brain, Mic, Play, Pause
} from 'lucide-react';
import { api } from '@/lib/api';

interface LibraryFile {
    id: string;
    filename: string;
    size_bytes: number;
    added_at: string;
    processed: boolean;
    metadata?: Record<string, any>;
}

interface SearchResult {
    text: string;
    score: number;
    metadata: Record<string, any>;
}

export default function KnowledgeBaseView() {
    const [files, setFiles] = useState<LibraryFile[]>([]);
    const [searchQuery, setSearchQuery] = useState('');
    const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
    const [isSearching, setIsSearching] = useState(false);
    const [isUploading, setIsUploading] = useState(false);
    const [isLoading, setIsLoading] = useState(true);
    const [activeTab, setActiveTab] = useState<'files' | 'search'>('files');
    const [dragOver, setDragOver] = useState(false);

    // Podcast state
    const [isGeneratingPodcast, setIsGeneratingPodcast] = useState(false);
    const [podcastAudio, setPodcastAudio] = useState<string | null>(null);
    const [isPlaying, setIsPlaying] = useState(false);
    const audioRef = React.useRef<HTMLAudioElement>(null);

    // Load files on mount
    useEffect(() => {
        loadFiles();
    }, []);

    const loadFiles = async () => {
        setIsLoading(true);
        try {
            const data = await api.listLibraryFiles();
            setFiles(data || []);
        } catch (e) {
            console.error('Failed to load files:', e);
        } finally {
            setIsLoading(false);
        }
    };

    const handleUpload = async (fileList: FileList | null) => {
        if (!fileList || fileList.length === 0) return;

        setIsUploading(true);
        try {
            for (let i = 0; i < fileList.length; i++) {
                const file = fileList[i];
                await api.uploadLibraryFile(file);
            }
            await loadFiles();
        } catch (e: any) {
            alert(`Upload failed: ${e.message}`);
        } finally {
            setIsUploading(false);
        }
    };

    const handleDelete = async (fileId: string) => {
        if (!confirm('Delete this file from Knowledge Base?')) return;
        try {
            await api.deleteLibraryFile(fileId);
            await loadFiles();
        } catch (e: any) {
            alert(`Delete failed: ${e.message}`);
        }
    };

    const handleSearch = async () => {
        if (!searchQuery.trim()) return;

        setIsSearching(true);
        setActiveTab('search');
        try {
            const results = await api.queryLibrary(searchQuery, 10);
            setSearchResults(results || []);
        } catch (e) {
            console.error('Search failed:', e);
            setSearchResults([]);
        } finally {
            setIsSearching(false);
        }
    };

    // Podcast Generation
    const handleGeneratePodcast = async () => {
        if (searchResults.length === 0) {
            alert('Please search for content first to generate a podcast.');
            return;
        }

        setIsGeneratingPodcast(true);
        try {
            // Combine search results into podcast text
            const podcastText = searchResults
                .slice(0, 5)
                .map((r, i) => `Section ${i + 1}: ${r.text}`)
                .join('\n\n');

            const response = await api.knowledge.generatePodcast(podcastText);

            if (response.status === 'success' && response.audio_base64) {
                const audioUrl = `data:audio/mp3;base64,${response.audio_base64}`;
                setPodcastAudio(audioUrl);
            } else {
                alert(response.error || 'Failed to generate podcast');
            }
        } catch (e: any) {
            alert(`Podcast generation failed: ${e.message}`);
        } finally {
            setIsGeneratingPodcast(false);
        }
    };

    const togglePlayPause = () => {
        if (audioRef.current) {
            if (isPlaying) {
                audioRef.current.pause();
            } else {
                audioRef.current.play();
            }
            setIsPlaying(!isPlaying);
        }
    };

    const formatFileSize = (bytes: number) => {
        if (bytes < 1024) return `${bytes} B`;
        if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
        return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    };

    const formatDate = (isoString: string) => {
        return new Date(isoString).toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    };

    const getFileIcon = (filename: string) => {
        const ext = filename.split('.').pop()?.toLowerCase();
        switch (ext) {
            case 'pdf': return <FileText className="w-5 h-5 text-red-400" />;
            case 'docx':
            case 'doc': return <FileText className="w-5 h-5 text-blue-400" />;
            case 'ipynb': return <FileText className="w-5 h-5 text-orange-400" />;
            case 'md':
            case 'txt': return <FileText className="w-5 h-5 text-slate-400" />;
            default: return <File className="w-5 h-5 text-slate-500" />;
        }
    };

    // Drag and drop handlers
    const handleDragOver = (e: React.DragEvent) => {
        e.preventDefault();
        setDragOver(true);
    };

    const handleDragLeave = () => setDragOver(false);

    const handleDrop = (e: React.DragEvent) => {
        e.preventDefault();
        setDragOver(false);
        handleUpload(e.dataTransfer.files);
    };

    return (
        <div className="h-full flex flex-col bg-slate-950">
            {/* Header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-slate-900/50">
                <div className="flex items-center space-x-3">
                    <Database className="w-6 h-6 text-indigo-400" />
                    <h2 className="text-lg font-bold text-white">Knowledge Base</h2>
                    <span className="text-xs text-slate-500 bg-slate-800 px-2 py-1 rounded-full">
                        {files.length} documents
                    </span>
                </div>
                <div className="flex items-center space-x-2">
                    <button
                        onClick={loadFiles}
                        className="p-2 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition-colors"
                        title="Refresh"
                    >
                        <RefreshCcw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
                    </button>
                </div>
            </div>

            {/* Search Bar */}
            <div className="px-6 py-4 border-b border-slate-800/50">
                <div className="flex items-center space-x-2">
                    <div className="relative flex-1">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                        <input
                            type="text"
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                            placeholder="Search your knowledge base..."
                            className="w-full pl-10 pr-4 py-2.5 bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-colors"
                        />
                    </div>
                    <button
                        onClick={handleSearch}
                        disabled={isSearching || !searchQuery.trim()}
                        className="px-4 py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-700 disabled:text-slate-500 text-white rounded-lg font-medium transition-colors flex items-center space-x-2"
                    >
                        {isSearching ? <Loader2 className="w-4 h-4 animate-spin" /> : <Brain className="w-4 h-4" />}
                        <span>Search</span>
                    </button>
                    <button
                        onClick={handleGeneratePodcast}
                        disabled={isGeneratingPodcast || searchResults.length === 0}
                        className="px-4 py-2.5 bg-purple-600 hover:bg-purple-500 disabled:bg-slate-700 disabled:text-slate-500 text-white rounded-lg font-medium transition-colors flex items-center space-x-2"
                        title="Generate audio podcast from search results"
                    >
                        {isGeneratingPodcast ? <Loader2 className="w-4 h-4 animate-spin" /> : <Mic className="w-4 h-4" />}
                        <span>Podcast</span>
                    </button>
                </div>
            </div>

            {/* Audio Player (visible when podcast is generated) */}
            {podcastAudio && (
                <div className="px-6 py-3 bg-purple-900/30 border-b border-purple-800/50 flex items-center space-x-4">
                    <button
                        onClick={togglePlayPause}
                        className="p-2 bg-purple-600 hover:bg-purple-500 text-white rounded-full transition-colors"
                    >
                        {isPlaying ? <Pause className="w-5 h-5" /> : <Play className="w-5 h-5" />}
                    </button>
                    <div className="flex-1">
                        <audio
                            ref={audioRef}
                            src={podcastAudio}
                            onEnded={() => setIsPlaying(false)}
                            className="w-full"
                            controls
                        />
                    </div>
                    <button
                        onClick={() => { setPodcastAudio(null); setIsPlaying(false); }}
                        className="p-2 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition-colors"
                        title="Close player"
                    >
                        <X className="w-4 h-4" />
                    </button>
                </div>
            )}

            {/* Tabs */}
            <div className="px-6 border-b border-slate-800/50">
                <div className="flex space-x-4">
                    <button
                        onClick={() => setActiveTab('files')}
                        className={`py-3 px-1 text-sm font-medium border-b-2 transition-colors ${activeTab === 'files'
                            ? 'border-indigo-500 text-indigo-400'
                            : 'border-transparent text-slate-400 hover:text-slate-200'
                            }`}
                    >
                        Documents
                    </button>
                    <button
                        onClick={() => setActiveTab('search')}
                        className={`py-3 px-1 text-sm font-medium border-b-2 transition-colors ${activeTab === 'search'
                            ? 'border-indigo-500 text-indigo-400'
                            : 'border-transparent text-slate-400 hover:text-slate-200'
                            }`}
                    >
                        Search Results {searchResults.length > 0 && `(${searchResults.length})`}
                    </button>
                </div>
            </div>

            {/* Content Area */}
            <div className="flex-1 overflow-y-auto p-6">
                {activeTab === 'files' ? (
                    <>
                        {/* Upload Zone */}
                        <div
                            onDragOver={handleDragOver}
                            onDragLeave={handleDragLeave}
                            onDrop={handleDrop}
                            className={`mb-6 border-2 border-dashed rounded-xl p-8 text-center transition-all ${dragOver
                                ? 'border-indigo-500 bg-indigo-500/10'
                                : 'border-slate-700 hover:border-slate-600'
                                }`}
                        >
                            {isUploading ? (
                                <div className="flex flex-col items-center space-y-2">
                                    <Loader2 className="w-8 h-8 text-indigo-400 animate-spin" />
                                    <p className="text-slate-400">Processing documents...</p>
                                </div>
                            ) : (
                                <label className="cursor-pointer flex flex-col items-center space-y-3">
                                    <Upload className="w-10 h-10 text-slate-500" />
                                    <div>
                                        <span className="text-indigo-400 font-medium">Click to upload</span>
                                        <span className="text-slate-500"> or drag and drop</span>
                                    </div>
                                    <p className="text-xs text-slate-600">PDF, DOCX, TXT, MD, IPYNB, CSV, JSON</p>
                                    <input
                                        type="file"
                                        multiple
                                        accept=".pdf,.docx,.doc,.txt,.md,.ipynb,.csv,.json"
                                        onChange={(e) => handleUpload(e.target.files)}
                                        className="hidden"
                                    />
                                </label>
                            )}
                        </div>

                        {/* File List */}
                        {isLoading ? (
                            <div className="flex items-center justify-center py-12">
                                <Loader2 className="w-8 h-8 text-indigo-400 animate-spin" />
                            </div>
                        ) : files.length === 0 ? (
                            <div className="text-center py-12">
                                <Database className="w-12 h-12 text-slate-700 mx-auto mb-4" />
                                <p className="text-slate-500">No documents yet</p>
                                <p className="text-sm text-slate-600 mt-1">Upload files to build your knowledge base</p>
                            </div>
                        ) : (
                            <div className="space-y-2">
                                {files.slice(0, 100).map((file) => (
                                    <div
                                        key={file.id}
                                        className="flex items-center justify-between p-4 bg-slate-800/50 hover:bg-slate-800 rounded-lg border border-slate-700/50 transition-colors group"
                                    >
                                        <div className="flex items-center space-x-4">
                                            {getFileIcon(file.filename)}
                                            <div>
                                                <p className="text-white font-medium">{file.filename}</p>
                                                <div className="flex items-center space-x-3 text-xs text-slate-500">
                                                    <span>{formatFileSize(file.size_bytes)}</span>
                                                    <span>•</span>
                                                    <span>{formatDate(file.added_at)}</span>
                                                    {file.processed && (
                                                        <>
                                                            <span>•</span>
                                                            <span className="text-emerald-400 flex items-center">
                                                                <CheckCircle className="w-3 h-3 mr-1" />
                                                                Indexed
                                                            </span>
                                                        </>
                                                    )}
                                                </div>
                                            </div>
                                        </div>
                                        <button
                                            onClick={() => handleDelete(file.id)}
                                            className="p-2 text-slate-500 hover:text-red-400 hover:bg-red-400/10 rounded-lg opacity-0 group-hover:opacity-100 transition-all"
                                            title="Delete"
                                        >
                                            <Trash2 className="w-4 h-4" />
                                        </button>
                                    </div>
                                ))}
                                {files.length > 100 && (
                                    <div className="text-center py-4 text-xs text-slate-500">
                                        Showing 100 of {files.length} documents. Search to find specific files.
                                    </div>
                                )}
                            </div>
                        )}
                    </>
                ) : (
                    /* Search Results Tab */
                    <div>
                        {isSearching ? (
                            <div className="flex items-center justify-center py-12">
                                <Loader2 className="w-8 h-8 text-indigo-400 animate-spin" />
                            </div>
                        ) : searchResults.length === 0 ? (
                            <div className="text-center py-12">
                                <Search className="w-12 h-12 text-slate-700 mx-auto mb-4" />
                                <p className="text-slate-500">No results found</p>
                                <p className="text-sm text-slate-600 mt-1">Try different keywords or upload more documents</p>
                            </div>
                        ) : (
                            <div className="space-y-4">
                                {searchResults.map((result, idx) => (
                                    <div
                                        key={idx}
                                        className="p-4 bg-slate-800/50 rounded-lg border border-slate-700/50"
                                    >
                                        <div className="flex items-center justify-between mb-2">
                                            <span className="text-xs text-indigo-400 font-medium">
                                                {result.metadata?.source || 'Unknown Source'}
                                            </span>
                                            <span className="text-xs text-slate-500">
                                                Score: {(1 / (1 + result.score) * 100).toFixed(0)}%
                                            </span>
                                        </div>
                                        <p className="text-slate-300 text-sm leading-relaxed line-clamp-4">
                                            {result.text}
                                        </p>
                                        {result.metadata?.page_number && (
                                            <p className="text-xs text-slate-600 mt-2">
                                                Page {result.metadata.page_number}
                                            </p>
                                        )}
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
}
