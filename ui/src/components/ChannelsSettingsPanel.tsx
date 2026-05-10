/**
 * ChannelsSettingsPanel - Configure Telegram, WhatsApp, Discord
 * 
 * Allows users to connect BioDockify AI to messaging platforms.
 */

import React, { useState, useEffect } from 'react';
import {
    MessageCircle,
    Send,
    Hash,
    RefreshCw,
    Play,
    Square,
    Eye,
    EyeOff
} from 'lucide-react';
import { useToast } from '@/hooks/use-toast';

interface ChannelConfig {
    enabled: boolean;
    configured: boolean;
    running: boolean;
}

interface ChannelsStatus {
    running: boolean;
    channels: {
        telegram: ChannelConfig;
        whatsapp: ChannelConfig;
        discord: ChannelConfig;
    };
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:3000';

export default function ChannelsSettingsPanel() {
    const { toast } = useToast();
    const [status, setStatus] = useState<ChannelsStatus | null>(null);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);

    // Telegram config
    const [telegramEnabled, setTelegramEnabled] = useState(false);
    const [telegramToken, setTelegramToken] = useState('');
    const [showTelegramToken, setShowTelegramToken] = useState(false);

    // WhatsApp config
    const [whatsappEnabled, setWhatsappEnabled] = useState(false);
    const [whatsappPhoneId, setWhatsappPhoneId] = useState('');
    const [whatsappAccessToken, setWhatsappAccessToken] = useState('');
    const [whatsappVerifyToken, setWhatsappVerifyToken] = useState('');

    // Discord config
    const [discordEnabled, setDiscordEnabled] = useState(false);
    const [discordToken, setDiscordToken] = useState('');
    const [showDiscordToken, setShowDiscordToken] = useState(false);

    useEffect(() => {
        fetchStatus();
    }, []);

    const fetchStatus = async () => {
        try {
            const res = await fetch(`${API_BASE}/api/channels/status`);
            const data = await res.json();
            setStatus(data);

            // Update local state from API
            if (data.channels) {
                setTelegramEnabled(data.channels.telegram?.enabled || false);
                setWhatsappEnabled(data.channels.whatsapp?.enabled || false);
                setDiscordEnabled(data.channels.discord?.enabled || false);
            }
        } catch (e) {
            console.error('Failed to fetch channels status:', e);
        } finally {
            setLoading(false);
        }
    };

