import React, { useState, useEffect } from 'react';
import { Plus, Trash2, Save, X, ExternalLink } from 'lucide-react';

interface CustomAPI {
    name: string;
    base_url: string;
    api_key: string;
    model: string;
    description: string;
}

interface CustomAPISettingsProps {
    // Add props if needed
}

export function CustomAPISettings({}: CustomAPISettingsProps) {
    const [customAPIs, setCustomAPIs] = useState<CustomAPI[]>([]);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [editingAPI, setEditingAPI] = useState<CustomAPI | null>(null);
    const [showForm, setShowForm] = useState(false);

    useEffect(() => {
        loadCustomAPIs();
    }, []);

    const loadCustomAPIs = async () => {
        try {
            const res = await fetch('/settings/custom-apis');
            const data = await res.json();
            setCustomAPIs(data.custom_apis || []);
        } catch (e) {
            console.error('Failed to load custom APIs:', e);
        } finally {
            setLoading(false);
        }
    };

    const handleSave = async () => {
        if (!editingAPI) return;
        setSaving(true);
        try {
            const res = await fetch('/settings/custom-apis', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(editingAPI)
            });
            const data = await res.json();
            setCustomAPIs(data.custom_apis || []);
            setShowForm(false);
            setEditingAPI(null);
        } catch (e) {
            console.error('Failed to save custom API:', e);
        } finally {
            setSaving(false);
        }
    };

    const handleDelete = async (name: string) => {
        if (!confirm(`Delete "${name}"?`)) return;
        try {
            const res = await fetch(`/settings/custom-apis/${encodeURIComponent(name)}`, {
                method: 'DELETE'
            });
            const data = await res.json();
            setCustomAPIs(data.custom_apis || []);
        } catch (e) {
            console.error('Failed to delete custom API:', e);
        }
    };

    const handleTest = async (api: CustomAPI) => {
        if (!api.base_url || !api.api_key) return;
        
        try {
            const res = await fetch(`${api.base_url}/models`, {
                headers: { 'Authorization': `Bearer ${api.api_key}` }
            });
            if (res.ok) {
                alert('Connection successful!');
            } else {
                alert(`Connection failed: ${res.status}`);
            }
        } catch (e) {
            alert(`Connection error: ${e}`);
        }
    };

    return (
        <div className="p-6 space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h3 className="text-lg font-semibold text-slate-200">Custom APIs</h3>
                    <p className="text-sm text-slate-400">
                        Add your own API endpoints (OpenAI-compatible)
                    </p>
                </div>
                <button
                    onClick={() => {
                        setEditingAPI({
                            name: '',
                            base_url: '',
                            api_key: '',
                            model: '',
                            description: ''
                        });
                        setShowForm(true);
                    }}
                    className="flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 rounded-lg text-white text-sm font-medium transition-colors"
                >
                    <Plus className="h-4 w-4" />
                    Add API
                </button>
            </div>

            {/* Custom API Form */}
            {showForm && editingAPI && (
                <div className="bg-slate-800 rounded-xl p-6 space-y-4">
                    <h4 className="font-medium text-slate-200">
                        {customAPIs.find(a => a.name === editingAPI.name) ? 'Edit' : 'New'} Custom API
                    </h4>
                    
                    <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-2">
                            <label className="text-sm text-slate-400">Name</label>
                            <input
                                type="text"
                                value={editingAPI.name}
                                onChange={e => setEditingAPI({...editingAPI, name: e.target.value})}
                                placeholder="My API"
                                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2 text-slate-200"
                            />
                        </div>
                        <div className="space-y-2">
                            <label className="text-sm text-slate-400">Model</label>
                            <input
                                type="text"
                                value={editingAPI.model}
                                onChange={e => setEditingAPI({...editingAPI, model: e.target.value})}
                                placeholder="gpt-4"
                                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2 text-slate-200"
                            />
                        </div>
                    </div>
                    
                    <div className="space-y-2">
                        <label className="text-sm text-slate-400">Base URL</label>
                        <input
                            type="text"
                            value={editingAPI.base_url}
                            onChange={e => setEditingAPI({...editingAPI, base_url: e.target.value})}
                            placeholder="https://api.example.com/v1"
                            className="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2 text-slate-200"
                        />
                    </div>
                    
                    <div className="space-y-2">
                        <label className="text-sm text-slate-400">API Key</label>
                        <input
                            type="password"
                            value={editingAPI.api_key}
                            onChange={e => setEditingAPI({...editingAPI, api_key: e.target.value})}
                            placeholder="sk-..."
                            className="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2 text-slate-200"
                        />
                    </div>
                    
                    <div className="space-y-2">
                        <label className="text-sm text-slate-400">Description (optional)</label>
                        <input
                            type="text"
                            value={editingAPI.description}
                            onChange={e => setEditingAPI({...editingAPI, description: e.target.value})}
                            placeholder="My custom model API"
                            className="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2 text-slate-200"
                        />
                    </div>
                    
                    <div className="flex gap-2">
                        <button
                            onClick={handleSave}
                            disabled={saving || !editingAPI.name || !editingAPI.base_url}
                            className="flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 rounded-lg text-white text-sm font-medium transition-colors"
                        >
                            <Save className="h-4 w-4" />
                            {saving ? 'Saving...' : 'Save'}
                        </button>
                        <button
                            onClick={() => {
                                setShowForm(false);
                                setEditingAPI(null);
                            }}
                            className="flex items-center gap-2 px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg text-white text-sm font-medium transition-colors"
                        >
                            <X className="h-4 w-4" />
                            Cancel
                        </button>
                    </div>
                </div>
            )}

            {/* Custom APIs List */}
            {loading ? (
                <div className="text-slate-400">Loading...</div>
            ) : customAPIs.length === 0 ? (
                <div className="text-slate-400 text-center py-8">
                    No custom APIs configured yet.
                    <br />
                    Click "Add API" to add your own API endpoint.
                </div>
            ) : (
                <div className="space-y-3">
                    {customAPIs.map((api) => (
                        <div
                            key={api.name}
                            className="bg-slate-800 rounded-xl p-4 flex items-center justify-between"
                        >
                            <div className="flex-1">
                                <div className="flex items-center gap-3">
                                    <span className="font-medium text-slate-200">{api.name}</span>
                                    <span className="text-xs text-slate-500 bg-slate-900 px-2 py-0.5 rounded">
                                        {api.model}
                                    </span>
                                </div>
                                <div className="text-sm text-slate-400 flex items-center gap-2 mt-1">
                                    <ExternalLink className="h-3 w-3" />
                                    {api.base_url}
                                </div>
                                {api.description && (
                                    <div className="text-xs text-slate-500 mt-1">
                                        {api.description}
                                    </div>
                                )}
                            </div>
                            <div className="flex items-center gap-2">
                                <button
                                    onClick={() => handleTest(api)}
                                    className="px-3 py-1.5 text-xs bg-slate-700 hover:bg-slate-600 rounded-lg text-slate-200 transition-colors"
                                    title="Test connection"
                                >
                                    Test
                                </button>
                                <button
                                    onClick={() => {
                                        setEditingAPI(api);
                                        setShowForm(true);
                                    }}
                                    className="p-1.5 text-slate-400 hover:text-slate-200 hover:bg-slate-700 rounded-lg transition-colors"
                                >
                                    Edit
                                </button>
                                <button
                                    onClick={() => handleDelete(api.name)}
                                    className="p-1.5 text-red-400 hover:text-red-300 hover:bg-slate-700 rounded-lg transition-colors"
                                >
                                    <Trash2 className="h-4 w-4" />
                                </button>
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {/* Help */}
            <div className="bg-slate-800/50 rounded-xl p-4 text-sm text-slate-400">
                <h4 className="font-medium text-slate-300 mb-2">How to use custom APIs:</h4>
                <ul className="space-y-1 text-slate-500">
                    <li>1. Use an OpenAI-compatible API endpoint</li>
                    <li>2. Enter your Base URL (e.g., https://api.myservice.com/v1)</li>
                    <li>3. Enter your API key</li>
                    <li>4. Specify the model name</li>
                    <li>5. Use "custom" provider and select your API in chat</li>
                </ul>
            </div>
        </div>
    );
}

export default CustomAPISettings;