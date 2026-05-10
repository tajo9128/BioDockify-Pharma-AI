import { StatisticsResult, AnalysisType } from '@/types/statistics';

/**
 * Calculate effect sizes for various statistical tests
 */
export function calculateEffectSize(
  analysisType: AnalysisType,
  data: any,
  testStatistics: any
): {
  effectSize: number;
  effectSizeName: string;
  interpretation: string;
  magnitude: 'negligible' | 'small' | 'medium' | 'large';
} | null {
  switch (analysisType) {
    case 't_test':
      return calculateCohensD(data);
    case 'anova':
      return calculateEtaSquared(testStatistics);
    case 'correlation':
      return calculateCorrelationEffect(testStatistics);
    case 'mann_whitney':
      return calculateRankBiserial(data, testStatistics);
    case 'kruskal_wallis':
      return calculateEpsilonSquared(testStatistics);
    case 'wilcoxon_signed_rank':
      return calculateRankBiserial(data, testStatistics);
    case 'chi_square':
      return calculatePhi(testStatistics, data);
    case 'logistic_regression':
      return calculateOddsRatio(testStatistics);
    case 'cox_ph':
      return calculateHazardRatio(testStatistics);
    case 'poisson_regression':
      return calculateIRR(testStatistics);
    case 'tost':
    case 'ci_approach':
      return calculateGMR(testStatistics);
    default:
      return null;
  }
}

function calculateCohensD(data: any) {
  // Calculate Cohen's d from group means and SDs
  const group1 = data.filter((row: any) => row.group === 'Group1');
  const group2 = data.filter((row: any) => row.group === 'Group2');
  
  if (group1.length === 0 || group2.length === 0) return null;
  
  const mean1 = group1.reduce((sum: number, row: any) => sum + row.value, 0) / group1.length;
  const mean2 = group2.reduce((sum: number, row: any) => sum + row.value, 0) / group2.length;
  
  const pooledSD = calculatePooledSD(group1.map((r: any) => r.value), group2.map((r: any) => r.value));
  
  const d = Math.abs(mean1 - mean2) / pooledSD;
  
  return {
    effectSize: d,
    effectSizeName: "Cohen's d",
    interpretation: `The difference between groups is ${d.toFixed(2)} standard deviations.`,
    magnitude: getCohensMagnitude(d)
  };
}

function calculatePooledSD(values1: number[], values2: number[]): number {
  const mean1 = values1.reduce((a, b) => a + b, 0) / values1.length;
  const mean2 = values2.reduce((a, b) => a + b, 0) / values2.length;
  
  const variance1 = values1.reduce((sum, v) => sum + Math.pow(v - mean1, 2), 0) / (values1.length - 1);
  const variance2 = values2.reduce((sum, v) => sum + Math.pow(v - mean2, 2), 0) / (values2.length - 1);
  
  const n1 = values1.length;
  const n2 = values2.length;
  
  return Math.sqrt(((n1 - 1) * variance1 + (n2 - 1) * variance2) / (n1 + n2 - 2));
}

function getCohensMagnitude(d: number): 'negligible' | 'small' | 'medium' | 'large' {
  if (d < 0.2) return 'negligible';
  if (d < 0.5) return 'small';
  if (d < 0.8) return 'medium';
  return 'large';
}

function calculateEtaSquared(testStatistics: any) {
  const F = testStatistics.F;
  const df1 = testStatistics.df1;
  const df2 = testStatistics.df2;
  
  const etaSquared = (df1 * F) / (df1 * F + df2);
  
  return {
    effectSize: etaSquared,
    effectSizeName: 'Eta-squared (η²)',
    interpretation: `${(etaSquared * 100).toFixed(1)}% of variance is explained by the group factor.`,
    magnitude: getEtaSquaredMagnitude(etaSquared)
  };
}

function getEtaSquaredMagnitude(eta2: number): 'negligible' | 'small' | 'medium' | 'large' {
  if (eta2 < 0.01) return 'negligible';
  if (eta2 < 0.06) return 'small';
  if (eta2 < 0.14) return 'medium';
  return 'large';
}

function calculateCorrelationEffect(testStatistics: any) {
  const r = testStatistics.r;
  
  return {
    effectSize: r,
    effectSizeName: 'Correlation coefficient (r)',
    interpretation: `There is a ${getCorrelationStrength(r)} ${r > 0 ? 'positive' : 'negative'} relationship between variables.`,
    magnitude: getCorrelationMagnitude(r)
  };
}

