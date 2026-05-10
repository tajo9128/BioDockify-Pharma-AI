'use client';

import { CheckCircle2, Clock, XCircle, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';

type Status = 'pending' | 'running' | 'completed' | 'failed';

interface StatusBadgeProps {
  status: Status;
  label?: string;
  size?: 'sm' | 'md' | 'lg';
}

export default function StatusBadge({ status, label, size = 'md' }: StatusBadgeProps) {
  const getSizeClasses = () => {
    switch (size) {
      case 'sm': return 'px-2.5 py-0.5 text-[10px] gap-1';
      case 'lg': return 'px-4 py-1.5 text-sm gap-2';
      default: return 'px-3 py-1 text-xs gap-1.5';
    }
  };

  const getConfig = (s: Status) => {
    switch (s) {
      case 'pending':
        return { style: 'bg-slate-500/10 text-slate-400 border-slate-500/20', icon: Clock, label: 'Pending' };
      case 'running':
        return { style: 'bg-indigo-500/10 text-indigo-400 border-indigo-500/30 animate-pulse-soft', icon: Loader2, label: 'Running', spin: true };
      case 'completed':
        return { style: 'bg-teal-500/10 text-teal-400 border-teal-500/30', icon: CheckCircle2, label: 'Completed' };
      case 'failed':
        return { style: 'bg-red-500/10 text-red-400 border-red-500/30', icon: XCircle, label: 'Failed' };
      default:
        return { style: 'bg-slate-500/10 text-slate-400', icon: Clock, label: 'Unknown' };
    }
  };

  const { style, icon: Icon, label: defaultLabel, spin } = getConfig(status);

  return (
    <div className={cn(
      'inline-flex items-center rounded-full border font-medium uppercase tracking-wider shadow-sm backdrop-blur-sm',
      getSizeClasses(),
      style
    )}>
      <Icon className={cn("w-3 h-3", spin && "animate-spin")} />
      <span>{label || defaultLabel}</span>
    </div>
  );
}
