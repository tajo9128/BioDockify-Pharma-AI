import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Google Drive Integration',
  description: 'Connect your Google Drive to BioDockify for seamless file management. Access protein structures, compound libraries, and docking results directly from Drive. Sync research data across devices and collaborate with your team.',
  keywords: ['Google Drive drug discovery', 'cloud file storage', 'research data sync', 'protein structure storage', 'docking results backup', 'collaborative research'],
  alternates: { canonical: '/tools/drive' },
  openGraph: {
    title: 'Google Drive Integration — Cloud File Management',
    description: 'Connect Google Drive to access and manage protein structures and docking results.',
    url: 'https://www.biodockify.com/tools/drive',
  },
};

export default function DriveLayout({ children }: { children: React.ReactNode }) {
  return children;
}
