'use client';

import { Check, Circle } from 'lucide-react';
import { cn } from '@/lib/utils';

type StepState = 'pending' | 'active' | 'completed';

interface ProgressStepProps {
  step: number;
  currentStep: number;
  totalSteps: number;
  label: string;
  isLast?: boolean;
}

export default function ProgressStep({
  step,
  currentStep,
  totalSteps,
  label,
  isLast = false,
}: ProgressStepProps) {
  const getState = (): StepState => {
    if (step < currentStep) return 'completed';
    if (step === currentStep) return 'active';
    return 'pending';
  };

  const state = getState();

  const getCircleStyle = () => {
    switch (state) {
      case 'completed':
        return {
          bg: 'bg-gradient-to-br from-[#00D4AA] to-[#5B9FF0]',
          border: 'border-[#00D4AA]/50',
          shadow: 'shadow-[0_0_20px_rgba(0,212,170,0.5)]',
          icon: <Check className="w-5 h-5 text-white" />,
        };
      case 'active':
        return {
          bg: 'bg-gradient-to-br from-[#5B9FF0] to-[#8B7CFD]',
          border: 'border-[#5B9FF0]/50',
          shadow: 'shadow-[0_0_25px_rgba(91,159,240,0.6)]',
          icon: <span className="text-white font-bold">{step}</span>,
        };
      default:
        return {
          bg: 'bg-gray-800/50',
          border: 'border-gray-700/50',
          shadow: '',
          icon: <Circle className="w-4 h-4 text-gray-600" />,
        };
    }
  };

  const getTextColor = () => {
    switch (state) {
      case 'completed':
        return 'text-[#00D4AA]';
      case 'active':
        return 'text-[#5B9FF0]';
      default:
        return 'text-gray-500';
    }
  };

  const circleStyle = getCircleStyle();

  return (
    <div className="flex items-center flex-1 relative">
      {/* Progress Circle */}
      <div className="flex flex-col items-center z-10">
        <div
          className={cn(
            'w-14 h-14 rounded-2xl border-2 flex items-center justify-center font-semibold transition-all duration-500',
            circleStyle.bg,
            circleStyle.border,
            circleStyle.shadow
          )}
        >
          {circleStyle.icon}
        </div>

        {/* Label */}
        <span className={cn(
          'text-sm mt-3 font-semibold tracking-wide transition-all duration-300',
          getTextColor()
        )}>
          {label}
        </span>
      </div>

      {/* Connecting Line */}
      {!isLast && (
        <div className="flex-1 h-1 mx-4 bg-gradient-to-r from-gray-700/50 to-gray-700/30 relative overflow-hidden rounded-full">
          {step < currentStep && (
            <div
              className="absolute inset-0 bg-gradient-to-r from-[#00D4AA] via-[#8B7CFD] to-[#5B9FF0] h-full transition-all duration-700 ease-out rounded-full"
              style={{
                width: '100%',
              }}
            />
          )}
          {step === currentStep && (
            <div
              className="absolute inset-0 bg-gradient-to-r from-[#5B9FF0] to-[#8B7CFD] h-full transition-all duration-700 ease-out rounded-full animate-pulse"
              style={{
                width: '50%',
              }}
            />
          )}
        </div>
      )}
    </div>
  );
}
