import React from 'react';
import analysisDefinitions from '@/lib/statistics/analysis-definitions';
import { Info, AlertTriangle, CheckCircle, XCircle, HelpCircle } from 'lucide-react';

export default function ParameterForm({ analysisType, data, dataTypes, parameters, onParametersChange, disabled }) {
  if (!analysisType) {
    return (
      <div className="h-full flex flex-col items-center justify-center text-slate-500">
        <div className="text-center">
          <Info className="w-12 h-12 mx-auto mb-4 opacity-50" />
          <p className="text-sm">Select an analysis type to see parameters</p>
        </div>
      </div>
    );
  }

  // Find analysis definition
  let analysisDef = null;
  for (const category of analysisDefinitions) {
    const found = category.analyses.find(a => a.id === analysisType);
    if (found) {
      analysisDef = found;
      break;
    }
  }

  if (!analysisDef) {
    return (
      <div className="h-full flex items-center justify-center text-red-400">
        <div className="text-center">
          <AlertTriangle className="w-12 h-12 mx-auto mb-4" />
          <p className="text-sm">Analysis type not found</p>
        </div>
      </div>
    );
  }

  const handleParameterChange = (name, value) => {
    onParametersChange({ ...parameters, [name]: value });
  };

  const getNumericColumns = () => dataTypes.filter(d => d.type === 'numeric').map(d => d.name);
  const getCategoricalColumns = () => dataTypes.filter(d => d.type === 'categorical' || d.type === 'binary').map(d => d.name);
  const getAllColumns = () => dataTypes.map(d => d.name);

  const renderParameter = (param) => {
    const value = parameters[param.name] ?? param.default;
    const error = param.validation ? param.validation(value) : null;

    const numericColumns = getNumericColumns();
    const categoricalColumns = getCategoricalColumns();
    const allColumns = getAllColumns();

    let inputElement = null;

    // Column selector
    if (param.options && param.options.some(o => ['outcome', 'group', 'time', 'event', 'variable1', 'variable2', 'test', 'reference'].includes(o.value))) {
      let options = param.options;
      
      // Auto-populate column options based on parameter purpose
      if (param.options.some(o => o.value === 'outcome')) {
        options = numericColumns.map(col => ({ value: col, label: col }));
      } else if (param.options.some(o => o.value === 'group')) {
        options = categoricalColumns.map(col => ({ value: col, label: col }));
      } else if (param.options.some(o => o.value === 'time' || o.value === 'event')) {
        options = numericColumns.map(col => ({ value: col, label: col }));
      } else if (param.options.some(o => o.value === 'variable1' || o.value === 'variable2')) {
        options = allColumns.map(col => ({ value: col, label: col }));
      }

      inputElement = (
        <select
          value={value || ''}
          onChange={(e) => handleParameterChange(param.name, e.target.value)}
          disabled={disabled}
          className={`w-full px-3 py-2 bg-slate-900 border rounded-lg text-sm text-slate-200 focus:outline-none focus:ring-2 transition-colors ${
            error ? 'border-red-900 focus:border-red-500' : 'border-slate-700 focus:border-cyan-500'
          }`}
        >
          <option value="">Select {param.label}</option>
          {options.map(opt => (
            <option key={opt.value} value={opt.value}>{opt.label}</option>
          ))}
        </select>
      );
    }
    // Select dropdown
    else if (param.type === 'select') {
      inputElement = (
        <select
          value={value || ''}
          onChange={(e) => handleParameterChange(param.name, e.target.value)}
          disabled={disabled}
          className={`w-full px-3 py-2 bg-slate-900 border rounded-lg text-sm text-slate-200 focus:outline-none focus:ring-2 transition-colors ${
            error ? 'border-red-900 focus:border-red-500' : 'border-slate-700 focus:border-cyan-500'
          }`}
        >
          {param.options && param.options.map(opt => (
            <option key={opt.value} value={opt.value}>{opt.label}</option>
          ))}
        </select>
      );
    }
    // Multi-select
    else if (param.type === 'multiselect') {
      const selectedOptions = Array.isArray(value) ? value : [];
      
      inputElement = (
        <div className="space-y-2">
          {param.options && param.options.map(opt => (
            <label key={opt.value} className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={selectedOptions.includes(opt.value)}
                onChange={(e) => {
                  if (e.target.checked) {
                    handleParameterChange(param.name, [...selectedOptions, opt.value]);
                  } else {
                    handleParameterChange(param.name, selectedOptions.filter(v => v !== opt.value));
                  }
                }}
                disabled={disabled}
                className="w-4 h-4 rounded border-slate-700 bg-slate-900 text-cyan-500 focus:ring-cyan-500"
              />
              <span className="text-sm text-slate-200">{opt.label}</span>
            </label>
          ))}
        </div>
      );
    }
    // Number input
    else if (param.type === 'number') {
      inputElement = (
        <input
          type="number"
          value={value ?? ''}
          onChange={(e) => handleParameterChange(param.name, e.target.value ? parseFloat(e.target.value) : null)}
          disabled={disabled}
          min={param.min}
          max={param.max}
          step={param.step || 0.01}
          placeholder={param.placeholder}
          className={`w-full px-3 py-2 bg-slate-900 border rounded-lg text-sm text-slate-200 focus:outline-none focus:ring-2 transition-colors ${
            error ? 'border-red-900 focus:border-red-500' : 'border-slate-700 focus:border-cyan-500'
          }`}
        />
      );
    }
    // Text input
    else if (param.type === 'text') {
      inputElement = (
        <input
          type="text"
          value={value || ''}
          onChange={(e) => handleParameterChange(param.name, e.target.value)}
          disabled={disabled}
          placeholder={param.placeholder}
          className={`w-full px-3 py-2 bg-slate-900 border rounded-lg text-sm text-slate-200 focus:outline-none focus:ring-2 transition-colors ${
            error ? 'border-red-900 focus:border-red-500' : 'border-slate-700 focus:border-cyan-500'
          }`}
        />
      );
    }
    // Checkbox
    else if (param.type === 'checkbox') {
      inputElement = (
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={value ?? false}
            onChange={(e) => handleParameterChange(param.name, e.target.checked)}
            disabled={disabled}
            className="w-4 h-4 rounded border-slate-700 bg-slate-900 text-cyan-500 focus:ring-cyan-500"
          />
          <span className="text-sm text-slate-200">{param.label}</span>
        </label>
      );
    }

    return (
      <div key={param.name} className="space-y-1">
        <div className="flex items-center gap-2">
          <label className="text-sm font-medium text-slate-300">
            {param.label}
            {param.required && <span className="text-red-400 ml-1">*</span>}
          </label>
          {param.description && (
            <div className="group relative">
              <HelpCircle className="w-4 h-4 text-slate-500 cursor-help" />
              <div className="absolute left-0 top-full mt-1 w-64 p-2 bg-slate-800 border border-slate-700 rounded-lg text-xs text-slate-300 shadow-xl opacity-0 group-hover:opacity-100 transition-opacity z-10">
                {param.description}
              </div>
            </div>
          )}
        </div>
        {inputElement}
        {error && (
          <div className="flex items-center gap-1 text-xs text-red-400">
            <XCircle className="w-3 h-3" />
            <span>{error}</span>
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="space-y-4">
      {/* Analysis Info */}
      <div className="p-3 bg-slate-900/50 border border-slate-800 rounded-lg">
        <div className="flex items-start gap-3">
          <Info className="w-5 h-5 text-cyan-400 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <h3 className="text-sm font-medium text-slate-200">{analysisDef.name}</h3>
            <p className="text-xs text-slate-500 mt-1">{analysisDef.description}</p>
            
            {analysisDef.examples && analysisDef.examples.length > 0 && (
              <div className="mt-2">
                <p className="text-xs font-medium text-slate-400 mb-1">Examples:</p>
                <ul className="text-xs text-slate-500 list-disc list-inside space-y-1">
                  {analysisDef.examples.slice(0, 2).map((example, i) => (
                    <li key={i}>{example}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Data Status */}
      {data.length === 0 ? (
        <div className="p-3 bg-orange-950/20 border border-orange-900/30 rounded-lg flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-orange-400 flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-medium text-orange-400">No data loaded</p>
            <p className="text-xs text-slate-500 mt-1">Upload a data file to begin analysis</p>
          </div>
        </div>
      ) : (
        <div className="p-3 bg-emerald-950/20 border border-emerald-900/30 rounded-lg flex items-start gap-3">
          <CheckCircle className="w-5 h-5 text-emerald-400 flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-medium text-emerald-400">Data loaded</p>
            <p className="text-xs text-slate-500 mt-1">
              {data.length} rows × {Object.keys(data[0]).length} columns
            </p>
          </div>
        </div>
      )}

      {/* Parameters */}
      <div className="space-y-3">
        {analysisDef.parameters.map(param => renderParameter(param))}
      </div>

      {/* Assumptions */}
      {analysisDef.assumptions && analysisDef.assumptions.length > 0 && (
        <div className="p-3 bg-slate-900/30 border border-slate-800 rounded-lg">
          <h4 className="text-xs font-medium text-slate-400 mb-2">Assumptions</h4>
          <ul className="text-xs text-slate-500 space-y-1">
            {analysisDef.assumptions.map((assumption, i) => (
              <li key={i} className="flex items-start gap-2">
                <span className="text-cyan-400">•</span>
                <span>{assumption}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
