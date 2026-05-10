'use client';

import { cn } from '@/lib/utils';

interface StatsCardProps {
  title: string;
  value: number | string;
  icon?: React.ReactNode;
  description?: string;
  trend?: {
    value: string;
    positive?: boolean;
  };
  className?: string;
  gradient?: 'blue' | 'purple' | 'cyan' | 'teal';
}

export default function StatsCard({
  title,
  value,
  icon,
  description,
  trend,
  className,
  gradient = 'blue',
}: StatsCardProps) {
  const getGradientClasses = () => {
    switch (gradient) {
      case 'cyan':
        return 'from-[#5B9FF0]/10 to-[#5B9FF0]/5 border-[#5B9FF0]/20';
      case 'purple':
        return 'from-[#8B7CFD]/10 to-[#8B7CFD]/5 border-[#8B7CFD]/20';
      case 'teal':
        return 'from-[#00D4AA]/10 to-[#00D4AA]/5 border-[#00D4AA]/20';
      default:
        return 'from-[#4A90E2]/10 to-[#4A90E2]/5 border-[#4A90E2]/20';
    }
  };

  return (
    <div
      className={cn(
        'glass-card relative overflow-hidden group',
        'transition-all duration-300',
        'hover:scale-[1.02] hover:shadow-2xl',
        className
      )}
    >
      {/* Gradient Background */}
      <div
        className={cn(
          'absolute inset-0 bg-gradient-to-br opacity-50 transition-opacity duration-300',
          getGradientClasses()
        )}
      />

      {/* Glow Effect */}
      <div
        className={cn(
          'absolute -top-20 -right-20 w-40 h-40 rounded-full blur-3xl opacity-10 group-hover:opacity-20 transition-opacity duration-300',
          gradient === 'cyan' && 'bg-[#5B9FF0]',
          gradient === 'purple' && 'bg-[#8B7CFD]',
          gradient === 'teal' && 'bg-[#00D4AA]',
          gradient === 'blue' && 'bg-[#4A90E2]'
        )}
      />

      <div className="relative p-6">
        <div className="flex items-start justify-between mb-4">
          {/* Title */}
          <h3 className="text-sm font-semibold text-gray-400 tracking-wide uppercase">
            {title}
          </h3>

          {/* Icon */}
          {icon && (
            <div className="w-10 h-10 rounded-xl bg-white/5 flex items-center justify-center border border-white/10 group-hover:bg-white/10 transition-colors">
              {icon}
            </div>
          )}
        </div>

        {/* Value */}
        <div className="flex items-baseline gap-3 mb-2">
          <span className="text-4xl font-bold text-white tracking-tight">
            {value}
          </span>
          {trend && (
            <span
              className={cn(
                'text-sm font-semibold px-2 py-1 rounded-lg',
                trend.positive
                  ? 'bg-[#00D4AA]/10 text-[#00D4AA]'
                  : 'bg-[#FC8181]/10 text-[#FC8181]'
              )}
            >
              {trend.value}
            </span>
          )}
        </div>

        {/* Description */}
        {description && (
          <p className="text-sm text-gray-500 font-medium">{description}</p>
        )}
      </div>
    </div>
  );
}
