import React from 'react';
import { Search, ChevronDown, ChevronRight, Zap, Activity, HeartPulse, FlaskConical, Beaker, Layers, Filter, Grid3x3 } from 'lucide-react';
import analysisDefinitions from '@/lib/statistics/analysis-definitions';

const categoryIcons = {
  basic: Zap,
  survival: HeartPulse,
  bioequivalence: FlaskConical,
  advanced: Beaker,
  pkpd: Activity,
  multiplicity: Filter,
  categorical: Grid3x3
};

const categoryColors = {
  basic: 'text-blue-400 border-blue-900 bg-blue-950/30',
  survival: 'text-red-400 border-red-900 bg-red-950/30',
  bioequivalence: 'text-purple-400 border-purple-900 bg-purple-950/30',
  advanced: 'text-cyan-400 border-cyan-900 bg-cyan-950/30',
  pkpd: 'text-emerald-400 border-emerald-900 bg-emerald-950/30',
  multiplicity: 'text-orange-400 border-orange-900 bg-orange-950/30',
  categorical: 'text-pink-400 border-pink-900 bg-pink-950/30'
};

export default function AnalysisSelector({ selectedAnalysis, onSelect, searchQuery, onSearchChange }) {
  const [expandedCategories, setExpandedCategories] = React.useState({
    basic: true,
    survival: true,
    bioequivalence: true,
    advanced: true,
    pkpd: true,
    multiplicity: true,
    categorical: true
  });

  const toggleCategory = (category) => {
    setExpandedCategories(prev => ({
      ...prev,
      [category]: !prev[category]
    }));
  };

  const filteredAnalyses = React.useMemo(() => {
    if (!searchQuery) return analysisDefinitions;
    const query = searchQuery.toLowerCase();
    return analysisDefinitions.map(cat => ({
      ...cat,
      analyses: cat.analyses.filter(analysis => 
        analysis.name.toLowerCase().includes(query) ||
        analysis.description.toLowerCase().includes(query) ||
        analysis.examples.some(example => example.toLowerCase().includes(query))
      )
    })).filter(cat => cat.analyses.length > 0);
  }, [searchQuery]);

  return (
    <div className="space-y-4">
      {/* Search Bar */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
        <input
          type="text"
          placeholder="Search analyses..."
          value={searchQuery}
          onChange={(e) => onSearchChange(e.target.value)}
          className="w-full pl-10 pr-4 py-2 bg-slate-900 border border-slate-800 rounded-lg text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500/50 focus:ring-1 focus:ring-cyan-500/50 transition-colors"
        />
      </div>

      {/* Analysis List */}
      <div className="space-y-2 overflow-y-auto max-h-[calc(100vh-300px)]">
        {filteredAnalyses.map(category => {
          const Icon = categoryIcons[category.category] || Layers;
          const colors = categoryColors[category.category];
          
          return (
            <div key={category.category} className="border border-slate-800 rounded-lg overflow-hidden">
              {/* Category Header */}
              <button
                onClick={() => toggleCategory(category.category)}
                className={`w-full flex items-center justify-between px-4 py-3 ${colors} transition-colors`}
              >
                <div className="flex items-center gap-3">
                  <Icon className="w-4 h-4" />
                  <span className="font-semibold text-sm">{category.name}</span>
                  <span className="text-xs opacity-70">({category.analyses.length})</span>
                </div>
                {expandedCategories[category.category] ? (
                  <ChevronDown className="w-4 h-4" />
                ) : (
                  <ChevronRight className="w-4 h-4" />
                )}
              </button>

              {/* Analysis Items */}
              {expandedCategories[category.category] && (
                <div className="bg-slate-950/50 divide-y divide-slate-800">
                  {category.analyses.map(analysis => (
                    <button
                      key={analysis.id}
                      onClick={() => onSelect(analysis.id)}
                      className={`w-full text-left px-4 py-3 hover:bg-slate-800/50 transition-colors ${
                        selectedAnalysis === analysis.id 
                          ? 'bg-cyan-950/30 border-l-2 border-cyan-500' 
                          : 'border-l-2 border-transparent'
                      }`}
                    >
                      <div className="font-medium text-sm text-slate-200">{analysis.name}</div>
                      <div className="text-xs text-slate-500 mt-1 line-clamp-2">{analysis.description}</div>
                    </button>
                  ))}
                </div>
              )}
            </div>
          );
        })}

        {filteredAnalyses.every(cat => cat.analyses.length === 0) && (
          <div className="text-center py-8 text-slate-500">
            <Search className="w-12 h-12 mx-auto mb-3 opacity-50" />
            <p className="text-sm">No analyses found</p>
          </div>
        )}
      </div>
    </div>
  );
}
