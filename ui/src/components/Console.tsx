'use client';

import { useEffect, useRef } from 'react';
import { Terminal, Code2, Activity } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface ConsoleLog {
  id: string;
  timestamp: string;
  message: string;
  type?: 'info' | 'success' | 'error' | 'phase';
}

interface ConsoleProps {
  logs: ConsoleLog[];
  title?: string;
}

export default function Console({ logs, title = 'Console Output' }: ConsoleProps) {
  const consoleEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    consoleEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  const getLogStyle = (type: ConsoleLog['type']) => {
    switch (type) {
      case 'phase':
        return {
          bg: 'bg-[#5B9FF0]/10',
          text: 'text-[#5B9FF0]',
          border: 'border-[#5B9FF0]/20',
          icon: <Terminal className="w-4 h-4" />
        };
      case 'success':
        return {
          bg: 'bg-[#00D4AA]/10',
          text: 'text-[#00D4AA]',
          border: 'border-[#00D4AA]/20',
          icon: <Activity className="w-4 h-4" />
        };
      case 'error':
        return {
          bg: 'bg-[#FC8181]/10',
          text: 'text-[#FC8181]',
          border: 'border-[#FC8181]/20',
          icon: <Terminal className="w-4 h-4" />
        };
      default:
        return {
          bg: 'bg-white/5',
          text: 'text-gray-300',
          border: 'border-white/5',
          icon: <Code2 className="w-4 h-4" />
        };
    }
  };

  return (
    <div className="glass-card overflow-hidden">
      {/* Modern Header */}
      <div className="bg-gradient-to-r from-[#1A1D24] to-[#14161B] px-6 py-4 flex items-center justify-between border-b border-white/5">
        <div className="flex items-center gap-3">
          <div className="flex gap-2">
            <div className="w-3 h-3 rounded-full bg-[#5B9FF0]" />
            <div className="w-3 h-3 rounded-full bg-[#F6AD55]" />
            <div className="w-3 h-3 rounded-full bg-[#00D4AA]" />
          </div>
          <span className="ml-3 text-sm text-gray-400 font-medium tracking-wide">
            {title}
          </span>
        </div>
        <div className="flex items-center gap-2 text-xs text-gray-500 font-mono">
          <span>{logs.length}</span>
          <span>logs</span>
        </div>
      </div>

      {/* Console Content */}
      <div className="p-6 font-mono text-sm h-96 overflow-y-auto">
        {logs.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-gray-500">
            <Terminal className="w-12 h-12 mb-3 opacity-30" />
            <p className="text-sm">Waiting for output...</p>
          </div>
        ) : (
          <div className="space-y-2">
            {logs.map((log) => {
              const style = getLogStyle(log.type);
              return (
                <div
                  key={log.id}
                  className={cn(
                    'flex items-start gap-3 p-3 rounded-xl border transition-all duration-200',
                    style.bg,
                    style.border
                  )}
                >
                  <div className={cn('mt-0.5 shrink-0', style.text)}>
                    {style.icon}
                  </div>
                  <div className="flex-1 min-w-0">
                    <span className="text-gray-600 mr-3 text-xs font-mono">
                      [{log.timestamp}]
                    </span>
                    <span className={cn('text-sm leading-relaxed', style.text)}>
                      {log.message}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        )}
        <div ref={consoleEndRef} />
      </div>
    </div>
  );
}
