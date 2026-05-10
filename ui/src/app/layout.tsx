import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { Toaster } from "@/components/ui/toaster";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "BioDockify v2.6.7 - Pharma Research AI",
  description: "The Integrated AI Research Workstation for Pharmaceutical & Life Sciences",
  keywords: ["BioDockify", "Pharma Research", "AI", "Drug Discovery", "PhD Research", "Neo4j", "Literature Review"],
  authors: [{ name: "BioDockify Team" }],
  icons: {
    icon: "/favicon.ico",
  },
  manifest: "/manifest.json",
  openGraph: {
    title: "BioDockify - Pharma Research AI",
    description: "Automate pharmaceutical research with AI-powered literature analysis and drug discovery",
    type: "website",
    images: ["/logo.png"],
  },
  appleWebApp: {
    capable: true,
    statusBarStyle: "black-translucent",
    title: "BioDockify",
  },
}

import ServiceWorkerRegister from "@/components/ServiceWorkerRegister";
import PWAInstallPrompt from '@/components/PWAInstallPrompt';

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark" suppressHydrationWarning>
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased bg-background text-foreground`}
      >
        <ServiceWorkerRegister />
        {children}
        <Toaster />
        <PWAInstallPrompt />
      </body>
    </html>
  );
}


