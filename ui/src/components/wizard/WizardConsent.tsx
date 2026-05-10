/**
 * WizardConsent Component
 * 
 * Handles explicit user consent during First-Run Wizard.
 * Follows BioDockify AI RULE 4: Non-negotiable user consent.
 * 
 * If consent not granted:
 * - DO NOT automate
 * - DO NOT retry
 * - DO NOT nag
 */

'use client';

import React, { useState, useEffect } from 'react';
import { Shield, Check, AlertCircle } from 'lucide-react';
import { getSystemController } from '@/lib/system-controller';
import { ConsentRequest, SystemState } from '@/lib/system-rules';

interface WizardConsentProps {
    onConsentComplete: (consent: SystemState['consent']) => void;
}

export default function WizardConsent({ onConsentComplete }: WizardConsentProps) {
    const controller = getSystemController();
    const [consentRequests, setConsentRequests] = useState<ConsentRequest[]>([]);
    const [acknowledged, setAcknowledged] = useState(false);

    useEffect(() => {
        setConsentRequests(controller.getConsentRequests());
    }, []);

    const handleConsentChange = (id: keyof SystemState['consent'], granted: boolean) => {
        controller.setConsent(id, granted);
        setConsentRequests(controller.getConsentRequests());
    };

    const handleContinue = () => {
        const state = controller.getState();
        onConsentComplete(state.consent);
    };

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center space-x-3 pb-4 border-b border-slate-800">
                <Shield className="w-6 h-6 text-sky-400" />
                <div>
                    <h3 className="text-lg font-semibold text-white">Privacy & Permissions</h3>
                    <p className="text-sm text-slate-400">
                        BioDockify will only perform actions you explicitly allow.
                    </p>
                </div>
            </div>

            {/* Consent Checkboxes */}
            <div className="space-y-4">
                {consentRequests.map((request) => (
                    <label
                        key={request.id}
                        className="flex items-start space-x-4 p-4 bg-slate-900/50 border border-slate-800 rounded-lg cursor-pointer hover:border-slate-700 transition-colors"
                    >
                        <div className="flex-shrink-0 mt-0.5">
                            <input
                                type="checkbox"
                                checked={request.granted}
                                onChange={(e) => handleConsentChange(request.id, e.target.checked)}
                                className="sr-only"
                            />
                            <div className={`w-5 h-5 rounded border-2 flex items-center justify-center transition-colors ${request.granted
                                ? 'bg-sky-500 border-sky-500'
                                : 'border-slate-600 hover:border-slate-500'
                                }`}>
                                {request.granted && <Check className="w-3 h-3 text-white" />}
                            </div>
                        </div>
                        <div className="flex-1">
                            <span className="text-white font-medium block">{request.label}</span>
                            <span className="text-sm text-slate-400">{request.description}</span>
                        </div>
                    </label>
                ))}
            </div>

            {/* Important Notice */}
            <div className="flex items-start space-x-3 p-4 bg-slate-900/30 border border-slate-800 rounded-lg">
                <AlertCircle className="w-5 h-5 text-slate-500 flex-shrink-0 mt-0.5" />
                <div className="text-sm text-slate-500">
                    <p className="font-medium text-slate-400">Your choice is respected.</p>
                    <p className="mt-1">
                        If you decline automation, BioDockify will not attempt to start services automatically.
                        You can change these settings later in the Settings panel.
                    </p>
                    <p className="mt-2 text-xs text-slate-600">
                        <span className="font-medium text-slate-500">Note:</span> During setup, BioDockify checks
                        internet connectivity (pings google.com, cloudflare.com, github.com), detects LM Studio
                        on local ports, and may auto-start LM Studio if enabled and not running.
                    </p>
                </div>
            </div>

            {/* Acknowledgment */}
            <label className="flex items-center space-x-3 cursor-pointer">
                <input
                    type="checkbox"
                    checked={acknowledged}
                    onChange={(e) => setAcknowledged(e.target.checked)}
                    className="sr-only"
                />
                <div className={`w-5 h-5 rounded border-2 flex items-center justify-center transition-colors ${acknowledged
                    ? 'bg-emerald-500 border-emerald-500'
                    : 'border-slate-600 hover:border-slate-500'
                    }`}>
                    {acknowledged && <Check className="w-3 h-3 text-white" />}
                </div>
                <span className="text-slate-300">
                    I understand how BioDockify handles my preferences
                </span>
            </label>

            {/* Continue Button */}
            <button
                onClick={handleContinue}
                disabled={!acknowledged}
                className={`w-full py-3 rounded-lg font-semibold transition-all ${acknowledged
                    ? 'bg-sky-500 hover:bg-sky-400 text-white'
                    : 'bg-slate-800 text-slate-500 cursor-not-allowed'
                    }`}
            >
                Continue Setup
            </button>
        </div>
    );
}
