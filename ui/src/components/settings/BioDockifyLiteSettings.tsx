
import React from 'react';
import { useSettings } from '../../hooks/useSettings';
import { MessageSquare, Mail, Phone, Send } from 'lucide-react';

interface Settings {
    nanobot?: {
        headless_browser?: boolean;
        stealth_mode?: boolean;
        browser_timeout?: number;
    };
    channels?: {
        telegram?: {
            enabled?: boolean;
            token?: string;
            allow_from?: string[];
        };
        whatsapp?: {
            enabled?: boolean;
            bridge_url?: string;
            auth_token?: string;
            allow_from?: string[];
        };
        discord?: {
            enabled?: boolean;
            token?: string;
            allow_from?: string[];
        };
        email?: {
            enabled?: boolean;
            smtp_host?: string;
            smtp_port?: number;
            smtp_user?: string;
            smtp_password?: string;
            from_email?: string;
            to_emails?: string;
        };
    };
}

export default function BioDockifyLiteSettings() {
    const { settings, updateSettings } = useSettings();

    const safeSettings = settings as Settings;

    const updateLite = (key: string, value: any) => {
        updateSettings('nanobot', {
            ...(safeSettings.nanobot || {}),
            [key]: value
        });
    };

    const updateChannel = (channel: string, key: string, value: any) => {
        updateSettings('channels', {
            ...(safeSettings.channels || {}),
            [channel]: {
                ...(safeSettings.channels?.[channel as keyof typeof safeSettings.channels] || {}),
                [key]: value
            }
        });
    };

    const headlessBrowser = safeSettings.nanobot?.headless_browser || false;
    const stealthMode = safeSettings.nanobot?.stealth_mode || false;
    const browserTimeout = safeSettings.nanobot?.browser_timeout || 30;

    const telegram = safeSettings.channels?.telegram || {};
    const whatsapp = safeSettings.channels?.whatsapp || {};
    const discord = safeSettings.channels?.discord || {};
    const email = safeSettings.channels?.email || {};

    return (
        <div className="space-y-6">
            <div>
                <h2 className="text-2xl font-bold text-white mb-2">BioDockify AI Lite</h2>
                <p className="text-slate-400">Configure the Coordinator Agent and notification channels.</p>
            </div>

            {/* Browser Automation */}
            <div className="bg-slate-800 rounded-lg p-6 border border-slate-700 space-y-6">
                <h3 className="text-lg font-semibold text-emerald-400">Browser Automation</h3>

                <div className="flex items-center justify-between">
                    <div>
                        <label className="text-slate-200 font-medium">Headless Mode</label>
                        <p className="text-xs text-slate-500">Run browser in background (faster, less visible)</p>
                    </div>
                    <input
                        type="checkbox"
                        checked={headlessBrowser}
                        onChange={(e) => updateLite('headless_browser', e.target.checked)}
                        className="h-5 w-5 rounded border-slate-600 bg-slate-900 text-emerald-600 focus:ring-emerald-500"
                    />
                </div>

                <div className="flex items-center justify-between">
                    <div>
                        <label className="text-slate-200 font-medium">Stealth Mode</label>
                        <p className="text-xs text-slate-500">Evade bot detection on academic sites</p>
                    </div>
                    <input
                        type="checkbox"
                        checked={stealthMode}
                        onChange={(e) => updateLite('stealth_mode', e.target.checked)}
                        className="h-5 w-5 rounded border-slate-600 bg-slate-900 text-emerald-600 focus:ring-emerald-500"
                    />
                </div>

                <div>
                    <label className="block text-sm font-medium text-slate-300 mb-1">Browser Timeout (seconds)</label>
                    <input
                        type="number"
                        value={browserTimeout}
                        onChange={(e) => updateLite('browser_timeout', parseInt(e.target.value))}
                        className="w-24 bg-slate-900 border border-slate-600 rounded px-2 py-1 text-white focus:outline-none focus:border-emerald-500"
                    />
                </div>
            </div>

            {/* Telegram Settings */}
            <div className="bg-slate-800 rounded-lg p-6 border border-slate-700 space-y-4">
                <div className="flex items-center gap-2">
                    <MessageSquare className="w-5 h-5 text-blue-400" />
                    <h3 className="text-lg font-semibold text-blue-400">Telegram</h3>
                </div>

                <div className="flex items-center justify-between">
                    <label className="text-slate-200 font-medium">Enable Telegram</label>
                    <input
                        type="checkbox"
                        checked={telegram.enabled || false}
                        onChange={(e) => updateChannel('telegram', 'enabled', e.target.checked)}
                        className="h-5 w-5 rounded border-slate-600 bg-slate-900 text-blue-500 focus:ring-blue-500"
                    />
                </div>

                {telegram.enabled && (
                    <>
                        <div>
                            <label className="block text-sm font-medium text-slate-300 mb-1">Bot Token</label>
                            <input
                                type="password"
                                value={telegram.token || ''}
                                onChange={(e) => updateChannel('telegram', 'token', e.target.value)}
                                placeholder="123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
                                className="w-full bg-slate-900 border border-slate-600 rounded px-3 py-2 text-white focus:outline-none focus:border-blue-500"
                            />
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-slate-300 mb-1">Allowed Chat IDs (comma separated)</label>
                            <input
                                type="text"
                                value={telegram.allow_from?.join(', ') || ''}
                                onChange={(e) => updateChannel('telegram', 'allow_from', e.target.value.split(',').map(s => s.trim()).filter(Boolean))}
                                placeholder="123456789, 987654321"
                                className="w-full bg-slate-900 border border-slate-600 rounded px-3 py-2 text-white focus:outline-none focus:border-blue-500"
                            />
                        </div>
                    </>
                )}
            </div>

            {/* WhatsApp Settings */}
            <div className="bg-slate-800 rounded-lg p-6 border border-slate-700 space-y-4">
                <div className="flex items-center gap-2">
                    <Phone className="w-5 h-5 text-green-400" />
                    <h3 className="text-lg font-semibold text-green-400">WhatsApp</h3>
                </div>

                <div className="flex items-center justify-between">
                    <label className="text-slate-200 font-medium">Enable WhatsApp</label>
                    <input
                        type="checkbox"
                        checked={whatsapp.enabled || false}
                        onChange={(e) => updateChannel('whatsapp', 'enabled', e.target.checked)}
                        className="h-5 w-5 rounded border-slate-600 bg-slate-900 text-green-500 focus:ring-green-500"
                    />
                </div>

                {whatsapp.enabled && (
                    <>
                        <div>
                            <label className="block text-sm font-medium text-slate-300 mb-1">Bridge URL</label>
                            <input
                                type="text"
                                value={whatsapp.bridge_url || 'ws://localhost:3001'}
                                onChange={(e) => updateChannel('whatsapp', 'bridge_url', e.target.value)}
                                placeholder="ws://localhost:3001"
                                className="w-full bg-slate-900 border border-slate-600 rounded px-3 py-2 text-white focus:outline-none focus:border-green-500"
                            />
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-slate-300 mb-1">Auth Token</label>
                            <input
                                type="password"
                                value={whatsapp.auth_token || ''}
                                onChange={(e) => updateChannel('whatsapp', 'auth_token', e.target.value)}
                                placeholder="Your auth token"
                                className="w-full bg-slate-900 border border-slate-600 rounded px-3 py-2 text-white focus:outline-none focus:border-green-500"
                            />
                        </div>
                    </>
                )}
            </div>

            {/* Discord Settings */}
            <div className="bg-slate-800 rounded-lg p-6 border border-slate-700 space-y-4">
                <div className="flex items-center gap-2">
                    <Send className="w-5 h-5 text-indigo-400" />
                    <h3 className="text-lg font-semibold text-indigo-400">Discord</h3>
                </div>

                <div className="flex items-center justify-between">
                    <label className="text-slate-200 font-medium">Enable Discord</label>
                    <input
                        type="checkbox"
                        checked={discord.enabled || false}
                        onChange={(e) => updateChannel('discord', 'enabled', e.target.checked)}
                        className="h-5 w-5 rounded border-slate-600 bg-slate-900 text-indigo-500 focus:ring-indigo-500"
                    />
                </div>

                {discord.enabled && (
                    <>
                        <div>
                            <label className="block text-sm font-medium text-slate-300 mb-1">Bot Token</label>
                            <input
                                type="password"
                                value={discord.token || ''}
                                onChange={(e) => updateChannel('discord', 'token', e.target.value)}
                                placeholder="MTEwNTY3ODkwMDAw.LoremIpsum.dolor_sit_Am3t_conS3ct3tur"
                                className="w-full bg-slate-900 border border-slate-600 rounded px-3 py-2 text-white focus:outline-none focus:border-indigo-500"
                            />
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-slate-300 mb-1">Allowed Channel IDs (comma separated)</label>
                            <input
                                type="text"
                                value={discord.allow_from?.join(', ') || ''}
                                onChange={(e) => updateChannel('discord', 'allow_from', e.target.value.split(',').map(s => s.trim()).filter(Boolean))}
                                placeholder="123456789012345678, 987654321098765432"
                                className="w-full bg-slate-900 border border-slate-600 rounded px-3 py-2 text-white focus:outline-none focus:border-indigo-500"
                            />
                        </div>
                    </>
                )}
            </div>

            {/* Email Settings */}
            <div className="bg-slate-800 rounded-lg p-6 border border-slate-700 space-y-4">
                <div className="flex items-center gap-2">
                    <Mail className="w-5 h-5 text-red-400" />
                    <h3 className="text-lg font-semibold text-red-400">Email (SMTP)</h3>
                </div>

                <div className="flex items-center justify-between">
                    <label className="text-slate-200 font-medium">Enable Email</label>
                    <input
                        type="checkbox"
                        checked={email.enabled || false}
                        onChange={(e) => updateChannel('email', 'enabled', e.target.checked)}
                        className="h-5 w-5 rounded border-slate-600 bg-slate-900 text-red-500 focus:ring-red-500"
                    />
                </div>

                {email.enabled && (
                    <>
                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <label className="block text-sm font-medium text-slate-300 mb-1">SMTP Host</label>
                                <input
                                    type="text"
                                    value={email.smtp_host || ''}
                                    onChange={(e) => updateChannel('email', 'smtp_host', e.target.value)}
                                    placeholder="smtp.gmail.com"
                                    className="w-full bg-slate-900 border border-slate-600 rounded px-3 py-2 text-white focus:outline-none focus:border-red-500"
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-slate-300 mb-1">SMTP Port</label>
                                <input
                                    type="number"
                                    value={email.smtp_port || 587}
                                    onChange={(e) => updateChannel('email', 'smtp_port', parseInt(e.target.value))}
                                    placeholder="587"
                                    className="w-full bg-slate-900 border border-slate-600 rounded px-3 py-2 text-white focus:outline-none focus:border-red-500"
                                />
                            </div>
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-slate-300 mb-1">SMTP Username</label>
                            <input
                                type="text"
                                value={email.smtp_user || ''}
                                onChange={(e) => updateChannel('email', 'smtp_user', e.target.value)}
                                placeholder="your-email@gmail.com"
                                className="w-full bg-slate-900 border border-slate-600 rounded px-3 py-2 text-white focus:outline-none focus:border-red-500"
                            />
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-slate-300 mb-1">SMTP Password</label>
                            <input
                                type="password"
                                value={email.smtp_password || ''}
                                onChange={(e) => updateChannel('email', 'smtp_password', e.target.value)}
                                placeholder="App password"
                                className="w-full bg-slate-900 border border-slate-600 rounded px-3 py-2 text-white focus:outline-none focus:border-red-500"
                            />
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-slate-300 mb-1">From Email</label>
                            <input
                                type="email"
                                value={email.from_email || ''}
                                onChange={(e) => updateChannel('email', 'from_email', e.target.value)}
                                placeholder="your-email@gmail.com"
                                className="w-full bg-slate-900 border border-slate-600 rounded px-3 py-2 text-white focus:outline-none focus:border-red-500"
                            />
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-slate-300 mb-1">To Emails (comma separated)</label>
                            <input
                                type="text"
                                value={email.to_emails || ''}
                                onChange={(e) => updateChannel('email', 'to_emails', e.target.value)}
                                placeholder="recipient1@example.com, recipient2@example.com"
                                className="w-full bg-slate-900 border border-slate-600 rounded px-3 py-2 text-white focus:outline-none focus:border-red-500"
                            />
                        </div>
                    </>
                )}
            </div>
        </div>
    );
}
