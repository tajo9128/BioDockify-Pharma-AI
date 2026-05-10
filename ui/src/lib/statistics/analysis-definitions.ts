import { AnalysisType, AnalysisCategory, AnalysisDefinition } from '@/types/statistics';

export const ANALYSIS_CATEGORIES: Record<AnalysisCategory, { name: string; description: string; icon: string }> = {
  basic: {
    name: 'Basic Statistics',
    description: 'Fundamental statistical analyses for basic research',
    icon: 'calculator'
  },
  survival: {
    name: 'Survival Analysis',
    description: 'Time-to-event and survival data analysis',
    icon: 'activity'
  },
  bioequivalence: {
    name: 'Bioequivalence',
    description: 'Bioequivalence and bioavailability studies',
    icon: 'scale'
  },
  advanced: {
    name: 'Advanced Biostatistics',
    description: 'Advanced regression and modeling techniques',
    icon: 'microscope'
  },
  pkpd: {
    name: 'PK/PD Analysis',
    description: 'Pharmacokinetic and pharmacodynamic analysis',
    icon: 'zap'
  },
  multiplicity: {
    name: 'Multiplicity Control',
    description: 'Methods for controlling multiple comparison errors',
    icon: 'layers'
  },
  categorical: {
    name: 'Categorical Data',
    description: 'Analysis of categorical and count data',
    icon: 'grid'
  }
};

