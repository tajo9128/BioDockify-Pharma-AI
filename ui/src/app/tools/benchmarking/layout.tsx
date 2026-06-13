import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Docking Benchmarking',
  description: 'Evaluate molecular docking engine accuracy, speed, and pose quality against standardized datasets. Compare AutoDock Vina, GNINA CNN, and RF ML scoring engines. Benchmark your docking protocols with CSAR, DUD-E, and PDBbind references.',
  keywords: ['docking benchmarking', 'docking accuracy', 'CSAR benchmark', 'DUD-E evaluation', 'PDBbind benchmark', 'scoring function comparison', 'docking validation'],
  alternates: { canonical: '/tools/benchmarking' },
  openGraph: {
    title: 'Docking Benchmarking — Engine Accuracy & Speed',
    description: 'Evaluate docking engine accuracy, speed, and pose quality against standardized datasets.',
    url: 'https://www.biodockify.com/tools/benchmarking',
  },
};

export default function BenchmarkingLayout({ children }: { children: React.ReactNode }) {
  return children;
}
