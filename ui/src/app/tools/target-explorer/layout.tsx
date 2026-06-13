import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Target Explorer',
  description: 'Search and explore protein targets for drug discovery. Browse protein databases, explore target structures, and identify promising therapeutic targets for your research. PDB integration with target annotations.',
  keywords: ['drug target', 'protein target explorer', 'therapeutic target', 'PDB search', 'target identification', 'drug discovery target', 'protein database'],
  alternates: { canonical: '/tools/target-explorer' },
  openGraph: {
    title: 'Target Explorer — Find Protein Drug Targets',
    description: 'Search and explore protein targets for drug discovery. PDB integration with target annotations.',
    url: 'https://www.biodockify.com/tools/target-explorer',
  },
};

export default function TargetExplorerLayout({ children }: { children: React.ReactNode }) {
  return children;
}
