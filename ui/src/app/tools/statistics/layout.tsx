import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Statistical Analysis Suite',
  description: 'Comprehensive statistical analysis suite for drug discovery research. 20+ statistical tests, 8+ chart types, publication-ready outputs. ANOVA, t-test, correlation analysis, and data visualization for docking results and bioactivity data.',
  keywords: ['statistical analysis drug discovery', 'ANOVA docking', 'publication-ready charts', 'bioinformatics statistics', 'data visualization', 'correlation analysis', 't-test molecular'],
  alternates: { canonical: '/tools/statistics' },
  openGraph: {
    title: 'Statistical Analysis — 20+ Tests, Publication-Ready',
    description: 'Comprehensive stats suite with ANOVA, t-test, correlation, and 8+ chart types for research data.',
    url: 'https://www.biodockify.com/tools/statistics',
  },
};

export default function StatisticsLayout({ children }: { children: React.ReactNode }) {
  return children;
}
