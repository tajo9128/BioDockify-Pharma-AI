import { AnalysisType, SuggestedTest, DataTypeDetection } from '@/types/statistics';
import { ANALYSES } from './analysis-definitions';

/**
 * Suggest appropriate statistical tests based on data characteristics
 */
export function suggestTests(
  detections: DataTypeDetection[],
  sampleSize?: number,
  isPaired?: boolean,
  hasTimeComponent?: boolean
): SuggestedTest[] {
  const suggestions: SuggestedTest[] = [];
  const numericCols = detections.filter(d => d.type === 'numeric' || d.type === 'ordinal').map(d => d.column);
  const categoricalCols = detections.filter(d => d.type === 'categorical' || d.type === 'binary').map(d => d.column);
  const timeCols = detections.filter(d => d.type === 'datetime').map(d => d.column);
  const actualSampleSize = sampleSize || 0;
  
  // Scenario 1: Two groups comparing a continuous outcome
  if (categoricalCols.length >= 1 && numericCols.length >= 1) {
    const groupCol = categoricalCols[0];
    const outcomeCol = numericCols[0];
    const uniqueGroups = detections.find(d => d.column === groupCol)?.uniqueCount || 2;
    
    if (uniqueGroups === 2) {
      // Two-group comparison
      const isNormal = actualSampleSize >= 30; // CLT assumption
      
      if (isNormal) {
        suggestions.push({
          analysisType: 't_test',
          reason: 'Comparing means of two independent groups with adequate sample size',
          confidence: 0.9,
          assumptions: ['Normal distribution', 'Equal variances (for Student\'s t)', 'Independent samples']
        });
      }
      
      if (isPaired) {
        suggestions.push({
          analysisType: 'wilcoxon_signed_rank',
          reason: 'Paired samples comparison using non-parametric test',
          confidence: 0.85,
          assumptions: ['Paired observations', 'Symmetric distribution of differences']
        });
      } else {
        suggestions.push({
          analysisType: 'mann_whitney',
          reason: 'Non-parametric alternative to t-test for two groups',
          confidence: 0.8,
          assumptions: ['Independent samples', 'Ordinal or continuous data']
        });
      }
    } else if (uniqueGroups >= 3) {
      // Multiple group comparison
      if (actualSampleSize >= 30) {
        suggestions.push({
          analysisType: 'anova',
          reason: `Comparing means across ${uniqueGroups} groups`,
          confidence: 0.9,
          assumptions: ['Normal distribution', 'Homogeneity of variance', 'Independent samples']
        });
      }
      
      suggestions.push({
        analysisType: 'kruskal_wallis',
        reason: 'Non-parametric alternative to ANOVA for multiple groups',
        confidence: 0.85,
        assumptions: ['Independent samples', 'Similar distribution shapes']
      });
    }
  }
  
  // Scenario 2: Relationship between two continuous variables
  if (numericCols.length >= 2) {
    const isNormal = actualSampleSize >= 30;
    
    if (isNormal) {
      suggestions.push({
        analysisType: 'correlation',
        reason: 'Assessing linear relationship between two continuous variables',
        confidence: 0.9,
        assumptions: ['Linear relationship', 'Normal distribution (for Pearson)', 'Bivariate normality']
      });
    } else {
      suggestions.push({
        analysisType: 'correlation',
        reason: 'Assessing monotonic relationship using non-parametric correlation',
        confidence: 0.85,
        assumptions: ['Monotonic relationship', 'Ordinal or continuous data']
      });
    }
  }
  
  // Scenario 3: Survival/time-to-event data
  if (hasTimeComponent || timeCols.length >= 1) {
    suggestions.push({
      analysisType: 'kaplan_meier',
      reason: 'Survival analysis for time-to-event data',
      confidence: 0.9,
      assumptions: ['Non-informative censoring', 'Independent events', 'Accurate event times']
    });
    
    if (categoricalCols.length >= 1) {
      suggestions.push({
        analysisType: 'log_rank',
        reason: 'Comparing survival curves between groups',
        confidence: 0.85,
        assumptions: ['Proportional hazards', 'Non-informative censoring']
      });
      
      suggestions.push({
        analysisType: 'cox_ph',
        reason: 'Cox proportional hazards model for survival with covariates',
        confidence: 0.85,
        assumptions: ['Proportional hazards', 'Linear log-hazard relationship']
      });
    }
  }
  
  // Scenario 4: Categorical data analysis
  if (categoricalCols.length >= 2) {
    suggestions.push({
      analysisType: 'chi_square',
      reason: 'Testing association between categorical variables',
      confidence: 0.8,
      assumptions: ['Independent observations', 'Expected frequency ≥ 5 in ≥ 80% of cells']
    });
    
    const binaryCols = detections.filter(d => d.type === 'binary');
    if (binaryCols.length === 2) {
      suggestions.push({
        analysisType: 'fisher_exact',
        reason: 'Exact test for 2×2 contingency table',
        confidence: 0.85,
        assumptions: ['Fixed row/column totals', 'Independent observations']
      });
    }
  }
  
  // Scenario 5: Paired/repeated measures
  if (isPaired) {
    suggestions.push({
      analysisType: 'wilcoxon_signed_rank',
      reason: 'Non-parametric test for paired continuous data',
      confidence: 0.9,
      assumptions: ['Paired observations', 'Symmetric distribution of differences']
    });
    
    suggestions.push({
      analysisType: 'sign_test',
      reason: 'Simple non-parametric test for paired data',
      confidence: 0.75,
      assumptions: ['Paired observations', 'Ordinal or continuous data']
    });
  }
  
  // Scenario 6: Repeated measures with multiple time points
  if (hasTimeComponent && categoricalCols.length >= 1) {
    suggestions.push({
      analysisType: 'friedman',
      reason: 'Non-parametric alternative to repeated measures ANOVA',
      confidence: 0.8,
      assumptions: ['Repeated measures', 'Ordinal or continuous data', 'Same distribution shapes']
    });
  }
  
  // Scenario 7: Binary outcome with predictors
  const binaryCols = detections.filter(d => d.type === 'binary').map(d => d.column);
  if (binaryCols.length >= 1 && (numericCols.length >= 1 || categoricalCols.length >= 2)) {
    suggestions.push({
      analysisType: 'logistic_regression',
      reason: 'Regression model for binary outcome with covariates',
      confidence: 0.85,
      assumptions: ['Binary outcome', 'Independent observations', 'Linearity of logit']
    });
  }
  
  // Scenario 8: Count data
  const potentialCountCols = numericCols.filter(col => {
    const detection = detections.find(d => d.column === col);
    return detection && detection.uniqueCount && detection.uniqueCount < 20 && detection.type === 'numeric';
  });
  
  if (potentialCountCols.length >= 1) {
    suggestions.push({
      analysisType: 'poisson_regression',
      reason: 'Regression model for count data with covariates',
      confidence: 0.8,
      assumptions: ['Count data', 'Mean equals variance', 'Independent observations']
    });
  }
  
  // Sort by confidence and return top suggestions
  return suggestions
    .sort((a, b) => b.confidence - a.confidence)
    .slice(0, 5); // Return top 5 suggestions
}

