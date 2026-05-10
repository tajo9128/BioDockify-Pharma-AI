
import React from 'react';
import { cn } from '@/lib/utils';
import { motion, HTMLMotionProps } from 'framer-motion';
import { Loader2 } from 'lucide-react';

interface NeonButtonProps extends HTMLMotionProps<"button"> {
    variant?: 'primary' | 'secondary' | 'danger' | 'ghost';
    size?: 'sm' | 'md' | 'lg';
    isLoading?: boolean;
    icon?: React.ReactNode;
    children: React.ReactNode;
}

export const NeonButton = React.forwardRef<HTMLButtonElement, NeonButtonProps>(
    ({ className, variant = 'primary', size = 'md', isLoading, icon, children, disabled, ...props }, ref) => {

        const variants = {
            primary: "bg-teal-500/10 text-teal-400 border border-teal-500/50 hover:bg-teal-500/20 hover:border-teal-400 hover:shadow-[0_0_20px_-5px_rgba(20,184,166,0.4)]",
            secondary: "bg-slate-800/40 text-slate-300 border border-slate-700 hover:bg-slate-700/60 hover:text-white hover:border-slate-500",
            danger: "bg-red-500/10 text-red-400 border border-red-500/50 hover:bg-red-500/20 hover:border-red-400 hover:shadow-[0_0_20px_-5px_rgba(239,68,68,0.4)]",
            ghost: "bg-transparent text-slate-400 hover:text-white hover:bg-white/5 border-transparent"
        };

        const sizes = {
            sm: "px-3 py-1.5 text-xs rounded-lg gap-1.5",
            md: "px-5 py-2.5 text-sm rounded-xl gap-2",
            lg: "px-8 py-4 text-base rounded-2xl gap-3"
        };

        return (
            <motion.button
                ref={ref}
                whileHover={{ scale: disabled ? 1 : 1.02 }}
                whileTap={{ scale: disabled ? 1 : 0.98 }}
                className={cn(
                    "inline-flex items-center justify-center font-medium transition-colors outline-none focus:ring-2 focus:ring-teal-500/20 disabled:opacity-50 disabled:cursor-not-allowed",
                    variants[variant],
                    sizes[size],
                    className
                )}
                disabled={disabled || isLoading}
                {...(props as any)}
            >
                {isLoading ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                ) : icon ? (
                    <span className="flex-shrink-0">{icon}</span>
                ) : null}

                <span>{children}</span>
            </motion.button>
        );
    }
);

NeonButton.displayName = "NeonButton";
