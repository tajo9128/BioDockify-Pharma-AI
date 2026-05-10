import React, { useState, useEffect } from 'react';
import { Database, RefreshCcw, ExternalLink, AlertTriangle } from 'lucide-react';
import { api } from '@/lib/api';

const DEFAULT_SURFSENSE_URL = "http://localhost:3003";

export default function SurfSenseView() {
    const [iframeKey, setIframeKey] = useState(0);
    const [isLoading, setIsLoading] = useState(true);
    const [loadError, setLoadError] = useState(false);
    const [surfsenseUrl, setSurfsenseUrl] = useState(DEFAULT_SURFSENSE_URL);

    // Load SurfSense URL from settings
    useEffect(() => {
        api.getSettings().then(settings => {
            const url = settings?.ai_provider?.surfsense_url || DEFAULT_SURFSENSE_URL;
            setSurfsenseUrl(url);
        }).catch(() => {
            // Use default if settings fail to load
        });
    }, []);

    const refreshIframe = () => {
        setIframeKey(prev => prev + 1);
        setIsLoading(true);
        setLoadError(false);
    };

    const handleIframeLoad = () => {
        setIsLoading(false);
        setLoadError(false);
    };

    const handleIframeError = () => {
        setIsLoading(false);
        setLoadError(true);
    };

    return (
        <div className="h-full flex flex-col bg-slate-950">
            {/* Header/Controls */}
            <div className="flex items-center justify-between px-6 py-3 border-b border-slate-800 bg-slate-900/50">
                <div className="flex items-center space-x-3">
                    <Database className="w-5 h-5 text-indigo-400" />
                    <h2 className="font-bold text-slate-200">SurfSense Knowledge Engine</h2>
                </div>
                <div className="flex items-center space-x-2">
                    <a
                        href={surfsenseUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="p-2 text-slate-400 hover:text-white transition-colors rounded hover:bg-slate-800"
                        title="Open in Browser"
                    >
                        <ExternalLink className="w-4 h-4" />
                    </a>
                    <button
                        onClick={refreshIframe}
                        className="p-2 text-slate-400 hover:text-white transition-colors rounded hover:bg-slate-800"
                        title="Reload"
                    >
                        <RefreshCcw className="w-4 h-4" />
                    </button>
                </div>
            </div>

            {/* Content Area */}
            <div className="flex-1 relative bg-slate-950">
                {isLoading && (
                    <div className="absolute inset-0 flex items-center justify-center z-10 bg-slate-950">
                        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-500" />
                    </div>
                )}

                {loadError ? (
                    <div className="absolute inset-0 flex flex-col items-center justify-center space-y-4 text-slate-400">
                        <Database className="w-12 h-12 opacity-20" />
                        <p>Failed to connect to SurfSense.</p>
                        <button
                            onClick={refreshIframe}
                            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg transition-colors"
                        >
                            Retry Connection
                        </button>
                    </div>
                ) : (
                    <iframe
                        key={iframeKey}
                        src={surfsenseUrl}
                        className="w-full h-full border-none bg-white" // SurfSense UI is likely light mode by default or needs white bg if loading
                        title="SurfSense Interface"
                        onLoad={handleIframeLoad}
                        onError={handleIframeError}
                        allow="clipboard-read; clipboard-write; microphone"
                    />
                )}
            </div>
        </div>
    );
}
