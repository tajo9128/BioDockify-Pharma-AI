import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Docking Results',
  robots: { index: false, follow: false },
};

export default function DockIdLayout({ children }: { children: React.ReactNode }) {
  return children;
}
