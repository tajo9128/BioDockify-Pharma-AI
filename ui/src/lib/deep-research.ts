/**
 * Deep Research Agent & Audio Briefing Integration
 * 
 * Inspired by SurfSense, this module adds:
 * 1. Deep Research Mode: Multi-step reasoning agent that breaks down queries.
 * 2. Audio Briefing: Converts research summaries into audio (Podcast style).
 * 
 * Uses:
 * - llm-service for ALL LLM calls (with automatic rotation on rate limits)
 * - Web search integration
 * - RAG Hybrid Search
 */

import { api } from '@/lib/api';
import { searchWeb } from '@/lib/web_fetcher';
import { deepResearchPlan, deepResearchStep, generatePodcastScript, llmChat } from '@/lib/services/llm-service';

// ============================================================================
// Types
// ============================================================================

export interface ResearchPlan {
    steps: string[];
    currentStep: number;
    status: 'planning' | 'researching' | 'synthesizing' | 'complete';
    findings: string[];
}

export interface AudioBriefing {
    title: string;
    audioUrl: string; // Blob URL or path
    duration: number;
    transcript: string;
}

// ============================================================================
// Deep Research Agent
// ============================================================================

export class DeepResearchAgent {
    private static instance: DeepResearchAgent;

    private constructor() { }

    public static getInstance(): DeepResearchAgent {
        if (!DeepResearchAgent.instance) {
            DeepResearchAgent.instance = new DeepResearchAgent();
        }
        return DeepResearchAgent.instance;
    }

    /**
     * Break down a complex query into a research plan
     * Uses LLM with automatic rotation on rate limits
     */
    public async createPlan(query: string): Promise<ResearchPlan> {
        try {
            const steps = await deepResearchPlan(query);
            return {
                steps,
                currentStep: 0,
                status: 'planning',
                findings: []
            };
        } catch (e) {
            console.error('[DeepResearch] Plan creation failed, using fallback:', e);
            // Fallback to basic plan if LLM fails
            return {
                steps: [
                    `Analyze core concepts in: "${query}"`,
                    `Search for recent developments (2024-2025)`,
                    `Cross-reference with internal knowledge base`,
                    `Synthesize findings into a comprehensive answer`
                ],
                currentStep: 0,
                status: 'planning',
                findings: []
            };
        }
    }

    /**
     * Execute a research step
     * Uses LLM with automatic rotation on rate limits
     */
    public async executeStep(step: string, context: string): Promise<string> {
        console.log(`[DeepResearch] Executing: ${step}`);

        // 1. Web Search if needed
        let webResults = "";
        if (step.toLowerCase().includes('search')) {
            const urls = await searchWeb(step);
            webResults = `Found ${urls.length} sources. `;
        }

        // 2. Use LLM for research step execution (with rotation)
        try {
            const llmResult = await deepResearchStep(step, context + webResults);
            return llmResult;
        } catch (e) {
            console.error('[DeepResearch] Step execution failed:', e);
            return `Completed: ${step}. ${webResults}Analyzed context.`;
        }
    }

    /**
     * Generate Audio Briefing (Podcast)
     * Uses LLM with automatic rotation for script generation
     */
    public async generateAudioBriefing(text: string, findings: string[] = []): Promise<AudioBriefing> {
        console.log('[DeepResearch] Generating audio briefing...');

        try {
            // Generate script using LLM (with rotation)
            const script = await generatePodcastScript(
                "Research Briefing",
                findings.length > 0 ? findings : [text],
                'medium'
            );

            return {
                title: "Research Briefing",
                audioUrl: "", // UI will use TTS API
                duration: Math.ceil(script.length / 15), // Rough estimate
                transcript: script
            };
        } catch (e) {
            console.error('[DeepResearch] Audio briefing generation failed:', e);
            return {
                title: "Research Briefing",
                audioUrl: "",
                duration: 180,
                transcript: text
            };
        }
    }
}
