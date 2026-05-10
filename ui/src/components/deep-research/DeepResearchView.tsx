import React, { useState } from 'react';
import { Search, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent } from '@/components/ui/card';
import { api } from '@/lib/api';
import { PipelineStepper } from './PipelineStepper';
import { ReviewViewer } from './ReviewViewer';

export const DeepResearchView: React.FC = () => {
    const [topic, setTopic] = useState('');
    const [isRunning, setIsRunning] = useState(false);
    const [step, setStep] = useState(0); // 0=Idle
    const [logs, setLogs] = useState<string[]>([]);
    const [result, setResult] = useState<any>(null);

    // License Guard
    const isLicenseActive = typeof window !== 'undefined' && localStorage.getItem('biodockify_license_active') === 'true';

    if (!isLicenseActive) {
        return (
            <div className="h-full flex items-center justify-center p-12">
                <div className="text-center space-y-4 bg-slate-900/50 p-8 rounded-2xl border border-slate-800 backdrop-blur-sm max-w-lg">
                    <div className="w-16 h-16 bg-slate-800/50 rounded-full flex items-center justify-center mx-auto mb-4 border border-slate-700">
                        <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-amber-500"><rect width="18" height="11" x="3" y="11" rx="2" ry="2" /><path d="M7 11V7a5 5 0 0 1 10 0v4" /></svg>
                    </div>
                    <h2 className="text-2xl font-bold text-white">Deep Research Locked</h2>
                    <p className="text-slate-400">
                        Autonomous research agents require verified credentials to access external academic databases.
                    </p>
                </div>
            </div>
        );
    }

    const handleRun = async () => {
        if (!topic.trim()) return;

        setIsRunning(true);
        setStep(1);
        setLogs(prev => [...prev, `Starting deep review for: "${topic}"...`]);
        setResult(null);

        // Simulate progress purely for UX until we have streaming
        // The real logs come back at the end
        const progressTimer = setInterval(() => {
            setStep(prev => {
                if (prev < 4) return prev + 1;
                return prev;
            });
            setLogs(prev => [...prev, "Processing phase..."]);
        }, 5000); // Artificial 5s steps just for visuals if it takes long

        try {
            // Call the autonomous agent
            const response = await api.agentExecute('deep_review', { topic });

            clearInterval(progressTimer);
            setStep(5); // Complete

            if (response.status === 'success' && response.results) {
                setResult(response.results);
                // Overwrite logs with real pipeline logs
                if (response.results.pipeline_log) {
                    setLogs(response.results.pipeline_log);
                }
            } else if (response.status === 'blocked') {
                setStep(4); // Stopped at compliance
                setResult(response.results || response); // Contains compliance report
                // If blocked, log might be at top level or in results
                if (response.results?.pipeline_log) setLogs(response.results.pipeline_log);
            } else {
                setLogs(prev => [...prev, `Error: ${response.error || 'Unknown failure'}`]);
            }
        } catch (error) {
            clearInterval(progressTimer);
            setLogs(prev => [...prev, `System Error: ${error}`]);
        } finally {
            setIsRunning(false);
        }
    };

    return (
        <div className="container mx-auto p-6 max-w-6xl space-y-8 animate-in fade-in">
            <div className="text-center space-y-2">
                <h1 className="text-3xl font-bold tracking-tight">Autonomous Deep Research</h1>
                <p className="text-muted-foreground">
                    BioDockify AI navigates the web, reads papers, screens, and synthesizes reports.
                </p>
            </div>

            {/* Input Section */}
            <Card className="border-2 border-blue-50 dark:border-blue-900/20 shadow-sm">
                <CardContent className="pt-6">
                    <div className="flex gap-4">
                        <div className="relative flex-1">
                            <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                            <Input
                                placeholder="Enter research topic (e.g. 'CRISPR off-target effects in T-cells')"
                                className="pl-10 h-10 text-lg"
                                value={topic}
                                onChange={(e) => setTopic(e.target.value)}
                                onKeyDown={(e) => e.key === 'Enter' && handleRun()}
                                disabled={isRunning}
                            />
                        </div>
                        <Button
                            size="lg"
                            onClick={handleRun}
                            disabled={isRunning || !topic}
                            className="w-32"
                        >
                            {isRunning ? <Loader2 className="animate-spin mr-2" /> : 'Run'}
                        </Button>
                    </div>
                </CardContent>
            </Card>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                {/* Left Column: Progress & Logs */}
                <div className="lg:col-span-1 space-y-6">
                    <Card>
                        <CardContent className="pt-6">
                            <PipelineStepper currentStep={step} logs={logs} />
                        </CardContent>
                    </Card>

                    {/* Stats Card (if result available) */}
                    {result && (
                        <Card>
                            <CardContent className="pt-6 space-y-2">
                                <h3 className="font-semibold text-sm text-gray-500 uppercase">Mission Stats</h3>
                                <div className="grid grid-cols-2 gap-4">
                                    <div className="bg-blue-50 dark:bg-blue-900/20 p-3 rounded">
                                        <p className="text-2xl font-bold text-blue-600">{result.papers_found || 0}</p>
                                        <p className="text-xs text-gray-500">Found</p>
                                    </div>
                                    <div className="bg-green-50 dark:bg-green-900/20 p-3 rounded">
                                        <p className="text-2xl font-bold text-green-600">{result.papers_reviewed || 0}</p>
                                        <p className="text-xs text-gray-500">Read</p>
                                    </div>
                                </div>
                            </CardContent>
                        </Card>
                    )}
                </div>

                {/* Right Column: Result Viewer */}
                <div className="lg:col-span-2">
                    <ReviewViewer
                        markdownContent={result?.report_content || ''}
                        topic={topic}
                        complianceReport={result?.compliance_report || (result?.status === 'blocked' ? result.compliance_report : undefined)}
                    />
                </div>
            </div>
        </div>
    );
};
