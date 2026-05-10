import React, { useState } from 'react';
import { Download, FileText, Table, TrendingUp, Info, CheckCircle, AlertTriangle, XCircle, Copy, Printer } from 'lucide-react';

export default function ResultsViewer({ result, data, analysisType }) {
  const [activeTab, setActiveTab] = useState('summary');
  const [copied, setCopied] = useState(null);

  if (!result) {
    return (
      <div className="h-full flex flex-col items-center justify-center text-slate-500">
        <div className="text-center">
          <Info className="w-12 h-12 mx-auto mb-4 opacity-50" />
          <p className="text-sm">Run an analysis to see results</p>
        </div>
      </div>
    );
  }

  const copyToClipboard = async (text, id) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(id);
      setTimeout(() => setCopied(null), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  const downloadReport = (format) => {
    // This would call the export API
    console.log(`Downloading report in ${format} format`);
    alert(`Export to ${format.toUpperCase()} - API endpoint needed`);
  };

  const renderSummary = () => (
    <div className="space-y-4">
      {/* Main Result */}
      <div className={`p-4 rounded-lg border ${
        result.significance < 0.05 
          ? 'bg-emerald-950/20 border-emerald-900/30' 
          : 'bg-amber-950/20 border-amber-900/30'
      }`}>
        <div className="flex items-start gap-3">
          {result.significance < 0.05 ? (
            <CheckCircle className="w-6 h-6 text-emerald-400 flex-shrink-0 mt-1" />
          ) : result.significance < 0.1 ? (
            <AlertTriangle className="w-6 h-6 text-amber-400 flex-shrink-0 mt-1" />
          ) : (
            <XCircle className="w-6 h-6 text-slate-400 flex-shrink-0 mt-1" />
          )}
          <div className="flex-1">
            <h3 className="font-semibold text-slate-200 mb-1">Result</h3>
            <p className="text-sm text-slate-300">{result.conclusion}</p>
          </div>
        </div>
      </div>

      {/* Test Statistics */}
      <div className="bg-slate-900/50 border border-slate-800 rounded-lg p-4">
        <h4 className="text-sm font-medium text-slate-300 mb-3">Test Statistics</h4>
        <div className="grid grid-cols-2 gap-3">
          {Object.entries(result.testStatistics).map(([key, value]) => (
            <div key={key} className="flex justify-between">
              <span className="text-xs text-slate-500 capitalize">{key.replace(/([A-Z])/g, ' $1').trim()}</span>
              <span className="text-xs text-slate-200 font-mono">
                {typeof value === 'number' ? value.toFixed(4) : value}
              </span>
            </div>
          ))}
          {result.pValue !== undefined && (
            <div className="flex justify-between col-span-2 pt-2 border-t border-slate-700">
              <span className="text-xs text-slate-500">P-value</span>
              <span className={`text-xs font-mono font-semibold ${
                result.pValue < 0.001 ? 'text-emerald-400' :
                result.pValue < 0.05 ? 'text-emerald-400' :
                result.pValue < 0.1 ? 'text-amber-400' :
                'text-slate-400'
              }`}>
                {result.pValue < 0.0001 ? '< 0.0001' : result.pValue.toFixed(4)}
              </span>
            </div>
          )}
          {result.sampleSize !== undefined && (
            <div className="flex justify-between col-span-2">
              <span className="text-xs text-slate-500">Sample Size</span>
              <span className="text-xs text-slate-200 font-mono">{result.sampleSize}</span>
            </div>
          )}
        </div>
      </div>

      {/* Effect Size */}
      {result.effectSize !== undefined && (
        <div className="bg-slate-900/50 border border-slate-800 rounded-lg p-4">
          <h4 className="text-sm font-medium text-slate-300 mb-3">Effect Size</h4>
          <div className="flex justify-between mb-2">
            <span className="text-xs text-slate-500">Effect Size</span>
            <span className="text-xs text-slate-200 font-mono">{result.effectSize.toFixed(4)}</span>
          </div>
          {result.effectSizeInterpretation && (
            <p className="text-xs text-slate-400 mt-2">{result.effectSizeInterpretation}</p>
          )}
        </div>
      )}

      {/* Confidence Interval */}
      {result.confidenceInterval && (
        <div className="bg-slate-900/50 border border-slate-800 rounded-lg p-4">
          <h4 className="text-sm font-medium text-slate-300 mb-3">
            {result.confidenceLevel * 100}% Confidence Interval
          </h4>
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-500">[</span>
            <span className="text-xs text-slate-200 font-mono">{result.confidenceInterval.lower.toFixed(4)}</span>
            <span className="text-xs text-slate-500">{','}</span>
            <span className="text-xs text-slate-200 font-mono">{result.confidenceInterval.upper.toFixed(4)}</span>
            <span className="text-xs text-slate-500">]</span>
          </div>
        </div>
      )}

      {/* Interpretation */}
      {result.interpretation && (
        <div className="bg-cyan-950/20 border border-cyan-900/30 rounded-lg p-4">
          <h4 className="text-sm font-medium text-cyan-400 mb-2 flex items-center gap-2">
            <TrendingUp className="w-4 h-4" />
            Interpretation
          </h4>
          <p className="text-sm text-slate-300">{result.interpretation}</p>
        </div>
      )}

      {/* Recommendation */}
      {result.recommendation && (
        <div className="bg-slate-900/50 border border-slate-800 rounded-lg p-4">
          <h4 className="text-sm font-medium text-slate-300 mb-2">Recommendation</h4>
          <p className="text-sm text-slate-400">{result.recommendation}</p>
        </div>
      )}
    </div>
  );

  const renderAPAText = () => {
    const apaText = result.apa || result.conclusion || '';
    return (
      <div className="space-y-4">
        <div className="bg-slate-950 border border-slate-800 rounded-lg p-4">
          <div className="flex items-start justify-between mb-3">
            <h4 className="text-sm font-medium text-slate-300">APA Format</h4>
            <button
              onClick={() => copyToClipboard(apaText, 'apa')}
              className="flex items-center gap-1 text-xs text-cyan-400 hover:text-cyan-300 transition-colors"
            >
              {copied === 'apa' ? <CheckCircle className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
              <span>{copied === 'apa' ? 'Copied!' : 'Copy'}</span>
            </button>
          </div>
          <p className="text-sm text-slate-300 font-serif leading-relaxed">{apaText}</p>
        </div>
        
        <div className="bg-blue-950/20 border border-blue-900/30 rounded-lg p-4">
          <h4 className="text-sm font-medium text-blue-400 mb-2 flex items-center gap-2">
            <Info className="w-4 h-4" />
            APA Guidelines
          </h4>
          <ul className="text-xs text-slate-400 space-y-1 list-disc list-inside">
            <li>Report exact p-values for p < 0.001</li>
            <li>Use appropriate decimals (usually 2-3)</li>
            <li>Include effect sizes and confidence intervals</li>
            <li>Specify test type and sample size</li>
          </ul>
        </div>
      </div>
    );
  };

  const renderTables = () => {
    const tables = result.tables || {};
    const tableEntries = Object.entries(tables);
    
    if (tableEntries.length === 0) {
      return (
        <div className="h-full flex items-center justify-center text-slate-500">
          <p className="text-sm">No tables available for this analysis</p>
        </div>
      );
    }

    return (
      <div className="space-y-4">
        {tableEntries.map(([name, tableData]) => {
          const rows = Array.isArray(tableData) ? tableData : tableData.rows || [];
          const columns = rows.length > 0 ? Object.keys(rows[0]) : [];
          
          return (
            <div key={name} className="bg-slate-950 border border-slate-800 rounded-lg overflow-hidden">
              <div className="px-4 py-3 bg-slate-900 border-b border-slate-800">
                <h4 className="text-sm font-medium text-slate-300">{name}</h4>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead className="bg-slate-900">
                    <tr>
                      {columns.map(col => (
                        <th key={col} className="px-4 py-2 text-left text-xs font-medium text-slate-400 uppercase">
                          {col}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800">
                    {rows.map((row, idx) => (
                      <tr key={idx} className="hover:bg-slate-900/30 transition-colors">
                        {columns.map(col => (
                          <td key={col} className="px-4 py-2 text-slate-300 font-mono">
                            {typeof row[col] === 'number' 
                              ? (row[col] % 1 === 0 ? row[col] : row[col].toFixed(4))
                              : row[col]
                            }
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          );
        })}
      </div>
    );
  };

  const renderAssumptions = () => {
    const assumptions = result.assumptionsCheck || [];
    
    if (assumptions.length === 0) {
      return (
        <div className="h-full flex items-center justify-center text-slate-500">
          <p className="text-sm">No assumptions checked for this analysis</p>
        </div>
      );
    }

    return (
      <div className="space-y-3">
        {assumptions.map((assumption, idx) => {
          const statusColors = {
            passed: 'text-emerald-400 border-emerald-900 bg-emerald-950/30',
            failed: 'text-red-400 border-red-900 bg-red-950/30',
            warning: 'text-amber-400 border-amber-900 bg-amber-950/30'
          };
          const statusIcons = {
            passed: CheckCircle,
            failed: XCircle,
            warning: AlertTriangle
          };
          const StatusIcon = statusIcons[assumption.status];
          
          return (
            <div key={idx} className={`p-4 rounded-lg border ${statusColors[assumption.status]}`}>
              <div className="flex items-start gap-3">
                <StatusIcon className={`w-5 h-5 flex-shrink-0 mt-0.5`} />
                <div className="flex-1">
                  <h4 className="text-sm font-medium mb-1">{assumption.name}</h4>
                  <p className="text-xs text-slate-400 mb-2">{assumption.interpretation}</p>
                  
                  {assumption.testStatistic !== undefined && (
                    <div className="flex gap-4 text-xs">
                      <span className="text-slate-500">Statistic: <span className="text-slate-300 font-mono">{assumption.testStatistic.toFixed(4)}</span></span>
                      {assumption.pValue !== undefined && (
                        <span className="text-slate-500">P-value: <span className="text-slate-300 font-mono">{assumption.pValue.toFixed(4)}</span></span>
                      )}
                    </div>
                  )}
                  
                  {assumption.remedy && (
                    <div className="mt-3 pt-3 border-t border-current/20">
                      <p className="text-xs">{assumption.remedy}</p>
                    </div>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    );
  };

  const renderExport = () => (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3">
        <button
          onClick={() => downloadReport('docx')}
          className="flex items-center gap-3 p-4 bg-slate-900/50 border border-slate-800 rounded-lg hover:bg-slate-900 hover:border-slate-700 transition-colors"
        >
          <FileText className="w-8 h-8 text-blue-400" />
          <div className="text-left">
            <div className="text-sm font-medium text-slate-200">DOCX</div>
            <div className="text-xs text-slate-500">Word Document</div>
          </div>
        </button>
        
        <button
          onClick={() => downloadReport('pdf')}
          className="flex items-center gap-3 p-4 bg-slate-900/50 border border-slate-800 rounded-lg hover:bg-slate-900 hover:border-slate-700 transition-colors"
        >
          <FileText className="w-8 h-8 text-red-400" />
          <div className="text-left">
            <div className="text-sm font-medium text-slate-200">PDF</div>
            <div className="text-xs text-slate-500">PDF Document</div>
          </div>
        </button>
        
        <button
          onClick={() => downloadReport('latex')}
          className="flex items-center gap-3 p-4 bg-slate-900/50 border border-slate-800 rounded-lg hover:bg-slate-900 hover:border-slate-700 transition-colors"
        >
          <FileText className="w-8 h-8 text-emerald-400" />
          <div className="text-left">
            <div className="text-sm font-medium text-slate-200">LaTeX</div>
            <div className="text-xs text-slate-500">TeX Source</div>
          </div>
        </button>
        
        <button
          onClick={() => window.print()}
          className="flex items-center gap-3 p-4 bg-slate-900/50 border border-slate-800 rounded-lg hover:bg-slate-900 hover:border-slate-700 transition-colors"
        >
          <Printer className="w-8 h-8 text-slate-400" />
          <div className="text-left">
            <div className="text-sm font-medium text-slate-200">Print</div>
            <div className="text-xs text-slate-500">Print Report</div>
          </div>
        </button>
      </div>
      
      <div className="bg-slate-900/50 border border-slate-800 rounded-lg p-4">
        <h4 className="text-sm font-medium text-slate-300 mb-3">Export Options</h4>
        <div className="space-y-3">
          <label className="flex items-center gap-2 cursor-pointer">
            <input type="checkbox" defaultChecked className="w-4 h-4 rounded border-slate-700 bg-slate-900 text-cyan-500" />
            <span className="text-sm text-slate-300">Include assumptions check</span>
          </label>
          <label className="flex items-center gap-2 cursor-pointer">
            <input type="checkbox" defaultChecked className="w-4 h-4 rounded border-slate-700 bg-slate-900 text-cyan-500" />
            <span className="text-sm text-slate-300">Include interpretation</span>
          </label>
          <label className="flex items-center gap-2 cursor-pointer">
            <input type="checkbox" defaultChecked className="w-4 h-4 rounded border-slate-700 bg-slate-900 text-cyan-500" />
            <span className="text-sm text-slate-300">Include APA format</span>
          </label>
          <label className="flex items-center gap-2 cursor-pointer">
            <input type="checkbox" defaultChecked className="w-4 h-4 rounded border-slate-700 bg-slate-900 text-cyan-500" />
            <span className="text-sm text-slate-300">Include tables</span>
          </label>
          <label className="flex items-center gap-2 cursor-pointer">
            <input type="checkbox" defaultChecked className="w-4 h-4 rounded border-slate-700 bg-slate-900 text-cyan-500" />
            <span className="text-sm text-slate-300">Include graphs</span>
          </label>
        </div>
      </div>
    </div>
  );

  return (
    <div className="h-full flex flex-col">
      {/* Tab Navigation */}
      <div className="flex gap-1 p-1 bg-slate-900 rounded-lg mb-4">
        <button
          onClick={() => setActiveTab('summary')}
          className={`flex-1 px-3 py-2 text-xs font-medium rounded-md transition-colors ${
            activeTab === 'summary' 
              ? 'bg-cyan-600 text-white' 
              : 'text-slate-400 hover:text-slate-300 hover:bg-slate-800'
          }`}
        >
          Summary
        </button>
        <button
          onClick={() => setActiveTab('apa')}
          className={`flex-1 px-3 py-2 text-xs font-medium rounded-md transition-colors ${
            activeTab === 'apa' 
              ? 'bg-cyan-600 text-white' 
              : 'text-slate-400 hover:text-slate-300 hover:bg-slate-800'
          }`}
        >
          APA
        </button>
        <button
          onClick={() => setActiveTab('tables')}
          className={`flex-1 px-3 py-2 text-xs font-medium rounded-md transition-colors ${
            activeTab === 'tables' 
              ? 'bg-cyan-600 text-white' 
              : 'text-slate-400 hover:text-slate-300 hover:bg-slate-800'
          }`}
        >
          <Table className="w-4 h-4 inline mr-1" />
          Tables
        </button>
        <button
          onClick={() => setActiveTab('assumptions')}
          className={`flex-1 px-3 py-2 text-xs font-medium rounded-md transition-colors ${
            activeTab === 'assumptions' 
              ? 'bg-cyan-600 text-white' 
              : 'text-slate-400 hover:text-slate-300 hover:bg-slate-800'
          }`}
        >
          Assumptions
        </button>
        <button
          onClick={() => setActiveTab('export')}
          className={`flex-1 px-3 py-2 text-xs font-medium rounded-md transition-colors ${
            activeTab === 'export' 
              ? 'bg-cyan-600 text-white' 
              : 'text-slate-400 hover:text-slate-300 hover:bg-slate-800'
          }`}
        >
          <Download className="w-4 h-4 inline mr-1" />
          Export
        </button>
      </div>

      {/* Tab Content */}
      <div className="flex-1 overflow-y-auto">
        {activeTab === 'summary' && renderSummary()}
        {activeTab === 'apa' && renderAPAText()}
        {activeTab === 'tables' && renderTables()}
        {activeTab === 'assumptions' && renderAssumptions()}
        {activeTab === 'export' && renderExport()}
      </div>
    </div>
  );
}
