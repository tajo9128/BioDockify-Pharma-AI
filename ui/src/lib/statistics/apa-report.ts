import { StatisticsResult, AnalysisType, ConfidenceInterval } from '@/types/statistics';

/**
 * Helper to get CI bounds as tuple
 */
function getCIBounds(ci: [number, number] | ConfidenceInterval): [number, number] {
  return Array.isArray(ci) ? ci : [ci.lower, ci.upper];
}

/**
 * Generate APA-formatted statistical report
 */
export function generateAPAReport(result: StatisticsResult): string {
  const { analysisType, testStatistics, pValue, pValues, effectSize, effectSizes, confidenceInterval, confidenceIntervals, confidenceLevel = 0.95 } = result;
  
  let report = '';
  
  // Header
  report += 'Statistical Analysis Report\n';
  report += '========================\n\n';
  
  // Analysis type
  report += `Analysis: ${formatAnalysisType(analysisType)}\n`;
  
  // Main statistic
  if (testStatistics) {
    const entries = Object.entries(testStatistics);
    if (entries.length > 0) {
      report += '\nTest Statistics:\n';
      entries.forEach(([key, value]) => {
        report += `  ${formatStatName(key)}: ${formatNumber(value)}\n`;
      });
    }
  }
  
  // P-values
  if (pValue !== undefined) {
    report += `\np ${formatPValue(pValue)}\n`;
  } else if (pValues) {
    const entries = Object.entries(pValues);
    if (entries.length > 0) {
      report += '\nP-values:\n';
      entries.forEach(([key, value]) => {
        report += `  ${key}: p = ${formatPValue(value)}\n`;
      });
    }
  }
  
  // Effect sizes
  if (effectSize !== undefined) {
    report += `\nEffect Size: ${formatNumber(effectSize)}`;
    if (result.effectSizeInterpretation) {
      report += ` (${result.effectSizeInterpretation})`;
    }
    report += '\n';
  } else if (effectSizes) {
    const entries = Object.entries(effectSizes);
    if (entries.length > 0) {
      report += '\nEffect Sizes:\n';
      entries.forEach(([key, value]) => {
        report += `  ${formatStatName(key)}: ${formatNumber(value)}\n`;
      });
    }
  }
  
  // Confidence intervals
  if (confidenceInterval) {
    const [lower, upper] = getCIBounds(confidenceInterval);
    report += `\n${Math.round(confidenceLevel * 100)}% CI [${formatNumber(lower)}, ${formatNumber(upper)}]\n`;
  } else if (confidenceIntervals) {
    const entries = Object.entries(confidenceIntervals);
    if (entries.length > 0) {
      report += `\n${Math.round(confidenceLevel * 100)}% Confidence Intervals:\n`;
      entries.forEach(([key, value]) => {
        const [lower, upper] = getCIBounds(value);
        report += `  ${key}: [${formatNumber(lower)}, ${formatNumber(upper)}]\n`;
      });
    }
  }
  
  // Interpretation
  if (result.interpretation) {
    report += '\nInterpretation:\n';
    report += `${result.interpretation}\n`;
  }
  
  // Recommendation
  if (result.recommendation) {
    report += `\nRecommendation: ${result.recommendation}\n`;
  }
  
  // Assumption checks
  if (result.assumptionsCheck && result.assumptionsCheck.length > 0) {
    report += '\nAssumption Checks:\n';
    result.assumptionsCheck.forEach(check => {
      const statusIcon = check.status === 'passed' ? '✓' : check.status === 'failed' ? '✗' : '⚠';
      report += `  ${statusIcon} ${check.name}`;
      if (check.interpretation) {
        report += `: ${check.interpretation}`;
      }
      report += '\n';
    });
  }
  
  return report;
}

/**
 * Generate inline APA citation format
 */
