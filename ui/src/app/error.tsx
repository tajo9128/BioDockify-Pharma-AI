'use client'

import { useEffect } from 'react'
import { AlertTriangle, RefreshCw } from 'lucide-react'

export default function Error({
    error,
    reset,
}: {
    error: Error & { digest?: string }
    reset: () => void
}) {
    useEffect(() => {
        // Ideally update this to send to Sentry or similar
        console.error('Runtime Error:', error)
    }, [error])

    return (
        <div className="flex h-full w-full flex-col items-center justify-center bg-slate-950 text-white gap-4 min-h-[400px]">
            <div className="bg-red-500/10 p-8 rounded-2xl border border-red-500/20 text-center max-w-md backdrop-blur-sm">
                <div className="w-16 h-16 bg-red-500/20 rounded-full flex items-center justify-center mx-auto mb-6 shadow-lg shadow-red-500/10">
                    <AlertTriangle className="w-8 h-8 text-red-500" />
                </div>
                <h2 className="text-xl font-bold mb-3 text-white">Application Error</h2>
                <p className="text-slate-400 mb-8 text-sm leading-relaxed">
                    {error.message || "An unexpected error occurred while loading this view."}
                </p>
                <button
                    onClick={() => reset()}
                    className="px-6 py-2.5 bg-gradient-to-r from-red-600 to-red-700 hover:from-red-500 hover:to-red-600 rounded-xl text-white text-sm font-semibold transition-all shadow-md hover:shadow-red-500/20 flex items-center gap-2 mx-auto"
                >
                    <RefreshCw className="w-4 h-4" />
                    Reload Application
                </button>
            </div>
        </div>
    )
}