function getCorrelationStrength(r: number): string {
  const absR = Math.abs(r);
  if (absR < 0.1) return 'very weak';
  if (absR < 0.3) return 'weak';
  if (absR < 0.5) return 'moderate';
  if (absR < 0.7) return 'strong';
  return 'very strong';
}

function getCorrelationMagnitude(r: number): 'negligible' | 'small' | 'medium' | 'large' {
  const absR = Math.abs(r);
  if (absR < 0.1) return 'negligible';
  if (absR < 0.3) return 'small';
  if (absR < 0.5) return 'medium';
  return 'large';
}

function calculateRankBiserial(data: any, testStatistics: any) {
  // Approximation from Mann-Whitney U
  const n1 = data.filter((row: any) => row.group === 'Group1').length;
  const n2 = data.filter((row: any) => row.group === 'Group2').length;
  const U = testStatistics.U || testStatistics.W;
  
  const rb = 1 - (2 * U) / (n1 * n2);
  
  return {
    effectSize: Math.abs(rb),
    effectSizeName: 'Rank-biserial correlation',
    interpretation: `There is a ${getCorrelationStrength(rb)} difference between groups.`,
    magnitude: getCorrelationMagnitude(rb)
  };
}

function calculateEpsilonSquared(testStatistics: any) {
  const H = testStatistics.H;
  const n = testStatistics.n || testStatistics.total;
  
  const epsilonSquared = H / (n - 1);
  
  return {
    effectSize: epsilonSquared,
    effectSizeName: 'Epsilon-squared (ε²)',
    interpretation: `${(epsilonSquared * 100).toFixed(1)}% of variance is explained by group differences.`,
    magnitude: getEtaSquaredMagnitude(epsilonSquared)
  };
}

function calculatePhi(testStatistics: any, data: any) {
  const chi2 = testStatistics.chi2;
  const n = data.length;
  
  const phi = Math.sqrt(chi2 / n);
  
  return {
    effectSize: phi,
    effectSizeName: 'Phi coefficient (φ)',
    interpretation: `There is a ${getCorrelationStrength(phi)} association between variables.`,
    magnitude: getCorrelationMagnitude(phi)
  };
}

function calculateOddsRatio(testStatistics: any) {
  const OR = testStatistics.odds_ratio || testStatistics.OR;
  
  return {
    effectSize: OR,
    effectSizeName: 'Odds Ratio (OR)',
    interpretation: OR > 1 
      ? `The odds are ${OR.toFixed(2)} times higher for the reference group.`
      : `The odds are ${(1/OR).toFixed(2)} times lower for the reference group.`,
    magnitude: getORMagnitude(OR)
  };
}

function getORMagnitude(OR: number): 'negligible' | 'small' | 'medium' | 'large' {
  const logOR = Math.log(OR);
  if (Math.abs(logOR) < 0.2) return 'negligible';
  if (Math.abs(logOR) < 0.5) return 'small';
  if (Math.abs(logOR) < 1.0) return 'medium';
  return 'large';
}

function calculateHazardRatio(testStatistics: any) {
  const HR = testStatistics.hazard_ratio || testStatistics.HR;
  
  return {
    effectSize: HR,
    effectSizeName: 'Hazard Ratio (HR)',
    interpretation: HR > 1 
      ? `The hazard is ${HR.toFixed(2)} times higher for the reference group.`
      : `The hazard is ${(1/HR).toFixed(2)} times lower for the reference group.`,
    magnitude: getORMagnitude(HR)
  };
}

function calculateIRR(testStatistics: any) {
  const IRR = testStatistics.incidence_rate_ratio || testStatistics.IRR;
  
  return {
    effectSize: IRR,
    effectSizeName: 'Incidence Rate Ratio (IRR)',
    interpretation: IRR > 1 
      ? `The rate is ${IRR.toFixed(2)} times higher for the reference group.`
      : `The rate is ${(1/IRR).toFixed(2)} times lower for the reference group.`,
    magnitude: getORMagnitude(IRR)
  };
}

function calculateGMR(testStatistics: any): {
  effectSize: number;
  effectSizeName: string;
  interpretation: string;
  magnitude: 'negligible' | 'small' | 'medium' | 'large';
} | null {
  const GMR = testStatistics.geometric_mean_ratio || testStatistics.GMR;
  
  if (GMR === undefined || GMR === null) return null;
  
  return {
    effectSize: GMR,
    effectSizeName: 'Geometric Mean Ratio (GMR)',
    interpretation: GMR >= 0.8 && GMR <= 1.25
      ? 'The ratio is within the bioequivalence range (80-125%).'
      : 'The ratio is outside the bioequivalence range.',
    magnitude: GMR >= 0.8 && GMR <= 1.25 ? 'small' : 'large'
  };
}

