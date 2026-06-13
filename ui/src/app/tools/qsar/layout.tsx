import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'QSAR Modeling Tool',
  description: 'Quantitative Structure-Activity Relationship (QSAR) modeling with 6 ML algorithms. Predict bioactivity from molecular structure. Random Forest, SVM, XGBoost, and more. Build, validate, and deploy QSAR models for lead optimization.',
  keywords: ['QSAR modeling', 'quantitative structure activity relationship', 'bioactivity prediction', 'machine learning drug discovery', 'QSAR ML models', 'Random Forest QSAR', 'XGBoost QSAR'],
  alternates: { canonical: '/tools/qsar' },
  openGraph: {
    title: 'QSAR Modeling — Predict Bioactivity with ML',
    description: '6 ML algorithms for quantitative structure-activity relationship modeling. 91% prediction accuracy.',
    url: 'https://www.biodockify.com/tools/qsar',
  },
};

export default function QSARLayout({ children }: { children: React.ReactNode }) {
  return children;
}
