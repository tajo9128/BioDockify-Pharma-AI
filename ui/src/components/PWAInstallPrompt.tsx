'use client';

import { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Download, X, Smartphone } from 'lucide-react';

interface BeforeInstallPromptEvent extends Event {
    prompt: () => Promise<void>;
    userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>;
}

export default function PWAInstallPrompt() {
    const [deferredPrompt, setDeferredPrompt] = useState<BeforeInstallPromptEvent | null>(null);
    const [showPrompt, setShowPrompt] = useState(false);
    const [isInstalled, setIsInstalled] = useState(false);

    useEffect(() => {
        // Check if already installed
        if (window.matchMedia('(display-mode: standalone)').matches) {
            setIsInstalled(true);
            return;
        }

        // Listen for the beforeinstallprompt event
        const handler = (e: Event) => {
            e.preventDefault();
            setDeferredPrompt(e as BeforeInstallPromptEvent);
            setShowPrompt(true);
        };

        window.addEventListener('beforeinstallprompt', handler);

        // Check if app was installed
        window.addEventListener('appinstalled', () => {
            setIsInstalled(true);
            setShowPrompt(false);
            setDeferredPrompt(null);
        });

        return () => {
            window.removeEventListener('beforeinstallprompt', handler);
        };
    }, []);

    const handleInstall = async () => {
        if (!deferredPrompt) return;

        try {
            await deferredPrompt.prompt();
            const { outcome } = await deferredPrompt.userChoice;

            if (outcome === 'accepted') {
                setIsInstalled(true);
            }
            setShowPrompt(false);
            setDeferredPrompt(null);
        } catch (error) {
            console.error('Install prompt error:', error);
        }
    };

    const handleDismiss = () => {
        setShowPrompt(false);
        // Store in localStorage to not show again for this session
        localStorage.setItem('pwa-install-dismissed', 'true');
    };

    // Don't show if already installed or dismissed
    if (isInstalled || !showPrompt) return null;

    // Check if was dismissed this session
    if (typeof window !== 'undefined' && localStorage.getItem('pwa-install-dismissed')) {
        return null;
    }

    return (
        <div className="fixed bottom-4 right-4 z-50 max-w-sm animate-in slide-in-from-bottom-4 fade-in duration-300">
            <div className="bg-gradient-to-br from-emerald-900/90 to-teal-900/90 backdrop-blur-lg border border-emerald-500/30 rounded-xl p-4 shadow-2xl shadow-emerald-900/50">
                <div className="flex items-start gap-3">
                    <div className="flex-shrink-0 p-2 bg-emerald-500/20 rounded-lg">
                        <Smartphone className="h-6 w-6 text-emerald-400" />
                    </div>
                    <div className="flex-1 min-w-0">
                        <h3 className="font-semibold text-white text-sm">
                            Install BioDockify
                        </h3>
                        <p className="text-xs text-emerald-200/80 mt-1">
                            Pin this Research Workstation for quick access. Works offline!
                        </p>
                        <div className="flex items-center gap-2 mt-3">
                            <Button
                                onClick={handleInstall}
                                size="sm"
                                className="bg-emerald-500 hover:bg-emerald-400 text-black font-medium gap-1"
                            >
                                <Download className="h-3.5 w-3.5" />
                                Install
                            </Button>
                            <Button
                                onClick={handleDismiss}
                                size="sm"
                                variant="ghost"
                                className="text-emerald-300/70 hover:text-white hover:bg-emerald-500/20"
                            >
                                Not now
                            </Button>
                        </div>
                    </div>
                    <button
                        onClick={handleDismiss}
                        className="flex-shrink-0 text-emerald-300/50 hover:text-white transition-colors"
                    >
                        <X className="h-4 w-4" />
                    </button>
                </div>
            </div>
        </div>
    );
}
