import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Batch Virtual Screening',
  description: 'Screen thousands of compounds in parallel with BioDockify batch docking. 3-engine consensus scoring (AutoDock Vina + GNINA CNN + Random Forest ML). Upload SMILES libraries, run high-throughput virtual screening, and rank results automatically.',
  keywords: ['batch docking', 'virtual screening', 'high-throughput screening', 'HTVS', 'compound library screening', 'AutoDock Vina batch', 'GNINA batch', 'consensus docking'],
  alternates: { canonical: '/dock/batch' },
  openGraph: {
    title: 'Batch Virtual Screening — 10,000+ Compounds in Parallel',
    description: 'Upload compound libraries and screen them against protein targets with 3-engine consensus scoring. Real-time monitoring.',
    url: 'https://www.biodockify.com/dock/batch',
  },
};

export default function BatchDockingLayout({ children }: { children: React.ReactNode }) {
  return children;
}
