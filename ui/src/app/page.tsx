'use client';

import React, { useState, useEffect } from 'react';
import { api } from '@/lib/api';
import Sidebar from '@/components/Sidebar';
import SettingsPanel from '@/components/SettingsPanel';
import ResearchWorkstation from '@/components/ResearchWorkstation';
import KnowledgeBaseView from '@/components/KnowledgeBaseView';
import StartupChecks from '@/components/StartupChecks';
import AgentChat from '@/components/AgentChat';
import HypothesisView from '@/components/HypothesisView';
import PublicationView from '@/components/PublicationView';
import StatisticsView from '@/components/StatisticsView';
import { AcademicWriterHub } from '@/components/writers/AcademicWriterHub';
import HomeDashboard from '@/components/HomeDashboard';


import FeedbackDialog from '@/components/FeedbackDialog'; // Ensure imported if used
import { Target, Network, Activity, CheckCircle2, Brain, Clock } from 'lucide-react';
import { ErrorBoundary } from '@/components/ui/ErrorBoundary';

// Mock DiagnosisDialog removed for No-Self-Config mode

const getStepIcon = (type: string) => {
  switch (type) {
    case 'decomposition':
      return <Target className="h-4 w-4" />
    case 'tool_selection':
      return <Network className="h-4 w-4" />
    case 'execution':
      return <Activity className="h-4 w-4" />
    case 'validation':
      return <CheckCircle2 className="h-4 w-4" />
    case 'analysis':
      return <Brain className="h-4 w-4" />
    default:
      return <Clock className="h-4 w-4" />
  }
}

