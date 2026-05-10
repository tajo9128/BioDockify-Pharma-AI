import React, { useState } from 'react';
import { BrowserRouter as Router, Routes, Route, useNavigate, Link } from 'react-router-dom';
import apiService from './api';
import ResearchDashboard from './components/ResearchDashboard';
import StatisticsView from './views/StatisticsView';
import BackendInitializer from './components/BackendInitializer';
import FirstRunWizard from './components/FirstRunWizard';
import { Microscope, ArrowRight, BarChart, Home, Settings, Database, FileText } from 'lucide-react';

const Navigation = () => {
  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-slate-900/95 backdrop-blur-md border-b border-slate-800">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <div className="flex items-center gap-3">
            <Link to="/" className="flex items-center gap-3">
              <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
                <Microscope size={20} className="text-white" />
              </div>
              <span className="text-white font-bold text-lg">BioDockify</span>
            </Link>
          </div>

          {/* Navigation Links */}
          <div className="flex items-center gap-1">
            <Link
              to="/"
              className="flex items-center gap-2 px-4 py-2 text-sm text-slate-300 hover:text-white hover:bg-slate-800 rounded-lg transition-colors"
            >
              <Home size={18} />
              <span>Research</span>
            </Link>
            <Link
              to="/statistics"
              className="flex items-center gap-2 px-4 py-2 text-sm text-slate-300 hover:text-white hover:bg-slate-800 rounded-lg transition-colors"
            >
              <BarChart size={18} />
              <span>Statistics</span>
            </Link>
            <Link
              to="/dashboard"
              className="flex items-center gap-2 px-4 py-2 text-sm text-slate-300 hover:text-white hover:bg-slate-800 rounded-lg transition-colors"
            >
              <Database size={18} />
              <span>Data</span>
            </Link>
            <Link
              to="/settings"
              className="flex items-center gap-2 px-4 py-2 text-sm text-slate-300 hover:text-white hover:bg-slate-800 rounded-lg transition-colors"
            >
              <Settings size={18} />
              <span>Settings</span>
            </Link>
          </div>

          {/* Action Buttons */}
          <div className="flex items-center gap-2">
            <button className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-sm font-medium transition-colors">
              <FileText size={18} />
              <span>New Project</span>
            </button>
          </div>
        </div>
      </div>
    </nav>
  );
};

const LandingPage = () => {
    const [title, setTitle] = useState('');
    const [loading, setLoading] = useState(false);
    const navigate = useNavigate();

    const handleStart = async (e) => {
        e.preventDefault();
        if (!title.trim()) return;

        setLoading(true);
        try {
            const res = await apiService.startResearch(title);
            navigate(`/dashboard/${res.task_id}`);
        } catch (err) {
            console.error(err);
            alert("Failed to start research");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen bg-slate-900 flex flex-col items-center justify-center p-4 text-white pt-20">
            <div className="max-w-2xl w-full space-y-8 text-center">

                <div className="space-y-4">
                    <div className="inline-flex items-center justify-center p-4 bg-blue-500/10 rounded-full mb-4">
                        <Microscope size={48} className="text-blue-400" />
                    </div>
                    <h1 className="text-5xl font-bold bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent">
                        BioDockify AI
                    </h1>
                    <p className="text-xl text-slate-400">
                        Zero-Cost Pharmaceutical Research Platform
                    </p>
                </div>

                <div className="bg-slate-800 p-8 rounded-2xl border border-slate-700 shadow-xl">
                    <form onSubmit={handleStart} className="space-y-4">
                        <div>
                            <label className="block text-left text-sm font-medium text-slate-400 mb-2">
                                Research Topic
                            </label>
                            <input
                                type="text"
                                value={title}
                                onChange={(e) => setTitle(e.target.value)}
                                placeholder="e.g. Alzheimer's Drug Repurposing"
                                className="w-full px-4 py-3 bg-slate-900 border border-slate-700 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition"
                            />
                        </div>

                        <button
                            type="submit"
                            disabled={loading}
                            className="w-full py-4 bg-blue-600 hover:bg-blue-500 text-white rounded-xl font-bold text-lg transition flex items-center justify-center gap-2 disabled:opacity-50"
                        >
                            {loading ? 'Initializing...' : (
                                <>
                                    Start Research <ArrowRight size={20} />
                                </>
                            )}
                        </button>
                    </form>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-left text-sm text-slate-400">
                    <div className="bg-slate-800/50 p-4 rounded-lg">
                        <strong className="text-white block mb-1">Literature Analysis</strong>
                        Parses PDFs to extract biomedical entities.
                    </div>
                    <div className="bg-slate-800/50 p-4 rounded-lg">
                        <strong className="text-white block mb-1">Knowledge Graph</strong>
                        Builds connections between Drugs and Diseases.
                    </div>
                    <div className="bg-slate-800/50 p-4 rounded-lg">
                        <strong className="text-white block mb-1">Zero-Cost AI</strong>
                        Runs locally or using free tier models.
                    </div>
                </div>

                {/* Feature Highlight: Statistics */}
                <div className="bg-gradient-to-r from-cyan-900/20 to-blue-900/20 p-6 rounded-xl border border-cyan-800/30">
                    <div className="flex items-center gap-3 mb-3">
                        <BarChart className="w-6 h-6 text-cyan-400" />
                        <strong className="text-white">Comprehensive Statistics</strong>
                    </div>
                    <p className="text-sm text-slate-400 mb-3">
                        Access 25+ statistical analyses including T-Tests, ANOVA, Survival Analysis, PK/PD Analysis, and more.
                    </p>
                    <Link
                        to="/statistics"
                        className="inline-flex items-center gap-2 px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg text-sm font-medium transition-colors"
                    >
                        <BarChart size={16} />
                        <span>Explore Statistics</span>
                    </Link>
                </div>

            </div>
        </div>
    );
};

const App = () => {
    const [showWizard, setShowWizard] = useState(() => {
        return localStorage.getItem('biodockify_first_run_complete') !== 'true';
    });

    const handleWizardComplete = (settings) => {
        console.log('Setup complete with settings:', settings);
        setShowWizard(false);
    };

    return (
        <BackendInitializer>
            {showWizard && <FirstRunWizard onComplete={handleWizardComplete} />}
            <Router>
                <Navigation />
                <div className="pt-16">
                    <Routes>
                        <Route path="/" element={<LandingPage />} />
                        <Route path="/dashboard/:taskId" element={<ResearchDashboard />} />
                        <Route path="/statistics" element={<StatisticsView />} />
                        <Route path="/dashboard" element={<ResearchDashboard />} />
                        <Route path="/settings" element={<div className="p-8 pt-20"><h1 className="text-2xl font-bold text-white">Settings</h1><p className="text-slate-400 mt-2">Settings panel coming soon.</p></div>} />
                    </Routes>
                </div>
            </Router>
        </BackendInitializer>
    );
};

export default App;
