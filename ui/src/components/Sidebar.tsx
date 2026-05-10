'use client';

import React from 'react';
import { Home, FlaskConical, FileText, Beaker, Settings, Sparkles, BookOpen, Fingerprint, Globe, Lightbulb, Brain, Hammer, Printer, Calculator, ShieldCheck, PenTool, Bot } from 'lucide-react';
import { cn } from '@/lib/utils';
import Image from 'next/image';
import FeedbackDialog from './FeedbackDialog';

interface SidebarProps {
  activeView: string;
  onViewChange: (view: string) => void;
}

export default function Sidebar({ activeView, onViewChange }: SidebarProps) {
  const [showFeedback, setShowFeedback] = React.useState(false);

  /* New Sidebar Organization */
  const mainNav = [
    { id: 'home', icon: Home, label: 'Home' },
    { id: 'agent-chat', icon: Bot, label: 'Chat' },
    { id: 'research', icon: FlaskConical, label: 'Research' },
    { id: 'writers', icon: PenTool, label: 'Academic Suite' },
    { id: 'results', icon: FileText, label: 'Results' },
    { id: 'statistics', icon: Calculator, label: 'Statistics' },
  ];

  /* Tools & System moved to bottom or specific sections */
  const bottomNav = [
    { id: 'surfsense', icon: Brain, label: 'Knowledge Base' },    // Base
    { id: 'settings', icon: Settings, label: 'Settings' },        // System
  ];

  const NavItem = ({ item, isBottom = false }: { item: any, isBottom?: boolean }) => {
    const Icon = item.icon;
    const isActive = activeView === item.id;
    // License check removed - Free for everyone
    const isLocked = false;

    return (
      <div className="relative group">
        <button
          onClick={() => onViewChange(item.id)}
          className={cn(
            "w-10 h-10 rounded-xl flex items-center justify-center transition-all duration-300 relative",
            isActive
              ? "bg-teal-500/20 text-teal-400 shadow-[0_0_15px_-5px_rgba(20,184,166,0.3)]"
              : "text-slate-400 hover:text-slate-200 hover:bg-white/5"
          )}
        >
          <Icon className={cn("w-5 h-5", isActive && "animate-pulse-soft")} strokeWidth={isActive ? 2.5 : 2} />
        </button>
        <div className="absolute left-full top-1/2 -translate-y-1/2 ml-4 px-3 py-1.5 glass-panel rounded-lg text-xs font-semibold text-slate-200 opacity-0 -translate-x-2 group-hover:opacity-100 group-hover:translate-x-0 transition-all pointer-events-none whitespace-nowrap border border-white/10 shadow-xl z-50">
          {item.label}
        </div>
      </div>
    );
  };

  return (
    <>
      <aside className="fixed left-0 top-0 bottom-0 z-40 flex flex-col w-20 glass-panel border-r border-white/5 shadow-2xl items-center py-6 backdrop-blur-xl bg-slate-950/80">

        {/* Brand Logo */}
        <div className="mb-8 w-10 h-10 relative group cursor-default">
          <Image src="/logo.png" alt="BioDockify" width={40} height={40} className="w-full h-full drop-shadow-lg group-hover:drop-shadow-[0_0_15px_rgba(0,212,170,0.5)] transition-all rounded-xl" />
        </div>

        {/* Main Navigation */}
        <nav className="flex flex-col gap-3 w-full items-center">
          {mainNav.map((item) => <NavItem key={item.id} item={item} />)}
        </nav>

        {/* Spacer */}
        <div className="flex-1" />

        {/* Bottom Navigation */}
        <nav className="flex flex-col gap-3 w-full items-center mb-4 border-t border-white/5 pt-4">
          {bottomNav.map((item) => <NavItem key={item.id} item={item} isBottom />)}
        </nav>

        {/* Feedback Button */}
        <button
          onClick={() => setShowFeedback(true)}
          className="mt-2 text-slate-500 hover:text-teal-400 transition-colors p-2 rounded-lg hover:bg-white/5 group relative"
        >
          <Lightbulb className="w-5 h-5" />
          <div className="absolute left-full top-1/2 -translate-y-1/2 ml-4 px-3 py-1.5 glass-panel rounded-lg text-xs font-semibold text-slate-200 opacity-0 -translate-x-2 group-hover:opacity-100 group-hover:translate-x-0 transition-all pointer-events-none whitespace-nowrap border border-white/10 shadow-xl z-50">
            Provide Feedback
          </div>
        </button>

      </aside>

      <FeedbackDialog isOpen={showFeedback} onClose={() => setShowFeedback(false)} />
    </>
  );
}