/**
 * Generate interpretation for effect size
 */
export function interpretEffectSize(
  analysisType: AnalysisType,
  effectSize: number
): string {
  const magnitude = effectSize < 0.2 ? 'negligible' :
                   effectSize < 0.5 ? 'small' :
                   effectSize < 0.8 ? 'medium' : 'large';
  
  const interpretations: Record<AnalysisType, string> = {
    descriptive_statistics: 'N/A for descriptive statistics',
    t_test: `Cohen's d of ${effectSize.toFixed(2)} indicates a ${magnitude} effect size.`,
    anova: `Eta-squared of ${(effectSize * 100).toFixed(1)}% indicates a ${magnitude} effect.`,
    correlation: `Correlation of ${effectSize.toFixed(2)} indicates a ${magnitude} relationship.`,
    mann_whitney: `Rank-biserial correlation of ${effectSize.toFixed(2)} indicates a ${magnitude} difference.`,
    kruskal_wallis: `Epsilon-squared of ${(effectSize * 100).toFixed(1)}% indicates a ${magnitude} effect.`,
    power_analysis: 'N/A for power analysis',
    kaplan_meier: 'Effect size depends on median survival difference.',
    log_rank: 'Effect size depends on hazard ratio.',
    cox_ph: `Hazard ratio of ${effectSize.toFixed(2)} indicates a ${magnitude} effect.`,
    tost: `Geometric mean ratio of ${effectSize.toFixed(2)}${effectSize >= 0.8 && effectSize <= 1.25 ? ' demonstrates bioequivalence' : ' indicates lack of bioequivalence'}.`,
    ci_approach: `Geometric mean ratio of ${effectSize.toFixed(2)}${effectSize >= 0.8 && effectSize <= 1.25 ? ' demonstrates bioequivalence' : ' indicates lack of bioequivalence'}.`,
    crossover_anova: 'Effect size depends on treatment difference.',
    logistic_regression: `Odds ratio of ${effectSize.toFixed(2)} indicates a ${magnitude} effect.`,
    poisson_regression: `Incidence rate ratio of ${effectSize.toFixed(2)} indicates a ${magnitude} effect.`,
    linear_mixed_effects: 'Effect size depends on model coefficients.',
    generalized_estimating_equations: 'Effect size depends on model coefficients.',
    repeated_measures_anova: 'Effect size depends on within-subject variance.',
    multivariate_analysis: 'Effect size depends on multivariate test statistics.',
    principal_component_analysis: 'Effect size depends on variance explained.',
    cluster_analysis: 'Effect size depends on cluster separation.',
    meta_analysis: `Pooled effect size of ${effectSize.toFixed(2)} indicates a ${magnitude} overall effect.`,
    nca_pk: 'Effect size depends on PK parameters.',
    auc_calculation: 'Effect size depends on AUC values.',
    cmax_tmax: 'Effect size depends on Cmax and Tmax.',
    half_life: 'Effect size depends on half-life values.',
    clearance: 'Effect size depends on CL and Vd values.',
    pd_response_modeling: 'Effect size depends on Emax and EC50.',
    dose_proportionality: 'Effect size depends on dose-response relationship.',
    bonferroni: 'N/A for multiplicity control',
    holm: 'N/A for multiplicity control',
    bh_fdr: 'N/A for multiplicity control',
    by: 'N/A for multiplicity control',
    wilcoxon_signed_rank: `Rank-biserial correlation of ${effectSize.toFixed(2)} indicates a ${magnitude} difference.`,
    sign_test: 'Effect size depends on proportion of positive differences.',
    friedman: `Kendall's W of ${effectSize.toFixed(2)} indicates a ${magnitude} effect.`,
    dunns: `Rank-biserial correlation indicates pairwise differences.`,
    chi_square: `Phi coefficient of ${effectSize.toFixed(2)} indicates a ${magnitude} association.`,
    fisher_exact: `Phi coefficient of ${effectSize.toFixed(2)} indicates a ${magnitude} association.`,
    mcnemar: 'Effect size depends on proportion of discordant pairs.',
    cmh: `Mantel-Haenszel OR of ${effectSize.toFixed(2)} indicates the common odds ratio.`
  };
  
  return interpretations[analysisType] || 'Effect size interpretation not available.';
}
