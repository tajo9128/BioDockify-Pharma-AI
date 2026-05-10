import React from 'react';
import ReactMarkdown from 'react-markdown';
import { Download, Copy, CheckCircle, AlertTriangle, FileText } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';

interface ComplianceReport {
    status: string; // "PASSED" | "FLAGGED" | "BLOCKED"
    overall_similarity: number;
    risk_level: string;
    details?: string;
}

interface ReviewViewerProps {
    markdownContent: string;
    complianceReport?: ComplianceReport;
    topic: string;
}

export const ReviewViewer: React.FC<ReviewViewerProps> = ({ markdownContent, complianceReport, topic }) => {

    const handleCopy = () => {
        navigator.clipboard.writeText(markdownContent);
    };

    const handleDownload = () => {
        const blob = new Blob([markdownContent], { type: 'text/markdown' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `review_${topic.replace(/\s+/g, '_').toLowerCase()}.md`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    };

    return (
        <Card className="w-full h-full border-t-4 border-t-blue-600 shadow-lg animate-in fade-in duration-500">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
                <div className="space-y-1">
                    <CardTitle className="text-2xl font-serif">Systematic Review</CardTitle>
                    <CardDescription>{topic}</CardDescription>
                </div>
                <div className="flex items-center space-x-2">
                    {complianceReport && (
                        <Badge variant={complianceReport.status === "PASSED" ? "default" : "destructive"} className="mr-2">
                            {complianceReport.status === "PASSED" ? <CheckCircle className="w-3 h-3 mr-1" /> : <AlertTriangle className="w-3 h-3 mr-1" />}
                            Plagiarism Check: {complianceReport.status} ({complianceReport.overall_similarity}%)
                        </Badge>
                    )}
                    <Button variant="outline" size="sm" onClick={handleCopy}>
                        <Copy className="w-4 h-4 mr-2" />
                        Copy
                    </Button>
                    <Button variant="default" size="sm" onClick={handleDownload}>
                        <Download className="w-4 h-4 mr-2" />
                        Export MD
                    </Button>
                </div>
            </CardHeader>
            <CardContent>
                <ScrollArea className="h-[600px] w-full rounded-md border p-4 bg-white dark:bg-gray-950">
                    <article className="prose dark:prose-invert max-w-none prose-headings:font-serif prose-h1:text-3xl prose-h2:text-2xl prose-a:text-blue-600">
                        {markdownContent ? (
                            <ReactMarkdown>{markdownContent}</ReactMarkdown>
                        ) : (
                            <div className="flex flex-col items-center justify-center h-full text-gray-400">
                                <FileText className="w-12 h-12 mb-4 opacity-50" />
                                <p>Report content will appear here...</p>
                            </div>
                        )}
                    </article>
                </ScrollArea>
            </CardContent>
        </Card>
    );
};
