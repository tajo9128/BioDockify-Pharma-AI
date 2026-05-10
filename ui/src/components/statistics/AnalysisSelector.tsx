import React, { useState } from 'react';
import { AnalysisCategory, AnalysisType } from '@/types/statistics';
import { ANALYSIS_CATEGORIES, getAnalysesByCategory } from '@/lib/statistics/analysis-definitions';
import { Calculator, Activity, Scale, Microscope, Zap, Layers, Grid, Search, ChevronDown } from 'lucide-react';

interface AnalysisSelectorProps {
  selectedAnalysis: AnalysisType | null;
  onSelect: (analysis: AnalysisType) => void;
  searchQuery?: string;
  onSearchChange?: (query: string) => void;
}

export default function AnalysisSelector({ selectedAnalysis, onSelect, searchQuery = '', onSearchChange }: AnalysisSelectorProps) {
  const [expandedCategories, setExpandedCategories] = useState<Set<AnalysisCategory>>(new Set(['basic', 'advanced']));
  const [searchMode, setSearchMode] = useState(false);

  const toggleCategory = (category: AnalysisCategory) => {
    const newExpanded = new Set(expandedCategories);
    if (newExpanded.has(category)) {
      newExpanded.delete(category);
    } else {
      newExpanded.add(category);
    }
    setExpandedCategories(newExpanded);
  };

  const getCategoryIcon = (category: AnalysisCategory) => {
    const icons: Record<AnalysisCategory, any> = {
      basic: Calculator,
      survival: Activity,
      bioequivalence: Scale,
      advanced: Microscope,
      pkpd: Zap,
      multiplicity: Layers,
      categorical: Grid
    };
    return icons[category] || Calculator;
  };

  const categories = Object.entries(ANALYSIS_CATEGORIES) as [AnalysisCategory, typeof ANALYSIS_CATEGORIES[keyof typeof ANALYSIS_CATEGORIES]][];

  return (
    <div className="space-y-4">
      {/* Search Bar */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-slate-500" />
        <input
          type="text"
          placeholder="Search analyses..."
          value={searchQuery}
          onChange={(e) => {
            onSearchChange?.(e.target.value);
            setSearchMode(e.target.value.length > 0);
          }}
          className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-10 pr-4 py-2 text-sm text-slate-200 placeholder-slate-500 focus:ring-1 focus:ring-cyan-500 focus:border-cyan-500 outline-none"
        />
      </div>

      {/* Analysis Categories */}
      <div className="space-y-2">
        {categories.map(([category, info]) => {
          const analyses = getAnalysesByCategory(category);
          const filteredAnalyses = searchQuery 
            ? analyses.filter(a => 
                a.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                a.description.toLowerCase().includes(searchQuery.toLowerCase())
              )
            : analyses;
          
          if (filteredAnalyses.length === 0) return null;
          
          const isExpanded = expandedCategories.has(category);
          const CategoryIcon = getCategoryIcon(category);

          return (
            <div key={category} className="border border-slate-800 rounded-lg overflow-hidden">
              {/* Category Header */}
              <button
                onClick={() => toggleCategory(category)}
                className="w-full flex items-center justify-between p-3 bg-slate-900/50 hover:bg-slate-800/50 transition-colors"
              >
                <div className="flex items-center gap-2">
                  <CategoryIcon className="w-4 h-4 text-cyan-500" />
                  <span className="font-medium text-sm text-slate-200">{info.name}</span>
                  <span className="text-xs text-slate-500">({filteredAnalyses.length})</span>
                </div>
                <ChevronDown 
                  className={`w-4 h-4 text-slate-400 transition-transform ${isExpanded ? 'rotate-180' : ''}`} 
                />
              </button>

              {/* Category Description */}
              {isExpanded && (
                <div className="px-3 pb-2">
                  <p className="text-xs text-slate-500">{info.description}</p>
                </div>
              )}

              {/* Analyses List */}
              {isExpanded && (
                <div className="border-t border-slate-800">
                  {filteredAnalyses.map((analysis) => (
                    <button
                      key={analysis.id}
                      onClick={() => onSelect(analysis.id)}
                      className={`w-full text-left p-3 border-b border-slate-800 last:border-b-0 hover:bg-slate-800/30 transition-colors ${
                        selectedAnalysis === analysis.id 
                          ? 'bg-cyan-950/50 border-l-2 border-l-cyan-500' 
                          : ''
                      }`}
                    >
                      <div className="text-sm font-medium text-slate-200">{analysis.name}</div>
                      <div className="text-xs text-slate-500 mt-1 line-clamp-2">{analysis.description}</div>
                      {analysis.minSampleSize && (
                        <div className="text-xs text-slate-600 mt-1">
                          Min sample size: {analysis.minSampleSize}
                        </div>
                      )}
                    </button>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
