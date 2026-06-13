import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Lead Optimization',
  description: 'Optimize lead compounds for better drug-like properties. Structure-based lead optimization with ADMET feedback, potency prediction, and selectivity analysis. Improve binding affinity while maintaining drug-likeness.',
  keywords: ['lead optimization', 'drug optimization', 'compound optimization', 'potency improvement', 'selectivity optimization', 'drug-like properties', 'lead compound refinement'],
  alternates: { canonical: '/tools/lead-optimization' },
  openGraph: {
    title: 'Lead Optimization — Improve Drug-Like Properties',
    description: 'Optimize lead compounds with ADMET feedback, potency prediction, and selectivity analysis.',
    url: 'https://www.biodockify.com/tools/lead-optimization',
  },
};

export default function LeadOptimizationLayout({ children }: { children: React.ReactNode }) {
  return children;
}
