
import React, { useState, useEffect } from 'react';
import { ShieldCheck, AlertTriangle, CheckCircle, FileText, Lock } from 'lucide-react';
import { api } from '@/lib/api';

interface CompliancePanelProps {
    text: string;
    onComplianceChange: (isCompliant: boolean) => void;
}

export default function CompliancePanel({ text, onComplianceChange }: CompliancePanelProps) {
    const [analyzing, setAnalyzing] = useState(false);
    const [report, setReport] = useState<any>(null);

    // Human Gate States
    const [reviewedCitations, setReviewedCitations] = useState(false);
    const [editedDraft, setEditedDraft] = useState(false);
    const [approvedWording, setApprovedWording] = useState(false);

    useEffect(() => {
        if (!text) return;

        const debounce = setTimeout(() => {
            analyzeText();
        }, 1000); // 1s debounce to avoid API spam

        return () => clearTimeout(debounce);
    }, [text]);

    const analyzeText = async () => {
        setAnalyzing(true);
        try {
            const res = await api.checkCompliance(text);
            setReport(res);
        } catch (e) {
            console.error("Compliance Check Failed", e);
        } finally {
            setAnalyzing(false);
        }
    };

    // derived state
    const isGateOpen = reviewedCitations && editedDraft && approvedWording;

    useEffect(() => {
        // Pass up the compliance state
        // Rule: Report must allow it AND Human Gate must be checked
        if (report && isGateOpen) {
            onComplianceChange(true);
        } else {
            onComplianceChange(false);
        }
    }, [report, isGateOpen, onComplianceChange]);


    if (!report) return <div className="text-slate-500 text-sm">Waiting for content analysis...</div>;

    const getScoreColor = (score: number) => {
        if (score >= 0.7) return 'text-green-400';
        if (score >= 0.4) return 'text-yellow-400';
        return 'text-red-400';
    };

    return (
        <div className="bg-slate-900 border border-slate-700 rounded-xl p-6 mt-6">
            <div className="flex items-center justify-between mb-6">
                <h3 className="text-lg font-bold text-white flex items-center">
                    <ShieldCheck className="w-5 h-5 mr-2 text-teal-400" />
                    Academic Writing Compliance
                </h3>
                {analyzing && <span className="text-xs text-slate-400 animate-pulse">Analyzing...</span>}
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                <div className="bg-slate-950 p-3 rounded-lg border border-slate-800">
                    <div className="text-xs text-slate-500 mb-1">Academic Tone</div>
                    <div className={`text-xl font-bold ${getScoreColor(report.scores.academic_tone)}`}>
                        {(report.scores.academic_tone * 100).toFixed(0)}%
                    </div>
                </div>
                <div className="bg-slate-950 p-3 rounded-lg border border-slate-800">
                    <div className="text-xs text-slate-500 mb-1">Evidence Density</div>
                    <div className={`text-xl font-bold ${getScoreColor(report.scores.evidence_density)}`}>
                        {(report.scores.evidence_density * 100).toFixed(0)}%
                    </div>
                    {report.scores.evidence_density < 0.3 && (
                        <div className="text-[10px] text-red-500 mt-1 flex items-center">
                            <AlertTriangle className="w-3 h-3 mr-1" /> Citations needed
                        </div>
                    )}
                </div>
                <div className="bg-slate-950 p-3 rounded-lg border border-slate-800">
                    <div className="text-xs text-slate-500 mb-1">Stylistic Variance</div>
                    <div className={`text-xl font-bold ${getScoreColor(report.scores.variability)}`}>
                        {(report.scores.variability * 100).toFixed(0)}%
                    </div>
                </div>
            </div>

            {report.issues.length > 0 && (
                <div className="mb-6 p-4 bg-slate-900/50 rounded-lg border border-yellow-900/30">
                    <h4 className="text-sm font-medium text-yellow-500 mb-2">Style Recommendations</h4>
                    <div className="space-y-2 max-h-32 overflow-y-auto custom-scrollbar">
                        {report.issues.map((issue: any, idx: number) => (
                            <div key={idx} className="text-xs text-slate-400 flex">
                                <span className="text-red-400 line-through mr-2">{issue.found}</span>
                                <span className="text-green-400">→ {issue.suggestion}</span>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* HUMAN REVISION GATE */}
            <div className="border-t border-slate-800 pt-6">
                <h4 className="text-sm font-bold text-slate-300 mb-3 flex items-center">
                    <Lock className="w-4 h-4 mr-2 text-orange-400" />
                    Human Revision Gate (Mandatory)
                </h4>
                <div className="space-y-3">
                    <label className="flex items-center space-x-3 cursor-pointer group">
                        <div className={`w-5 h-5 rounded border flex items-center justify-center transition-colors ${reviewedCitations ? 'bg-teal-500 border-teal-500' : 'bg-slate-950 border-slate-600 group-hover:border-slate-500'}`}>
                            {reviewedCitations && <CheckCircle className="w-3.5 h-3.5 text-white" />}
                        </div>
                        <input type="checkbox" className="hidden" checked={reviewedCitations} onChange={e => setReviewedCitations(e.target.checked)} />
                        <span className="text-sm text-slate-400 group-hover:text-slate-200">I have verified all citations and references.</span>
                    </label>

                    <label className="flex items-center space-x-3 cursor-pointer group">
                        <div className={`w-5 h-5 rounded border flex items-center justify-center transition-colors ${editedDraft ? 'bg-teal-500 border-teal-500' : 'bg-slate-950 border-slate-600 group-hover:border-slate-500'}`}>
                            {editedDraft && <CheckCircle className="w-3.5 h-3.5 text-white" />}
                        </div>
                        <input type="checkbox" className="hidden" checked={editedDraft} onChange={e => setEditedDraft(e.target.checked)} />
                        <span className="text-sm text-slate-400 group-hover:text-slate-200">I have manually edited heavily stylized AI phrasing.</span>
                    </label>

                    <label className="flex items-center space-x-3 cursor-pointer group">
                        <div className={`w-5 h-5 rounded border flex items-center justify-center transition-colors ${approvedWording ? 'bg-teal-500 border-teal-500' : 'bg-slate-950 border-slate-600 group-hover:border-slate-500'}`}>
                            {approvedWording && <CheckCircle className="w-3.5 h-3.5 text-white" />}
                        </div>
                        <input type="checkbox" className="hidden" checked={approvedWording} onChange={e => setApprovedWording(e.target.checked)} />
                        <span className="text-sm text-slate-400 group-hover:text-slate-200">I approve the final wording and assert authorship.</span>
                    </label>
                </div>

                <div className="mt-4 p-3 bg-slate-950 rounded border border-slate-800 flex items-center justify-between">
                    <span className="text-xs text-slate-500 italic">
                        disclosure: &quot;AI tools were used for drafting assistance...&quot;
                    </span>
                    <button
                        onClick={() => navigator.clipboard.writeText("AI tools were used for literature organization and drafting assistance. All content was reviewed, edited, and validated by the author.")}
                        className="text-xs text-teal-400 hover:text-teal-300 font-medium"
                    >
                        Copy Statement
                    </button>
                </div>

            </div>
        </div>
    );
}