    const handleSaveTelegram = async () => {
        setSaving(true);
        try {
            await fetch(`${API_BASE}/api/channels/telegram`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    enabled: telegramEnabled,
                    token: telegramToken,
                    allowed_users: []
                })
            });
            toast({ title: "Telegram Saved", description: "Configuration updated successfully." });
            fetchStatus();
        } catch (e) {
            toast({ title: "Failed", description: "Could not save Telegram config.", variant: "destructive" });
        } finally {
            setSaving(false);
        }
    };

    const handleSaveWhatsApp = async () => {
        setSaving(true);
        try {
            await fetch(`${API_BASE}/api/channels/whatsapp`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    enabled: whatsappEnabled,
                    phone_id: whatsappPhoneId,
                    access_token: whatsappAccessToken,
                    verify_token: whatsappVerifyToken
                })
            });
            toast({ title: "WhatsApp Saved", description: "Configuration updated successfully." });
            fetchStatus();
        } catch (e) {
            toast({ title: "Failed", description: "Could not save WhatsApp config.", variant: "destructive" });
        } finally {
            setSaving(false);
        }
    };

    const handleSaveDiscord = async () => {
        setSaving(true);
        try {
            await fetch(`${API_BASE}/api/channels/discord`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    enabled: discordEnabled,
                    token: discordToken,
                    allowed_guilds: []
                })
            });
            toast({ title: "Discord Saved", description: "Configuration updated successfully." });
            fetchStatus();
        } catch (e) {
            toast({ title: "Failed", description: "Could not save Discord config.", variant: "destructive" });
        } finally {
            setSaving(false);
        }
    };

    const handleStartChannels = async () => {
        try {
            await fetch(`${API_BASE}/api/channels/start`, { method: 'POST' });
            toast({ title: "Starting", description: "Messaing channels are booting up..." });
            setTimeout(fetchStatus, 2000);
        } catch (e) {
            toast({ title: "Bootstrap Failed", description: "Check backend connection.", variant: "destructive" });
        }
    };

    const handleStopChannels = async () => {
        try {
            await fetch(`${API_BASE}/api/channels/stop`, { method: 'POST' });
            alert('Channels stopped');
            fetchStatus();
        } catch (e) {
            alert('Failed to stop channels');
        }
    };

    if (loading) {
        return (
            <div className="p-8 text-center text-slate-400">
                <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2" />
                Loading channels configuration...
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                    <div className="p-2 bg-gradient-to-br from-purple-500 to-pink-500 rounded-lg">
                        <MessageCircle className="w-6 h-6 text-white" />
                    </div>
                    <div>
                        <h2 className="text-xl font-bold text-white">Messaging Channels</h2>
                        <p className="text-sm text-slate-400">Connect BioDockify AI to Telegram, WhatsApp, Discord</p>
                    </div>
                </div>

                {/* Start/Stop Buttons */}
                <div className="flex gap-2">
                    {status?.running ? (
                        <button
                            onClick={handleStopChannels}
                            className="flex items-center gap-2 px-4 py-2 bg-red-600 hover:bg-red-500 text-white rounded-lg font-medium"
                        >
                            <Square className="w-4 h-4" />
                            Stop All
                        </button>
                    ) : (
                        <button
                            onClick={handleStartChannels}
                            className="flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg font-medium"
                        >
                            <Play className="w-4 h-4" />
                            Start Channels
                        </button>
                    )}
                </div>
            </div>

            {/* Status Banner */}
            <div className={`p-4 rounded-lg border ${status?.running
                ? 'bg-emerald-950/30 border-emerald-500/30'
                : 'bg-slate-900 border-slate-700'}`}
            >
                <div className="flex items-center gap-2">
                    {status?.running ? (
                        <>
                            <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                            <span className="text-emerald-400 font-medium">Channels Active</span>
                        </>
                    ) : (
                        <>
                            <div className="w-2 h-2 rounded-full bg-slate-500" />
                            <span className="text-slate-400">Channels Stopped</span>
                        </>
                    )}
                </div>
            </div>

            {/* Telegram */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
                <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-3">
                        <Send className="w-5 h-5 text-blue-400" />
                        <h3 className="text-lg font-semibold text-white">Telegram Bot</h3>
                        {status?.channels.telegram?.running && (
                            <span className="px-2 py-0.5 text-xs bg-emerald-500/20 text-emerald-400 rounded">Running</span>
                        )}
                    </div>
                    <label className="flex items-center gap-2 cursor-pointer">
                        <input
                            type="checkbox"
                            checked={telegramEnabled}
                            onChange={(e) => setTelegramEnabled(e.target.checked)}
                            className="w-4 h-4 rounded"
                        />
                        <span className="text-sm text-slate-400">Enable</span>
                    </label>
                </div>

                <div className="space-y-4">
                    <div>
                        <label className="block text-sm text-slate-400 mb-1">Bot Token</label>
                        <div className="relative">
                            <input
                                type={showTelegramToken ? 'text' : 'password'}
                                value={telegramToken}
                                onChange={(e) => setTelegramToken(e.target.value)}
                                placeholder="123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
                                className="w-full bg-slate-950 border border-slate-700 rounded-lg px-4 py-2 text-white pr-10"
                            />
                            <button
                                onClick={() => setShowTelegramToken(!showTelegramToken)}
                                className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-white"
                            >
                                {showTelegramToken ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                            </button>
                        </div>
                        <p className="text-xs text-slate-500 mt-1">
                            Get from <a href="https://t.me/BotFather" target="_blank" rel="noreferrer" className="text-blue-400 hover:underline">@BotFather</a>
                        </p>
                    </div>

                    <button
                        onClick={handleSaveTelegram}
                        disabled={saving}
                        className="w-full bg-blue-600 hover:bg-blue-500 text-white py-2 rounded-lg font-medium disabled:opacity-50"
                    >
                        {saving ? 'Saving...' : 'Save Telegram Config'}
                    </button>
                </div>
            </div>

            {/* WhatsApp */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
                <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-3">
                        <MessageCircle className="w-5 h-5 text-green-400" />
                        <h3 className="text-lg font-semibold text-white">WhatsApp Business</h3>
                        {status?.channels.whatsapp?.running && (
                            <span className="px-2 py-0.5 text-xs bg-emerald-500/20 text-emerald-400 rounded">Running</span>
                        )}
                    </div>
                    <label className="flex items-center gap-2 cursor-pointer">
                        <input
                            type="checkbox"
                            checked={whatsappEnabled}
                            onChange={(e) => setWhatsappEnabled(e.target.checked)}
                            className="w-4 h-4 rounded"
                        />
                        <span className="text-sm text-slate-400">Enable</span>
                    </label>
                </div>

                <div className="space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <label className="block text-sm text-slate-400 mb-1">Phone Number ID</label>
                            <input
                                type="text"
                                value={whatsappPhoneId}
                                onChange={(e) => setWhatsappPhoneId(e.target.value)}
                                placeholder="Phone Number ID"
                                className="w-full bg-slate-950 border border-slate-700 rounded-lg px-4 py-2 text-white"
                            />
                        </div>
                        <div>
                            <label className="block text-sm text-slate-400 mb-1">Verify Token</label>
                            <input
                                type="text"
                                value={whatsappVerifyToken}
                                onChange={(e) => setWhatsappVerifyToken(e.target.value)}
                                placeholder="Webhook verify token"
                                className="w-full bg-slate-950 border border-slate-700 rounded-lg px-4 py-2 text-white"
                            />
                        </div>
                    </div>
                    <div>
                        <label className="block text-sm text-slate-400 mb-1">Access Token</label>
                        <input
                            type="password"
                            value={whatsappAccessToken}
                            onChange={(e) => setWhatsappAccessToken(e.target.value)}
                            placeholder="WhatsApp Cloud API access token"
                            className="w-full bg-slate-950 border border-slate-700 rounded-lg px-4 py-2 text-white"
                        />
                    </div>
                    <p className="text-xs text-slate-500">
                        Requires WhatsApp Business API access. <a href="https://developers.facebook.com/docs/whatsapp/cloud-api" target="_blank" rel="noreferrer" className="text-green-400 hover:underline">Learn more</a>
                    </p>

                    <button
                        onClick={handleSaveWhatsApp}
                        disabled={saving}
                        className="w-full bg-green-600 hover:bg-green-500 text-white py-2 rounded-lg font-medium disabled:opacity-50"
                    >
                        {saving ? 'Saving...' : 'Save WhatsApp Config'}
                    </button>
                </div>
            </div>

            {/* Discord */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
                <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-3">
                        <Hash className="w-5 h-5 text-indigo-400" />
                        <h3 className="text-lg font-semibold text-white">Discord Bot</h3>
                        {status?.channels.discord?.running && (
                            <span className="px-2 py-0.5 text-xs bg-emerald-500/20 text-emerald-400 rounded">Running</span>
                        )}
                    </div>
                    <label className="flex items-center gap-2 cursor-pointer">
                        <input
                            type="checkbox"
                            checked={discordEnabled}
                            onChange={(e) => setDiscordEnabled(e.target.checked)}
                            className="w-4 h-4 rounded"
                        />
                        <span className="text-sm text-slate-400">Enable</span>
                    </label>
                </div>

                <div className="space-y-4">
                    <div>
                        <label className="block text-sm text-slate-400 mb-1">Bot Token</label>
                        <div className="relative">
                            <input
                                type={showDiscordToken ? 'text' : 'password'}
                                value={discordToken}
                                onChange={(e) => setDiscordToken(e.target.value)}
                                placeholder="Enter Discord bot token"
                                className="w-full bg-slate-950 border border-slate-700 rounded-lg px-4 py-2 text-white pr-10"
                            />
                            <button
                                onClick={() => setShowDiscordToken(!showDiscordToken)}
                                className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-white"
                            >
                                {showDiscordToken ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                            </button>
                        </div>
                        <p className="text-xs text-slate-500 mt-1">
                            Get from <a href="https://discord.com/developers/applications" target="_blank" rel="noreferrer" className="text-indigo-400 hover:underline">Discord Developer Portal</a>
                        </p>
                    </div>

                    <button
                        onClick={handleSaveDiscord}
                        disabled={saving}
                        className="w-full bg-indigo-600 hover:bg-indigo-500 text-white py-2 rounded-lg font-medium disabled:opacity-50"
                    >
                        {saving ? 'Saving...' : 'Save Discord Config'}
                    </button>
                </div>
            </div>
        </div>
    );
}
