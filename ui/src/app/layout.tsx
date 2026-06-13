import type { Metadata } from 'next';
import Header from '@/biodockify/Header';
import Footer from '@/biodockify/Footer';
import { ThemeProvider } from '@/biodockify/ThemeContext';
import './globals.css';

export const metadata: Metadata = {
  metadataBase: new URL('https://www.biodockify.com'),
  title: {
    default: 'BioDockify — AI-Powered Drug Discovery & Molecular Docking Platform',
    template: '%s | BioDockify',
  },
  description: 'BioDockify is the leading AI-powered drug discovery platform. Molecular docking with 3-engine consensus scoring, QSAR modeling, ADMET prediction, MD simulation, and an autonomous AI research agent. 15,000+ researchers. Free to start.',
  keywords: ['drug discovery', 'molecular docking', 'AI drug discovery', 'QSAR modeling', 'ADMET prediction', 'virtual screening', 'computational chemistry', 'AutoDock Vina', 'GNINA', 'pharmacophore', 'molecular dynamics', 'pharmaceutical research', 'BioDockify'],
  robots: { index: true, follow: true, 'max-snippet': -1, 'max-image-preview': 'large', 'max-video-preview': -1 },
  authors: [{ name: 'BioDockify' }],
  alternates: { canonical: '/' },
  openGraph: {
    type: 'website',
    siteName: 'BioDockify',
    url: 'https://www.biodockify.com/',
    title: 'BioDockify — AI-Powered Drug Discovery Platform',
    description: 'Cloud-native molecular docking with 3-engine consensus scoring. QSAR, ADMET, MD simulation, and an autonomous AI agent. 15,000+ researchers. Free to start.',
    images: [{ url: '/brand/logo-white.svg', width: 1200, height: 630 }],
    locale: 'en_US',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'BioDockify — AI-Powered Drug Discovery Platform',
    description: '3-engine consensus molecular docking, QSAR, ADMET, MD simulation & AI agent. Free to start.',
    images: ['/brand/logo-white.svg'],
    site: '@biodockify',
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark" suppressHydrationWarning>
      <head>
        <link rel="icon" type="image/svg+xml" href="/brand/icon.svg" />
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet" />
        <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify({
          "@context": "https://schema.org", "@type": "Organization", "name": "BioDockify",
          "url": "https://www.biodockify.com/", "logo": "https://www.biodockify.com/brand/logo-white.svg",
          "sameAs": ["https://github.com/biodockify", "https://twitter.com/biodockify", "https://linkedin.com/company/biodockify"]
        }) }} />
      </head>
      <body className="antialiased font-['Inter']">
        <ThemeProvider>
          <Header />
          <main className="min-h-screen">{children}</main>
          <Footer />
        </ThemeProvider>
      </body>
    </html>
  );
}
