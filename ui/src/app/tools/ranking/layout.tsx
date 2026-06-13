import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Compound Ranking Tool',
  description: 'Rank docked compounds by binding affinity and drug-likeness. Multi-criteria scoring with customizable weights for binding energy, ADMET properties, and structural diversity. Prioritize hits for experimental validation.',
  keywords: ['compound ranking', 'hit prioritization', 'binding affinity ranking', 'drug-likeness scoring', 'multi-criteria screening', 'hit selection', 'virtual screening ranking'],
  alternates: { canonical: '/tools/ranking' },
  openGraph: {
    title: 'Compound Ranking — Prioritize Hits by Drug-Likeness',
    description: 'Rank docked compounds by binding affinity, ADMET, and structural diversity.',
    url: 'https://www.biodockify.com/tools/ranking',
  },
};

export default function RankingLayout({ children }: { children: React.ReactNode }) {
  return children;
}
