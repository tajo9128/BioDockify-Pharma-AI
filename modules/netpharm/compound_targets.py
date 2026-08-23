"""Curated compound-target database for network pharmacology.

Offline starter knowledge base: well-documented phytochemicals and common
drugs with their primary protein targets (HGNC symbols). Sources: DrugBank
mechanism summaries, KEGG DGROUP, and pharmacology literature reviews.
Extend with `custom` compounds at analysis time; users can also supply
their own mapping.
"""

COMPOUND_TARGETS = {
    # ── Phytochemicals ──────────────────────────────────────────────
    "Curcumin": ["TNF", "IL6", "NFKB1", "PTGS2", "AKT1", "TP53", "MAPK1", "BCL2", "CASP3", "MMP9"],
    "Quercetin": ["PTGS2", "NOS2", "TNF", "IL6", "CYP1A1", "MAPK1", "AKT1", "BCL2", "CASP3", "HIF1A"],
    "Resveratrol": ["SIRT1", "TP53", "NFKB1", "TNF", "AKT1", "MAPK1", "PTGS2", "BCL2", "CASP3", "ACE"],
    "Berberine": ["PRKAA1", "NFKB1", "TNF", "IL6", "PTGS2", "LDLR", "INS", "CYP2D6", "ABCB1", "AKT1"],
    "EGCG": ["PTGS2", "NOS2", "TNF", "MAPK1", "AKT1", "HIF1A", "MMP9", "VEGFA", "BCL2", "CASP3"],
    "Genistein": ["ESR1", "EGFR", "PTK2", "AKT1", "MAPK1", "NFKB1", "TP53", "BCL2"],
    "Apigenin": ["NFKB1", "TNF", "PTGS2", "CASP3", "MAPK1", "BCL2", "CDK1", "TOP2A"],
    "Luteolin": ["PTGS2", "NOS2", "TNF", "IL6", "NFKB1", "MAPK1", "CASP3", "TOP2A"],
    "Kaempferol": ["PTGS2", "NFKB1", "TNF", "AKT1", "MAPK1", "CASP3", "BCL2", "ESR1"],
    "Baicalein": ["PTGS2", "LOX5", "NFKB1", "TNF", "CASP3", "MAPK1"],
    "Sulforaphane": ["NFE2L2", "KEAP1", "NFKB1", "CASP3", "BCL2"],
    "Gingerol": ["PTGS2", "TNF", "NFKB1", "TRPV1", "IL6"],
    "Rutin": ["PTGS2", "NOS2", "TNF", "IL6", "MMP9", "VEGFA"],
    "Ginsenoside Rb1": ["NOS3", "TNF", "IL6", "AKT1", "NFKB1", "SLC6A4"],
    "Caffeic acid": ["PTGS2", "NFKB1", "TNF", "NOS2"],
    "Ferulic acid": ["PTGS2", "NFKB1", "TNF", "ACE"],
    "Allicin": ["PTGS2", "NFKB1", "TNF", "TRPA1"],
    "Withaferin A": ["NFKB1", "TNF", "BCL2", "CASP3", "AKT1", "TP53", "MAPK1"],
    "Ashwagandhanolide": ["NFKB1", "TNF", "CASP3"],
    "Baicalin": ["PTGS2", "TNF", "IL6", "NFKB1", "CASP3"],
    "Catechin": ["PTGS2", "NOS2", "TNF", "NFKB1", "ACE"],
    "Hesperidin": ["PTGS2", "NOS2", "TNF", "IL6", "NFKB1"],
    "Silibinin": ["PTGS2", "TNF", "NFKB1", "CASP3", "AKT1", "BCL2"],
    "Piperine": ["PTGS2", "NFKB1", "CYP3A4", "TNF"],
    "THC": ["CNR1", "CNR2", "FAAH"],
    "CBD": ["CNR1", "CNR2", "FAAH", "TRPV1", "GPR55"],

    # ── Common drugs ────────────────────────────────────────────────
    "Aspirin": ["PTGS1", "PTGS2", "NFKB1"],
    "Ibuprofen": ["PTGS1", "PTGS2"],
    "Diclofenac": ["PTGS1", "PTGS2"],
    "Paracetamol": ["PTGS2", "PTGS1", "TRPV1", "CYP2E1"],
    "Celecoxib": ["PTGS2"],
    "Morphine": ["OPRM1", "OPRD1", "OPRK1"],
    "Metformin": ["PRKAA1", "INSR", "G6PC", "SLC2A4"],
    "Atorvastatin": ["HMGCR"],
    "Losartan": ["AGTR1"],
    "Enalapril": ["ACE"],
    "Amlodipine": ["CACNA1C"],
    "Metoprolol": ["ADRB1"],
    "Salbutamol": ["ADRB2"],
    "Atenolol": ["ADRB1"],
    "Omeprazole": ["ATP4A"],
    "Ranitidine": ["HRH2"],
    "Furosemide": ["SLC12A1", "SLC12A3"],
    "Digoxin": ["ATP1A1"],
    "Warfarin": ["VKORC1", "CYP2C9"],
    "Diazepam": ["GABRA1", "GABRA2"],
    "Fluoxetine": ["SLC6A4"],
    "Sertraline": ["SLC6A4"],
    "Imipramine": ["SLC6A4", "SLC6A3"],
    "Haloperidol": ["DRD2", "DRD3"],
    "Chlorpromazine": ["DRD2", "HTR2A"],
    "Clozapine": ["DRD2", "HTR2A", "HTR1A"],
    "Caffeine": ["ADORA1", "ADORA2A", "PDE4D", "PDE10A"],
    "Imatinib": ["ABL1", "KIT", "PDGFRA"],
    "Gefitinib": ["EGFR"],
    "Erlotinib": ["EGFR"],
    "Tamoxifen": ["ESR1"],
    "Insulin (human)": ["INSR", "IRS1"],
    "Levothyroxine": ["THRB", "THRA"],
    "Prednisolone": ["NR3C1"],
    "Alendronate": ["FDPS", "GGPS1"],
    "Colchicine": ["TUBB1", "TUBA1A"],
    "Methotrexate": ["DHFR", "SLC19A1"],
    "Allopurinol": ["XDH"],
    "Sildenafil": ["PDE5A"],
    "Rivaroxaban": ["F10"],
    "Apixaban": ["F10"],
    "Dabigatran": ["F2", "F10"],
}


def get_compound_targets(compound: str):
    c = compound.strip().lower()
    for name, targets in COMPOUND_TARGETS.items():
        if name.lower() == c:
            return name, list(targets)
    # partial match
    for name, targets in COMPOUND_TARGETS.items():
        if c in name.lower():
            return name, list(targets)
    return None, None