// Basic Statistics Analyses
const basicAnalyses: AnalysisDefinition[] = [
  {
    id: 'descriptive_statistics',
    category: 'basic',
    name: 'Descriptive Statistics',
    description: 'Calculate mean, median, mode, standard deviation, variance, quartiles, and other descriptive statistics for your data.',
    parameters: [
      {
        name: 'columns',
        label: 'Columns to analyze',
        type: 'columns',
        subtype: 'numeric',
        required: true,
        description: 'Select numeric columns for descriptive statistics'
      }
    ],
    requiredColumns: ['columns'],
    optionalColumns: [],
    outputs: ['mean', 'median', 'mode', 'std', 'variance', 'min', 'max', 'q1', 'q3'],
    assumptions: ['Numeric data', 'Random sampling recommended'],
    examples: ['Calculate summary statistics for patient ages', 'Get descriptive stats for lab results'],
    references: ['Agresti, A. (2012). Categorical Data Analysis']
  },
  {
    id: 't_test',
    category: 'basic',
    name: 'Independent Samples T-Test',
    description: 'Compare means between two independent groups. Assumes normal distribution and equal variances (for Student\'s t-test).',
    parameters: [
      {
        name: 'outcome',
        label: 'Outcome Variable',
        type: 'column',
        subtype: 'numeric',
        required: true
      },
      {
        name: 'group',
        label: 'Group Variable',
        type: 'column',
        subtype: 'group',
        required: true
      },
      {
        name: 'variance_assumption',
        label: 'Variance Assumption',
        type: 'select',
        options: ['equal', 'unequal'],
        defaultValue: 'equal',
        required: false
      },
      {
        name: 'alternative',
        label: 'Alternative Hypothesis',
        type: 'select',
        options: ['two-sided', 'greater', 'less'],
        defaultValue: 'two-sided',
        required: false
      },
      {
        name: 'confidence_level',
        label: 'Confidence Level',
        type: 'select',
        options: ['0.90', '0.95', '0.99'],
        defaultValue: '0.95',
        required: false
      }
    ],
    minSampleSize: 10,
    assumptions: ['Normal distribution', 'Independent samples', 'Equal variances (for Student\'s t)']
  },
  {
    id: 'anova',
    category: 'basic',
    name: 'One-Way ANOVA',
    description: 'Compare means across three or more groups. Tests if all group means are equal.',
    parameters: [
      {
        name: 'outcome',
        label: 'Outcome Variable',
        type: 'column',
        subtype: 'numeric',
        required: true
      },
      {
        name: 'group',
        label: 'Group Variable',
        type: 'column',
        subtype: 'group',
        required: true
      },
      {
        name: 'post_hoc',
        label: 'Post-hoc Test',
        type: 'select',
        options: ['none', 'tukey', 'bonferroni', 'sidak', 'holm-sidak'],
        defaultValue: 'none',
        required: false
      },
      {
        name: 'confidence_level',
        label: 'Confidence Level',
        type: 'select',
        options: ['0.90', '0.95', '0.99'],
        defaultValue: '0.95',
        required: false
      }
    ],
    minSampleSize: 15,
    assumptions: ['Normal distribution', 'Independent samples', 'Homogeneity of variance']
  },
  {
    id: 'correlation',
    category: 'basic',
    name: 'Correlation Analysis',
    description: 'Analyze the relationship between two continuous variables. Supports Pearson (parametric) and Spearman (non-parametric) correlation coefficients.',
    parameters: [
      {
        name: 'variable1',
        label: 'First Variable',
        type: 'column',
        subtype: 'numeric',
        required: true
      },
      {
        name: 'variable2',
        label: 'Second Variable',
        type: 'column',
        subtype: 'numeric',
        required: true
      },
      {
        name: 'method',
        label: 'Correlation Method',
        type: 'select',
        options: ['pearson', 'spearman', 'kendall'],
        defaultValue: 'pearson',
        required: false
      },
      {
        name: 'confidence_level',
        label: 'Confidence Level',
        type: 'select',
        options: ['0.90', '0.95', '0.99'],
        defaultValue: '0.95',
        required: false
      }
    ],
    minSampleSize: 10,
    assumptions: ['Linear relationship (Pearson)', 'Normal distribution (Pearson)', 'Paired observations']
  },
  {
    id: 'mann_whitney',
    category: 'basic',
    name: 'Mann-Whitney U Test',
    description: 'Non-parametric test for comparing two independent groups. Tests if one group tends to have larger values than the other.',
    parameters: [
      {
        name: 'outcome',
        label: 'Outcome Variable',
        type: 'column',
        subtype: 'numeric',
        required: true
      },
      {
        name: 'group',
        label: 'Group Variable',
        type: 'column',
        subtype: 'group',
        required: true
      },
      {
        name: 'alternative',
        label: 'Alternative Hypothesis',
        type: 'select',
        options: ['two-sided', 'greater', 'less'],
        defaultValue: 'two-sided',
        required: false
      },
      {
        name: 'confidence_level',
        label: 'Confidence Level',
        type: 'select',
        options: ['0.90', '0.95', '0.99'],
        defaultValue: '0.95',
        required: false
      }
    ],
    minSampleSize: 8,
    assumptions: ['Independent samples', 'Ordinal or continuous data', 'Similar distribution shapes']
  },
  {
    id: 'kruskal_wallis',
    category: 'basic',
    name: 'Kruskal-Wallis Test',
    description: 'Non-parametric alternative to one-way ANOVA for comparing three or more groups.',
    parameters: [
      {
        name: 'outcome',
        label: 'Outcome Variable',
        type: 'column',
        subtype: 'numeric',
        required: true
      },
      {
        name: 'group',
        label: 'Group Variable',
        type: 'column',
        subtype: 'group',
        required: true
      },
      {
        name: 'post_hoc',
        label: 'Post-hoc Test',
        type: 'select',
        options: ['none', 'dunn', 'conover', 'bonferroni'],
        defaultValue: 'none',
        required: false
      },
      {
        name: 'confidence_level',
        label: 'Confidence Level',
        type: 'select',
        options: ['0.90', '0.95', '0.99'],
        defaultValue: '0.95',
        required: false
      }
    ],
    minSampleSize: 12,
    assumptions: ['Independent samples', 'Ordinal or continuous data', 'Similar distribution shapes']
  },
  {
    id: 'power_analysis',
    category: 'basic',
    name: 'Power Analysis',
    description: 'Calculate statistical power, sample size, or minimum detectable effect size for planned studies.',
    parameters: [
      {
        name: 'test_type',
        label: 'Test Type',
        type: 'select',
        options: ['t-test', 'anova', 'correlation', 'proportion'],
        defaultValue: 't-test',
        required: true
      },
      {
        name: 'effect_size',
        label: 'Effect Size (Cohen\'s d, f, r, h)',
        type: 'number',
        defaultValue: 0.5,
        hint: 'Small=0.2, Medium=0.5, Large=0.8',
        required: false
      },
      {
        name: 'sample_size',
        label: 'Sample Size (per group)',
        type: 'number',
        min: 2,
        defaultValue: 30,
        required: false
      },
      {
        name: 'power',
        label: 'Power (1-β)',
        type: 'number',
        min: 0.01,
        max: 0.99,
        step: 0.01,
        defaultValue: 0.80,
        required: false
      },
      {
        name: 'alpha',
        label: 'Significance Level (α)',
        type: 'number',
        min: 0.001,
        max: 0.10,
        step: 0.001,
        defaultValue: 0.05,
        required: false
      },
      {
        name: 'groups',
        label: 'Number of Groups',
        type: 'number',
        min: 2,
        defaultValue: 2,
        required: false
      }
    ],
    minSampleSize: 0,
    assumptions: ['Known effect size or sample size', 'Normality assumption for most tests']
  }
];

