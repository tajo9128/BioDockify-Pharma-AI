
import React, { useState, useRef } from 'react';
import { Upload, FileText, CheckCircle, Plus } from 'lucide-react';

export interface ExternalAIInsight {
    id: string;
    tool: string; // e.g., "NotebookLM", "ChatGPT"
    link: string;
    summary: string; // The content
    validated_by_user: boolean;
    timestamp: string;
    sourceType: 'paste' | 'file';
    fileName?: string;
}

interface ExternalInsightImporterProps {
    onImport: (insight: ExternalAIInsight) => void;
}

export default function ExternalInsightImporter({ onImport }: ExternalInsightImporterProps) {
    const [activeTab, setActiveTab] = useState<'paste' | 'file'>('paste');
    const [tool, setTool] = useState('NotebookLM');
    const [url, setUrl] = useState('');
    const [content, setContent] = useState('');
    const [file, setFile] = useState<File | null>(null);
    const [isValidated, setIsValidated] = useState(true); // Default to true as user is manually importing

    const fileInputRef = useRef<HTMLInputElement>(null);

    const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files[0]) {
            const selectedFile = e.target.files[0];
            setFile(selectedFile);

            // Basic text reading for .txt, generic handling for others
            if (selectedFile.type === "text/plain") {
                const text = await selectedFile.text();
                setContent(text);
            } else {
                setContent(`[Binary File Attached: ${selectedFile.name}] - Content parsing requires backend.`);
            }
        }
    };

    const handleSubmit = () => {
        if (!content && !file) return;

        const insight: ExternalAIInsight = {
            id: `ext-${Date.now()}`,
            tool,
            link: url,
            summary: content,
            validated_by_user: isValidated,
            timestamp: new Date().toISOString(),
            sourceType: activeTab,
            fileName: file?.name
        };

        onImport(insight);

        // Reset form
        setContent('');
        setUrl('');
        setFile(null);
        if (fileInputRef.current) fileInputRef.current.value = '';
    };

    return (
        <div className="bg-slate-900 border border-slate-700 rounded-xl overflow-hidden shadow-sm">
            <div className="bg-slate-950 p-3 border-b border-slate-700 flex items-center justify-between">
                <h3 className="text-sm font-bold text-slate-300 flex items-center">
                    <Upload className="w-4 h-4 mr-2 text-teal-500" />
                    Import External Insight
                </h3>
                <div className="flex space-x-1 bg-slate-900 rounded p-1 border border-slate-800">
                    <button
                        onClick={() => setActiveTab('paste')}
                        className={`px-3 py-1 text-xs font-medium rounded transition-colors ${activeTab === 'paste' ? 'bg-teal-600 text-white shadow' : 'text-slate-400 hover:text-slate-200'}`}
                    >
                        Link + Paste
                    </button>
                    <button
                        onClick={() => setActiveTab('file')}
                        className={`px-3 py-1 text-xs font-medium rounded transition-colors ${activeTab === 'file' ? 'bg-teal-600 text-white shadow' : 'text-slate-400 hover:text-slate-200'}`}
                    >
                        File Upload
                    </button>
                </div>
            </div>

            <div className="p-4 space-y-4">
                {/* Common Fields */}
                <div className="grid grid-cols-2 gap-4">
                    <div>
                        <label className="block text-xs font-bold text-slate-500 mb-1 uppercase">Source Tool</label>
                        <select
                            value={tool}
                            onChange={(e) => setTool(e.target.value)}
                            className="w-full bg-slate-800 border-slate-700 rounded text-sm text-slate-200 p-2 focus:ring-1 focus:ring-teal-500 outline-none"
                        >
                            <option value="NotebookLM">Google NotebookLM</option>
                            <option value="ChatGPT">ChatGPT / Claude</option>
                            <option value="Perplexity">Perplexity AI</option>
                            <option value="Other">Other Source</option>
                        </select>
                    </div>
                    <div>
                        <label className="block text-xs font-bold text-slate-500 mb-1 uppercase">Source Link (URL)</label>
                        <input
                            type="text"
                            value={url}
                            onChange={(e) => setUrl(e.target.value)}
                            placeholder="https://notebooklm.google.com/..."
                            className="w-full bg-slate-800 border-slate-700 rounded text-sm text-slate-200 p-2 focus:ring-1 focus:ring-teal-500 outline-none"
                        />
                    </div>
                </div>

                {/* Tab Content */}
                {activeTab === 'paste' ? (
                    <div>
                        <label className="block text-xs font-bold text-slate-500 mb-1 uppercase">Paste Content / Summary</label>
                        <textarea
                            value={content}
                            onChange={(e) => setContent(e.target.value)}
                            placeholder="Paste the key insights, summary, or output from NotebookLM here..."
                            className="w-full h-32 bg-slate-800 border-slate-700 rounded text-sm text-slate-200 p-3 focus:ring-1 focus:ring-teal-500 outline-none resize-none font-mono"
                        />
                    </div>
                ) : (
                    <div>
                        <label className="block text-xs font-bold text-slate-500 mb-1 uppercase">File Attachment</label>
                        <div
                            onClick={() => fileInputRef.current?.click()}
                            className="border-2 border-dashed border-slate-700 hover:border-teal-500/50 hover:bg-slate-800/50 rounded-xl p-8 flex flex-col items-center justify-center cursor-pointer transition-all group"
                        >
                            <input
                                type="file"
                                ref={fileInputRef}
                                onChange={handleFileChange}
                                className="hidden"
                                accept=".txt,.md,.json,.csv,.docx,.pdf"
                            />
                            <FileText className="w-8 h-8 text-slate-600 group-hover:text-teal-500 mb-2 transition-colors" />
                            <p className="text-sm text-slate-400 group-hover:text-slate-200 font-medium">
                                {file ? file.name : "Click to upload .docx, .pdf, .txt"}
                            </p>
                            <p className="text-xs text-slate-600 mt-1">
                                {file ? `${(file.size / 1024).toFixed(1)} KB` : "Supports drag & drop (simulated)"}
                            </p>
                        </div>
                        {file && (
                            <div className="mt-2 text-xs text-slate-500">
                                <span className="font-bold">Preview:</span> {content.substring(0, 100)}...
                            </div>
                        )}
                    </div>
                )}

                {/* Validation Checkbox */}
                <div className="flex items-center space-x-2 bg-slate-800/50 p-2 rounded border border-slate-800">
                    <div
                        onClick={() => setIsValidated(!isValidated)}
                        className={`w-4 h-4 rounded border flex items-center justify-center cursor-pointer transition-colors ${isValidated ? 'bg-green-500 border-green-600' : 'border-slate-600'}`}
                    >
                        {isValidated && <CheckCircle className="w-3 h-3 text-white" />}
                    </div>
                    <span className="text-xs text-slate-400 select-none cursor-pointer" onClick={() => setIsValidated(!isValidated)}>
                        I have verified this content aligns with original sources (Human Verification)
                    </span>
                </div>

                {/* Action Button */}
                <button
                    onClick={handleSubmit}
                    disabled={!content && !file}
                    className="w-full bg-teal-600 hover:bg-teal-500 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-bold py-3 rounded-lg flex items-center justify-center space-x-2 transition-all shadow-lg shadow-teal-900/20"
                >
                    <Plus className="w-4 h-4" />
                    <span>Add External Evidence</span>
                </button>
            </div>
        </div>
    );
}
