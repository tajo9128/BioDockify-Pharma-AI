import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import apiService from '../api';
import { Activity, Database, FileText, CheckCircle, AlertCircle, Loader } from 'lucide-react';

const ResearchDashboard = () => {
    const { taskId } = useParams();
    const navigate = useNavigate();
    const [status, setStatus] = useState('loading');
    const [result, setResult] = useState(null);
    const [error, setError] = useState(null);
    const [logs, setLogs] = useState([]);

    useEffect(() => {
        let pollInterval;

        const checkStatus = async () => {
            try {
                const data = await apiService.getTaskStatus(taskId);
                setStatus(data.status);

                if (data.status === 'completed') {
                    setResult(data.result);
                    clearInterval(pollInterval);
                } else if (data.status === 'failed') {
                    setError('Research task failed.');
                    clearInterval(pollInterval);
                }

                // Simulate logs based on status
                if (data.status === 'planning') addLog('Planning research steps...');
                if (data.status === 'executing') addLog('Executing research modules...');

            } catch (err) {
                setError('Failed to fetch status');
                clearInterval(pollInterval);
            }
        };

        checkStatus();
        pollInterval = setInterval(checkStatus, 2000);

        return () => clearInterval(pollInterval);
    }, [taskId]);

    const addLog = (msg) => {
        setLogs(prev => {
            if (prev.includes(msg)) return prev;
            return [...prev, msg];
        });
    };

    const StatusBadge = ({ status }) => {
        const colors = {
            pending: 'bg-yellow-500/20 text-yellow-400',
            planning: 'bg-blue-500/20 text-blue-400',
            executing: 'bg-purple-500/20 text-purple-400',
            completed: 'bg-green-500/20 text-green-400',
            failed: 'bg-red-500/20 text-red-400'
        };
        return (
            <span className={`px-3 py-1 rounded-full text-sm font-medium ${colors[status] || 'bg-gray-500/20'}`}>
                {status.toUpperCase()}
            </span>
        );
    };

    return (
        <div className="min-h-screen bg-slate-900 text-white p-8">
            <div className="max-w-6xl mx-auto space-y-6">

                {/* Header */}
                <div className="flex justify-between items-center bg-slate-800 p-6 rounded-xl border border-slate-700">
                    <div>
                        <h1 className="text-2xl font-bold flex items-center gap-2">
                            <Activity className="text-blue-400" />
                            Research Context: {result?.title || taskId}
                        </h1>
                        <p className="text-slate-400 mt-1">ID: {taskId}</p>
                    </div>
                    <StatusBadge status={status} />
                </div>

                {/* Stats Grid */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    <div className="bg-slate-800 p-6 rounded-xl border border-slate-700">
                        <h3 className="text-slate-400 text-sm font-medium mb-2 flex items-center gap-2">
                            <FileText size={16} /> Extracted Text
                        </h3>
                        <p className="text-3xl font-bold">{result?.text_length || 0} <span className="text-sm font-normal text-slate-500">chars</span></p>
                    </div>

                    <div className="bg-slate-800 p-6 rounded-xl border border-slate-700">
                        <h3 className="text-slate-400 text-sm font-medium mb-2 flex items-center gap-2">
                            <Database size={16} /> Entities Found
                        </h3>
                        <div className="space-y-1">
                            <div className="flex justify-between">
                                <span>Drugs:</span>
                                <span className="font-bold text-blue-400">{result?.entities?.drugs?.length || 0}</span>
                            </div>
                            <div className="flex justify-between">
                                <span>Diseases:</span>
                                <span className="font-bold text-red-400">{result?.entities?.diseases?.length || 0}</span>
                            </div>
                            <div className="flex justify-between">
                                <span>Genes:</span>
                                <span className="font-bold text-green-400">{result?.entities?.genes?.length || 0}</span>
                            </div>
                        </div>
                    </div>

                    <div className="bg-slate-800 p-6 rounded-xl border border-slate-700">
                        <h3 className="text-slate-400 text-sm font-medium mb-2 flex items-center gap-2">
                            <CheckCircle size={16} /> Knowledge Graph
                        </h3>
                        <div className="space-y-1 text-sm">
                            <p>Nodes: {result?.stats?.Drugs || 0} Drugs, {result?.stats?.Diseases || 0} Diseases</p>
                            <p>Density: Low (MVP)</p>
                        </div>
                    </div>
                </div>

                {/* Logs / Progress */}
                <div className="bg-slate-950 p-6 rounded-xl border border-slate-800 font-mono text-sm h-64 overflow-y-auto">
                    <h3 className="text-slate-500 mb-4 sticky top-0 bg-slate-950 pb-2 border-b border-slate-800">Execution Log</h3>
                    {logs.map((log, i) => (
                        <div key={i} className="mb-1 text-green-400/80">
                            <span className="text-slate-600">[{new Date().toLocaleTimeString()}]</span> {log}
                        </div>
                    ))}
                    {status === 'completed' && (
                        <div className="text-green-500 mt-4 font-bold">✓ Research Complete. Results ready for review.</div>
                    )}
                </div>

                {/* Action Bar */}
                <div className="flex justify-end gap-4">
                    <button onClick={() => navigate('/')} className="px-6 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg transition">
                        Back to Home
                    </button>
                </div>

            </div>
        </div>
    );
};

export default ResearchDashboard;