// Survival Analysis
const survivalAnalyses: AnalysisDefinition[] = [
  {
    id: 'kaplan_meier',
    category: 'survival',
    name: 'Kaplan-Meier Estimator',
    description: 'Estimate survival function from time-to-event data. Handles censored observations.',
    parameters: [
      {
        name: 'time',
        label: 'Time to Event',
        type: 'column',
        subtype: 'numeric',
        required: true,
        description: 'Time until event or censoring'
      },
      {
        name: 'event',
        label: 'Event Indicator',
        type: 'column',
        subtype: 'binary',
        required: true,
        description: '1=event occurred, 0=censored'
      },
      {
        name: 'group',
        label: 'Group Variable (optional)',
        type: 'column',
        subtype: 'group',
        required: false,
        description: 'Categorical variable for group comparison'
      },
      {
        name: 'confidence_level',
        label: 'Confidence Level',
        type: 'select',
        options: ['0.90', '0.95', '0.99'],
        defaultValue: '0.95',
        required: false
      }
    ],
    minSampleSize: 10,
    assumptions: ['Non-informative censoring', 'Independent events', 'Accurate event times']
  },
  {
    id: 'log_rank',
    category: 'survival',
    name: 'Log-Rank Test',
    description: 'Compare survival distributions between two or more groups using the log-rank test.',
    parameters: [
      {
        name: 'time',
        label: 'Time to Event',
        type: 'column',
        subtype: 'numeric',
        required: true
      },
      {
        name: 'event',
        label: 'Event Indicator',
        type: 'column',
        subtype: 'binary',
        required: true
      },
      {
        name: 'group',
        label: 'Group Variable',
        type: 'column',
        subtype: 'group',
        required: true
      },
      {
        name: 'confidence_level',
        label: 'Confidence Level',
        type: 'select',
        options: ['0.90', '0.95', '0.99'],
        defaultValue: '0.95',
        required: false
      }
    ],
    minSampleSize: 20,
    assumptions: ['Proportional hazards', 'Non-informative censoring', 'Independent groups']
  },
  {
    id: 'cox_ph',
    category: 'survival',
    name: 'Cox Proportional Hazards Model',
    description: 'Semiparametric regression model for survival data with covariates. Estimates hazard ratios.',
    parameters: [
      {
        name: 'time',
        label: 'Time to Event',
        type: 'column',
        subtype: 'numeric',
        required: true
      },
      {
        name: 'event',
        label: 'Event Indicator',
        type: 'column',
        subtype: 'binary',
        required: true
      },
      {
        name: 'covariates',
        label: 'Covariates',
        type: 'columns',
        subtype: 'numeric',
        required: true,
        description: 'Predictor variables for the model'
      },
      {
        name: 'strata',
        label: 'Strata Variables (optional)',
        type: 'columns',
        required: false,
        description: 'Variables for stratification'
      },
      {
        name: 'confidence_level',
        label: 'Confidence Level',
        type: 'select',
        options: ['0.90', '0.95', '0.99'],
        defaultValue: '0.95',
        required: false
      }
    ],
    minSampleSize: 30,
    assumptions: ['Proportional hazards', 'Linear log-hazard relationship', 'Independent censoring']
  }
];

// Bioequivalence Analyses
const bioequivalenceAnalyses: AnalysisDefinition[] = [
  {
    id: 'tost',
    category: 'bioequivalence',
    name: 'Two One-Sided Tests (TOST)',
    description: 'Assess bioequivalence using the Two One-Sided Tests procedure. Standard method for bioequivalence assessment.',
    parameters: [
      {
        name: 'test',
        label: 'Test Treatment Values',
        type: 'column',
        subtype: 'numeric',
        required: true
      },
      {
        name: 'reference',
        label: 'Reference Treatment Values',
        type: 'column',
        subtype: 'numeric',
        required: true
      },
      {
        name: 'log_transform',
        label: 'Log Transform Data',
        type: 'boolean',
        defaultValue: true,
        required: false
      },
      {
        name: 'lower_bound',
        label: 'Lower Equivalence Bound',
        type: 'number',
        defaultValue: 80,
        required: false
      },
      {
        name: 'upper_bound',
        label: 'Upper Equivalence Bound',
        type: 'number',
        defaultValue: 125,
        required: false
      },
      {
        name: 'confidence_level',
        label: 'Confidence Level',
        type: 'select',
        options: ['0.90', '0.95'],
        defaultValue: '0.90',
        required: false
      }
    ],
    minSampleSize: 12,
    assumptions: ['Normal distribution (or log-normal)', 'Independent samples', 'Randomized crossover design']
  },
  {
    id: 'ci_approach',
    category: 'bioequivalence',
    name: 'Confidence Interval Approach',
    description: 'Assess bioequivalence using the confidence interval approach. Bioequivalence if 90% CI falls within 80-125%.',
    parameters: [
      {
        name: 'test',
        label: 'Test Treatment Values',
        type: 'column',
        subtype: 'numeric',
        required: true
      },
      {
        name: 'reference',
        label: 'Reference Treatment Values',
        type: 'column',
        subtype: 'numeric',
        required: true
      },
      {
        name: 'log_transform',
        label: 'Log Transform Data',
        type: 'boolean',
        defaultValue: true,
        required: false
      },
      {
        name: 'lower_bound',
        label: 'Lower Equivalence Bound',
        type: 'number',
        defaultValue: 80,
        required: false
      },
      {
        name: 'upper_bound',
        label: 'Upper Equivalence Bound',
        type: 'number',
        defaultValue: 125,
        required: false
      }
    ],
    minSampleSize: 12,
    assumptions: ['Normal distribution (or log-normal)', 'Independent samples', 'Adequate washout period']
  },
  {
    id: 'crossover_anova',
    category: 'bioequivalence',
    name: 'Crossover ANOVA',
    description: 'Analyze crossover study data with ANOVA, accounting for sequence, period, and treatment effects.',
    parameters: [
      {
        name: 'outcome',
        label: 'Outcome Variable',
        type: 'column',
        subtype: 'numeric',
        required: true
      },
      {
        name: 'subject',
        label: 'Subject ID',
        type: 'column',
        required: true
      },
      {
        name: 'period',
        label: 'Period',
        type: 'column',
        subtype: 'group',
        required: true
      },
      {
        name: 'sequence',
        label: 'Sequence',
        type: 'column',
        subtype: 'group',
        required: true
      },
      {
        name: 'treatment',
        label: 'Treatment',
        type: 'column',
        subtype: 'group',
        required: true
      },
      {
        name: 'confidence_level',
        label: 'Confidence Level',
        type: 'select',
        options: ['0.90', '0.95'],
        defaultValue: '0.95',
        required: false
      }
    ],
    minSampleSize: 12,
    assumptions: ['Normal distribution', 'No carryover effect', 'Adequate washout period', 'Randomized design']
  }
];

