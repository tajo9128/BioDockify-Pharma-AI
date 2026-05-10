import React, { useState } from 'react';
import { StatisticsResult } from '@/types/statistics';
import { generateAPAReport, generateInlineAPA, generateInterpretationParagraph } from '@/lib/statistics/apa-report';
import { calculateEffectSize } from '@/lib/statistics/effect-size';
import { CheckCircle, XCircle, AlertCircle, Download, FileText, Image as ImageIcon, Table as TableIcon } from 'lucide-react';

interface ResultsViewerProps {
  result: StatisticsResult;
  data?: any[];
  analysisType?: string;
}

export default function ResultsViewer({ result, data, analysisType }: ResultsViewerProps) {
  const [activeTab, setActiveTab] = useState<'overview' | 'statistics' | 'interpretation' | 'tables' | 'export'>('overview');

  const renderTabButton = (id: typeof activeTab, icon: React.ReactNode, label: string, count?: number) => (
    <button
      onClick={() => setActiveTab(id)}
      className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
        activeTab === id
          ? 'bg-cyan-950/50 text-cyan-400 border border-cyan-900'
          : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
      }`}
    >
      {icon}
      <span>{label}</span>
      {count !== undefined && count > 0 && (
        <span className="ml-1 px-2 py-0.5 text-xs rounded-full bg-slate-800 text-slate-400">{count}</span>
      )}
    </button>
  );

  const renderOverviewTab = () => (
    <div className="space-y-4">
      {/* Summary Card */}
      <div className="bg-slate-900/30 rounded-lg p-4 border border-slate-800">
        <h3 className="text-sm font-medium text-cyan-400 mb-3">Analysis Summary</h3>
        <div className="space-y-2">
          {result.analysisType && (
            <div className="flex justify-between text-sm">
              <span className="text-slate-400">Analysis Type:</span>
              <span className="text-slate-200 font-medium">{result.analysisType}</span>
            </div>
          )}
          {result.sampleSize && (
            <div className="flex justify-between text-sm">
              <span className="text-slate-400">Sample Size:</span>
              <span className="text-slate-200">{result.sampleSize}</span>
            </div>
          )}
          {result.confidenceLevel && (
            <div className="flex justify-between text-sm">
              <span className="text-slate-400">Confidence Level:</span>
              <span className="text-slate-200">{Math.round(result.confidenceLevel * 100)}%</span>
            </div>
          )}
          {result.significance !== undefined && (
            <div className="flex justify-between text-sm">
              <span className="text-slate-400">Significance Level (α):</span>
              <span className="text-slate-200">{result.significance}</span>
            </div>
          )}
        </div>
      </div>

      {/* Conclusion Card */}
      <div className={`rounded-lg p-4 border ${
        (result.pValue ?? Infinity) < (result.significance ?? 0.05)
          ? 'bg-green-950/30 border-green-900'
          : 'bg-amber-950/30 border-amber-900'
      }`}>
        <div className="flex items-start gap-3">
          {(result.pValue ?? Infinity) < (result.significance ?? 0.05) ? (
            <CheckCircle className="w-5 h-5 text-green-400 mt-0.5 flex-shrink-0" />
          ) : (
            <XCircle className="w-5 h-5 text-amber-400 mt-0.5 flex-shrink-0" />
          )}
          <div>
            <h3 className="text-sm font-medium mb-1">
              {(result.pValue ?? Infinity) < (result.significance ?? 0.05) ? 'Result: Statistically Significant' : 'Result: Not Statistically Significant'}
            </h3>
            <p className="text-sm text-slate-400">{result.conclusion}</p>
            {result.recommendation && (
              <p className="text-sm text-slate-300 mt-2">{result.recommendation}</p>
            )}
          </div>
        </div>
      </div>

      {/* Effect Size Card */}
      {result.effectSize !== undefined || result.effectSizes ? (
        <div className="bg-slate-900/30 rounded-lg p-4 border border-slate-800">
          <h3 className="text-sm font-medium text-cyan-400 mb-3">Effect Size</h3>
          {result.effectSize !== undefined && (
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-slate-400">Value:</span>
                <span className="text-slate-200 font-medium">{result.effectSize.toFixed(4)}</span>
              </div>
              {result.effectSizeInterpretation && (
                <div className="flex justify-between text-sm">
                  <span className="text-slate-400">Interpretation:</span>
                  <span className="text-slate-200">{result.effectSizeInterpretation}</span>
                </div>
              )}
            </div>
          )}
          {result.effectSizes && Object.keys(result.effectSizes).length > 0 && (
            <div className="space-y-2">
              {Object.entries(result.effectSizes).map(([key, value]) => (
                <div key={key} className="flex justify-between text-sm">
                  <span className="text-slate-400">{key}:</span>
                  <span className="text-slate-200 font-medium">{typeof value === 'number' ? value.toFixed(4) : JSON.stringify(value)}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      ) : null}

      {/* Confidence Interval Card */}
      {result.confidenceInterval || result.confidenceIntervals ? (
        <div className="bg-slate-900/30 rounded-lg p-4 border border-slate-800">
          <h3 className="text-sm font-medium text-cyan-400 mb-3">
            {Math.round((result.confidenceLevel || 0.95) * 100)}% Confidence Interval
          </h3>
          {result.confidenceInterval && (
            <div className="text-center">
              <span className="text-lg font-medium text-slate-200">
                {Array.isArray(result.confidenceInterval) 
                  ? `[${result.confidenceInterval[0].toFixed(4)}, ${result.confidenceInterval[1].toFixed(4)}]`
                  : `[${result.confidenceInterval.lower.toFixed(4)}, ${result.confidenceInterval.upper.toFixed(4)}]`}
              </span>
            </div>
          )}
          {result.confidenceIntervals && Object.keys(result.confidenceIntervals).length > 0 && (
            <div className="space-y-2 mt-3">
              {Object.entries(result.confidenceIntervals).map(([key, value]) => (
                <div key={key} className="flex justify-between text-sm">
                  <span className="text-slate-400">{key}:</span>
                  <span className="text-slate-200">
                    {Array.isArray(value) 
                      ? `[${value[0].toFixed(4)}, ${value[1].toFixed(4)}]`
                      : `[${value.lower.toFixed(4)}, ${value.upper.toFixed(4)}]`}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      ) : null}
    </div>
  );

  const renderStatisticsTab = () => (
    <div className="space-y-4">
      {/* Test Statistics */}
      {result.testStatistics && Object.keys(result.testStatistics).length > 0 && (
        <div className="bg-slate-900/30 rounded-lg p-4 border border-slate-800">
          <h3 className="text-sm font-medium text-cyan-400 mb-3">Test Statistics</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <tbody>
                {Object.entries(result.testStatistics).map(([key, value]) => (
                  <tr key={key} className="border-b border-slate-800 last:border-b-0">
                    <td className="py-2 text-slate-400">{key}</td>
                    <td className="py-2 text-slate-200 text-right font-mono">
                      {typeof value === 'number' ? value.toFixed(4) : JSON.stringify(value)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* P-values */}
      {result.pValue !== undefined || (result.pValues && Object.keys(result.pValues).length > 0) ? (
        <div className="bg-slate-900/30 rounded-lg p-4 border border-slate-800">
          <h3 className="text-sm font-medium text-cyan-400 mb-3">P-values</h3>
          {result.pValue !== undefined && (
            <div className="flex justify-between text-sm items-center py-2">
              <span className="text-slate-400">P-value</span>
              <span className={`font-mono font-medium ${
                (result.pValue ?? Infinity) < (result.significance ?? 0.05) ? 'text-green-400' : 'text-amber-400'
              }`}>
                {(result.pValue ?? Infinity) < 0.001 ? '< 0.001' : result.pValue?.toFixed(4)}
              </span>
            </div>
          )}
          {result.pValues && Object.entries(result.pValues).map(([key, value]) => {
            const numValue = Number(value);
            const isSignificant = numValue < (result.significance ?? 0.05);
            return (
              <div key={key} className="flex justify-between text-sm items-center py-2 border-t border-slate-800">
                <span className="text-slate-400">{key}</span>
                <span className={`font-mono font-medium ${isSignificant ? 'text-green-400' : 'text-amber-400'}`}>
                  {numValue < 0.001 ? '< 0.001' : numValue.toFixed(4)}
                </span>
              </div>
            );
          })}
        </div>
      ) : null}

      {/* Adjusted P-values */}
      {result.adjustedPValues && Object.keys(result.adjustedPValues).length > 0 ? (
        <div className="bg-slate-900/30 rounded-lg p-4 border border-slate-800">
          <h3 className="text-sm font-medium text-cyan-400 mb-3">Adjusted P-values</h3>
          {Object.entries(result.adjustedPValues).map(([key, value]) => {
            const numValue = Number(value);
            const isSignificant = numValue < (result.significance ?? 0.05);
            return (
              <div key={key} className="flex justify-between text-sm items-center py-2 border-b border-slate-800 last:border-b-0">
                <span className="text-slate-400">{key}</span>
                <span className={`font-mono font-medium ${isSignificant ? 'text-green-400' : 'text-amber-400'}`}>
                  {numValue < 0.001 ? '< 0.001' : numValue.toFixed(4)}
                </span>
              </div>
            );
          })}
        </div>
      ) : null}
    </div>
  );

  const renderInterpretationTab = () => (
    <div className="space-y-4">
      {/* Interpretation Paragraph */}
      {result.interpretation && (
        <div className="bg-slate-900/30 rounded-lg p-4 border border-slate-800">
          <h3 className="text-sm font-medium text-cyan-400 mb-3">Interpretation</h3>
          <p className="text-sm text-slate-300 leading-relaxed">{result.interpretation}</p>
        </div>
      )}

      {/* Auto-generated Interpretation Paragraph */}
      {analysisType && (
        <div className="bg-slate-900/30 rounded-lg p-4 border border-slate-800">
          <h3 className="text-sm font-medium text-cyan-400 mb-3">Generated Interpretation</h3>
          <p className="text-sm text-slate-300 leading-relaxed">
            {generateInterpretationParagraph(result)}
          </p>
        </div>
      )}

      {/* APA-formatted Report */}
      {analysisType && (
        <div className="bg-slate-900/30 rounded-lg p-4 border border-slate-800">
          <h3 className="text-sm font-medium text-cyan-400 mb-3">APA-formatted Report</h3>
          <div className="bg-slate-950 rounded p-3 font-mono text-xs text-slate-300 whitespace-pre-wrap">
            {generateAPAReport(result)}
          </div>
          <div className="mt-3 text-xs text-slate-500">
            <strong>Inline citation:</strong> {generateInlineAPA(result)}
          </div>
        </div>
      )}

      {/* Assumption Checks */}
      {result.assumptionsCheck && result.assumptionsCheck.length > 0 ? (
        <div className="bg-slate-900/30 rounded-lg p-4 border border-slate-800">
          <h3 className="text-sm font-medium text-cyan-400 mb-3">Assumption Checks</h3>
          <div className="space-y-2">
            {result.assumptionsCheck.map((check, idx) => (
              <div key={idx} className={`flex items-start gap-3 p-3 rounded border ${
                check.status === 'passed'
                  ? 'bg-green-950/20 border-green-900'
                  : check.status === 'failed'
                  ? 'bg-red-950/20 border-red-900'
                  : 'bg-amber-950/20 border-amber-900'
              }`}>
                {check.status === 'passed' && <CheckCircle className="w-4 h-4 text-green-400 mt-0.5 flex-shrink-0" />}
                {check.status === 'failed' && <XCircle className="w-4 h-4 text-red-400 mt-0.5 flex-shrink-0" />}
                {check.status === 'warning' && <AlertCircle className="w-4 h-4 text-amber-400 mt-0.5 flex-shrink-0" />}
                <div className="flex-1">
                  <p className="text-sm text-slate-200">{check.name}</p>
                  {check.interpretation && (
                    <p className="text-xs text-slate-400 mt-1">{check.interpretation}</p>
                  )}
                  {check.remedy && (
                    <p className="text-xs text-cyan-400 mt-1">Remedy: {check.remedy}</p>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );

  const renderTablesTab = () => (
    <div className="space-y-4">
      {/* Data Summary Table */}
      {data && data.length > 0 && (
        <div className="bg-slate-900/30 rounded-lg p-4 border border-slate-800">
          <h3 className="text-sm font-medium text-cyan-400 mb-3">Data Summary</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-slate-800">
                  {Object.keys(data[0]).map((key) => (
                    <th key={key} className="text-left py-2 px-3 text-slate-400 font-medium">{key}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {data.slice(0, 10).map((row, idx) => (
                  <tr key={idx} className="border-b border-slate-800 last:border-b-0">
                    {Object.values(row).map((value, vIdx) => (
                      <td key={vIdx} className="py-2 px-3 text-slate-300">
                        {typeof value === 'number' ? value.toFixed(2) : String(value)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
            {data.length > 10 && (
              <p className="text-xs text-slate-500 mt-2">Showing 10 of {data.length} rows</p>
            )}
          </div>
        </div>
      )}

      {/* Publication-quality Table Placeholder */}
      <div className="bg-slate-900/30 rounded-lg p-6 border border-slate-800 text-center">
        <TableIcon className="w-12 h-12 mx-auto mb-3 text-slate-600" />
        <h3 className="text-sm font-medium text-slate-300 mb-2">Publication-quality Table</h3>
        <p className="text-xs text-slate-500 mb-4">Generate a formatted table suitable for publication in pharmaceutical journals.</p>
        <button className="px-4 py-2 bg-cyan-950/30 hover:bg-cyan-950/50 border border-cyan-900 rounded-lg text-xs text-cyan-400 transition-colors">
          Generate Table
        </button>
      </div>

      {/* Graph Placeholder */}
      <div className="bg-slate-900/30 rounded-lg p-6 border border-slate-800 text-center">
        <ImageIcon className="w-12 h-12 mx-auto mb-3 text-slate-600" />
        <h3 className="text-sm font-medium text-slate-300 mb-2">Publication-quality Graph</h3>
        <p className="text-xs text-slate-500 mb-4">Generate a formatted graph suitable for publication in pharmaceutical journals.</p>
        <button className="px-4 py-2 bg-cyan-950/30 hover:bg-cyan-950/50 border border-cyan-900 rounded-lg text-xs text-cyan-400 transition-colors">
          Generate Graph
        </button>
      </div>
    </div>
  );

  const renderExportTab = () => (
    <div className="space-y-4">
      <div className="bg-slate-900/30 rounded-lg p-4 border border-slate-800">
        <h3 className="text-sm font-medium text-cyan-400 mb-3">Export Results</h3>
        <p className="text-xs text-slate-400 mb-4">Export your analysis results in various formats for reporting and publication.</p>
      </div>

      <div className="grid grid-cols-1 gap-3">
        <button className="flex items-center gap-3 p-4 bg-slate-900/30 hover:bg-slate-800/50 border border-slate-800 rounded-lg transition-colors">
          <FileText className="w-5 h-5 text-blue-400" />
          <div className="text-left flex-1">
            <div className="text-sm font-medium text-slate-200">Export to DOCX</div>
            <div className="text-xs text-slate-500">Microsoft Word document with full report</div>
          </div>
          <Download className="w-4 h-4 text-slate-500" />
        </button>

        <button className="flex items-center gap-3 p-4 bg-slate-900/30 hover:bg-slate-800/50 border border-slate-800 rounded-lg transition-colors">
          <FileText className="w-5 h-5 text-orange-400" />
          <div className="text-left flex-1">
            <div className="text-sm font-medium text-slate-200">Export to PDF</div>
            <div className="text-xs text-slate-500">PDF document with formatted tables and graphs</div>
          </div>
          <Download className="w-4 h-4 text-slate-500" />
        </button>

        <button className="flex items-center gap-3 p-4 bg-slate-900/30 hover:bg-slate-800/50 border border-slate-800 rounded-lg transition-colors">
          <FileText className="w-5 h-5 text-cyan-400" />
          <div className="text-left flex-1">
            <div className="text-sm font-medium text-slate-200">Export to LaTeX</div>
            <div className="text-xs text-slate-500">LaTeX source code for academic papers</div>
          </div>
          <Download className="w-4 h-4 text-slate-500" />
        </button>

        <button className="flex items-center gap-3 p-4 bg-slate-900/30 hover:bg-slate-800/50 border border-slate-800 rounded-lg transition-colors">
          <ImageIcon className="w-5 h-5 text-green-400" />
          <div className="text-left flex-1">
            <div className="text-sm font-medium text-slate-200">Export Figures</div>
            <div className="text-xs text-slate-500">Download high-resolution images</div>
          </div>
          <Download className="w-4 h-4 text-slate-500" />
        </button>
      </div>
    </div>
  );

  return (
    <div className="bg-slate-950/50 rounded-xl border border-slate-800">
      {/* Tab Header */}
      <div className="flex items-center gap-1 p-2 border-b border-slate-800 overflow-x-auto">
        {renderTabButton('overview', <span className="w-4 h-4" />, 'Overview')}
        {renderTabButton('statistics', <span className="w-4 h-4" />, 'Statistics')}
        {renderTabButton('interpretation', <span className="w-4 h-4" />, 'Interpretation')}
        {renderTabButton('tables', <TableIcon className="w-4 h-4" />, 'Tables & Graphs')}
        {renderTabButton('export', <Download className="w-4 h-4" />, 'Export')}
      </div>

      {/* Tab Content */}
      <div className="p-4">
        {activeTab === 'overview' && renderOverviewTab()}
        {activeTab === 'statistics' && renderStatisticsTab()}
        {activeTab === 'interpretation' && renderInterpretationTab()}
        {activeTab === 'tables' && renderTablesTab()}
        {activeTab === 'export' && renderExportTab()}
      </div>
    </div>
  );
}
