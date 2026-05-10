
import { NextRequest, NextResponse } from 'next/server';
import { ProviderSelector } from '@/lib/llm/provider-selector';

// Initialize provider selector
// Note: This needs to differ if running on Edge vs Node. Next.js API routes default to Node unless specified.
const providerSelector = new ProviderSelector();

// Mock database or import real one if available. 
// For now we simulate DB or use a simple in-memory store if needed, 
// but ideally we should connect to the Prisma DB defined in schema.
// import { db } from '@/lib/db'; 

export async function POST(request: NextRequest) {
    try {
        const body = await request.json();
        let { taskId, topic, mode } = body;

        if (!taskId) {
            taskId = crypto.randomUUID();
        }

        if (!topic) {
            return NextResponse.json({ error: 'Topic is required' }, { status: 400 });
        }

        // 1. Select Provider
        const provider = await providerSelector.getBestProvider();
        console.log(`[API] Using provider: ${provider.name}`);

        // 2. Build Prompt (Simplified for MVP)
        const prompt = `Research Topic: ${topic}\nMode: ${mode}\n\nPlease provide a comprehensive analysis.`;

        // 3. Call LLM
        // This is a blocking call for simplicity. In prod, use a queue or streaming.
        const response = await provider.complete(prompt);

        // 4. Return result
        return NextResponse.json({
            taskId,
            status: 'completed',
            result: response,
            provider: provider.name
        });

    } catch (error: any) {
        console.error('[API] Research failed:', error);
        return NextResponse.json({ error: error.message }, { status: 500 });
    }
}