// --- Main Component ---
export default function PharmaceuticalResearchApp() {
  const [activeView, setActiveView] = useState<string>('home');
  // Lifted workstation mode state to allow Hub to control it
  const [workstationMode, setWorkstationMode] = useState<'search' | 'synthesize' | 'write' | 'thesis_writer' | 'review_writer' | 'research_writer'>('search');

  const [hasOnboarded, setHasOnboarded] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  // Agent State
  const [goal, setGoal] = useState('');
  const [stage, setStage] = useState('planning');
  const [taskId, setTaskId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isExecuting, setIsExecuting] = useState(false);
  const [thinkingSteps, setThinkingSteps] = useState<any[]>([]);
  const [currentTask, setCurrentTask] = useState<any | null>(null);

  // Global Dialog State
  const [isFeedbackOpen, setIsFeedbackOpen] = useState(false);
  const [diagError, setDiagError] = useState<string | null>(null);

  // Refs for cleanup (EventSource/polling)
  const eventSourceRef = React.useRef<EventSource | null>(null);
  const pollingIntervalRef = React.useRef<NodeJS.Timeout | null>(null);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      // Clean up EventSource if exists
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
      // Clean up polling interval if exists
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
        pollingIntervalRef.current = null;
      }
    };
  }, []);

  useEffect(() => {
    // Listen for global events
    const handleFeedback = () => setIsFeedbackOpen(true);

    window.addEventListener('open-feedback', handleFeedback);

    return () => {
      window.removeEventListener('open-feedback', handleFeedback);
    };
  }, []);



  const handleExecute = async () => {
    if (!goal.trim()) {
      setError("Please enter a research goal");
      return;
    }

    setIsExecuting(true);
    setError(null);
    setThinkingSteps([]);
    setCurrentTask(null);

    try {
      // 1. Start Task
      const { taskId } = await api.startResearch(goal, 'synthesize');

      setTaskId(taskId);
      setCurrentTask({
        id: taskId,
        goal,
        status: 'pending',
        progress: 0,
        createdAt: new Date().toISOString()
      });

      // 2. Poll Status
      const interval = setInterval(async () => {
        try {
          const taskStatus = await api.getStatus(taskId);

          // Update Task State
          setCurrentTask((prev: any) => prev ? { ...prev, status: taskStatus.status, progress: taskStatus.progress } : null);

          // Update Thinking Steps (Logs) - capped at last 100 to prevent state growth
          if (taskStatus.logs && taskStatus.logs.length > 0) {
            const steps = taskStatus.logs.slice(-100).map((log: string, idx: number) => {
              let type = 'info';
              let content = log;
              if (log.toLowerCase().includes('thought') || log.includes('Thinking')) type = 'thought';
              else if (log.toLowerCase().includes('action') || log.includes('Executing')) type = 'action';
              else if (log.toLowerCase().includes('result') || log.includes('Found')) type = 'result';

              return { type, content, id: `${taskId}-${idx}`, timestamp: new Date() };
            });
            setThinkingSteps(steps);
          }

          // Check Completion
          if (taskStatus.status === 'completed' || taskStatus.status === 'failed') {
            clearInterval(interval);
            setIsExecuting(false);
            if (taskStatus.status === 'failed') setError("Research task failed check logs.");
          }
        } catch (e) {
          console.error("Polling error", e);
          clearInterval(interval);
          setIsExecuting(false);
          setError("Connection lost during research task.");
        }
      }, 2000);

    } catch (e: any) {
      setError(e.message || "Failed to start research");
      setIsExecuting(false);
    }
  };

  const handleStop = async () => {
    if (!taskId) return;
    try {
      await api.cancelResearch(taskId);
      setIsExecuting(false);
      setError("Research cancelled by user.");
      // Optional: Add a log entry locally or wait for poll to update
      setThinkingSteps(prev => [...prev, { type: 'error', content: 'Process stopped by user.', id: 'cancel', timestamp: new Date() }]);
    } catch (e: any) {
      console.error("Failed to cancel", e);
    }
  };


  useEffect(() => {
    checkOnboardingStatus();
  }, []);

  const checkOnboardingStatus = async () => {
    try {
      // We now perform startup checks every session or if not marked as optimized
      // For now, let's reset hasOnboarded to false to ensure checks run
      // unless we want to skip them? User asked to "remove first run open homepage"
      // BUT "check internet, check lm studio then welcome" implies checks run.

      // So we force hasOnboarded = false initially (default)
      // Checks will run and set it to true.

      // If we want to persist "persona" we can check settings, but wizard is gone.
      const settings = await api.getSettings();
      // We don't auto-set hasOnboarded here anymore, we let StartupChecks do it.
    } catch (e) {
      console.warn("Failed to check settings:", e);
    } finally {
      setIsLoading(false);
    }
  };

  const c_settings = async (viewOrSettings: any) => {
    // Merge and save
    try {
      // Check if it's a view string (from Advanced Settings button) or settings object
      if (typeof viewOrSettings === 'string') {
        // User clicked "Open Advanced Settings"
        setHasOnboarded(true);
        setActiveView(viewOrSettings); // Navigate to the specified view
      } else {
        // Normal completion with settings object
        const current = await api.getSettings() || {};
        const updated = { ...current, ...viewOrSettings };
        await api.saveSettings(updated);
        setHasOnboarded(true);
      }
    } catch (e) {
      console.error("Failed to save wizard settings", e);
      // Allow proceed anyway for demo
      setHasOnboarded(true);
    }
  };

  if (isLoading) return <div className="min-h-screen bg-slate-950 flex items-center justify-center text-teal-500">Initializing BioDockify...</div>;

  // Render View Strategy
  const renderContent = () => {
    switch (activeView) {
      case 'settings':
        return (
          <ErrorBoundary name="Settings">
            <div className="h-full overflow-y-auto p-8">
              <SettingsPanel onClose={() => setActiveView('home')} />
            </div>
          </ErrorBoundary>
        );
      case 'surfsense':
        return (
          <ErrorBoundary name="KnowledgeBase">
            <div className="h-full overflow-hidden">
              <KnowledgeBaseView />
            </div>
          </ErrorBoundary>
        );
      case 'publication':
        return (
          <ErrorBoundary name="Publication">
            <PublicationView />
          </ErrorBoundary>
        );
      case 'statistics':
        return (
          <ErrorBoundary name="Statistics">
            <StatisticsView />
          </ErrorBoundary>
        );
      case 'hypothesis':
        return (
          <ErrorBoundary name="Hypothesis">
            <HypothesisView />
          </ErrorBoundary>
        );
      case 'agent-chat':
        return (
          <ErrorBoundary name="AgentChat">
            <div className="h-full overflow-hidden">
              {/* Import dynamically if needed but we'll import top level for now */}
              <AgentChat />
            </div>
          </ErrorBoundary>
        );
      case 'home':
        return <HomeDashboard onNavigate={setActiveView} />;
      case 'research':
        // Core Workstation
        return (
          <ErrorBoundary name="Workstation">
            <ResearchWorkstation
              view={activeView}
              goal={goal}
              onGoalChange={setGoal}
              onExecute={handleExecute}
              onStop={handleStop}
              isExecuting={isExecuting}
              thinkingSteps={thinkingSteps}
              error={error}
              mode={workstationMode}
              onModeChange={setWorkstationMode}
            />
          </ErrorBoundary>
        );
      case 'results':
      case 'lab':
      case 'autonomous':
        return (
          <div className="h-full flex items-center justify-center text-slate-500 flex-col">
            <h2 className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-teal-400 to-indigo-500 mb-2">Module Under Development</h2>
            <p>We are still calibrating the {activeView} module.</p>
          </div>
        );
      case 'writers':
        return (
          <ErrorBoundary name="WriterHub">
            <AcademicWriterHub
              onSelectMode={(mode) => {
                setWorkstationMode(mode);
                setActiveView('research'); // Navigate to Workstation
              }}
            />
          </ErrorBoundary>
        );
      default:
        // Fallback or Unknown
        return (
          <div className="h-full flex items-center justify-center text-slate-500">
            Select a module from the sidebar.
          </div>
        );
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 font-sans selection:bg-teal-500/30">

      {/* First Run Wizard / Startup Checks Overlay */}
      {!hasOnboarded && (
        <StartupChecks onComplete={() => setHasOnboarded(true)} />
      )}

      {/* Background Ambience */}
      <div className="fixed inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-slate-900 via-slate-950 to-black -z-10" />

      {/* Main Layout */}
      <div className="flex h-screen overflow-hidden">
        <Sidebar activeView={activeView} onViewChange={setActiveView} />

        <main className="flex-1 relative overflow-hidden ml-20">
          {renderContent()}
        </main>
      </div>

      {/* Global Dialogs */}
      <FeedbackDialog
        isOpen={isFeedbackOpen}
        onClose={() => setIsFeedbackOpen(false)}
      />
    </div>
  );
}
