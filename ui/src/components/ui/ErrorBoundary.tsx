'use client';

import React, { Component, ErrorInfo, ReactNode } from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

interface Props {
    children: ReactNode;
    fallback?: ReactNode;
    name?: string; // Component name for debugging
}

interface State {
    hasError: boolean;
    error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
    public state: State = {
        hasError: false,
        error: null,
    };

    public static getDerivedStateFromError(error: Error): State {
        return { hasError: true, error };
    }

    public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
        console.error(`ErrorBoundary caught an error in ${this.props.name || 'Component'}:`, error, errorInfo);
    }

    private handleRetry = () => {
        this.setState({ hasError: false, error: null });
    };

    public render() {
        if (this.state.hasError) {
            if (this.props.fallback) {
                return this.props.fallback;
            }

            return (
                <div className="flex flex-col items-center justify-center p-6 h-full min-h-[150px] bg-slate-900/50 border border-red-500/20 rounded-xl text-center">
                    <AlertTriangle className="w-8 h-8 text-red-500 mb-2" />
                    <h3 className="text-sm font-semibold text-red-400 mb-1">
                        {this.props.name ? `${this.props.name} Error` : 'Component Error'}
                    </h3>
                    <p className="text-xs text-slate-500 mb-4 max-w-[200px] line-clamp-2">
                        {this.state.error?.message || 'Something went wrong.'}
                    </p>
                    <button
                        onClick={this.handleRetry}
                        className="px-3 py-1.5 bg-red-500/10 hover:bg-red-500/20 text-red-400 text-xs rounded-md transition-colors flex items-center gap-1"
                    >
                        <RefreshCw className="w-3 h-3" />
                        Retry
                    </button>
                </div>
            );
        }

        return this.props.children;
    }
}
