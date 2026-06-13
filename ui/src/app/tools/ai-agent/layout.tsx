import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'AI Research Agent',
  description: 'Autonomous AI agent for drug discovery research. Ask questions about molecular docking, compound screening, and pharmacology. Powered by advanced language models. Launch docking jobs, analyze results, and get research insights through natural language.',
  keywords: ['AI drug discovery agent', 'artificial intelligence pharmacology', 'AI molecular docking', 'autonomous research agent', 'drug discovery chatbot', 'AI pharmaceutical research'],
  alternates: { canonical: '/tools/ai-agent' },
  openGraph: {
    title: 'AI Research Agent — Autonomous Drug Discovery Assistant',
    description: 'Ask questions, launch docking jobs, and analyze results through natural language.',
    url: 'https://www.biodockify.com/tools/ai-agent',
  },
};

export default function AIAgentLayout({ children }: { children: React.ReactNode }) {
  return children;
}
