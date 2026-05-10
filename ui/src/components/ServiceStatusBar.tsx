/**
 * ServiceStatusBar Component
 * 
 * Displays real-time status of all services in the UI.
 * Shows: Ollama, Neo4j, Backend status with auto-recovery indicators.
 */

'use client';

import React, { useEffect, useState } from 'react';
import {
    Circle,
    RefreshCcw,
    Wifi,
    WifiOff,
    Database,
    Brain,
    Server,
    AlertTriangle,
    Check
} from 'lucide-react';
import {
    getServiceLifecycleManager,
    ServiceStatus
} from '@/lib/service-lifecycle';

interface ServiceStatusBarProps {
    compact?: boolean;
    showLabels?: boolean;
}

export default function ServiceStatusBar({ compact = false, showLabels = true }: ServiceStatusBarProps) {
    const [services, setServices] = useState<ServiceStatus[]>([]);
    const [isChecking, setIsChecking] = useState(false);

    const manager = getServiceLifecycleManager();

    useEffect(() => {
        // Initial load
        setServices(manager.getAllStatuses());

        // Subscribe to updates
        const unsubscribe = manager.subscribe((serviceMap) => {
            setServices(Array.from(serviceMap.values()));
        });

        // Initial check
        refreshServices();

        return unsubscribe;
    }, []);

    const refreshServices = async () => {
        setIsChecking(true);
        await manager.checkAllServices();
        setServices(manager.getAllStatuses());
        setIsChecking(false);
    };

    const getServiceIcon = (name: string) => {
        switch (name.toLowerCase()) {
            case 'lm studio':
            case 'ollama':
                return <Brain className="w-4 h-4 text-purple-400" />;
            case 'surfsense':
                return <Database className="w-4 h-4 text-indigo-400" />;
            case 'backend api':
                return <Server className="w-4 h-4" />;
            default:
                return <Circle className="w-4 h-4" />;
        }
    };

    const getStatusColor = (running: boolean, error?: string) => {
        if (error) return 'text-red-400';
        return running ? 'text-emerald-400' : 'text-slate-500';
    };

    const getStatusDot = (running: boolean, error?: string) => {
        if (error) return 'bg-red-400';
        return running ? 'bg-emerald-400' : 'bg-slate-600';
    };

    if (compact) {
        return (
            <div className="flex items-center space-x-2">
                {services.map((service) => (
                    <div
                        key={service.name}
                        className={`flex items-center space-x-1 ${getStatusColor(service.running, service.error)}`}
                        title={`${service.name}: ${service.running ? 'Online' : 'Offline'}`}
                    >
                        <div className={`w-2 h-2 rounded-full ${getStatusDot(service.running, service.error)}`} />
                        {showLabels && (
                            <span className="text-xs">{service.name.split(' ')[0]}</span>
                        )}
                    </div>
                ))}
                <button
                    onClick={refreshServices}
                    disabled={isChecking}
                    className="p-1 hover:bg-slate-800 rounded transition-colors"
                    title="Refresh services"
                >
                    <RefreshCcw className={`w-3 h-3 text-slate-500 ${isChecking ? 'animate-spin' : ''}`} />
                </button>
            </div>
        );
    }

    return (
        <div className="bg-slate-900/50 border border-slate-800 rounded-lg p-4">
            <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider">
                    Services
                </h3>
                <button
                    onClick={refreshServices}
                    disabled={isChecking}
                    className="flex items-center space-x-1 text-xs text-slate-500 hover:text-slate-300 transition-colors"
                >
                    <RefreshCcw className={`w-3 h-3 ${isChecking ? 'animate-spin' : ''}`} />
                    <span>Refresh</span>
                </button>
            </div>

            <div className="space-y-2">
                {services.map((service) => (
                    <div
                        key={service.name}
                        className="flex items-center justify-between p-2 bg-slate-800/50 rounded-lg"
                    >
                        <div className="flex items-center space-x-3">
                            <div className={getStatusColor(service.running, service.error)}>
                                {getServiceIcon(service.name)}
                            </div>
                            <div>
                                <span className="text-sm text-slate-300">{service.name}</span>
                                {service.error && (
                                    <p className="text-xs text-red-400">{service.error}</p>
                                )}
                            </div>
                        </div>
                        <div className="flex items-center space-x-2">
                            {service.running ? (
                                <span className="flex items-center space-x-1 text-xs text-emerald-400">
                                    <Check className="w-3 h-3" />
                                    <span>Online</span>
                                </span>
                            ) : (
                                <span className="flex items-center space-x-1 text-xs text-slate-500">
                                    <AlertTriangle className="w-3 h-3" />
                                    <span>Offline</span>
                                </span>
                            )}
                        </div>
                    </div>
                ))}
            </div>

            {/* Overall Status */}
            <div className="mt-3 pt-3 border-t border-slate-800">
                {services.every(s => s.running) ? (
                    <div className="flex items-center space-x-2 text-emerald-400">
                        <Wifi className="w-4 h-4" />
                        <span className="text-sm">All systems operational</span>
                    </div>
                ) : (
                    <div className="flex items-center space-x-2 text-amber-400">
                        <WifiOff className="w-4 h-4" />
                        <span className="text-sm">Some services unavailable</span>
                    </div>
                )}
            </div>
        </div>
    );
}
