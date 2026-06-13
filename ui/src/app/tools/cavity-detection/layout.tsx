import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Binding Site Detection',
  description: 'Identify potential binding cavities in protein structures. Automated binding site detection with geometric and energetic analysis. Find druggable pockets for targeted molecular docking and drug discovery.',
  keywords: ['binding site detection', 'binding cavity', 'druggable pocket', 'protein binding site', 'cavity detection algorithm', 'active site identification'],
  alternates: { canonical: '/tools/cavity-detection' },
  openGraph: {
    title: 'Binding Site Detection — Find Druggable Pockets',
    description: 'Automated identification of binding cavities in protein structures for targeted drug discovery.',
    url: 'https://www.biodockify.com/tools/cavity-detection',
  },
};

export default function CavityDetectionLayout({ children }: { children: React.ReactNode }) {
  return children;
}