// Advanced Biostatistics
const advancedAnalyses: AnalysisDefinition[] = [
  {
    id: 'logistic_regression',
    category: 'advanced',
    name: 'Logistic Regression',
    description: 'Regression model for binary outcomes. Estimates odds ratios for predictor variables.',
    parameters: [
      {
        name: 'outcome',
        label: 'Binary Outcome',
        type: 'column',
        subtype: 'binary',
        required: true
      },
      {
        name: 'predictors',
        label: 'Predictor Variables',
        type: 'columns',
        required: true,
        description: 'Covariates for the model'
      },
      {
        name: 'penalty',
        label: 'Regularization Penalty',
        type: 'select',
        options: ['none', 'l1', 'l2', 'elasticnet'],
        defaultValue: 'none',
        required: false
      },
      {
        name: 'confidence_level',
        label: 'Confidence Level',
        type: 'select',
        options: ['0.90', '0.95', '0.99'],
        defaultValue: '0.95',
        required: false
      }
    ],
    minSampleSize: 30,
    assumptions: ['Binary outcome', 'Independent observations', 'Linearity of logit', 'No perfect multicollinearity']
  },
  {
    id: 'poisson_regression',
    category: 'advanced',
    name: 'Poisson Regression',
    description: 'Regression model for count data. Estimates incidence rate ratios for predictor variables.',
    parameters: [
      {
        name: 'outcome',
        label: 'Count Outcome',
        type: 'column',
        subtype: 'numeric',
        required: true
      },
      {
        name: 'predictors',
        label: 'Predictor Variables',
        type: 'columns',
        required: true
      },
      {
        name: 'offset',
        label: 'Offset Variable (optional)',
        type: 'column',
        required: false,
        description: 'Exposure time or population size'
      },
      {
        name: 'confidence_level',
        label: 'Confidence Level',
        type: 'select',
        options: ['0.90', '0.95', '0.99'],
        defaultValue: '0.95',
        required: false
      }
    ],
    minSampleSize: 30,
    assumptions: ['Count data', 'Mean equals variance', 'Independent observations']
  },
  {
    id: 'linear_mixed_effects',
    category: 'advanced',
    name: 'Linear Mixed Effects Model',
    description: 'Regression model with random effects for clustered or repeated measures data.',
    parameters: [
      {
        name: 'outcome',
        label: 'Outcome Variable',
        type: 'column',
        subtype: 'numeric',
        required: true
      },
      {
        name: 'fixed_effects',
        label: 'Fixed Effects',
        type: 'columns',
        required: true
      },
      {
        name: 'random_effects',
        label: 'Random Effects (Grouping Variables)',
        type: 'columns',
        required: true,
        description: 'Variables defining clusters or repeated measures'
      },
      {
        name: 'correlation_structure',
        label: 'Correlation Structure',
        type: 'select',
        options: ['independent', 'compound_symmetry', 'autoregressive', 'unstructured'],
        defaultValue: 'independent',
        required: false
      },
      {
        name: 'confidence_level',
        label: 'Confidence Level',
        type: 'select',
        options: ['0.90', '0.95', '0.99'],
        defaultValue: '0.95',
        required: false
      }
    ],
    minSampleSize: 30,
    assumptions: ['Normal distribution of residuals', 'Random effects are normally distributed', 'Missing at random']
  },
  {
    id: 'generalized_estimating_equations',
    category: 'advanced',
    name: 'Generalized Estimating Equations',
    description: 'Extension of generalized linear models for correlated data using GEE.',
    parameters: [
      {
        name: 'outcome',
        label: 'Outcome Variable',
        type: 'column',
        subtype: 'numeric',
        required: true
      },
      {
        name: 'predictors',
        label: 'Predictor Variables',
        type: 'columns',
        required: true
      },
      {
        name: 'group',
        label: 'Group Variable',
        type: 'column',
        required: true,
        description: 'Variable defining clusters'
      },
      {
        name: 'family',
        label: 'Distribution Family',
        type: 'select',
        options: ['gaussian', 'binomial', 'poisson', 'gamma'],
        defaultValue: 'gaussian',
        required: false
      },
      {
        name: 'correlation',
        label: 'Correlation Structure',
        type: 'select',
        options: ['independent', 'exchangeable', 'autoregressive', 'unstructured'],
        defaultValue: 'exchangeable',
        required: false
      }
    ],
    minSampleSize: 30,
    assumptions: ['Missing at random', 'Correct correlation structure specified', 'Large sample asymptotics']
  },
  {
    id: 'meta_analysis',
    category: 'advanced',
    name: 'Meta-Analysis',
    description: 'Combine results from multiple studies to estimate overall effect size.',
    parameters: [
      {
        name: 'study_effect',
        label: 'Study Effect Sizes',
        type: 'column',
        subtype: 'numeric',
        required: true
      },
      {
        name: 'study_se',
        label: 'Standard Errors',
        type: 'column',
        subtype: 'numeric',
        required: true
      },
      {
        name: 'study_id',
        label: 'Study ID (optional)',
        type: 'column',
        required: false
      },
      {
        name: 'method',
        label: 'Pooling Method',
        type: 'select',
        options: ['fixed', 'random'],
        defaultValue: 'random',
        required: false
      },
      {
        name: 'confidence_level',
        label: 'Confidence Level',
        type: 'select',
        options: ['0.90', '0.95', '0.99'],
        defaultValue: '0.95',
        required: false
      }
    ],
    minSampleSize: 3,
    assumptions: ['Independent studies', 'Comparable populations and interventions', 'Sufficient data per study']
  }
];

