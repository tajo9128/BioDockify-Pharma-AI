import React from 'react';
import { CheckCircle, Search, Filter, BookOpen, FileText } from 'lucide-react';

interface PipelineStepperProps {
    currentStep: number; // 0 to 4 (0=Idle, 1=Discovery, 2=Screening, 3=Retrieval, 4=Synthesis)
    logs?: string[];
}

const steps = [
    { id: 1, label: 'Discovery', icon: Search, description: 'Aggregating sources (PubMed, ArXiv)' },
    { id: 2, label: 'Screening', icon: Filter, description: 'AI Relevance Filtering' },
    { id: 3, label: 'Retrieval', icon: BookOpen, description: 'Deep Headless Reading' },
    { id: 4, label: 'Synthesis', icon: FileText, description: 'RAG Writing & Compliance' },
];

export const PipelineStepper: React.FC<PipelineStepperProps> = ({ currentStep, logs = [] }) => {
    return (
        <div className="space-y-6">
            <div className="relative">
                {/* Progress Bar Background */}
                <div className="absolute top-5 left-0 w-full h-1 bg-gray-200 dark:bg-gray-800 rounded-full" />

                {/* Progress Bar Fill */}
                <div
                    className="absolute top-5 left-0 h-1 bg-blue-600 rounded-full transition-all duration-500 ease-in-out"
                    style={{ width: `${Math.max(0, (currentStep - 1) / (steps.length - 1)) * 100}%` }}
                />

                <div className="relative flex justify-between">
                    {steps.map((step, index) => {
                        const isCompleted = currentStep > step.id;
                        const isActive = currentStep === step.id;
                        const Icon = isCompleted ? CheckCircle : step.icon;

                        return (
                            <div key={step.id} className="flex flex-col items-center group">
                                <div
                                    className={`w-10 h-10 rounded-full flex items-center justify-center border-2 z-10 transition-colors
                    ${isCompleted ? 'bg-blue-600 border-blue-600 text-white' :
                                            isActive ? 'bg-white dark:bg-gray-900 border-blue-600 text-blue-600 animate-pulse ring-4 ring-blue-100 dark:ring-blue-900/30' :
                                                'bg-white dark:bg-gray-900 border-gray-300 dark:border-gray-700 text-gray-400'}`}
                                >
                                    <Icon size={18} />
                                </div>
                                <div className="mt-3 text-center">
                                    <p className={`text-sm font-semibold transition-colors
                    ${isActive || isCompleted ? 'text-gray-900 dark:text-gray-100' : 'text-gray-500'}`}>
                                        {step.label}
                                    </p>
                                    <p className="text-xs text-gray-500 max-w-[100px] hidden md:block mt-1">
                                        {step.description}
                                    </p>
                                </div>
                            </div>
                        );
                    })}
                </div>
            </div>

            {/* Live Logs Console */}
            <div className="mt-8 bg-gray-900 rounded-lg p-4 font-mono text-xs text-green-400 h-48 overflow-y-auto shadow-inner border border-gray-800">
                {logs.length === 0 ? (
                    <span className="text-gray-600 italic">Waiting to start research protocol...</span>
                ) : (
                    logs.map((log, i) => (
                        <div key={i} className="mb-1 border-l-2 border-transparent hover:border-green-600 pl-2">
                            <span className="text-gray-500 mr-2">[{new Date().toLocaleTimeString()}]</span>
                            {log}
                        </div>
                    ))
                )}
                {currentStep > 0 && currentStep < 5 && (
                    <div className="animate-pulse mt-2">_</div>
                )}
            </div>
        </div>
    );
};
