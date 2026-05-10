export type HypothesisStatus = 'proposed' | 'investigating' | 'accepted' | 'rejected' | 'suspended';
export type EvidenceType = 'supporting' | 'contradicting';

export interface Evidence {
    id: string;
    description: string;
    source_id?: string;
    source_type: string;
    confidence: number;
    added_at: string;
}

export interface Hypothesis {
    id: string;
    statement: string;
    rationale: string;
    status: HypothesisStatus;
    confidence_score: number;
    evidence: Evidence[];
    created_at: string;
    updated_at: string;
    tags: string[];
}
