
import React, { useState, useRef } from 'react';
import { api, API_BASE } from '@/lib/api';
import { Calculator, BarChart3, GraduationCap, Microscope, AlertTriangle, CheckCircle2, Download, FileJson, FileSpreadsheet, FileCode, FileText, Loader2 } from 'lucide-react';
import ProgressStep from './ProgressStep';

type Tier = 'basic' | 'analytical' | 'advanced';
type FormatType = 'json' | 'csv' | 'latex' | 'markdown';

export default function StatisticsView() {
    // Input State
    const [dataInput, setDataInput] = useState('group,value\nTreatment,12.5\nTreatment,13.2\nTreatment,11.8\nControl,10.1\nControl,10.5\nControl,9.8');
    const [design, setDesign] = useState('two_group');
    const [tier, setTier] = useState<Tier>('basic');

    // Output State
    const [result, setResult] = useState<any>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // Progress State
    const [currentStep, setCurrentStep] = useState(0);
    const [totalSteps, setTotalSteps] = useState(5);
    const [progressSteps] = useState([
        'Data Parsing',
        'Statistical Tests',
        'Assumption Checks',
        'Result Generation',
        'Export Preparation'
    ]);

    // Export State
    const [exporting, setExporting] = useState<FormatType | null>(null);
    const [exportUrl, setExportUrl] = useState<string | null>(null);

    const resultRef = useRef<any>(null);

    const handleAnalyze = async () => {
        setLoading(true);
        setError(null);
        setResult(null);
        setCurrentStep(0);
        setExportUrl(null);

        try {
            // Step 1: Data Parsing
            setCurrentStep(1);
            await new Promise(resolve => setTimeout(resolve, 500)); // Simulate processing

            const rows = dataInput.trim().split('\n');
            const headers = rows[0].split(',').map(h => h.trim());
            const data = rows.slice(1).map(row => {
                const values = row.split(',');
                const obj: any = {};
                headers.forEach((h, i) => {
                    const val = values[i]?.trim();
                    const num = parseFloat(val);
                    obj[h] = isNaN(num) ? val : num;
                });
                return obj;
            });

            // Step 2: Statistical Tests
            setCurrentStep(2);
            const res = await api.analyzeStatistics(data, design, tier);
            resultRef.current = res;

            // Step 3: Assumption Checks (for analytical/advanced tiers)
            if (tier === 'analytical' || tier === 'advanced') {
                setCurrentStep(3);
                await new Promise(resolve => setTimeout(resolve, 300));
            }

            // Step 4: Result Generation
            setCurrentStep(4);
            await new Promise(resolve => setTimeout(resolve, 300));

            setResult(res);

            // Step 5: Export Preparation
            setCurrentStep(5);
            await new Promise(resolve => setTimeout(resolve, 200));

        } catch (e: any) {
            console.error(e);
            setError(e.message || "Analysis failed");
        } finally {
            setLoading(false);
        }
    };

    const handleExport = async (format: FormatType) => {
        if (!result) return;

        setExporting(format);
        try {
            const exportResult = await api.statistics.export(result, format);

            if (exportResult.success && exportResult.output_path) {
                // Create download URL
                const downloadUrl = `${API_BASE}/statistics/download?path=${encodeURIComponent(exportResult.output_path)}`;
                setExportUrl(downloadUrl);

                // Trigger download
                const link = document.createElement('a');
                link.href = downloadUrl;
                link.download = `analysis_${format}.${format}`;
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
            }
        } catch (e: any) {
            console.error('Export failed:', e);
            setError(e.message || `Export to ${format} failed`);
        } finally {
            setExporting(null);
        }
    };

    const getTierIcon = (t: string) => {
        switch (t) {
            case 'basic': return <GraduationCap className="w-4 h-4" />;
            case 'analytical': return <BarChart3 className="w-4 h-4" />;
            case 'advanced': return <Microscope className="w-4 h-4" />;
            default: return null;
        }
    }

    const getFormatIcon = (format: FormatType) => {
        switch (format) {
            case 'json': return <FileJson className="w-4 h-4" />;
            case 'csv': return <FileSpreadsheet className="w-4 h-4" />;
            case 'latex': return <FileCode className="w-4 h-4" />;
            case 'markdown': return <FileText className="w-4 h-4" />;
            default: return null;
        }
    }

    return (
        <div className="h-full flex flex-col bg-slate-950 text-slate-100 p-6 overflow-hidden">
            {/* Header */}
            <div className="flex justify-between items-center mb-6">
                <div>
                    <h1 className="text-3xl font-light tracking-tight text-white flex items-center gap-3">
                        <Calculator className="h-8 w-8 text-cyan-500" />
                        Unified Statistical Engine
                    </h1>
                    <p className="text-slate-400 mt-1">Multi-tier analysis for verified scientific rigor.</p>
                </div>

                {/* Tier Switcher */}
                <div className="bg-slate-900 p-1 rounded-lg flex gap-1 border border-slate-800">
                    {(['basic', 'analytical', 'advanced'] as Tier[]).map(t => (
                        <button
                            key={t}
                            onClick={() => setTier(t)}
                            className={`px-4 py-2 rounded-md text-sm font-medium transition-all flex items-center gap-2 ${tier === t
                                ? 'bg-cyan-900/50 text-cyan-200 border border-cyan-700/50'
                                : 'text-slate-400 hover:text-white hover:bg-white/5'
                                }`}
                        >
                            {getTierIcon(t)}
                            {t.charAt(0).toUpperCase() + t.slice(1)}
                        </button>
                    ))}
                </div>
            </div>

            <div className="flex-1 flex gap-6 overflow-hidden">
                {/* Input Panel */}
                <div className="w-1/3 flex flex-col gap-4 animate-in fade-in slide-in-from-left-4">
                    <div className="bg-slate-900/50 border border-slate-800 rounded-lg p-4 flex flex-col flex-1">
                        <label className="text-xs text-slate-500 uppercase tracking-wider font-semibold mb-2">Data Input (CSV Format)</label>
                        <textarea
                            className="flex-1 bg-slate-950 border border-slate-800 rounded p-4 font-mono text-sm text-slate-300 focus:ring-1 focus:ring-cyan-500 outline-none resize-none"
                            value={dataInput}
                            onChange={e => setDataInput(e.target.value)}
                            placeholder="col1,col2..."
                        />
                    </div>

                    <div className="bg-slate-900/50 border border-slate-800 rounded-lg p-4">
                        <label className="text-xs text-slate-500 uppercase tracking-wider font-semibold mb-2 block">Study Design</label>
                        <select
                            value={design}
                            onChange={(e: any) => setDesign(e.target.value)}
                            className="w-full bg-slate-950 border border-slate-800 rounded p-2 text-white focus:ring-1 focus:ring-cyan-500 outline-none"
                        >
                            {/* BASIC TIER */}
                            <option value="descriptive">Descriptive Statistics</option>
                            <option value="two_group">Two Group Comparison (T-Test)</option>

                            {/* ANALYTICAL TIER */}
                            {(tier === 'analytical' || tier === 'advanced') && (
                                <>
                                    <option value="anova">Multi Group (ANOVA)</option>
                                    <option value="correlation">Correlation Analysis</option>
                                    <option value="regression">Linear Regression</option>
                                    <option value="wilcoxon">Wilcoxon Signed Rank Test (Non-Parametric)</option>
                                    <option value="sign_test">Sign Test (Non-Parametric)</option>
                                    <option value="chi_goodness">Chi-Square Goodness of Fit</option>
                                    <option value="chi_independence">Chi-Square Test of Independence</option>
                                    <option value="fisher">Fisher's Exact Test</option>
                                    <option value="mcnemar">McNemar&apos;s Test</option>
                                </>
                            )}

                            {/* ADVANCED TIER */}
                            {tier === 'advanced' && (
                                <>
                                    <option value="survival">Survival Analysis (Kaplan-Meier)</option>
                                    <option value="pca">Principal Component Analysis (PCA)</option>
                                    <option value="bayesian">Bayesian Inference</option>
                                    <option value="friedman">Friedman Test (Repeated Measures)</option>
                                    <option value="dunns">Dunn&apos;s Post-Hoc Test</option>
                                    <option value="cmh">Cochran-Mantel-Haenszel Test</option>
                                </>
                            )}
                        </select>
                    </div>

                    <button
                        onClick={handleAnalyze}
                        disabled={loading}
                        className="bg-cyan-600 hover:bg-cyan-500 disabled:bg-slate-700 disabled:cursor-not-allowed text-white font-medium py-3 rounded-lg shadow-lg shadow-cyan-500/20 transition-all active:scale-95 flex items-center justify-center gap-2"
                    >
                        {loading ? (
                            <><Loader2 className="w-4 h-4 animate-spin" /> Analyzing...</>
                        ) : (
                            'Run Analysis'
                        )}
                    </button>

                    {/* Progress Display Box */}
                    {(loading || result) && (
                        <div className="bg-slate-900/50 border border-slate-800 rounded-lg p-4">
                            <div className="flex items-center justify-between mb-3">
                                <label className="text-xs text-slate-500 uppercase tracking-wider font-semibold">Analysis Progress</label>
                                <span className="text-xs text-slate-400">{currentStep} / {totalSteps}</span>
                            </div>
                            <div className="flex items-center gap-1">
                                {progressSteps.map((step, index) => (
                                    <ProgressStep
                                        key={index}
                                        step={index + 1}
                                        currentStep={currentStep}
                                        totalSteps={totalSteps}
                                        label={step}
                                        isLast={index === progressSteps.length - 1}
                                    />
                                ))}
                            </div>
                        </div>
                    )}
                </div>

                {/* Results Panel */}
                <div className="flex-1 bg-slate-900/30 border border-slate-800 rounded-lg p-6 overflow-y-auto animate-in fade-in slide-in-from-right-4 relative">
                    {error && (
                        <div className="bg-red-900/20 border border-red-500/50 text-red-200 p-4 rounded-lg flex items-start gap-3">
                            <AlertTriangle className="w-5 h-5 shrink-0 mt-0.5" />
                            <div>
                                <h4 className="font-semibold">Analysis Error</h4>
                                <p className="text-sm opacity-80">{error}</p>
                            </div>
                        </div>
                    )}

                    {result && !error && (
                        <div className="space-y-6">

                            {/* Tier 1: Summary Card */}
                            <div className="glass-panel p-6 rounded-xl border-l-4 border-cyan-500">
                                <h3 className="text-lg font-light text-cyan-300 mb-2">Summary</h3>
                                <p className="text-xl leading-relaxed font-medium">{result.summary || "No summary available."}</p>

                                {result.recommendation && (
                                    <div className="mt-4 flex items-center gap-2 text-emerald-400 bg-emerald-950/30 px-3 py-1.5 rounded-full w-fit text-sm">
                                        <CheckCircle2 className="w-4 h-4" />
                                        {result.recommendation}
                                    </div>
                                )}
                            </div>

                            {/* Tier 2: Analytical Details (Assumptions) */}
                            {(tier === 'analytical' || tier === 'advanced') && (
                                <div className="space-y-4">
                                    <div className="flex items-center gap-2 text-slate-400">
                                        <BarChart3 className="w-5 h-5" />
                                        <span className="text-sm font-semibold uppercase tracking-wider">Assumption Checks</span>
                                    </div>

                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                        {(result.assumptions_check || []).map((check: string, i: number) => (
                                            <div key={i} className="bg-slate-800/50 p-4 rounded-lg border border-slate-700">
                                                <p className="text-sm text-slate-300">{check}</p>
                                            </div>
                                        ))}
                                        {(!result.assumptions_check || result.assumptions_check.length === 0) && (
                                            <p className="text-slate-500 text-sm italic">No specific assumptions flagged for this test.</p>
                                        )}
                                    </div>
                                </div>
                            )}

                            {/* Tier 3: Advanced Methodology */}
                            {tier === 'advanced' && (
                                <div className="bg-slate-950 border border-indigo-900/50 rounded-lg p-5">
                                    <div className="flex items-center gap-2 text-indigo-400 mb-4">
                                        <Microscope className="w-5 h-5" />
                                        <span className="text-sm font-semibold uppercase tracking-wider">Methodology Report</span>
                                    </div>
                                    <p className="font-mono text-sm text-slate-300 leading-relaxed bg-black/30 p-4 rounded border border-white/5">
                                        {result.methodology_text}
                                    </p>

                                    <div className="mt-4 pt-4 border-t border-white/5">
                                        <h4 className="text-xs text-slate-500 uppercase mb-2">Reproducibility Metadata</h4>
                                        <pre className="text-xs text-slate-600 overflow-auto">
                                            {JSON.stringify(result.reproducibility || {}, null, 2)}
                                        </pre>
                                    </div>
                                </div>
                            )}

                            {/* Export Options */}
                            <div className="bg-slate-900/50 border border-slate-800 rounded-lg p-4">
                                <div className="flex items-center gap-2 mb-4">
                                    <Download className="w-5 h-5 text-cyan-500" />
                                    <h3 className="text-sm font-semibold text-slate-300">Export Results</h3>
                                </div>
                                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                                    {(['json', 'csv', 'latex', 'markdown'] as FormatType[]).map(format => (
                                        <button
                                            key={format}
                                            onClick={() => handleExport(format)}
                                            disabled={exporting !== null || loading}
                                            className={`flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-all ${
                                                exporting === format
                                                    ? 'bg-cyan-600 text-white cursor-wait'
                                                    : 'bg-slate-800 text-slate-300 hover:bg-slate-700 hover:text-white disabled:opacity-50 disabled:cursor-not-allowed'
                                            }`}
                                        >
                                            {exporting === format ? (
                                                <Loader2 className="w-4 h-4 animate-spin" />
                                            ) : (
                                                getFormatIcon(format)
                                            )}
                                            {format.toUpperCase()}
                                        </button>
                                    ))}
                                </div>
                                {exportUrl && (
                                    <div className="mt-3 text-xs text-emerald-400">
                                        ✓ Export complete. Download started automatically.
                                    </div>
                                )}
                            </div>

                            {/* Raw Data Dump (Debug/Trace) */}
                            {(tier === 'analytical' || tier === 'advanced') && (
                                <details className="text-xs text-slate-500 cursor-pointer">
                                    <summary className="hover:text-slate-300 transition-colors">View Raw JSON Response</summary>
                                    <pre className="mt-2 p-4 bg-black rounded overflow-auto max-h-60 border border-slate-800">
                                        {JSON.stringify(result, null, 2)}
                                    </pre>
                                </details>
                            )}
                        </div>
                    )}

                    {!result && !loading && !error && (
                        <div className="h-full flex flex-col items-center justify-center text-slate-600">
                            <Calculator className="w-16 h-16 opacity-10 mb-4" />
                            <p>Enter data and select a design to run analysis.</p>
                        </div>
                    )}
                </div>
            </div>
        </div >
    );
}
