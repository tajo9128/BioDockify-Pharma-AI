import React from 'react';
import {
    Brain,
    Settings,
    Database,
    MessageSquare,
    User,
    Shield
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface SettingsSidebarProps {
    activeTab: string;
    setActiveTab: (tab: string) => void;
}

export const SettingsSidebar: React.FC<SettingsSidebarProps> = ({ activeTab, setActiveTab }) => {
    const tabs = [
        { id: 'general', label: 'General & Persona', icon: User },
        { id: 'brain', label: 'AI & Brain', icon: Brain },
        { id: 'agent', label: 'Agent Behavior', icon: Shield },
        { id: 'research', label: 'Research Tools', icon: Database },
        { id: 'channels', label: 'Channels', icon: MessageSquare },
        { id: 'system', label: 'System', icon: Settings },
    ];

    return (
        <aside className="w-64 border-r border-border bg-card/50 backdrop-blur-sm">
            <div className="p-6">
                <h2 className="text-lg font-semibold tracking-tight text-foreground/90 flex items-center gap-2">
                    <Settings className="w-5 h-5" />
                    Settings
                </h2>
                <p className="text-sm text-muted-foreground mt-1">
                    Manage your AI preferences
                </p>
            </div>
            <nav className="space-y-1 px-3">
                {tabs.map((tab) => {
                    const Icon = tab.icon;
                    const isActive = activeTab === tab.id;

                    return (
                        <button
                            key={tab.id}
                            onClick={() => setActiveTab(tab.id)}
                            className={cn(
                                "w-full flex items-center gap-3 px-3 py-2.5 text-sm font-medium rounded-md transition-colors",
                                isActive
                                    ? "bg-primary/15 text-primary"
                                    : "text-muted-foreground hover:bg-muted hover:text-foreground"
                            )}
                        >
                            <Icon className={cn("w-4 h-4", isActive ? "text-primary" : "text-muted-foreground")} />
                            {tab.label}
                        </button>
                    );
                })}
            </nav>
        </aside>
    );
};
