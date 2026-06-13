import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'ADMET Prediction Tool',
  description: 'Free ADMET prediction tool. Predict Absorption, Distribution, Metabolism, Excretion, and Toxicity properties from SMILES. Drug-likeness evaluation, Lipinski Rule of Five, PAINS filters, toxicity risk, and BBB penetration analysis.',
  keywords: ['ADMET prediction', 'drug-likeness', 'Lipinski rule of five', 'PAINS filter', 'toxicity prediction', 'BBB penetration', 'absorption prediction', 'bioavailability'],
  alternates: { canonical: '/tools/admet' },
  openGraph: {
    title: 'ADMET Prediction — Drug-Likess & Toxicity Analysis',
    description: 'Predict ADMET properties from SMILES. Drug-likeness, PAINS, toxicity risk, BBB penetration.',
    url: 'https://www.biodockify.com/tools/admet',
  },
};

export default function ADMETLayout({ children }: { children: React.ReactNode }) {
  return children;
}
