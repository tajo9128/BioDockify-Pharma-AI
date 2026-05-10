import { DataTypeDetection } from '@/types/statistics';

/**
 * Auto-detect data types for columns in a dataset
 */
export function detectDataTypes(data: any[]): DataTypeDetection[] {
  if (!data || data.length === 0) return [];

  const columns = Object.keys(data[0]);
  const detections: DataTypeDetection[] = [];

  for (const column of columns) {
    const values = data.map(row => row[column]).filter(v => v !== null && v !== undefined && v !== '');
    const detection = analyzeColumn(column, values);
    detections.push(detection);
  }

  return detections;
}

function analyzeColumn(column: string, values: any[]): DataTypeDetection {
  if (values.length === 0) {
    return { column, type: 'categorical', confidence: 0.5, uniqueCount: 0, missingCount: 0 };
  }

  const missingCount = values.length - values.filter(v => v !== null && v !== undefined && v !== '').length;
  const uniqueValues = new Set(values);
  const uniqueCount = uniqueValues.size;
  const totalValues = values.length;

  // Check if numeric
  const numericValues = values.map(v => parseFloat(v)).filter(v => !isNaN(v));
  const isNumeric = numericValues.length > 0;
  const allNumeric = numericValues.length === totalValues;

  // Check if binary
  if (uniqueCount === 2 && isNumeric) {
    const uniqueNums = Array.from(uniqueValues).map(v => parseFloat(v));
    if (uniqueNums.every(n => n === 0 || n === 1)) {
      return {
        column,
        type: 'binary',
        confidence: 1.0,
        values: Array.from(uniqueValues),
        uniqueCount,
        missingCount
      };
    }
  }

  // Check if datetime
  if (isDateTime(values)) {
    return {
      column,
      type: 'datetime',
      confidence: 0.95,
      values: values.slice(0, 5),
      uniqueCount,
      missingCount
    };
  }

  // Check if ordinal (numeric with limited unique values)
  if (allNumeric && uniqueCount <= 10 && uniqueCount >= 3) {
    return {
      column,
      type: 'ordinal',
      confidence: 0.8,
      values: Array.from(uniqueValues).slice(0, 5),
      uniqueCount,
      missingCount
    };
  }

  // Check if numeric
  if (allNumeric) {
    return {
      column,
      type: 'numeric',
      confidence: 0.9,
      uniqueCount,
      missingCount
    };
  }

  // Check if categorical with many unique values
  if (uniqueCount > totalValues * 0.5) {
    return {
      column,
      type: 'categorical',
      confidence: 0.7,
      values: values.slice(0, 5),
      uniqueCount,
      missingCount
    };
  }

  // Default to categorical
  return {
    column,
    type: 'categorical',
    confidence: 0.8,
    values: values.slice(0, 5),
    uniqueCount,
    missingCount
  };
}

function isDateTime(values: any[]): boolean {
  const datePatterns = [
    /^\d{4}-\d{2}-\d{2}$/, // YYYY-MM-DD
    /^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}/, // ISO datetime
    /^\d{1,2}\/\d{1,2}\/\d{4}/, // MM/DD/YYYY or DD/MM/YYYY
    /^\d{4}\/\d{2}\/\d{2}/, // YYYY/MM/DD
  ];

  const dateCount = values.filter(v => {
    if (typeof v !== 'string') return false;
    return datePatterns.some(pattern => pattern.test(v));
  }).length;

  return dateCount > values.length * 0.8;
}

/**
 * Get columns by data type
 */
export function getColumnsByType(detections: DataTypeDetection[], type: string): string[] {
  return detections.filter(d => d.type === type).map(d => d.column);
}

/**
 * Get suggested columns for specific analysis types
 */
export function getSuggestedColumns(detections: DataTypeDetection[]): {
  numeric: string[];
  categorical: string[];
  binary: string[];
  datetime: string[];
  groups: string[];
} {
  return {
    numeric: getColumnsByType(detections, 'numeric'),
    categorical: getColumnsByType(detections, 'categorical'),
    binary: getColumnsByType(detections, 'binary'),
    datetime: getColumnsByType(detections, 'datetime'),
    groups: [...getColumnsByType(detections, 'categorical'), ...getColumnsByType(detections, 'binary')]
  };
}
