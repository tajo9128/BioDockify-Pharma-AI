import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Molecular Dynamics (MD) Simulation',
  description: 'Run GPU-accelerated molecular dynamics simulations on BioDockify. GROMACS and OpenMM powered trajectories from 20ns to 100ns. Analyze protein-ligand stability, RMSD, RMSF, and hydrogen bonds. Cloud-based MD simulation for drug discovery.',
  keywords: ['molecular dynamics simulation', 'MD simulation', 'GROMACS', 'OpenMM', 'GPU molecular dynamics', 'protein-ligand MD', 'RMSD analysis', 'drug discovery simulation'],
  alternates: { canonical: '/md-simulation' },
  openGraph: {
    title: 'Molecular Dynamics Simulation — GPU-Accelerated MD',
    description: 'Run GROMACS and OpenMM simulations with GPU acceleration. 20ns–100ns trajectories, stability analysis, and more.',
    url: 'https://www.biodockify.com/md-simulation',
  },
};

export default function MDSimulationLayout({ children }: { children: React.ReactNode }) {
  return children;
}
