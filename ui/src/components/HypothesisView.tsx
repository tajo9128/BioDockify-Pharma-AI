
import React, { useState, useEffect } from 'react';
import { Plus, FlaskConical, CheckCircle2, XCircle, AlertCircle, RefreshCw, ChevronRight } from 'lucide-react';
import { api } from '@/lib/api';
import { Hypothesis, HypothesisStatus } from '@/lib/hypothesisTypes';
import { formatDate } from '@/lib/utils'; // Assuming this exists or I'll implement inline

export default function HypothesisView() {
    const [hypotheses, setHypotheses] = useState<Hypothesis[]>([]);
    const [loading, setLoading] = useState(true);
    const [showAddForm, setShowAddForm] = useState(false);

    // New Hypothesis State
    const [newStatement, setNewStatement] = useState('');
    const [newRationale, setNewRationale] = useState('');

    useEffect(() => {
        fetchHypotheses();
    }, []);

    const fetchHypotheses = async () => {
        try {
            setLoading(true);
            // We need to extend api.ts to support these new endpoints, 
            // but for now I'll assume I can add them or use fetch directly if needed.
            // Ideally I should update api.ts first. I'll mock the fetch here if api.ts isn't updated, 
            // but I plan to update api.ts next.
            // Let's assume api.ts has getHypotheses(). 
            // Since I can't edit api.ts in this same turn easily without context, 
            // I will put a placeholder logic here that might fail if api.ts is not updated.
            // Wait, I should perform the api.ts update first or inline the fetch.
            // I'll inline fetch for now to be safe, then refactor to api.ts.

            const res = await fetch('/api/hypothesis');
            if (res.ok) {
                const data = await res.json();
                setHypotheses(data);
            }
        } catch (e) {
            console.error("Failed to fetch hypotheses", e);
        } finally {
            setLoading(false);
        }
    };

    const handleCreate = async () => {
        if (!newStatement.trim()) return;
        try {
            const res = await fetch('/api/hypothesis?statement=' + encodeURIComponent(newStatement) + '&rationale=' + encodeURIComponent(newRationale), {
                method: 'POST'
            });
            if (res.ok) {
                setNewStatement('');
                setNewRationale('');
                setShowAddForm(false);
                fetchHypotheses();
            }
        } catch (e) {
            console.error("Failed to create hypothesis", e);
        }
    };

    const getStatusColor = (status: HypothesisStatus) => {
        switch (status) {
            case 'proposed': return 'bg-blue-500/20 text-blue-400 border-blue-500/50';
            case 'investigating': return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/50';
            case 'accepted': return 'bg-green-500/20 text-green-400 border-green-500/50';
            case 'rejected': return 'bg-red-500/20 text-red-400 border-red-500/50';
            case 'suspended': return 'bg-slate-500/20 text-slate-400 border-slate-500/50';
            default: return 'bg-slate-800 border-slate-700';
        }
    };

    return (
        <div className="h-full flex flex-col bg-slate-950 text-slate-100 p-6 overflow-hidden">
            {/* Header */}
            <div className="flex justify-between items-center mb-8">
                <div>
                    <h1 className="text-3xl font-light tracking-tight text-white flex items-center gap-3">
                        <FlaskConical className="h-8 w-8 text-teal-500" />
                        Scientific Method
                    </h1>
                    <p className="text-slate-400 mt-1">Manage hypotheses, track evidence, and falsify claims.</p>
                </div>
                <button
                    onClick={() => setShowAddForm(true)}
                    className="bg-teal-600 hover:bg-teal-500 text-white px-4 py-2 rounded-md flex items-center gap-2 transition-colors"
                >
                    <Plus className="h-4 w-4" />
                    New Hypothesis
                </button>
            </div>

            {/* Add Form */}
            {showAddForm && (
                <div className="mb-6 bg-slate-900/50 border border-slate-800 p-4 rounded-lg animate-in fade-in slide-in-from-top-4">
                    <h3 className="text-sm font-medium text-slate-300 mb-3">Propose New Hypothesis</h3>
                    <input
                        className="w-full bg-slate-950 border border-slate-800 rounded p-2 text-white mb-2 focus:ring-1 focus:ring-teal-500 outline-none"
                        placeholder="Hypothesis Statement (e.g. Protein X inhibits Pathway Y...)"
                        value={newStatement}
                        onChange={e => setNewStatement(e.target.value)}
                    />
                    <textarea
                        className="w-full bg-slate-950 border border-slate-800 rounded p-2 text-white mb-3 focus:ring-1 focus:ring-teal-500 outline-none h-20"
                        placeholder="Rationale / Initial Observations..."
                        value={newRationale}
                        onChange={e => setNewRationale(e.target.value)}
                    />
                    <div className="flex justify-end gap-2">
                        <button onClick={() => setShowAddForm(false)} className="px-3 py-1 text-slate-400 hover:text-white">Cancel</button>
                        <button onClick={handleCreate} className="px-3 py-1 bg-teal-600 rounded text-white hover:bg-teal-500">Propose</button>
                    </div>
                </div>
            )}

            {/* Kanban Board / List */}
            <div className="flex-1 overflow-y-auto pr-2">
                {loading ? (
                    <div className="flex items-center justify-center h-64 text-slate-500 gap-2">
                        <RefreshCw className="h-5 w-5 animate-spin" /> Loading Hypotheses...
                    </div>
                ) : hypotheses.length === 0 ? (
                    <div className="flex flex-col items-center justify-center h-64 text-slate-500 border border-dashed border-slate-800 rounded-lg">
                        <FlaskConical className="h-10 w-10 mb-2 opacity-50" />
                        <p>No hypotheses tracked yet. Propose one to start.</p>
                    </div>
                ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                        {hypotheses.map(h => (
                            <div key={h.id} className="bg-slate-900/50 border border-slate-800 rounded-lg p-5 hover:border-slate-700 transition-colors group cursor-pointer">
                                <div className="flex justify-between items-start mb-3">
                                    <span className={`text-xs px-2 py-0.5 rounded-full border ${getStatusColor(h.status)} uppercase font-bold tracking-wider`}>
                                        {h.status}
                                    </span>
                                    <span className="text-xs text-slate-500 font-mono">
                                        Conf: {(h.confidence_score * 100).toFixed(0)}%
                                    </span>
                                </div>

                                <h3 className="text-lg font-medium text-slate-100 mb-2 leading-snug">
                                    {h.statement}
                                </h3>

                                <p className="text-sm text-slate-400 line-clamp-3 mb-4 h-15">
                                    {h.rationale}
                                </p>

                                <div className="mt-auto border-t border-slate-800/50 pt-3 flex justify-between items-center">
                                    <div className="flex gap-2 text-xs text-slate-500">
                                        <span>{h.evidence.length} Evidence</span>
                                    </div>
                                    <ChevronRight className="h-4 w-4 text-slate-600 group-hover:text-teal-400 transition-colors" />
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}