/**
 * Get detailed explanation for a test
 */
export function getTestExplanation(analysisType: AnalysisType): {
  whenToUse: string;
  prerequisites: string[];
  interpretationTips: string[];
  commonPitfalls: string[];
} {
  const analysis = ANALYSES.find(a => a.id === analysisType);
  
  const baseExplanation = {
    whenToUse: analysis?.description || 'See analysis description',
    prerequisites: analysis?.assumptions || [],
    interpretationTips: [
      'Consider practical significance, not just statistical significance',
      'Report effect sizes and confidence intervals',
      'Check assumptions before interpreting results'
    ],
    commonPitfalls: [
      'Violating test assumptions',
      'Multiple comparisons without adjustment',
      'Over-interpreting non-significant results',
      'Confusing statistical and practical significance'
    ]
  };
  
  // Add specific tips based on analysis type
  if (analysisType === 't_test' || analysisType === 'anova') {
    baseExplanation.interpretationTips.push('Check for outliers that may affect results');
    baseExplanation.commonPitfalls.push('Assuming normality with small samples');
  }
  
  if (analysisType === 'correlation') {
    baseExplanation.interpretationTips.push('Visualize relationship with scatterplot');
    baseExplanation.commonPitfalls.push('Assuming causation from correlation');
    baseExplanation.commonPitfalls.push('Non-linear relationships may be missed');
  }
  
  if (['kaplan_meier', 'log_rank', 'cox_ph'].includes(analysisType)) {
    baseExplanation.interpretationTips.push('Check censoring pattern');
    baseExplanation.interpretationTips.push('Verify proportional hazards assumption for Cox model');
  }
  
  if (['tost', 'ci_approach', 'crossover_anova'].includes(analysisType)) {
    baseExplanation.interpretationTips.push('Bioequivalence concluded if 90% CI within 80-125%');
    baseExplanation.commonPitfalls.push('Inadequate washout period in crossover studies');
  }
  
  return baseExplanation;
}
