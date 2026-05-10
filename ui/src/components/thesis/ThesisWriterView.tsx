import React, { useState, useEffect } from 'react';
import { api } from '@/lib/api';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { AlertCircle, CheckCircle, Lock, PenTool, FileText, ChevronRight, ShieldCheck, AlertTriangle, Search } from 'lucide-react';
import ReactMarkdown from 'react-markdown';

interface ChapterTemplate {
    id: string;
    title: string;
    sections: { title: string; description: string; required_proofs: string[] }[];
    proof_type_required: string;
}

export const ThesisWriterView: React.FC = () => {
    const [structure, setStructure] = useState<Record<string, ChapterTemplate> | null>(null);
    const [validations, setValidations] = useState<Record<string, any>>({});
    const [selectedChapter, setSelectedChapter] = useState<string | null>(null);
    const [generatedContent, setGeneratedContent] = useState<Record<string, string>>({});
    const [loading, setLoading] = useState(false);
    const [isGenerating, setIsGenerating] = useState(false);
    const [reviewResults, setReviewResults] = useState<Record<string, any>>({});
    const [isReviewing, setIsReviewing] = useState(false);

    useEffect(() => {
        loadStructure();
    }, []);

    const loadStructure = async () => {
        setLoading(true);
        try {
            const struct = await api.thesis.getStructure();
            setStructure(struct);

            // Validate all chapters
            const valResults: Record<string, any> = {};
            for (const key of Object.keys(struct)) {
                valResults[key] = await api.thesis.validateChapter(key);
            }
            setValidations(valResults);

            // Select first chapter by default
            if (Object.keys(struct).length > 0) {
                setSelectedChapter(Object.keys(struct)[0]);
            }
        } catch (e) {
            console.error("Failed to load thesis structure", e);
        } finally {
            setLoading(false);
        }
    };

    const handleGenerate = async (chapterId: string) => {
        if (!structure) return;
        setIsGenerating(true);
        try {
            const result = await api.thesis.generateChapter(chapterId, "Automated Thesis Generation"); // Topic should be dynamic
            if (result.status === 'success' && result.content) {
                setGeneratedContent(prev => ({ ...prev, [chapterId]: result.content! }));
            } else {
                alert(`Generation Blocked: ${result.reason}`);
            }
        } catch (e) {
            console.error("Generation failed", e);
        } finally {
            setIsGenerating(false);
        }
    };

    const handleReviewCitations = async (chapterId: string) => {
        const content = generatedContent[chapterId];
        if (!content) return;
        setIsReviewing(true);
        try {
            const results = await api.literature.verifyCitations(content);
            setReviewResults(prev => ({ ...prev, [chapterId]: results }));
        } catch (e) {
            console.error("Citations review failed", e);
        } finally {
            setIsReviewing(false);
        }
    };

    if (loading) return <div className="p-8 text-center text-slate-400">Loading PhD Protocol...</div>;

    const currentTemplate = selectedChapter && structure ? structure[selectedChapter] : null;
    const currentValidation = selectedChapter ? validations[selectedChapter] : null;

    return (
        <div className="h-full flex flex-col bg-slate-950 text-slate-200">
            <header className="px-6 py-4 border-b border-slate-800 flex justify-between items-center bg-slate-900/50">
                <div>
                    <h1 className="text-2xl font-bold font-serif text-white flex items-center gap-3">
                        <span className="p-2 bg-blue-900/30 rounded-lg text-blue-400"><FileText className="w-6 h-6" /></span>
                        PhD Thesis Compiler
                    </h1>
                    <p className="text-sm text-slate-400 ml-14">Strict compliance mode active via BioDockify AI Validator.</p>
                </div>
                <div className="flex gap-2">
                    <Button variant="outline" size="sm" onClick={loadStructure}>Re-Validate All</Button>
                </div>
            </header>

            <div className="flex-1 flex overflow-hidden">
                {/* Sidebar: Chapters */}
                <div className="w-80 border-r border-slate-800 bg-slate-900/30 overflow-y-auto">
                    <div className="p-4 space-y-2">
                        {structure && Object.entries(structure).map(([key, chapter]) => {
                            const isValid = validations[key]?.status === 'valid';
                            return (
                                <button
                                    key={key}
                                    onClick={() => setSelectedChapter(key)}
                                    className={`w-full text-left p-3 rounded-lg border transition-all flex items-center justify-between group
                                        ${selectedChapter === key
                                            ? 'bg-blue-600/10 border-blue-500/50 text-white'
                                            : 'bg-slate-900 border-slate-800 text-slate-400 hover:bg-slate-800'}`}
                                >
                                    <div className="flex flex-col">
                                        <span className="text-xs font-mono uppercase opacity-50">{key.replace('chapter_', 'Chapter ')}</span>
                                        <span className="font-semibold text-sm truncate">{chapter.title}</span>
                                    </div>
                                    {isValid ? (
                                        <CheckCircle className="w-4 h-4 text-green-500" />
                                    ) : (
                                        <Lock className="w-4 h-4 text-red-500/50" />
                                    )}
                                </button>
                            );
                        })}
                    </div>
                </div>

                {/* Main Content */}
                <div className="flex-1 flex flex-col overflow-hidden">
                    {currentTemplate ? (
                        <div className="flex-1 flex flex-col p-6 overflow-y-auto">
                            {/* Validation Status Banner */}
                            <div className={`mb-6 p-4 rounded-lg border flex items-start gap-3
                                ${currentValidation?.status === 'valid'
                                    ? 'bg-green-900/10 border-green-500/30 text-green-200'
                                    : 'bg-red-900/10 border-red-500/30 text-red-200'}`}
                            >
                                {currentValidation?.status === 'valid' ? (
                                    <CheckCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
                                ) : (
                                    <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
                                )}
                                <div>
                                    <h3 className="font-bold">
                                        {currentValidation?.status === 'valid' ? "Ready for Drafting" : "Missing Proofs"}
                                    </h3>
                                    <p className="text-sm opacity-80 mt-1">
                                        {currentValidation?.status === 'valid'
                                            ? `All required artifacts are present (${currentTemplate.proof_type_required}).`
                                            : `Cannot draft this chapter. ${currentValidation?.message || 'Required artifacts not found.'}`}
                                    </p>
                                    {currentValidation?.missing_items && (
                                        <ul className="mt-2 list-disc list-inside text-sm font-mono bg-black/20 p-2 rounded">
                                            {currentValidation.missing_items.map((item: string) => (
                                                <li key={item} className="text-red-300">{item}</li>
                                            ))}
                                        </ul>
                                    )}
                                </div>
                                {currentValidation?.status === 'valid' && (
                                    <Button
                                        className="ml-auto bg-green-600 hover:bg-green-500 text-white"
                                        onClick={() => handleGenerate(currentTemplate.id)}
                                        disabled={isGenerating}
                                    >
                                        {isGenerating ? "Drafting..." : "Generate Draft"}
                                        <PenTool className="w-4 h-4 ml-2" />
                                    </Button>
                                )}
                            </div>

                            {/* Generated Content or Plan */}
                            <div className="flex-1 bg-white dark:bg-slate-900 rounded-lg border border-slate-800 shadow-xl overflow-hidden flex flex-col">
                                <Tabs defaultValue={generatedContent[currentTemplate.id] ? "draft" : "structure"} className="flex-1 flex flex-col">
                                    <div className="border-b border-slate-800 px-4 py-2 bg-slate-950">
                                        <TabsList className="bg-slate-900">
                                            <TabsTrigger value="structure">Structure Plan</TabsTrigger>
                                            <TabsTrigger value="draft">Review Draft</TabsTrigger>
                                        </TabsList>
                                    </div>

                                    <TabsContent value="structure" className="flex-1 p-6 overflow-y-auto">
                                        <div className="max-w-3xl mx-auto space-y-6">
                                            <h2 className="text-2xl font-serif text-white border-b pb-2 mb-6">Chapter Plan: {currentTemplate.title}</h2>
                                            {currentTemplate.sections.map((section, idx) => (
                                                <div key={idx} className="bg-slate-800/50 p-4 rounded-lg border border-slate-700">
                                                    <h3 className="text-lg font-bold text-teal-400 mb-1">{idx + 1}. {section.title}</h3>
                                                    <p className="text-slate-400 text-sm mb-3 italic">{section.description}</p>
                                                    <div className="flex gap-2">
                                                        {section.required_proofs.map(proof => (
                                                            <Badge key={proof} variant="secondary" className="bg-slate-700 text-xs">
                                                                Requires: {proof}
                                                            </Badge>
                                                        ))}
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                    </TabsContent>

                                    <TabsContent value="draft" className="flex-1 p-0 overflow-hidden relative">
                                        {generatedContent[currentTemplate.id] ? (
                                            <ScrollArea className="h-full p-8 text-slate-800 dark:text-slate-200">
                                                <article className="prose dark:prose-invert max-w-none">
                                                    <ReactMarkdown>{generatedContent[currentTemplate.id]}</ReactMarkdown>
                                                </article>

                                                {/* Citation Verification UI */}
                                                <div className="mt-12 pt-8 border-t border-slate-200 dark:border-slate-800">
                                                    <div className="flex items-center justify-between mb-4">
                                                        <div className="flex items-center gap-2">
                                                            <ShieldCheck className="w-5 h-5 text-blue-500" />
                                                            <h3 className="text-lg font-bold">Reviewer Agent Analysis</h3>
                                                        </div>
                                                        <Button
                                                            variant="outline"
                                                            size="sm"
                                                            onClick={() => handleReviewCitations(currentTemplate.id)}
                                                            disabled={isReviewing}
                                                            className="border-blue-500/30 text-blue-400 hover:bg-blue-500/10"
                                                        >
                                                            {isReviewing ? "Verifying Citations..." : "Verify Integrity"}
                                                            {isReviewing ? <Search className="w-4 h-4 ml-2 animate-pulse" /> : <CheckCircle className="w-4 h-4 ml-2" />}
                                                        </Button>
                                                    </div>

                                                    {reviewResults[currentTemplate.id] ? (
                                                        <div className="space-y-4">
                                                            <div className="grid grid-cols-4 gap-4">
                                                                <div className="bg-slate-50 dark:bg-slate-900/50 p-3 rounded border border-slate-200 dark:border-slate-800">
                                                                    <div className="text-xs text-slate-500 mb-1">Integrity Score</div>
                                                                    <div className={`text-xl font-bold ${reviewResults[currentTemplate.id].integrity_score > 80 ? 'text-green-500' : 'text-orange-500'}`}>
                                                                        {reviewResults[currentTemplate.id].integrity_score}%
                                                                    </div>
                                                                </div>
                                                                <div className="bg-slate-50 dark:bg-slate-900/50 p-3 rounded border border-slate-200 dark:border-slate-800">
                                                                    <div className="text-xs text-slate-500 mb-1">Valid Citations</div>
                                                                    <div className="text-xl font-bold text-green-500">{reviewResults[currentTemplate.id].valid_count}</div>
                                                                </div>
                                                                <div className="bg-slate-50 dark:bg-slate-900/50 p-3 rounded border border-slate-200 dark:border-slate-800">
                                                                    <div className="text-xs text-slate-500 mb-1">Suspicious</div>
                                                                    <div className="text-xl font-bold text-red-500">{reviewResults[currentTemplate.id].suspicious_count}</div>
                                                                </div>
                                                                <div className="bg-slate-50 dark:bg-slate-900/50 p-3 rounded border border-slate-200 dark:border-slate-800">
                                                                    <div className="text-xs text-slate-500 mb-1">Unverified</div>
                                                                    <div className="text-xl font-bold text-slate-400">{reviewResults[currentTemplate.id].unverified_count}</div>
                                                                </div>
                                                            </div>

                                                            {reviewResults[currentTemplate.id].suspicious_count > 0 && (
                                                                <div className="bg-red-500/10 border border-red-500/30 p-3 rounded text-red-300 text-sm flex gap-2">
                                                                    <AlertTriangle className="w-4 h-4 flex-shrink-0" />
                                                                    <span>BioDockify detected <strong>{reviewResults[currentTemplate.id].suspicious_count} potential hallucinations</strong>. Review flagged citations carefully.</span>
                                                                </div>
                                                            )}

                                                            <div className="space-y-2">
                                                                {reviewResults[currentTemplate.id].details.map((detail: any, idx: number) => (
                                                                    <div key={idx} className="flex items-center justify-between p-2 rounded bg-slate-50 dark:bg-slate-900/30 border border-slate-100 dark:border-slate-800 text-xs">
                                                                        <div className="flex items-center gap-2">
                                                                            <Badge variant={detail.status === 'VALID' ? 'outline' : 'destructive'} className="text-[10px] scale-90">
                                                                                {detail.status}
                                                                            </Badge>
                                                                            <code className="text-slate-400">{detail.citation}</code>
                                                                        </div>
                                                                        {detail.status === 'VALID' && (
                                                                            <span className="text-slate-500 italic truncate ml-4 max-w-xs">{detail.match}</span>
                                                                        )}
                                                                        {detail.status === 'SUSPICIOUS' && (
                                                                            <span className="text-red-400/80 italic">{detail.reason}</span>
                                                                        )}
                                                                    </div>
                                                                ))}
                                                            </div>
                                                        </div>
                                                    ) : (
                                                        <p className="text-sm text-slate-500 italic">No verification performed on this draft yet. Click &quot;Verify Integrity&quot; to audit citations.</p>
                                                    )}
                                                </div>
                                            </ScrollArea>
                                        ) : (
                                            <div className="h-full flex flex-col items-center justify-center text-slate-500">
                                                <FileText className="w-16 h-16 opacity-20 mb-4" />
                                                <p>No draft generated yet.</p>
                                                <Button
                                                    variant="link"
                                                    className="text-teal-400"
                                                    onClick={() => (document.querySelector('[value="structure"]') as HTMLElement)?.click()}
                                                >
                                                    View Structure Plan
                                                </Button>
                                            </div>
                                        )}
                                    </TabsContent>
                                </Tabs>
                            </div>
                        </div>
                    ) : (
                        <div className="flex-1 flex items-center justify-center text-slate-500">
                            Select a chapter to begin.
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};
