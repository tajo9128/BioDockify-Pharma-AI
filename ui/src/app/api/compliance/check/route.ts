
import { NextRequest, NextResponse } from 'next/server';

interface ComplianceRequest {
    text: string;
}

export async function POST(request: NextRequest) {
    try {
        const { text } = await request.json() as ComplianceRequest;

        if (!text) {
            return NextResponse.json({
                compliant: false,
                scores: { academic_tone: 0, evidence_density: 0, variability: 0 },
                issues: []
            });
        }

        // --- 1. Style Check ---
        const styleRules = [
            { pattern: /\b(In conclusion,)\b/gi, replacement: "Collectively, these findings suggest" },
            { pattern: /\b(It is important to note that)\b/gi, replacement: "Notably," },
            { pattern: /\b(This study proves)\b/gi, replacement: "These results demonstrate, within experimental limits," },
            { pattern: /\b(undoubtedly)\b/gi, replacement: "strongly" },
            { pattern: /\b(game-changer)\b/gi, replacement: "significant advancement" },
            { pattern: /\b(revolutionize)\b/gi, replacement: "transform" },
            { pattern: /\b(delve into)\b/gi, replacement: "investigate" },
            { pattern: /\b(comprehensive overview)\b/gi, replacement: "systematic review" }
        ];

        const issues = [];
        for (const rule of styleRules) {
            let match;
            // Reset lastIndex for global regex if needed, or just match
            // primitive regex use here
            const regex = new RegExp(rule.pattern);
            if (regex.test(text)) {
                issues.push({
                    type: 'Tone',
                    found: text.match(rule.pattern)?.[0] || 'Term',
                    suggestion: rule.replacement
                });
            }
        }

        // --- 2. Evidence Check ---
        // Matches (Author, 2024) or [1] or [1-3]
        const citationPattern = /\(.*?, \d{4}\)|\[[\d,\- ]+\]/g;
        const sentences = text.split(/[.!?]+/).filter(s => s.trim().length > 0);
        let citedSentences = 0;

        sentences.forEach(sent => {
            if (citationPattern.test(sent)) citedSentences++;
        });

        const evidenceScore = sentences.length > 0 ? (citedSentences / sentences.length) : 0;

        // --- 3. Variability Check ---
        const lengths = sentences.map(s => s.split(/\s+/).length);
        let variabilityScore = 0.5; // default
        if (lengths.length > 1) {
            const mean = lengths.reduce((a, b) => a + b, 0) / lengths.length;
            const variance = lengths.reduce((a, b) => a + Math.pow(b - mean, 2), 0) / lengths.length;
            const stdev = Math.sqrt(variance);
            const cv = mean > 0 ? stdev / mean : 0;
            variabilityScore = Math.min(cv * 2.5, 1.0);
        }

        return NextResponse.json({
            compliant: true, // Just a pass-through for analysis, frontend decides strictness
            scores: {
                academic_tone: Math.max(0, 1.0 - (issues.length * 0.1)),
                evidence_density: parseFloat(evidenceScore.toFixed(2)),
                variability: parseFloat(variabilityScore.toFixed(2))
            },
            issues,
            metrics: {
                sentence_count: sentences.length,
                citation_count: (text.match(citationPattern) || []).length
            }
        });

    } catch (error: any) {
        return NextResponse.json({ error: error.message }, { status: 500 });
    }
}