// PK/PD Analyses
const pkpdAnalyses: AnalysisDefinition[] = [
  {
    id: 'nca_pk',
    category: 'pkpd',
    name: 'Non-Compartmental PK Analysis',
    description: 'Comprehensive non-compartmental pharmacokinetic analysis including AUC, Cmax, Tmax, half-life, clearance, volume of distribution.',
    parameters: [
      {
        name: 'time',
        label: 'Time',
        type: 'column',
        subtype: 'numeric',
        required: true
      },
      {
        name: 'concentration',
        label: 'Concentration',
        type: 'column',
        subtype: 'numeric',
        required: true
      },
      {
        name: 'dose',
        label: 'Dose',
        type: 'number',
        defaultValue: 1,
        required: false
      },
      {
        name: 'route',
        label: 'Route of Administration',
        type: 'select',
        options: ['IV', 'EV', 'PO', 'IM', 'SC'],
        defaultValue: 'EV',
        required: false
      },
      {
        name: 'subject',
        label: 'Subject ID (optional)',
        type: 'column',
        required: false
      },
      {
        name: 'confidence_level',
        label: 'Confidence Level',
        type: 'select',
        options: ['0.90', '0.95'],
        defaultValue: '0.90',
        required: false
      }
    ],
    minSampleSize: 3,
    assumptions: ['Linear pharmacokinetics', 'Sufficient time points', 'Terminal phase reached']
  },
  {
    id: 'auc_calculation',
    category: 'pkpd',
    name: 'AUC Calculation',
    description: 'Calculate area under the concentration-time curve using linear and logarithmic trapezoidal rules.',
    parameters: [
      {
        name: 'time',
        label: 'Time',
        type: 'column',
        subtype: 'numeric',
        required: true
      },
      {
        name: 'concentration',
        label: 'Concentration',
        type: 'column',
        subtype: 'numeric',
        required: true
      },
      {
        name: 'method',
        label: 'Integration Method',
        type: 'select',
        options: ['linear', 'log-linear', 'mixed'],
        defaultValue: 'mixed',
        required: false
      },
      {
        name: 'extend_to_infinity',
        label: 'Extend to Infinity',
        type: 'boolean',
        defaultValue: true,
        required: false
      },
      {
        name: 'confidence_level',
        label: 'Confidence Level',
        type: 'select',
        options: ['0.90', '0.95'],
        defaultValue: '0.90',
        required: false
      }
    ],
    minSampleSize: 3,
    assumptions: ['Adequate time points', 'No missing data points']
  },
  {
    id: 'cmax_tmax',
    category: 'pkpd',
    name: 'Cmax and Tmax Determination',
    description: 'Determine maximum concentration and time to maximum concentration from PK data.',
    parameters: [
      {
        name: 'time',
        label: 'Time',
        type: 'column',
        subtype: 'numeric',
        required: true
      },
      {
        name: 'concentration',
        label: 'Concentration',
        type: 'column',
        subtype: 'numeric',
        required: true
      },
      {
        name: 'subject',
        label: 'Subject ID (optional)',
        type: 'column',
        required: false
      },
      {
        name: 'confidence_level',
        label: 'Confidence Level',
        type: 'select',
        options: ['0.90', '0.95'],
        defaultValue: '0.90',
        required: false
      }
    ],
    minSampleSize: 3,
    assumptions: ['Adequate sampling frequency', 'True Cmax captured']
  },
  {
    id: 'half_life',
    category: 'pkpd',
    name: 'Half-Life Estimation',
    description: 'Estimate elimination half-life from the terminal phase of the concentration-time curve.',
    parameters: [
      {
        name: 'time',
        label: 'Time',
        type: 'column',
        subtype: 'numeric',
        required: true
      },
      {
        name: 'concentration',
        label: 'Concentration',
        type: 'column',
        subtype: 'numeric',
        required: true
      },
      {
        name: 'subject',
        label: 'Subject ID (optional)',
        type: 'column',
        required: false
      },
      {
        name: 'min_terminal_points',
        label: 'Minimum Terminal Points',
        type: 'number',
        min: 3,
        defaultValue: 3,
        required: false
      },
      {
        name: 'confidence_level',
        label: 'Confidence Level',
        type: 'select',
        options: ['0.90', '0.95'],
        defaultValue: '0.90',
        required: false
      }
    ],
    minSampleSize: 5,
    assumptions: ['Terminal phase reached', 'Linear elimination', 'Sufficient terminal points']
  },
  {
    id: 'clearance',
    category: 'pkpd',
    name: 'Clearance and Volume of Distribution',
    description: 'Calculate clearance (CL) and volume of distribution (Vd) from PK data.',
    parameters: [
      {
        name: 'time',
        label: 'Time',
        type: 'column',
        subtype: 'numeric',
        required: true
      },
      {
        name: 'concentration',
        label: 'Concentration',
        type: 'column',
        subtype: 'numeric',
        required: true
      },
      {
        name: 'dose',
        label: 'Dose',
        type: 'number',
        defaultValue: 1,
        required: false
      },
      {
        name: 'route',
        label: 'Route of Administration',
        type: 'select',
        options: ['IV', 'EV', 'PO', 'IM', 'SC'],
        defaultValue: 'EV',
        required: false
      },
      {
        name: 'subject',
        label: 'Subject ID (optional)',
        type: 'column',
        required: false
      },
      {
        name: 'confidence_level',
        label: 'Confidence Level',
        type: 'select',
        options: ['0.90', '0.95'],
        defaultValue: '0.90',
        required: false
      }
    ],
    minSampleSize: 5,
    assumptions: ['Linear pharmacokinetics', 'Terminal phase reached', 'Accurate dose']
  },
  {
    id: 'pd_response_modeling',
    category: 'pkpd',
    name: 'PD Response Modeling',
    description: 'Model pharmacodynamic response-concentration relationship using Emax or sigmoid Emax models.',
    parameters: [
      {
        name: 'concentration',
        label: 'Concentration',
        type: 'column',
        subtype: 'numeric',
        required: true
      },
      {
        name: 'response',
        label: 'Response',
        type: 'column',
        subtype: 'numeric',
        required: true
      },
      {
        name: 'model_type',
        label: 'Model Type',
        type: 'select',
        options: ['Emax', 'Sigmoid Emax', 'Linear', 'Quadratic'],
        defaultValue: 'Emax',
        required: false
      },
      {
        name: 'subject',
        label: 'Subject ID (optional)',
        type: 'column',
        required: false
      },
      {
        name: 'confidence_level',
        label: 'Confidence Level',
        type: 'select',
        options: ['0.90', '0.95'],
        defaultValue: '0.95',
        required: false
      }
    ],
    minSampleSize: 10,
    assumptions: ['Adequate concentration range', 'Pharmacodynamic equilibrium reached']
  }
];

