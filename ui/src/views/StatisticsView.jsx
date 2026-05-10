import React, { useState, useEffect } from 'react';
import { AnalysisType } from '@/types/statistics';
import { detectDataTypes, getSuggestedColumns } from '@/lib/statistics/data-detection';
import { suggestTests, getTestExplanation } from '@/lib/statistics/test-suggestion';
import { generateAPAReport, generateInlineAPA, generateInterpretationParagraph } from '@/lib/statistics/apa-report';
import { calculateEffectSize, interpretEffectSize } from '@/lib/statistics/effect-size';
import AnalysisSelector from '@/components/statistics/AnalysisSelector';
import ParameterForm from '@/components/statistics/ParameterForm';
import ResultsViewer from '@/components/statistics/ResultsViewer';
import { 
  Upload, 
  Sparkles, 
  Database, 
  FileText, 
  BarChart, 
  CheckCircle,
  AlertCircle,
  Play,
  RefreshCw,
  Download,
  AlertTriangle,
  Info
} from 'lucide-react';

export default function StatisticsView() {
  // State for data and analysis
  const [data, setData] = useState([]);
  const [dataTypes, setDataTypes] = useState([]);
  const [selectedAnalysis, setSelectedAnalysis] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [parameters, setParameters] = useState({});
  const [results, setResults] = useState(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [error, setError] = useState(null);
  const [showDataPreview, setShowDataPreview] = useState(false);
  const [showAssumptions, setShowAssumptions] = useState(false);
  const [autoDetectedDataTypes, setAutoDetectedDataTypes] = useState(false);
  const [assumptionsChecked, setAssumptionsChecked] = useState(false);
  const [suggestedTests, setSuggestedTests] = useState([]);
  const [effectSizesGenerated, setEffectSizesGenerated] = useState(false);
  const [apaReportGenerated, setApaReportGenerated] = useState(false);
  const [interpretationProvided, setInterpretationProvided] = useState(false);

  // Detect data types when data changes
  useEffect(() => {
    if (data && data.length > 0) {
      const detected = detectDataTypes(data);
      setDataTypes(detected);
      const suggested = getSuggestedColumns(detected);
      console.log('Detected data types:', detected);
      console.log('Suggested columns:', suggested);
    }
  }, [data]);

  // Handle file upload
  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch('/api/statistics/upload', {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        throw new Error('Failed to upload file');
      }

      const result = await response.json();
      setData(result.data);
      setError(null);
    } catch (err) {
      setError(err.message);
      console.error('Upload error:', err);
    }
  };

  // Auto-detect data types
  const handleAutoDetectDataTypes = () => {
    if (data && data.length > 0) {
      const detected = detectDataTypes(data);
      setDataTypes(detected);
      setAutoDetectedDataTypes(true);
    }
  };

  // Test assumptions
  const handleTestAssumptions = async () => {
    if (!selectedAnalysis || data.length === 0) {
      setError('Please select an analysis and upload data first');
      return;
    }

    try {
      const response = await fetch('/api/statistics/assumptions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          analysisType: selectedAnalysis,
          data: data,
          parameters: parameters
        })
      });

      if (!response.ok) {
        throw new Error('Failed to test assumptions');
      }

      const result = await response.json();
      setShowAssumptions(true);
      setAssumptionsChecked(true);
      
      // Add assumptions to results if they exist
      if (results) {
        setResults({ ...results, assumptionsCheck: result.assumptionsCheck });
      }
    } catch (err) {
      setError(err.message);
    }
  };

  // Suggest appropriate tests
  const handleSuggestTests = () => {
    if (data.length === 0) {
      setError('Please upload data first');
      return;
    }

    const suggested = suggestTests(dataTypes, data.length, false, false);
    setSuggestedTests(suggested);
    console.log('Suggested tests:', suggested);
  };

  // Generate effect sizes
  const handleGenerateEffectSizes = () => {
    if (!results) {
      setError('Please run an analysis first');
      return;
    }

    const effectSizeData = calculateEffectSize(selectedAnalysis, data, results.testStatistics);
    if (effectSizeData) {
      setEffectSizesGenerated(true);
      setResults({ ...results, effectSize: effectSizeData.effectSize, effectSizeInterpretation: effectSizeData.interpretation });
    }
  };

  // Generate APA report
  const handleGenerateAPAReport = () => {
    if (!results) {
      setError('Please run an analysis first');
      return;
    }

    setApaReportGenerated(true);
    console.log('APA Report:', generateAPAReport(results));
  };

  // Generate interpretation
  const handleGenerateInterpretation = () => {
    if (!results) {
      setError('Please run an analysis first');
      return;
    }

    const interpretation = generateInterpretationParagraph(results);
    setInterpretationProvided(true);
    setResults({ ...results, interpretation: interpretation });
  };

  // Run analysis
  const handleRunAnalysis = async () => {
    if (!selectedAnalysis) {
      setError('Please select an analysis type');
      return;
    }

    if (data.length === 0) {
      setError('Please upload data first');
      return;
    }

    setIsAnalyzing(true);
    setError(null);

    try {
      const response = await fetch('/api/statistics/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          analysisType: selectedAnalysis,
          data: data,
          parameters: parameters
        })
      });

      if (!response.ok) {
        throw new Error('Analysis failed');
      }

      const result = await response.json();
      setResults(result);
      setAssumptionsChecked(false);
      setEffectSizesGenerated(false);
      setApaReportGenerated(false);
      setInterpretationProvided(false);
    } catch (err) {
      setError(err.message);
      console.error('Analysis error:', err);
    } finally {
      setIsAnalyzing(false);
    }
  };

  // Export to DOCX
  const handleExportToDocx = async () => {
    if (!results) {
      setError('Please run an analysis first');
      return;
    }

    try {
      const response = await fetch('/api/statistics/export/docx', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          results: results,
          data: data,
          analysisType: selectedAnalysis
        })
      });

      if (!response.ok) {
        throw new Error('Failed to export');
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `statistics_${selectedAnalysis}_${Date.now()}.docx`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <div className="flex h-screen bg-slate-950 text-slate-200">
      {/* Left Sidebar - Analysis Selection */}
      <div className="w-96 border-r border-slate-800 flex flex-col">
        <div className="p-4 border-b border-slate-800">
          <h1 className="text-xl font-bold text-cyan-400 flex items-center gap-2">
            <BarChart className="w-6 h-6" />
            Statistics Analysis
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Comprehensive pharmaceutical statistics
          </p>
        </div>

        <div className="flex-1 overflow-y-auto p-4">
          <AnalysisSelector
            selectedAnalysis={selectedAnalysis}
            onSelect={setSelectedAnalysis}
            searchQuery={searchQuery}
            onSearchChange={setSearchQuery}
          />
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top Bar - Helper Features */}
        <div className="border-b border-slate-800 p-4">
          <div className="flex flex-wrap gap-2">
            {/* Data Upload */}
            <label className="flex items-center gap-2 px-4 py-2 bg-cyan-950/30 hover:bg-cyan-950/50 border border-cyan-900 rounded-lg text-sm text-cyan-400 cursor-pointer transition-colors">
              <Upload className="w-4 h-4" />
              <span>Upload Data</span>
              <input type="file" className="hidden" accept=".csv,.xlsx,.xls" onChange={handleFileUpload} />
            </label>

            {/* Auto-detect Data Types */}
            <button
              onClick={handleAutoDetectDataTypes}
              disabled={!data || data.length === 0}
              className="flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-lg text-sm text-slate-300 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Database className="w-4 h-4" />
              <span>Auto-detect Data Types</span>
            </button>

            {/* Test Assumptions */}
            <button
              onClick={handleTestAssumptions}
              disabled={!selectedAnalysis || !data || data.length === 0}
              className="flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-lg text-sm text-slate-300 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <CheckCircle className="w-4 h-4" />
              <span>Test Assumptions</span>
            </button>

            {/* Suggest Tests */}
            <button
              onClick={handleSuggestTests}
              disabled={!data || data.length === 0}
              className="flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-lg text-sm text-slate-300 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Sparkles className="w-4 h-4" />
              <span>Suggest Tests</span>
            </button>

            {/* Generate Effect Sizes */}
            <button
              onClick={handleGenerateEffectSizes}
              disabled={!results}
              className="flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-lg text-sm text-slate-300 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <BarChart className="w-4 h-4" />
              <span>Effect Sizes</span>
            </button>

            {/* Generate APA Report */}
            <button
              onClick={handleGenerateAPAReport}
              disabled={!results}
              className="flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-lg text-sm text-slate-300 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <FileText className="w-4 h-4" />
              <span>APA Report</span>
            </button>

            {/* Generate Interpretation */}
            <button
              onClick={handleGenerateInterpretation}
              disabled={!results}
              className="flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-lg text-sm text-slate-300 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Info className="w-4 h-4" />
              <span>Interpretation</span>
            </button>

            {/* Export to DOCX */}
            <button
              onClick={handleExportToDocx}
              disabled={!results}
              className="flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-lg text-sm text-slate-300 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Download className="w-4 h-4" />
              <span>Export DOCX</span>
            </button>
          </div>
        </div>

        {/* Content Grid */}
        <div className="flex-1 overflow-hidden grid grid-cols-2 gap-4 p-4">
          {/* Left Panel - Parameters */}
          <div className="flex flex-col border border-slate-800 rounded-lg bg-slate-950/50 overflow-hidden">
            <div className="p-4 border-b border-slate-800">
              <h2 className="text-lg font-semibold text-cyan-400 flex items-center gap-2">
                <Sparkles className="w-5 h-5" />
                Parameters
              </h2>
            </div>
            <div className="flex-1 overflow-y-auto p-4">
              <ParameterForm
                analysisType={selectedAnalysis}
                data={data}
                dataTypes={dataTypes}
                parameters={parameters}
                onParametersChange={setParameters}
                disabled={isAnalyzing}
              />
            </div>
            <div className="p-4 border-t border-slate-800">
              <button
                onClick={handleRunAnalysis}
                disabled={!selectedAnalysis || !data || data.length === 0 || isAnalyzing}
                className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-cyan-600 hover:bg-cyan-700 disabled:bg-slate-800 disabled:text-slate-500 text-white rounded-lg font-medium transition-colors disabled:cursor-not-allowed"
              >
                {isAnalyzing ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    <span>Analyzing...</span>
                  </>
                ) : (
                  <>
                    <Play className="w-4 h-4" />
                    <span>Run Analysis</span>
                  </>
                )}
              </button>
            </div>
          </div>

          {/* Right Panel - Results */}
          <div className="flex flex-col border border-slate-800 rounded-lg bg-slate-950/50 overflow-hidden">
            <div className="p-4 border-b border-slate-800">
              <h2 className="text-lg font-semibold text-cyan-400 flex items-center gap-2">
                <BarChart className="w-5 h-5" />
                Results
              </h2>
            </div>
            <div className="flex-1 overflow-y-auto p-4">
              {error && (
                <div className="mb-4 p-4 bg-red-950/30 border border-red-900 rounded-lg flex items-start gap-3">
                  <AlertTriangle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
                  <div>
                    <h3 className="text-sm font-medium text-red-400">Error</h3>
                    <p className="text-sm text-slate-300 mt-1">{error}</p>
                  </div>
                </div>
              )}

              {results ? (
                <ResultsViewer result={results} data={data} analysisType={selectedAnalysis} />
              ) : (
                <div className="flex items-center justify-center h-full text-slate-500">
                  <div className="text-center">
                    <BarChart className="w-12 h-12 mx-auto mb-4 opacity-50" />
                    <p>Run an analysis to see results</p>
                    <p className="text-xs mt-2">Select an analysis, configure parameters, and upload data to get started.</p>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Bottom Panel - Data Info */}
        {data && data.length > 0 && (
          <div className="border-t border-slate-800 p-4">
            <div className="bg-slate-900/30 rounded-lg p-4 border border-slate-800">
              <h3 className="text-sm font-medium text-cyan-400 mb-3 flex items-center gap-2">
                <Database className="w-4 h-4" />
                Data Information
              </h3>
              <div className="grid grid-cols-4 gap-4 text-sm">
                <div>
                  <div className="text-slate-500">Total Rows</div>
                  <div className="text-slate-200 font-medium">{data.length}</div>
                </div>
                <div>
                  <div className="text-slate-500">Total Columns</div>
                  <div className="text-slate-200 font-medium">{Object.keys(data[0]).length}</div>
                </div>
                <div>
                  <div className="text-slate-500">Numeric Columns</div>
                  <div className="text-slate-200 font-medium">{dataTypes.filter(d => d.type === 'numeric').length}</div>
                </div>
                <div>
                  <div className="text-slate-500">Categorical Columns</div>
                  <div className="text-slate-200 font-medium">{dataTypes.filter(d => d.type === 'categorical' || d.type === 'binary').length}</div>
                </div>
              </div>
              {autoDetectedDataTypes && (
                <div className="mt-3 pt-3 border-t border-slate-800">
                  <div className="text-xs text-green-400 flex items-center gap-1">
                    <CheckCircle className="w-3 h-3" />
                    Data types auto-detected successfully
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