export function generateInlineAPA(result: StatisticsResult): string {
  const { analysisType, testStatistics, pValue, pValues, effectSize, effectSizes, confidenceInterval, confidenceLevel = 0.95 } = result;
  
  let citation = '';
  
  // Get primary test statistic
  const statEntries = Object.entries(testStatistics || {});
  if (statEntries.length > 0) {
    const [statName, statValue] = statEntries[0];
    citation += `${formatStatSymbol(statName)} = ${formatNumber(statValue)}`;
  }
  
  // Add p-value
  if (pValue !== undefined) {
    citation += `, ${formatPValue(pValue)}`;
  } else if (pValues) {
    const pEntries = Object.entries(pValues);
    if (pEntries.length > 0) {
      citation += `, p = ${formatPValue(pEntries[0][1])}`;
    }
  }
  
  // Add effect size
  if (effectSize !== undefined) {
    citation += `, d = ${formatNumber(effectSize)}`;
  } else if (effectSizes) {
    const esEntries = Object.entries(effectSizes);
    if (esEntries.length > 0) {
      citation += `, ${formatStatSymbol(esEntries[0][0])} = ${formatNumber(esEntries[0][1])}`;
    }
  }
  
  // Add confidence interval
  if (confidenceInterval) {
    const [lower, upper] = getCIBounds(confidenceInterval);
    citation += `, ${Math.round(confidenceLevel * 100)}% CI [${formatNumber(lower)}, ${formatNumber(upper)}]`;
  }
  
  return citation;
}

/**
 * Generate interpretation paragraph
 */
export function generateInterpretationParagraph(result: StatisticsResult): string {
  const { analysisType, pValue, pValues, effectSize, effectSizes, confidenceInterval } = result;
  
  let paragraph = '';
  
  // Determine significance
  const isSignificant = pValue !== undefined ? pValue < 0.05 : 
                        pValues ? Object.values(pValues).some(p => p < 0.05) : false;
  
  // Start with the analysis type
  paragraph += `A ${formatAnalysisType(analysisType)} was conducted to `;
  
  // Add appropriate context based on analysis type
  switch (analysisType) {
    case 't_test':
    case 'mann_whitney':
      paragraph += 'compare the means between two groups. ';
      break;
    case 'anova':
    case 'kruskal_wallis':
      paragraph += 'compare means across multiple groups. ';
      break;
    case 'correlation':
      paragraph += 'examine the relationship between variables. ';
      break;
    case 'kaplan_meier':
      paragraph += 'estimate survival functions. ';
      break;
    case 'log_rank':
      paragraph += 'compare survival distributions between groups. ';
      break;
    case 'cox_ph':
      paragraph += 'assess the effect of covariates on survival. ';
      break;
    case 'logistic_regression':
      paragraph += 'predict a binary outcome using predictor variables. ';
      break;
    case 'tost':
    case 'ci_approach':
      paragraph += 'assess bioequivalence between formulations. ';
      break;
    case 'nca_pk':
      paragraph += 'estimate pharmacokinetic parameters. ';
      break;
    default:
      paragraph += 'analyze the data. ';
  }
  
  // Add results
  if (isSignificant) {
    paragraph += 'The results indicated a statistically significant difference';
    if (effectSize !== undefined) {
      const magnitude = Math.abs(effectSize) > 0.8 ? 'large' : 
                       Math.abs(effectSize) > 0.5 ? 'medium' : 
                       Math.abs(effectSize) > 0.2 ? 'small' : 'negligible';
      paragraph += ` with a ${magnitude} effect size`;
    }
    paragraph += '. ';
  } else {
    paragraph += 'No statistically significant difference was found. ';
  }
  
  // Add confidence interval interpretation
  if (confidenceInterval) {
    const [lower, upper] = getCIBounds(confidenceInterval);
    if (lower > 0 || upper < 0) {
      paragraph += `The ${Math.round((result.confidenceLevel || 0.95) * 100)}% confidence interval [${formatNumber(lower)}, ${formatNumber(upper)}] does not include zero, supporting the significance of the finding. `;
    } else {
      paragraph += `The ${Math.round((result.confidenceLevel || 0.95) * 100)}% confidence interval [${formatNumber(lower)}, ${formatNumber(upper)}] includes zero, indicating uncertainty about the effect. `;
    }
  }
  
  // Add bioequivalence specific interpretation
  if (['tost', 'ci_approach'].includes(analysisType)) {
    if (confidenceInterval) {
      const [lower, upper] = getCIBounds(confidenceInterval);
      if (lower >= 80 && upper <= 125) {
        paragraph += 'The 90% confidence interval falls within the bioequivalence acceptance range (80-125%), indicating bioequivalence. ';
      } else {
        paragraph += 'The 90% confidence interval falls outside the bioequivalence acceptance range, indicating failure to demonstrate bioequivalence. ';
      }
    }
  }
  
  // Add clinical/research significance
  if (result.recommendation) {
    paragraph += result.recommendation;
  }
  
  return paragraph;
}

// Helper functions

