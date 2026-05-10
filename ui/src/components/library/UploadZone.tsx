import React, { useCallback, useState } from 'react';
import { Upload, FileText, CheckCircle, AlertCircle, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { api } from '@/lib/api';
import { toast } from 'sonner';

interface UploadZoneProps {
    onUploadComplete: () => void;
}

export function UploadZone({ onUploadComplete }: UploadZoneProps) {
    const [isDragging, setIsDragging] = useState(false);
    const [isUploading, setIsUploading] = useState(false);

    const handleDragOver = (e: React.DragEvent) => {
        e.preventDefault();
        setIsDragging(true);
    };

    const handleDragLeave = (e: React.DragEvent) => {
        e.preventDefault();
        setIsDragging(false);
    };

    const handleDrop = useCallback(async (e: React.DragEvent) => {
        e.preventDefault();
        setIsDragging(false);

        const files = Array.from(e.dataTransfer.files);
        if (files.length === 0) return;

        await processFiles(files);
    }, []);

    const handleFileInput = async (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files.length > 0) {
            const files = Array.from(e.target.files);
            await processFiles(files);
        }
    };

    const processFiles = async (files: File[]) => {
        setIsUploading(true);
        let successCount = 0;
        let failCount = 0;

        for (const file of files) {
            try {
                const formData = new FormData();
                formData.append('file', file);

                await api.uploadFile(formData);
                successCount++;
            } catch (error) {
                console.error(`Failed to upload ${file.name}:`, error);
                failCount++;
            }
        }

        setIsUploading(false);

        if (successCount > 0) {
            toast.success(`Successfully uploaded ${successCount} file(s)`);
            onUploadComplete();
        }
        if (failCount > 0) {
            toast.error(`Failed to upload ${failCount} file(s)`);
        }
    };

    return (
        <div
            className={cn(
                "relative border-2 border-dashed rounded-xl p-8 transition-all duration-200 ease-in-out text-center cursor-pointer group",
                isDragging
                    ? "border-teal-500 bg-teal-500/10 scale-[1.01]"
                    : "border-slate-700 hover:border-slate-500 bg-slate-900/50 hover:bg-slate-900",
                isUploading && "opacity-50 pointer-events-none"
            )}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={() => document.getElementById('file-upload')?.click()}
        >
            <input
                type="file"
                id="file-upload"
                className="hidden"
                multiple
                onChange={handleFileInput}
                accept=".pdf,.docx,.txt,.md,.ipynb"
            />

            <div className="flex flex-col items-center gap-3">
                <div className={cn(
                    "p-4 rounded-full transition-colors",
                    isDragging ? "bg-teal-500/20 text-teal-400" : "bg-slate-800 text-slate-400 group-hover:text-slate-300"
                )}>
                    {isUploading ? (
                        <Loader2 className="w-8 h-8 animate-spin" />
                    ) : (
                        <Upload className="w-8 h-8" />
                    )}
                </div>

                <div className="space-y-1">
                    <h3 className="font-medium text-slate-200">
                        {isUploading ? "Uploading..." : "Drop files here or click to browse"}
                    </h3>
                    <p className="text-sm text-slate-500">
                        Supports PDF, DOCX, TXT, MD, IPYNB
                    </p>
                </div>
            </div>
        </div>
    );
}
