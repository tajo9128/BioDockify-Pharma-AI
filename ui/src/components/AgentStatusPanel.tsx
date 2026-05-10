'use client';

import React, { useEffect, useState } from 'react';
import { Brain, CheckCircle, XCircle, Clock, Activity, ChevronDown, ChevronUp } from 'lucide-react';

interface ThinkingTrace {
    step: string;
    reasoning: string;
    timestamp: string;
}

interface ExecutionLog {
    action: string;
    status: string;
    details: Record<string, any>;
    timestamp: string;
}

interface AgentStatus {
    current_task: string | null;
    current_step: number;
    total_steps: number;
    progress_percent: number;
    is_running: boolean;
    latest_thinking: ThinkingTrace | null;
    recent_log: ExecutionLog[];
}

interface AgentStatusPanelProps {
    /** If true, uses WebSocket for real-time updates. Otherwise polls /agent-status */
    useWebSocket?: boolean;
    /** Polling interval in ms (only used if useWebSocket is false) */
    pollInterval?: number;
    /** Custom API base URL */
    apiBaseUrl?: string;
    /** Callback when agent completes */
    onComplete?: () => void;
}

export default function AgentStatusPanel({
    useWebSocket = true,
    pollInterval = 2000,
    apiBaseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:3000',
    onComplete
}: AgentStatusPanelProps) {
    const [status, setStatus] = useState<AgentStatus | null>(null);
    const [connected, setConnected] = useState(false);
    const [expanded, setExpanded] = useState(true);
    const [allThinking, setAllThinking] = useState<ThinkingTrace[]>([]);

    // WebSocket connection
    useEffect(() => {
        if (!useWebSocket) return;

        const wsUrl = `${apiBaseUrl.replace('http', 'ws')}/api/research/ws/agent-thinking`;
        let ws: WebSocket | null = null;
        let reconnectTimeout: NodeJS.Timeout | null = null;

        const connect = () => {
            ws = new WebSocket(wsUrl);

            ws.onopen = () => {
                console.log('[AgentStatusPanel] WebSocket connected');
                setConnected(true);
            };

            ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    if (data.type === 'agent_status') {
                        const newStatus = data.data as AgentStatus;
                        setStatus(newStatus);

                        // Accumulate thinking traces
                        if (newStatus.latest_thinking) {
                            setAllThinking(prev => {
                                const exists = prev.some(t =>
                                    t.timestamp === newStatus.latest_thinking?.timestamp
                                );
                                if (!exists && newStatus.latest_thinking) {
                                    return [...prev, newStatus.latest_thinking];
                                }
                                return prev;
                            });
                        }

                        // Check for completion
                        if (!newStatus.is_running && newStatus.progress_percent === 100) {
                            onComplete?.();
                        }
                    }
                } catch (e) {
                    console.error('[AgentStatusPanel] Parse error:', e);
                }
            };

            ws.onclose = () => {
                setConnected(false);
                // Reconnect after 3 seconds
                reconnectTimeout = setTimeout(connect, 3000);
            };

            ws.onerror = () => {
                ws?.close();
            };
        };

        connect();

        return () => {
            if (ws) {
                ws.onopen = null;
                ws.onmessage = null;
                ws.onclose = null;
                ws.onerror = null;
                ws.close();
                ws = null;
            }
            if (reconnectTimeout) {
                clearTimeout(reconnectTimeout);
                reconnectTimeout = null;
            }
        };
    }, [useWebSocket, apiBaseUrl, onComplete]);

    // Polling fallback
    useEffect(() => {
        if (useWebSocket) return;

        const fetchStatus = async () => {
            try {
                const res = await fetch(`${apiBaseUrl}/api/research/agent-status`);
                if (res.ok) {
                    const data = await res.json();
                    setStatus(data);
                    setConnected(true);
                }
            } catch {
                setConnected(false);
            }
        };

        fetchStatus();
        const interval = setInterval(fetchStatus, pollInterval);
        return () => clearInterval(interval);
    }, [useWebSocket, apiBaseUrl, pollInterval]);

    // Reset thinking traces when new task starts
    useEffect(() => {
        if (status?.current_step === 0 && status?.is_running) {
            setAllThinking([]);
        }
    }, [status?.current_task, status?.current_step, status?.is_running]);

    if (!status) {
        return (
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
                <div className="flex items-center gap-2 text-slate-400">
                    <Activity className="w-4 h-4 animate-pulse" />
                    <span className="text-sm">Connecting to agent...</span>
                </div>
            </div>
        );
    }

    const statusColor = status.is_running
        ? 'text-sky-400'
        : status.progress_percent === 100
            ? 'text-emerald-400'
            : 'text-slate-400';

    return (
        <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
            {/* Header */}
            <div
                className="flex items-center justify-between p-4 cursor-pointer hover:bg-slate-800/50 transition-colors"
                onClick={() => setExpanded(!expanded)}
            >
                <div className="flex items-center gap-3">
                    <div className={`p-2 rounded-lg ${status.is_running ? 'bg-sky-500/20' : 'bg-slate-800'}`}>
                        <Brain className={`w-5 h-5 ${statusColor} ${status.is_running ? 'animate-pulse' : ''}`} />
                    </div>
                    <div>
                        <h3 className="font-semibold text-white">
                            {status.current_task || 'Agent Idle'}
                        </h3>
                        <p className="text-xs text-slate-400">
                            {status.is_running ? 'Thinking...' : 'Ready'}
                            {connected && <span className="ml-2 text-emerald-400">● Connected</span>}
                        </p>
                    </div>
                </div>
                <div className="flex items-center gap-4">
                    {/* Progress */}
                    <div className="text-right">
                        <span className={`text-lg font-bold ${statusColor}`}>
                            {status.progress_percent}%
                        </span>
                        <p className="text-xs text-slate-500">
                            Step {status.current_step}/{status.total_steps}
                        </p>
                    </div>
                    {expanded ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
                </div>
            </div>

            {/* Progress Bar */}
            <div className="h-1 bg-slate-800">
                <div
                    className={`h-full transition-all duration-500 ${status.is_running ? 'bg-sky-500' : 'bg-emerald-500'
                        }`}
                    style={{ width: `${status.progress_percent}%` }}
                />
            </div>

            {expanded && (
                <div className="p-4 space-y-4">
                    {/* Current Thinking */}
                    {status.latest_thinking && (
                        <div className="bg-slate-800/50 rounded-lg p-3 border border-slate-700">
                            <div className="flex items-center gap-2 mb-2">
                                <Brain className="w-4 h-4 text-purple-400" />
                                <span className="text-sm font-medium text-purple-400">
                                    {status.latest_thinking.step}
                                </span>
                            </div>
                            <p className="text-sm text-slate-300 leading-relaxed">
                                {status.latest_thinking.reasoning}
                            </p>
                        </div>
                    )}

                    {/* Thinking History */}
                    {allThinking.length > 1 && (
                        <div className="space-y-2">
                            <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                                Thinking History
                            </h4>
                            <div className="max-h-40 overflow-y-auto space-y-2">
                                {allThinking.slice(0, -1).reverse().map((trace, i) => (
                                    <div key={i} className="flex items-start gap-2 text-xs text-slate-400">
                                        <Clock className="w-3 h-3 mt-0.5 flex-shrink-0" />
                                        <div>
                                            <span className="text-slate-500">{trace.step}:</span>{' '}
                                            <span>{trace.reasoning.slice(0, 100)}...</span>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Execution Log */}
                    {status.recent_log.length > 0 && (
                        <div className="space-y-2">
                            <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                                Recent Actions
                            </h4>
                            <div className="space-y-1">
                                {status.recent_log.map((log, i) => (
                                    <div key={i} className="flex items-center gap-2 text-xs">
                                        {log.status === 'success' ? (
                                            <CheckCircle className="w-3 h-3 text-emerald-400" />
                                        ) : log.status === 'error' ? (
                                            <XCircle className="w-3 h-3 text-red-400" />
                                        ) : (
                                            <Activity className="w-3 h-3 text-sky-400" />
                                        )}
                                        <span className="text-slate-300">{log.action}</span>
                                        <span className="text-slate-500 ml-auto">
                                            {new Date(log.timestamp).toLocaleTimeString()}
                                        </span>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
