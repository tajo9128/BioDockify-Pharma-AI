'use client'

import { AlertTriangle, RefreshCw } from 'lucide-react'

export default function GlobalError({
    error,
    reset,
}: {
    error: Error & { digest?: string }
    reset: () => void
}) {
    return (
        <html>
            <body className="bg-slate-950 text-white">
                <div className="flex h-screen w-full flex-col items-center justify-center gap-4">
                    <div className="bg-red-500/10 p-10 rounded-3xl border border-red-500/20 text-center max-w-lg backdrop-blur-xl shadow-2xl">
                        <div className="w-20 h-20 bg-red-500/20 rounded-full flex items-center justify-center mx-auto mb-6 shadow-lg shadow-red-500/10 animate-pulse">
                            <AlertTriangle className="w-10 h-10 text-red-500" />
                        </div>
                        <h2 className="text-2xl font-bold mb-4 text-white">Critical System Failure</h2>
                        <div className="bg-black/30 rounded-lg p-4 mb-8 text-left font-mono text-xs text-red-200 overflow-auto max-h-32 border border-white/5">
                            {error.message || "Unknown Critical Error"}
                            {error.digest && <div className="mt-2 text-slate-500">Digest: {error.digest}</div>}
                        </div>

                        <button
                            onClick={() => reset()}
                            className="w-full px-6 py-3 bg-white text-slate-900 hover:bg-slate-200 rounded-xl text-base font-bold transition-all shadow-lg flex items-center justify-center gap-2"
                        >
                            <RefreshCw className="w-5 h-5" />
                            Restart System
                        </button>
                    </div>
                </div>
            </body>
        </html>
    )
}
