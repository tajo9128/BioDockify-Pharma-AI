import React, { useState, useEffect } from 'react';
import { AnalysisType, AnalysisParameter, DataTypeDetection } from '@/types/statistics';
import { getAnalysesByCategory } from '@/lib/statistics/analysis-definitions';
import { getColumnsByType, getSuggestedColumns } from '@/lib/statistics/data-detection';
import { Info, Sliders, Database, Clock } from 'lucide-react';

interface ParameterFormProps {
  analysisType: AnalysisType | null;
  data: any[];
  dataTypes: DataTypeDetection[];
  parameters: Record<string, any>;
  onParametersChange: (params: Record<string, any>) => void;
  disabled?: boolean;
}

export default function ParameterForm({ 
  analysisType, 
  data, 
  dataTypes,
  parameters, 
  onParametersChange,
  disabled = false
}: ParameterFormProps) {
  const [localParams, setLocalParams] = useState<Record<string, any>>(parameters);
  const suggestedColumns = dataTypes.length > 0 ? getSuggestedColumns(dataTypes) : {
    numeric: [], categorical: [], binary: [], datetime: [], groups: []
  };

  useEffect(() => {
    setLocalParams(parameters);
  }, [parameters]);

  if (!analysisType) {
    return (
      <div className="flex items-center justify-center h-64 text-slate-500">
        <div className="text-center">
          <Sliders className="w-12 h-12 mx-auto mb-4 opacity-50" />
          <p>Select an analysis type to see parameters</p>
        </div>
      </div>
    );
  }

  // Find the analysis definition
  const allAnalyses = Object.values(getAnalysesByCategory('basic'))
    .concat(...Object.values(getAnalysesByCategory('survival')))
    .concat(...Object.values(getAnalysesByCategory('bioequivalence')))
    .concat(...Object.values(getAnalysesByCategory('advanced')))
    .concat(...Object.values(getAnalysesByCategory('pkpd')))
    .concat(...Object.values(getAnalysesByCategory('multiplicity')))
    .concat(...Object.values(getAnalysesByCategory('categorical')));

  const analysis = allAnalyses.find(a => a.id === analysisType);
  
  if (!analysis || !analysis.parameters) {
    return (
      <div className="flex items-center justify-center h-64 text-slate-500">
        <div className="text-center">
          <Info className="w-12 h-12 mx-auto mb-4 opacity-50" />
          <p>No parameters required for this analysis</p>
        </div>
      </div>
    );
  }

  const handleParameterChange = (paramName: string, value: any) => {
    const newParams = { ...localParams, [paramName]: value };
    setLocalParams(newParams);
    onParametersChange(newParams);
  };

  const renderParameterInput = (param: AnalysisParameter) => {
    const value = localParams[param.name] !== undefined ? localParams[param.name] : param.defaultValue;
    const isRequired = param.required;

    switch (param.type) {
      case 'column':
        return (
          <select
            value={value || ''}
            onChange={(e) => handleParameterChange(param.name, e.target.value)}
            disabled={disabled}
            className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-200 focus:ring-1 focus:ring-cyan-500 focus:border-cyan-500 outline-none disabled:opacity-50"
            required={isRequired}
          >
            <option value="">{isRequired ? 'Select a column *' : 'Select a column (optional)'}</option>
            {data.length > 0 && Object.keys(data[0]).map((col) => {
              const colType = dataTypes.find(d => d.column === col);
              const typeIcon = colType ? `(${colType.type})` : '';
              const suggestion = param.subtype === 'numeric' && colType?.type === 'numeric' ? ' (Recommended)' :
                               param.subtype === 'categorical' && ['categorical', 'binary'].includes(colType?.type || '') ? ' (Recommended)' :
                               param.subtype === 'group' && ['categorical', 'binary'].includes(colType?.type || '') ? ' (Recommended)' :
                               param.subtype === 'datetime' && colType?.type === 'datetime' ? ' (Recommended)' : '';
              return (
                <option key={col} value={col}>
                  {col} {typeIcon}{suggestion}
                </option>
              );
            })}
          </select>
        );

      case 'columns':
        return (
          <select
            value={value || ''}
            onChange={(e) => handleParameterChange(param.name, e.target.value)}
            disabled={disabled}
            className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-200 focus:ring-1 focus:ring-cyan-500 focus:border-cyan-500 outline-none disabled:opacity-50"
            required={isRequired}
          >
            <option value="">{isRequired ? 'Select columns *' : 'Select columns (optional)'}</option>
            {data.length > 0 && Object.keys(data[0]).map((col) => {
              const colType = dataTypes.find(d => d.column === col);
              const typeIcon = colType ? `(${colType.type})` : '';
              return (
                <option key={col} value={col}>
                  {col} {typeIcon}
                </option>
              );
            })}
          </select>
        );

      case 'select':
        return (
          <select
            value={value || ''}
            onChange={(e) => handleParameterChange(param.name, e.target.value)}
            disabled={disabled}
            className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-200 focus:ring-1 focus:ring-cyan-500 focus:border-cyan-500 outline-none disabled:opacity-50"
            required={isRequired}
          >
            <option value="">{isRequired ? 'Select an option *' : 'Select an option (optional)'}</option>
            {param.options?.map((opt) => {
              const isString = typeof opt === 'string';
              const optValue = isString ? opt : (opt as { value: string; label: string }).value;
              const optLabel = isString ? opt : (opt as { value: string; label: string }).label;
              return (
                <option key={optValue} value={optValue}>
                  {optLabel}
                </option>
              );
            })}
          </select>
        );

      case 'number':
        return (
          <input
            type="number"
            step={param.step || 0.01}
            min={param.min}
            max={param.max}
            value={value || ''}
            onChange={(e) => handleParameterChange(param.name, parseFloat(e.target.value))}
            disabled={disabled}
            placeholder={param.placeholder || ''}
            className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-200 focus:ring-1 focus:ring-cyan-500 focus:border-cyan-500 outline-none disabled:opacity-50"
            required={isRequired}
          />
        );

      case 'boolean':
        return (
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={value || false}
              onChange={(e) => handleParameterChange(param.name, e.target.checked)}
              disabled={disabled}
              className="w-4 h-4 rounded border-slate-700 text-cyan-500 focus:ring-cyan-500 bg-slate-950"
            />
            <span className="text-sm text-slate-300">{value ? 'Yes' : 'No'}</span>
          </label>
        );

      case 'text':
        return (
          <input
            type="text"
            value={value || ''}
            onChange={(e) => handleParameterChange(param.name, e.target.value)}
            disabled={disabled}
            placeholder={param.placeholder || ''}
            className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-200 focus:ring-1 focus:ring-cyan-500 focus:border-cyan-500 outline-none disabled:opacity-50"
            required={isRequired}
          />
        );

      default:
        return (
          <input
            type="text"
            value={value || ''}
            onChange={(e) => handleParameterChange(param.name, e.target.value)}
            disabled={disabled}
            className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-200 focus:ring-1 focus:ring-cyan-500 focus:border-cyan-500 outline-none disabled:opacity-50"
          />
        );
    }
  };

  return (
    <div className="space-y-6">
      {/* Analysis Description */}
      <div className="bg-slate-900/30 rounded-lg p-4 border border-slate-800">
        <h3 className="text-sm font-medium text-cyan-400 mb-2">{analysis.name}</h3>
        <p className="text-sm text-slate-400">{analysis.description}</p>
        {analysis.assumptions && analysis.assumptions.length > 0 && (
          <div className="mt-3">
            <p className="text-xs text-slate-500 font-medium mb-1">Assumptions:</p>
            <ul className="text-xs text-slate-500 space-y-1">
              {analysis.assumptions.map((assumption, idx) => (
                <li key={idx} className="flex items-start gap-2">
                  <span>•</span>
                  <span>{assumption}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {/* Parameters Form */}
      <div className="space-y-4">
        <h3 className="text-sm font-medium text-slate-200 flex items-center gap-2">
          <Sliders className="w-4 h-4" />
          Parameters
        </h3>

        {analysis.parameters.map((param) => (
          <div key={param.name} className="space-y-2">
            <div className="flex items-center gap-2">
              <label className="text-sm font-medium text-slate-200">
                {param.label}
                {param.required && <span className="text-red-400 ml-1">*</span>}
              </label>
              {param.description && (
                <div className="group relative">
                  <Info className="w-4 h-4 text-slate-500 cursor-help" />
                  <div className="absolute left-6 top-0 z-10 invisible group-hover:visible w-64 p-2 bg-slate-800 border border-slate-700 rounded-lg text-xs text-slate-300 shadow-lg">
                    {param.description}
                  </div>
                </div>
              )}
            </div>
            {renderParameterInput(param)}
            {param.hint && (
              <p className="text-xs text-slate-500">{param.hint}</p>
            )}
          </div>
        ))}
      </div>

      {/* Auto-suggestion buttons */}
      <div className="space-y-3 pt-4 border-t border-slate-800">
        <h3 className="text-sm font-medium text-slate-200 flex items-center gap-2">
          <Database className="w-4 h-4" />
          Auto-Suggestions
        </h3>

        <div className="grid grid-cols-2 gap-2">
          {suggestedColumns.numeric.length > 0 && (
            <button
              type="button"
              onClick={() => {
                const outcomeParam = analysis.parameters.find(p => p.subtype === 'numeric');
                if (outcomeParam && suggestedColumns.numeric.length > 0) {
                  handleParameterChange(outcomeParam.name, suggestedColumns.numeric[0]);
                }
              }}
              disabled={disabled}
              className="px-3 py-2 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-lg text-xs text-slate-300 transition-colors disabled:opacity-50"
            >
              Auto-fill Outcome Variable
            </button>
          )}

          {suggestedColumns.groups.length > 0 && (
            <button
              type="button"
              onClick={() => {
                const groupParam = analysis.parameters.find(p => p.subtype === 'group');
                if (groupParam && suggestedColumns.groups.length > 0) {
                  handleParameterChange(groupParam.name, suggestedColumns.groups[0]);
                }
              }}
              disabled={disabled}
              className="px-3 py-2 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-lg text-xs text-slate-300 transition-colors disabled:opacity-50"
            >
              Auto-fill Group Variable
            </button>
          )}

          {suggestedColumns.datetime.length > 0 && (
            <button
              type="button"
              onClick={() => {
                const timeParam = analysis.parameters.find(p => p.subtype === 'datetime');
                if (timeParam && suggestedColumns.datetime.length > 0) {
                  handleParameterChange(timeParam.name, suggestedColumns.datetime[0]);
                }
              }}
              disabled={disabled}
              className="px-3 py-2 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-lg text-xs text-slate-300 transition-colors disabled:opacity-50"
            >
              Auto-fill Time Variable
            </button>
          )}

          <button
            type="button"
            onClick={() => {
              const newParams: Record<string, any> = {};
              analysis.parameters.forEach(param => {
                if (param.defaultValue !== undefined) {
                  newParams[param.name] = param.defaultValue;
                }
              });
              setLocalParams(newParams);
              onParametersChange(newParams);
            }}
            disabled={disabled}
            className="px-3 py-2 bg-cyan-950/30 hover:bg-cyan-950/50 border border-cyan-900 rounded-lg text-xs text-cyan-400 transition-colors disabled:opacity-50"
          >
            Reset to Defaults
          </button>
        </div>
      </div>
    </div>
  );
}
