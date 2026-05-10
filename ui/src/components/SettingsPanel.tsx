import React, { useState } from 'react';
import { SettingsLayout } from './settings/SettingsLayout';
import { ModelIntelligenceSettings } from './settings/ModelIntelligenceSettings';
import BioDockifyLiteSettings from './settings/BioDockifyLiteSettings';
import { SystemSettings } from './settings/SystemSettings';
import { CustomAPISettings } from './settings/CustomAPISettings';
import { BrainSettings } from './settings/BrainSettings';
import { GeneralSettings } from './settings/GeneralSettings';
import { ResearchSettings } from './settings/ResearchSettings';
import { useSettings } from '../hooks/useSettings';
import { Settings } from '../lib/api';

interface SettingsPanelProps {
    onClose?: () => void;
}

export default function SettingsPanel({ onClose }: SettingsPanelProps) {
    const [activeTab, setActiveTab] = useState('models');
    const { settings, updateSettings } = useSettings();

    const handleReset = () => {
        console.log("Reset requested - not implemented");
    };

    const handleModelUpdate = (newSettings: Settings) => {
        if (newSettings.ai_provider) {
            updateSettings('ai_provider', newSettings.ai_provider);
        }
    };

    const handleSettingChange = (section: keyof Settings, value: any) => {
        updateSettings(section, value);
    };

    return (
        <div className="fixed inset-0 bg-slate-950 z-50 flex flex-col h-screen w-screen overflow-hidden">
            <SettingsLayout activeTab={activeTab} setActiveTab={setActiveTab} onClose={onClose}>
                {activeTab === 'models' && (
                    <ModelIntelligenceSettings
                        settings={settings as Settings}
                        onUpdate={handleModelUpdate}
                    />
                )}
                {activeTab === 'agent0' && (
                    <BioDockifyLiteSettings />
                )}
                {activeTab === 'custom_api' && <CustomAPISettings />}
                {activeTab === 'biodockify' && (
                    <GeneralSettings
                        settings={settings as Settings}
                        onSettingChange={handleSettingChange}
                    />
                )}
                {activeTab === 'system' && (
                    <SystemSettings
                        settings={settings as Settings}
                        onSettingChange={handleSettingChange}
                        onReset={handleReset}
                    />
                )}
                {activeTab === 'diagnostics' && (
                    <BrainSettings
                        settings={settings as Settings}
                        onSettingChange={handleSettingChange}
                    />
                )}
            </SettingsLayout>
        </div>
    );
}
