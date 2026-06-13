import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'SMILES Converter',
  description: 'Convert between SMILES, IUPAC names, and other molecular formats. Parse, validate, and transform chemical notation. Generate canonical SMILES, InChI, and InChIKey for compound identification and database matching.',
  keywords: ['SMILES converter', 'IUPAC name conversion', 'canonical SMILES', 'InChI converter', 'InChIKey generator', 'chemical format conversion', 'molecular notation'],
  alternates: { canonical: '/tools/smiles-converter' },
  openGraph: {
    title: 'SMILES Converter — Chemical Format Tool',
    description: 'Convert between SMILES, IUPAC, InChI, and InChIKey formats.',
    url: 'https://www.biodockify.com/tools/smiles-converter',
  },
};

export default function SmilesConverterLayout({ children }: { children: React.ReactNode }) {
  return children;
}
