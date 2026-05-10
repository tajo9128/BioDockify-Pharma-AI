/**
 * Type definitions for Statistics Analysis in BioDockify AI
 * 
 * This file contains all TypeScript interfaces and types for the
 * comprehensive statistics analysis system supporting 25+ analyses.
 */

export type AnalysisCategory = 
  | 'basic'
  | 'survival'
  | 'bioequivalence'
  | 'advanced'
  | 'pkpd'
  | 'multiplicity'
  | 'categorical';

export type DataType = 'numeric' | 'categorical' | 'binary' | 'datetime' | 'text' | 'ordinal';

export interface DataTypeDetection {
  column: string;
  type: 'numeric' | 'categorical' | 'binary' | 'datetime' | 'ordinal';
  confidence: number;
  values?: any[];
  uniqueCount?: number;
  missingCount?: number;
}

export type CorrelationMethod = 'pearson' | 'spearman' | 'kendall';
export type TTestType = 'independent' | 'paired';
export type VarianceAssumption = 'equal' | 'unequal';
export type AlternativeHypothesis = 'two-sided' | 'less' | 'greater';
export type PostHocMethod = 'bonferroni' | 'holm' | 'tukey' | 'dunns' | 'none';
export type PAdjustMethod = 'bonferroni' | 'holm' | 'bh_fdr' | 'by';

export type AnalysisType =
  // Basic Statistics
  | 'descriptive_statistics'
  | 't_test'
  | 'anova'
  | 'correlation'
  | 'mann_whitney'
  | 'kruskal_wallis'
  | 'power_analysis'
  // Survival Analysis
  | 'kaplan_meier'
  | 'log_rank'
  | 'cox_ph'
  // Bioequivalence
  | 'tost'
  | 'ci_approach'
  | 'crossover_anova'
  // Advanced Biostatistics
  | 'logistic_regression'
  | 'poisson_regression'
  | 'linear_mixed_effects'
  | 'generalized_estimating_equations'
  | 'repeated_measures_anova'
  | 'multivariate_analysis'
  | 'principal_component_analysis'
  | 'cluster_analysis'
  // PK/PD Analysis
  | 'nca_pk'
  | 'auc_calculation'
  | 'cmax_tmax'
  | 'half_life'
  | 'clearance'
  | 'pd_response_modeling'
  | 'dose_proportionality'
  // Multiplicity Control
  | 'bonferroni'
  | 'holm'
  | 'bh_fdr'
  | 'by'
  // Categorical Tests
  | 'wilcoxon_signed_rank'
  | 'sign_test'
  | 'friedman'
  | 'dunns'
  | 'chi_square'
  | 'fisher_exact'
  | 'mcnemar'
  | 'cmh'
  // Meta Analysis
  | 'meta_analysis';

export interface DataColumnType {
  name: string;
  type: DataType;
  nullable: boolean;
  unique: number;
  sample?: any[];
}

export interface SuggestedColumn {
  name: string;
  reason: string;
  confidence: number;
}

export interface TestSuggestion {
  analysisType: AnalysisType;
  confidence: number;
  reasons: string[];
  parameters?: Record<string, any>;
}

export interface SuggestedTest {
  analysisType: AnalysisType;
  reason: string;
  confidence: number;
  assumptions?: string[];
}

export interface EffectSizeResult {
  effectSize: number;
  interpretation: string;
  magnitude: 'negligible' | 'small' | 'medium' | 'large';
}

export interface ConfidenceInterval {
  lower: number;
  upper: number;
  level: number;
}

export interface AssumptionCheck {
  name: string;
  status: 'passed' | 'failed' | 'warning';
  testStatistic?: number;
  pValue?: number;
  interpretation: string;
  remedy?: string;
}

// Alias for AnalysisResult used in ResultsViewer
export type StatisticsResult = AnalysisResult;