// Multiplicity Control
const multiplicityAnalyses: AnalysisDefinition[] = [
  {
    id: 'bonferroni',
    category: 'multiplicity',
    name: 'Bonferroni Correction',
    description: 'Adjust p-values for multiple comparisons using Bonferroni method. Conservative but widely used.',
    parameters: [
      {
        name: 'p_values',
        label: 'P-values to Adjust',
        type: 'columns',
        subtype: 'numeric',
        required: true
      },
      {
        name: 'alpha',
        label: 'Family-wise Error Rate',
        type: 'number',
        min: 0.001,
        max: 0.10,
        step: 0.001,
        defaultValue: 0.05,
        required: false
      }
    ],
    minSampleSize: 0,
    assumptions: ['Independent tests (conservative if not)']
  },
  {
    id: 'holm',
    category: 'multiplicity',
    name: 'Holm-Bonferroni Method',
    description: 'Adjust p-values for multiple comparisons using Holm-Bonferroni method. Less conservative than Bonferroni.',
    parameters: [
      {
        name: 'p_values',
        label: 'P-values to Adjust',
        type: 'columns',
        subtype: 'numeric',
        required: true
      },
      {
        name: 'alpha',
        label: 'Family-wise Error Rate',
        type: 'number',
        min: 0.001,
        max: 0.10,
        step: 0.001,
        defaultValue: 0.05,
        required: false
      }
    ],
    minSampleSize: 0,
    assumptions: ['Independent tests (conservative if not)']
  },
  {
    id: 'bh_fdr',
    category: 'multiplicity',
    name: 'Benjamini-Hochberg FDR Control',
    description: 'Control false discovery rate (FDR) using Benjamini-Hochberg procedure. Less conservative than family-wise methods.',
    parameters: [
      {
        name: 'p_values',
        label: 'P-values to Adjust',
        type: 'columns',
        subtype: 'numeric',
        required: true
      },
      {
        name: 'q',
        label: 'Target FDR',
        type: 'number',
        min: 0.01,
        max: 0.20,
        step: 0.01,
        defaultValue: 0.05,
        required: false
      }
    ],
    minSampleSize: 0,
    assumptions: ['Independent or positively dependent tests']
  }
];

