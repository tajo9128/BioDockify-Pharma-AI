
import React from 'react';
import { cn } from '@/lib/utils';
import { motion, HTMLMotionProps } from 'framer-motion';

interface GlassCardProps extends HTMLMotionProps<"div"> {
    children: React.ReactNode;
    variant?: 'default' | 'thin' | 'glow';
    className?: string;
    noPadding?: boolean;
}

export const GlassCard = React.forwardRef<HTMLDivElement, GlassCardProps>(
    ({ children, variant = 'default', className, noPadding = false, ...props }, ref) => {

        const variants = {
            default: "bg-white/5 border border-white/10 backdrop-blur-xl shadow-xl",
            thin: "bg-white/[0.02] border border-white/5 backdrop-blur-lg",
            glow: "bg-white/5 border border-teal-500/30 shadow-[0_0_15px_-3px_rgba(20,184,166,0.2)] backdrop-blur-xl"
        };

        return (
            <motion.div
                ref={ref}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3 }}
                className={cn(
                    "rounded-2xl overflow-hidden transition-all duration-300",
                    variants[variant],
                    noPadding ? "" : "p-6",
                    className
                )}
                {...props}
            >
                {children}
            </motion.div>
        );
    }
);

GlassCard.displayName = "GlassCard";
