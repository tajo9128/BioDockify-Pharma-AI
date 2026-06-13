import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Pricing & Plans',
  description: 'BioDockify pricing plans for drug discovery research. Free Starter plan with basic docking, Professional at $49/mo with 3-engine consensus + MD simulation, and Enterprise with unlimited docking. Start free today.',
  keywords: ['BioDockify pricing', 'drug discovery pricing', 'molecular docking cost', 'pharma software plans', 'QSAR pricing', 'ADMET pricing'],
  alternates: { canonical: '/pricing' },
  openGraph: {
    title: 'BioDockify Pricing — Simple, Transparent Plans',
    description: 'Free to start. Professional at $49/mo. Enterprise custom pricing. All plans include core molecular docking features.',
    url: 'https://www.biodockify.com/pricing',
  },
};

export default function PricingLayout({ children }: { children: React.ReactNode }) {
  return children;
}