function formatAnalysisType(type: AnalysisType): string {
  const names: Record<AnalysisType, string> = {
    descriptive_statistics: 'Descriptive Statistics Analysis',
    t_test: 'Independent Samples T-Test',
    anova: 'One-Way ANOVA',
    correlation: 'Correlation Analysis',
    mann_whitney: 'Mann-Whitney U Test',
    kruskal_wallis: 'Kruskal-Wallis Test',
    power_analysis: 'Power Analysis',
    kaplan_meier: 'Kaplan-Meier Survival Estimator',
    log_rank: 'Log-Rank Test',
    cox_ph: 'Cox Proportional Hazards Model',
    tost: 'Two One-Sided Tests (TOST)',
    ci_approach: 'Confidence Interval Approach',
    crossover_anova: 'Crossover ANOVA',
    logistic_regression: 'Logistic Regression',
    poisson_regression: 'Poisson Regression',
    linear_mixed_effects: 'Linear Mixed Effects Model',
    generalized_estimating_equations: 'Generalized Estimating Equations',
    repeated_measures_anova: 'Repeated Measures ANOVA',
    multivariate_analysis: 'Multivariate Analysis',
    principal_component_analysis: 'Principal Component Analysis',
    cluster_analysis: 'Cluster Analysis',
    meta_analysis: 'Meta-Analysis',
    nca_pk: 'Non-Compartmental PK Analysis',
    auc_calculation: 'AUC Calculation',
    cmax_tmax: 'Cmax and Tmax Determination',
    half_life: 'Half-Life Estimation',
    clearance: 'Clearance and Volume of Distribution',
    pd_response_modeling: 'PD Response Modeling',
    dose_proportionality: 'Dose Proportionality',
    bonferroni: 'Bonferroni Correction',
    holm: 'Holm-Bonferroni Method',
    bh_fdr: 'Benjamini-Hochberg FDR Control',
    by: 'Benjamini-Yekutieli FDR Control',
    wilcoxon_signed_rank: 'Wilcoxon Signed-Rank Test',
    sign_test: 'Sign Test',
    friedman: 'Friedman Test',
    dunns: "Dunn's Post-Hoc Test",
    chi_square: 'Chi-Square Test',
    fisher_exact: 'Fisher\'s Exact Test',
    mcnemar: 'McNemar\'s Test',
    cmh: 'Cochran-Mantel-Haenszel Test'
  };
  return names[type] || type;
}

function formatStatName(name: string): string {
  const formatted: Record<string, string> = {
    't': 't statistic',
    'F': 'F statistic',
    'chi2': 'χ² statistic',
    'z': 'z statistic',
    'U': 'U statistic',
    'H': 'H statistic',
    'W': 'W statistic',
    'df': 'degrees of freedom',
    'df1': 'numerator df',
    'df2': 'denominator df',
    'r': 'correlation coefficient',
    'r2': 'coefficient of determination',
    'eta_squared': 'η²',
    'omega_squared': 'ω²',
    'cohen_d': "Cohen's d",
    'hedges_g': 'Hedges\' g',
    'cliffs_delta': 'Cliff\'s δ',
    'odds_ratio': 'odds ratio',
    'hazard_ratio': 'hazard ratio',
    'incidence_rate_ratio': 'incidence rate ratio',
    'auc': 'AUC',
    'cmax': 'Cmax',
    'tmax': 'Tmax',
    'half_life': 't₁/₂',
    'clearance': 'CL',
    'volume_of_distribution': 'Vd',
    'log_likelihood': 'log-likelihood',
    'aic': 'AIC',
    'bic': 'BIC'
  };
  return formatted[name] || name;
}

function formatStatSymbol(name: string): string {
  const symbols: Record<string, string> = {
    't_statistic': 't',
    'f_statistic': 'F',
    'chi2_statistic': 'χ²',
    'z_statistic': 'z',
    'u_statistic': 'U',
    'h_statistic': 'H',
    'w_statistic': 'W',
    'eta_squared': 'η²',
    'omega_squared': 'ω²',
    'cohen_d': 'd',
    'hedges_g': 'g',
    'cliffs_delta': 'δ',
    'odds_ratio': 'OR',
    'hazard_ratio': 'HR',
    'incidence_rate_ratio': 'IRR'
  };
  return symbols[name] || name;
}

function formatPValue(p: number): string {
  if (p < 0.001) {
    return 'p < .001';
  } else if (p < 0.01) {
    return `p = ${p.toFixed(3)}`;
  } else {
    return `p = ${p.toFixed(2)}`;
  }
}

function formatNumber(num: number): string {
  if (Math.abs(num) < 0.01 || Math.abs(num) >= 1000) {
    return num.toExponential(2);
  } else {
    return num.toFixed(2);
  }
}
