import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Pharmacophore Analysis',
  description: 'Identify pharmacophoric features and molecular descriptors for drug design. Generate 3D pharmacophore models from protein-ligand complexes. Feature-based virtual screening for lead discovery.',
  keywords: ['pharmacophore modeling', 'pharmacophore analysis', '3D pharmacophore', 'molecular descriptors', 'feature-based screening', 'drug design pharmacophore'],
  alternates: { canonical: '/tools/pharmacophore' },
  openGraph: {
    title: 'Pharmacophore Analysis — Feature-Based Drug Design',
    description: 'Identify pharmacophoric features and generate 3D pharmacophore models from protein-ligand complexes.',
    url: 'https://www.biodockify.com/tools/pharmacophore',
  },
};

export default function PharmacophoreLayout({ children }: { children: React.ReactNode }) {
  return children;
}
