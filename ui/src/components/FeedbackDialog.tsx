import React, { useState } from 'react';
import { X, Send, MessageSquare } from 'lucide-react';

interface FeedbackDialogProps {
    isOpen: boolean;
    onClose: () => void;
}

export default function FeedbackDialog({ isOpen, onClose }: FeedbackDialogProps) {
    const [formData, setFormData] = useState({
        name: '',
        email: '',
        subject: '',
        message: ''
    });
    const [isSending, setIsSending] = useState(false);
    const [sent, setSent] = useState(false);

    if (!isOpen) return null;

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setIsSending(true);

        // Simulate API call
        await new Promise(resolve => setTimeout(resolve, 1500));

        setSent(true);
        setIsSending(false);

        setTimeout(() => {
            onClose();
            setSent(false);
            setFormData({ name: '', email: '', subject: '', message: '' });
        }, 2000);
    };

    return (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/50 backdrop-blur-sm animate-in fade-in duration-200">
            <div className="w-full max-w-md bg-slate-950 border border-slate-800 rounded-2xl shadow-2xl overflow-hidden animate-in slide-in-from-bottom-4 zoom-in-95 duration-300">

                {/* Header */}
                <div className="flex items-center justify-between p-4 border-b border-slate-800 bg-slate-900/50">
                    <h3 className="text-lg font-bold text-white flex items-center gap-2">
                        <MessageSquare className="w-5 h-5 text-teal-400" />
                        Contact Support
                    </h3>
                    <button onClick={onClose} className="text-slate-500 hover:text-white transition-colors">
                        <X className="w-5 h-5" />
                    </button>
                </div>

                {/* Content */}
                <div className="p-6">
                    {sent ? (
                        <div className="text-center py-8 space-y-4">
                            <div className="w-16 h-16 bg-teal-500/10 rounded-full flex items-center justify-center mx-auto">
                                <Send className="w-8 h-8 text-teal-400" />
                            </div>
                            <h4 className="text-xl font-bold text-white">Message Sent!</h4>
                            <p className="text-slate-400">Thank you for your feedback. We&apos;ll get back to you shortly.</p>
                        </div>
                    ) : (
                        <form onSubmit={handleSubmit} className="space-y-4">
                            <div className="grid grid-cols-2 gap-4">
                                <div className="space-y-1">
                                    <label className="text-xs font-bold text-slate-500 uppercase">Name</label>
                                    <input
                                        required
                                        value={formData.name}
                                        onChange={e => setFormData({ ...formData, name: e.target.value })}
                                        className="w-full bg-slate-900 border border-slate-800 rounded-lg px-3 py-2 text-sm text-white focus:ring-1 focus:ring-teal-500 outline-none"
                                        placeholder="Dr. Smith"
                                    />
                                </div>
                                <div className="space-y-1">
                                    <label className="text-xs font-bold text-slate-500 uppercase">Email</label>
                                    <input
                                        required
                                        type="email"
                                        value={formData.email}
                                        onChange={e => setFormData({ ...formData, email: e.target.value })}
                                        className="w-full bg-slate-900 border border-slate-800 rounded-lg px-3 py-2 text-sm text-white focus:ring-1 focus:ring-teal-500 outline-none"
                                        placeholder="name@lab.com"
                                    />
                                </div>
                            </div>

                            <div className="space-y-1">
                                <label className="text-xs font-bold text-slate-500 uppercase">Subject</label>
                                <select
                                    value={formData.subject}
                                    onChange={e => setFormData({ ...formData, subject: e.target.value })}
                                    className="w-full bg-slate-900 border border-slate-800 rounded-lg px-3 py-2 text-sm text-white focus:ring-1 focus:ring-teal-500 outline-none"
                                >
                                    <option value="">Select a topic...</option>
                                    <option value="bug">Report a Bug</option>
                                    <option value="feature">Feature Request</option>
                                    <option value="billing">Billing/License</option>
                                    <option value="other">Other</option>
                                </select>
                            </div>

                            <div className="space-y-1">
                                <label className="text-xs font-bold text-slate-500 uppercase">Message</label>
                                <textarea
                                    required
                                    value={formData.message}
                                    onChange={e => setFormData({ ...formData, message: e.target.value })}
                                    className="w-full h-32 bg-slate-900 border border-slate-800 rounded-lg px-3 py-2 text-sm text-white focus:ring-1 focus:ring-teal-500 outline-none resize-none"
                                    placeholder="How can we help you?"
                                />
                            </div>

                            <button
                                type="submit"
                                disabled={isSending}
                                className="w-full bg-teal-600 hover:bg-teal-500 text-white font-bold py-3 rounded-lg flex items-center justify-center space-x-2 transition-all shadow-lg shadow-teal-900/20 disabled:opacity-50"
                            >
                                {isSending ? (
                                    <span className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                                ) : (
                                    <>
                                        <span>Send Message</span>
                                        <Send className="w-4 h-4" />
                                    </>
                                )}
                            </button>
                        </form>
                    )}
                </div>
            </div>
        </div>
    );
}
