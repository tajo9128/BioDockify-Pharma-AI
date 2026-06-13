import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: '3D Molecular Viewer',
  description: 'Interactive 3D molecular viewer for protein structures and ligand poses. Visualize docking results with detailed binding interactions, hydrogen bonds, and hydrophobic contacts. Web-based 3Dmol.js rendering with measurement tools.',
  keywords: ['3D molecular viewer', 'protein visualization', 'ligand pose viewer', '3Dmol.js', 'molecular graphics', 'binding interaction visualization', 'protein-ligand 3D'],
  alternates: { canonical: '/tools/3d-viewer' },
  openGraph: {
    title: '3D Molecular Viewer — Interactive Protein Visualization',
    description: 'Visualize protein structures and ligand poses with interactive 3D rendering. Binding interaction analysis.',
    url: 'https://www.biodockify.com/tools/3d-viewer',
  },
};

export default function Viewer3DLayout({ children }: { children: React.ReactNode }) {
  return children;
}