// Categorical Data Analyses
const categoricalAnalyses: AnalysisDefinition[] = [
  {
    id: 'wilcoxon_signed_rank',
    category: 'categorical',
    name: 'Wilcoxon Signed-Rank Test',
    description: 'Non-parametric test for paired continuous data. Tests if differences are symmetric around zero.',
    parameters: [
      {
        name: 'outcome1',
        label: 'First Outcome (Pre)',
        type: 'column',
        subtype: 'numeric',
        required: true
      },
      {
        name: 'outcome2',
        label: 'Second Outcome (Post)',
        type: 'column',
        subtype: 'numeric',
        required: true
      },
      {
        name: 'alternative',
        label: 'Alternative Hypothesis',
        type: 'select',
        options: ['two-sided', 'greater', 'less'],
        defaultValue: 'two-sided',
        required: false
      },
      {
        name: 'confidence_level',
        label: 'Confidence Level',
        type: 'select',
        options: ['0.90', '0.95', '0.99'],
        defaultValue: '0.95',
        required: false
      }
    ],
    minSampleSize: 8,
    assumptions: ['Paired observations', 'Symmetric distribution of differences', 'Continuous data']
  },
  {
    id: 'sign_test',
    category: 'categorical',
    name: 'Sign Test',
    description: 'Simple non-parametric test for paired data based on signs of differences.',
    parameters: [
      {
        name: 'outcome1',
        label: 'First Outcome (Pre)',
        type: 'column',
        subtype: 'numeric',
        required: true
      },
      {
        name: 'outcome2',
        label: 'Second Outcome (Post)',
        type: 'column',
        subtype: 'numeric',
        required: true
      },
      {
        name: 'alternative',
        label: 'Alternative Hypothesis',
        type: 'select',
        options: ['two-sided', 'greater', 'less'],
        defaultValue: 'two-sided',
        required: false
      }
    ],
    minSampleSize: 5,
    assumptions: ['Paired observations', 'Ordinal or continuous data']
  },
  {
    id: 'friedman',
    category: 'categorical',
    name: 'Friedman Test',
    description: 'Non-parametric alternative to repeated measures ANOVA for comparing multiple related groups.',
    parameters: [
      {
        name: 'outcome',
        label: 'Outcome Variable',
        type: 'column',
        subtype: 'numeric',
        required: true
      },
      {
        name: 'block',
        label: 'Block/Subject ID',
        type: 'column',
        required: true
      },
      {
        name: 'treatment',
        label: 'Treatment/Group',
        type: 'column',
        subtype: 'group',
        required: true
      },
      {
        name: 'post_hoc',
        label: 'Post-hoc Test',
        type: 'select',
        options: ['none', 'dunn', 'conover', 'wilcoxon'],
        defaultValue: 'none',
        required: false
      },
      {
        name: 'confidence_level',
        label: 'Confidence Level',
        type: 'select',
        options: ['0.90', '0.95', '0.99'],
        defaultValue: '0.95',
        required: false
      }
    ],
    minSampleSize: 10,
    assumptions: ['Paired/related samples', 'Ordinal or continuous data', 'Same distribution shapes']
  },
  {
    id: 'dunns',
    category: 'categorical',
    name: "Dunn's Post-Hoc Test",
    description: 'Post-hoc test for pairwise comparisons after Kruskal-Wallis or Friedman tests.',
    parameters: [
      {
        name: 'outcome',
        label: 'Outcome Variable',
        type: 'column',
        subtype: 'numeric',
        required: true
      },
      {
        name: 'group',
        label: 'Group Variable',
        type: 'column',
        subtype: 'group',
        required: true
      },
      {
        name: 'p_adjust',
        label: 'P-value Adjustment',
        type: 'select',
        options: ['bonferroni', 'holm', 'sidak', 'fdr_bh'],
        defaultValue: 'bonferroni',
        required: false
      },
      {
        name: 'confidence_level',
        label: 'Confidence Level',
        type: 'select',
        options: ['0.90', '0.95', '0.99'],
        defaultValue: '0.95',
        required: false
      }
    ],
    minSampleSize: 10,
    assumptions: ['Non-parametric comparison', 'Independent groups']
  },
  {
    id: 'chi_square',
    category: 'categorical',
    name: 'Chi-Square Test',
    description: 'Test association between two categorical variables using chi-square test of independence.',
    parameters: [
      {
        name: 'variable1',
        label: 'First Categorical Variable',
        type: 'column',
        subtype: 'group',
        required: true
      },
      {
        name: 'variable2',
        label: 'Second Categorical Variable',
        type: 'column',
        subtype: 'group',
        required: true
      },
      {
        name: 'correction',
        label: 'Yates\' Continuity Correction',
        type: 'boolean',
        defaultValue: false,
        required: false
      },
      {
        name: 'confidence_level',
        label: 'Confidence Level',
        type: 'select',
        options: ['0.90', '0.95', '0.99'],
        defaultValue: '0.95',
        required: false
      }
    ],
    minSampleSize: 20,
    assumptions: ['Independent observations', 'Expected frequency ≥5 in ≥80% cells', 'No empty cells']
  },
  {
    id: 'fisher_exact',
    category: 'categorical',
    name: "Fisher's Exact Test",
    description: 'Exact test for 2×2 contingency tables when chi-square assumptions are not met.',
    parameters: [
      {
        name: 'variable1',
        label: 'First Binary Variable',
        type: 'column',
        subtype: 'binary',
        required: true
      },
      {
        name: 'variable2',
        label: 'Second Binary Variable',
        type: 'column',
        subtype: 'binary',
        required: true
      },
      {
        name: 'alternative',
        label: 'Alternative Hypothesis',
        type: 'select',
        options: ['two-sided', 'greater', 'less'],
        defaultValue: 'two-sided',
        required: false
      },
      {
        name: 'confidence_level',
        label: 'Confidence Level',
        type: 'select',
        options: ['0.90', '0.95', '0.99'],
        defaultValue: '0.95',
        required: false
      }
    ],
    minSampleSize: 2,
    assumptions: ['Fixed row/column totals', 'Independent observations', '2×2 table']
  },
  {
    id: 'mcnemar',
    category: 'categorical',
    name: "McNemar's Test",
    description: 'Test for paired proportions in a 2×2 table (e.g., before/after).',
    parameters: [
      {
        name: 'outcome1',
        label: 'First Binary Outcome (Pre)',
        type: 'column',
        subtype: 'binary',
        required: true
      },
      {
        name: 'outcome2',
        label: 'Second Binary Outcome (Post)',
        type: 'column',
        subtype: 'binary',
        required: true
      },
      {
        name: 'correction',
        label: 'Continuity Correction',
        type: 'boolean',
        defaultValue: true,
        required: false
      },
      {
        name: 'confidence_level',
        label: 'Confidence Level',
        type: 'select',
        options: ['0.90', '0.95', '0.99'],
        defaultValue: '0.95',
        required: false
      }
    ],
    minSampleSize: 10,
    assumptions: ['Paired observations', 'Binary outcomes', 'Large discordant pairs for approximation']
  },
  {
    id: 'cmh',
    category: 'categorical',
    name: 'Cochran-Mantel-Haenszel Test',
    description: 'Test association between two binary variables while stratifying by a third variable.',
    parameters: [
      {
        name: 'variable1',
        label: 'First Binary Variable',
        type: 'column',
        subtype: 'binary',
        required: true
      },
      {
        name: 'variable2',
        label: 'Second Binary Variable',
        type: 'column',
        subtype: 'binary',
        required: true
      },
      {
        name: 'strata',
        label: 'Strata Variable',
        type: 'column',
        subtype: 'group',
        required: true
      },
      {
        name: 'confidence_level',
        label: 'Confidence Level',
        type: 'select',
        options: ['0.90', '0.95', '0.99'],
        defaultValue: '0.95',
        required: false
      }
    ],
    minSampleSize: 15,
    assumptions: ['Independent strata', 'Consistent association across strata', 'Binary outcomes']
  }
];

// Combine all analyses
export const ANALYSES: AnalysisDefinition[] = [
  ...basicAnalyses,
  ...survivalAnalyses,
  ...bioequivalenceAnalyses,
  ...advancedAnalyses,
  ...pkpdAnalyses,
  ...multiplicityAnalyses,
  ...categoricalAnalyses
];

// Get analyses by category
export function getAnalysesByCategory(category: AnalysisCategory): AnalysisDefinition[] {
  return ANALYSES.filter(analysis => analysis.category === category);
}

// Get analysis by ID
export function getAnalysisById(id: AnalysisType): AnalysisDefinition | undefined {
  return ANALYSES.find(analysis => analysis.id === id);
}

// Search analyses
export function searchAnalyses(query: string): AnalysisDefinition[] {
  const lowerQuery = query.toLowerCase();
  return ANALYSES.filter(analysis =>
    analysis.name.toLowerCase().includes(lowerQuery) ||
    analysis.description.toLowerCase().includes(lowerQuery) ||
    analysis.category.toLowerCase().includes(lowerQuery)
  );
}

// Get all analysis categories
export function getAllCategories(): AnalysisCategory[] {
  return Object.keys(ANALYSIS_CATEGORIES) as AnalysisCategory[];
}