export interface AnalysisResult {
  analysisType: AnalysisType;
  testStatistics: Record<string, any>;
  pValue?: number;
  pValues?: Record<string, number>;
  confidenceInterval?: [number, number] | ConfidenceInterval;
  confidenceIntervals?: Record<string, [number, number] | ConfidenceInterval>;
  confidenceLevel: number;
  sampleSize: number;
  degreesOfFreedom?: number;
  conclusion: string;
  recommendation?: string;
  significance: number;
  effectSize?: number;
  effectSizes?: Record<string, number>;
  effectSizeInterpretation?: string;
  interpretation?: string;
  assumptionsCheck?: AssumptionCheck[];
  adjustedPValues?: Record<string, number>;
  residuals?: Record<string, any[]>;
  plots?: Record<string, any>;
  tables?: Record<string, any[]>;
}

export interface APAReport {
  inline: string;
  full: string;
  bibliography?: string;
}

export interface AnalysisParameter {
  name: string;
  label: string;
  type: 'text' | 'number' | 'select' | 'multiselect' | 'checkbox' | 'radio' | 'file' | 'column' | 'columns' | 'boolean';
  subtype?: 'numeric' | 'categorical' | 'binary' | 'group' | 'datetime';
  required: boolean;
  default?: any;
  defaultValue?: any;
  options?: Array<{ value: string; label: string } | string>;
  min?: number;
  max?: number;
  step?: number;
  hint?: string;
  placeholder?: string;
  description?: string;
  dependsOn?: string;
  validation?: (value: any) => string | null;
}

export interface AnalysisDefinition {
  id: AnalysisType;
  name: string;
  category: AnalysisCategory;
  description: string;
  parameters: AnalysisParameter[];
  requiredColumns?: string[];
  optionalColumns?: string[];
  outputs?: string[];
  assumptions?: string[];
  examples?: string[];
  references?: string[];
  icon?: string;
  minSampleSize?: number;
}

export interface AnalysisParameters {
  // Common parameters
  outcome?: string;
  group?: string;
  groups?: string[];
  variable1?: string;
  variable2?: string;
  variables?: string[];
  subject?: string;
  
  // T-test specific
  testType?: TTestType;
  varianceAssumption?: VarianceAssumption;
  
  // ANOVA specific
  postHoc?: PostHocMethod;
  
  // Correlation specific
  method?: CorrelationMethod;
  
  // Non-parametric specific
  alternative?: AlternativeHypothesis;
  
  // Power analysis specific
  powerTestType?: string;
  effectSize?: number;
  powerAlpha?: number;
  power?: number;
  sampleSize?: number;
  
  // Survival analysis specific
  time?: string;
  event?: string;
  covariates?: string[];
  strata?: string[];
  
  // Bioequivalence specific
  bioequivalenceTest?: string;
  reference?: string;
  logTransform?: boolean;
  confidenceLevel?: number;
  
  // PK/PD specific
  dose?: number;
  route?: 'IV' | 'EV';
  concentration?: string;
  concentrationColumn?: string;
  
  // Multiplicity control specific
  pValues?: string[];
  multiplicityAlpha?: number;
  q?: number;
  
  // Categorical tests specific
  col1?: string;
  col2?: string;
  stratifyBy?: string;
  correction?: boolean;
  expected?: number[];
  
  // General
  columns?: string[];
  title?: string;
  storeResults?: boolean;
}

export interface DataRow {
  [key: string]: any;
}

export interface DataSet {
  data: DataRow[];
  metadata: {
    rows: number;
    columns: number;
    columnsList: string[];
    columnTypes: Record<string, string>;
  };
}

export interface StatisticsViewProps {
  data?: DataRow[];
  initialAnalysis?: AnalysisType;
}

export interface AnalysisSelectorProps {
  selectedAnalysis: AnalysisType | null;
  onSelect: (analysis: AnalysisType) => void;
  searchQuery: string;
  onSearchChange: (query: string) => void;
}

export interface ParameterFormProps {
  analysisType: AnalysisType | null;
  data: DataRow[];
  dataTypes: DataColumnType[];
  parameters: AnalysisParameters;
  onParametersChange: (params: AnalysisParameters) => void;
  disabled?: boolean;
}

export interface ResultsViewerProps {
  result: AnalysisResult;
  data: DataRow[];
  analysisType: AnalysisType;
}

export interface ExportOptions {
  format: 'docx' | 'pdf' | 'latex' | 'json' | 'csv';
  includeAssumptions: boolean;
  includeInterpretation: boolean;
  includeAPA: boolean;
  includeTables: boolean;
  includeGraphs: boolean;
}
