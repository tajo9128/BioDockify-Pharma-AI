"""Enhanced Regulatory Affairs API — eCTD structure, ICH guidelines, stability
study planning, BE report generation, IND/NDA checklist.

For regulatory affairs professionals. All references cite FDA/EMA/ICH guidelines.
"""
from helpers.api import ApiHandler, Request, Response
import logging, math
import numpy as np

log = logging.getLogger("regulatory_enhanced")


def _kb_store(title, content, tags=None):
    try:
        from modules.knowledge.auto_store import auto_store
        auto_store("regulatory_enhanced", title, content, source="Regulatory Affairs",
                   tags=tags or ["regulatory"], category="regulatory_enhanced")
    except Exception:
        pass


class RegulatoryEnhancedHandler(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict:
        action = input.get("action", "")
        result = None
        if action == "ectd_structure": result = self._ectd_structure(input)
        elif action == "ich_guidelines": result = self._ich_guidelines(input)
        elif action == "stability_planner": result = self._stability_planner(input)
        elif action == "be_report": result = self._be_report(input)
        elif action == "ind_nda_checklist": result = self._ind_nda_checklist(input)
        else:
            return {
                "actions": ["ectd_structure", "ich_guidelines", "stability_planner", "be_report", "ind_nda_checklist"],
                "hint": "Regulatory: eCTD structure, ICH guidelines, stability planning, BE reports, IND/NDA checklists"
            }
        if result and not result.get("error"):
            _kb_store(f"Regulatory — {action.replace('_', ' ').title()}", result, ["regulatory", action])
        return result

    def _ectd_structure(self, input):
        """Common Technical Document (CTD) / eCTD structure.
        
        Returns the standard ICH M4 CTD module structure with descriptions.
        Reference: ICH M4: The Common Technical Document, 2003.
        """
        region = input.get("region", "ICH")  # ICH, FDA, EMA

        ctd = {
            "module_1": {
                "title": "Administrative Information and Prescribing Information",
                "region_specific": True,
                "contents": [
                    "1.1 Cover letter",
                    "1.2 Application form",
                    "1.3 Product information (SmPC, PIL, labeling)",
                    "1.4 Information about the experts",
                    "1.5 Specific requirements for region",
                ]
            },
            "module_2": {
                "title": "Common Technical Document Summaries",
                "contents": [
                    "2.1 CTD Table of Contents",
                    "2.2 CTD Introduction",
                    "2.3 Quality Overall Summary (QOS)",
                    "2.4 Nonclinical Overview",
                    "2.5 Clinical Overview",
                    "2.6 Nonclinical Written and Tabulated Summaries",
                    "2.7 Clinical Summary",
                ]
            },
            "module_3": {
                "title": "Quality (Chemistry, Manufacturing and Controls)",
                "contents": [
                    "3.1 Table of Contents",
                    "3.2 Body of Data",
                    "  3.2.S Drug Substance",
                    "    3.2.S.1 General Information",
                    "    3.2.S.2 Manufacture",
                    "    3.2.S.3 Characterisation",
                    "    3.2.S.4 Control of Drug Substance",
                    "    3.2.S.5 Reference Standards",
                    "    3.2.S.6 Container Closure System",
                    "    3.2.S.7 Stability",
                    "  3.2.P Drug Product",
                    "    3.2.P.1 Description and Composition",
                    "    3.2.P.2 Pharmaceutical Development",
                    "    3.2.P.3 Manufacture",
                    "    3.2.P.4 Control of Excipients",
                    "    3.2.P.5 Control of Drug Product",
                    "    3.2.P.6 Reference Standards",
                    "    3.2.P.7 Container Closure System",
                    "    3.2.P.8 Stability",
                ]
            },
            "module_4": {
                "title": "Nonclinical Study Reports",
                "contents": [
                    "4.1 Table of Contents",
                    "4.2 Study Reports",
                    "  4.2.1 Pharmacology",
                    "  4.2.2 Pharmacokinetics",
                    "  4.2.3 Toxicology",
                ]
            },
            "module_5": {
                "title": "Clinical Study Reports",
                "contents": [
                    "5.1 Table of Contents",
                    "5.2 Tabular Listing of All Clinical Studies",
                    "5.3 Clinical Study Reports",
                    "  5.3.1 Reports of Biopharmaceutic Studies",
                    "  5.3.2 Reports of PK Studies",
                    "  5.3.3 Reports of PD Studies",
                    "  5.3.4 Reports of Efficacy and Safety Studies",
                    "  5.3.5 Reports of Post-marketing Experience",
                    "  5.3.6 Case Report Forms and Patient Narratives",
                ]
            }
        }

        if region == "FDA":
            ctd["module_1"]["contents"].extend([
                "FDA Form 356h (Application to Market)",
                "FDA Form 1571 (IND)",
                "Debarment certification",
                "Patent information (Orange Book listing)",
            ])
        elif region == "EMA":
            ctd["module_1"]["contents"].extend([
                "Cover Letter (EU)",
                "Application form (EMA/FHIR eAF)",
                "SmPC, PIL, Labelling (QRD template)",
                "Orphan designation (if applicable)",
            ])

        return {
            "success": True,
            "region": region,
            "structure": ctd,
            "reference": "ICH M4: The Common Technical Document, 2003"
        }

    def _ich_guidelines(self, input):
        """ICH guideline navigator with summaries."""
        category = input.get("category", "")

        guidelines = {
            "quality": [
                {"code": "Q1A(R2)", "title": "Stability Testing of New Drug Substances", "summary": "Defines stability study conditions, testing frequency, and acceptance criteria for new drug substances."},
                {"code": "Q1B", "title": "Photostability Testing", "summary": "Standardized conditions for photostability testing (D65 fluorescent + UV)."},
                {"code": "Q1D", "title": "Bracketing and Matrixing", "summary": "Statistical approaches to reduce stability testing burden."},
                {"code": "Q1E", "title": "Evaluation of Stability Data", "summary": "How to evaluate and extrapolate shelf life from stability data."},
                {"code": "Q2(R2)", "title": "Validation of Analytical Procedures", "summary": "Parameters: specificity, linearity, accuracy, precision, LOD, LOQ, range, robustness."},
                {"code": "Q3A(R2)", "title": "Impurities in New Drug Substances", "summary": "Reporting, identification, and qualification thresholds for impurities."},
                {"code": "Q3B(R2)", "title": "Impurities in New Drug Products", "summary": "Degradation product thresholds and qualification requirements."},
                {"code": "Q3C(R8)", "title": "Residual Solvents", "summary": "Permitted daily exposure limits for residual solvents (Class 1/2/3)."},
                {"code": "Q3D(R2)", "title": "Elemental Impurities", "summary": "PDE limits for elemental impurities (Pb, Cd, Hg, As, etc.)."},
                {"code": "Q5A(R2)", "title": "Viral Safety", "summary": "Viral safety evaluation of biotechnology products."},
                {"code": "Q6A", "title": "Specifications", "summary": "Setting specifications for chemical drug substances and products."},
                {"code": "Q7", "title": "GMP for Active Pharmaceutical Ingredients", "summary": "GMP requirements specific to API manufacturing."},
                {"code": "Q8(R2)", "title": "Pharmaceutical Development", "summary": "Quality by Design (QbD) principles, Design Space, Control Strategy."},
                {"code": "Q9(R1)", "title": "Quality Risk Management", "summary": "Risk assessment tools: FMEA, FTA, HACCP for pharmaceutical quality."},
                {"code": "Q10", "title": "Pharmaceutical Quality System", "summary": "Lifecycle approach to quality management."},
                {"code": "Q11", "title": "Development and Manufacture of Drug Substances", "summary": "QbD for drug substance, process validation."},
                {"code": "Q12", "title": "Lifecycle Management", "summary": "Post-approval change management, structured approach."},
                {"code": "Q13", "title": "Continuous Manufacturing", "summary": "Regulatory framework for continuous manufacturing of drug substances and products."},
                {"code": "Q14", "title": "Analytical Procedure Development", "summary": "Science and risk-based approach to analytical procedure development."},
            ],
            "safety": [
                {"code": "S1A", "title": "Need for Carcinogenicity Studies", "summary": "When carcinogenicity studies are required."},
                {"code": "S1B", "title": "Testing for Carcinogenicity", "summary": "Reduced carcinogenicity testing approaches."},
                {"code": "S2(R1)", "title": "Genotoxicity Testing", "summary": "Standard battery: bacterial reverse mutation + in vitro + in vivo micronucleus."},
                {"code": "S3A", "title": "Toxicokinetics", "summary": "Exposure assessment in nonclinical studies."},
                {"code": "S3B", "title": "Pharmacokinetics in Repeat-Dose Studies", "summary": "PK sampling in toxicity studies."},
                {"code": "S5(R3)", "title": "Reproductive Toxicology", "summary": "Fertility, embryo-fetal development, pre/postnatal studies."},
                {"code": "S6(R1)", "title": "Preclinical Safety of Biotechnology Products", "summary": "Nonclinical testing for biologics."},
                {"code": "S7A", "title": "Safety Pharmacology", "summary": "Core battery: cardiovascular, respiratory, CNS."},
                {"code": "S7B", "title": "QT Prolongation", "summary": "hERG channel and in vivo QT assessment."},
                {"code": "S8", "title": "Immunotoxicology", "summary": "When immunotoxicity studies are needed."},
                {"code": "S9", "title": "Nonclinical Evaluation for Anticancer Pharmaceuticals", "summary": "Reduced nonclinical requirements for oncology."},
                {"code": "S10", "title": "Photosafety Evaluation", "summary": "Phototoxicity assessment."},
                {"code": "S11", "title": "Nonclinical Safety for Pediatric", "summary": "Juvenile animal studies for pediatric drugs."},
                {"code": "S12", "title": "Nonclinical Biodistribution for Gene Therapy", "summary": "Biodistribution requirements for GTx."},
            ],
            "clinical": [
                {"code": "E1", "title": "Extent of Population Exposure", "summary": "Safety database size requirements (100-300 patients for 6 months)."},
                {"code": "E2A", "title": "Clinical Safety Data Management", "summary": "Definitions and standards for expedited reporting of adverse events."},
                {"code": "E2B(R3)", "title": "Individual Case Safety Report (ICSR)", "summary": "Electronic submission format for adverse event reports."},
                {"code": "E2C(R2)", "title": "Periodic Benefit-Risk Evaluation Report", "summary": "PSUR/PBRER requirements and format."},
                {"code": "E2F", "title": "Development Safety Update Report", "summary": "DSUR format and content requirements."},
                {"code": "E3", "title": "Structure and Content of Clinical Study Reports", "summary": "CSR format, CONSORT adaptation for pharma."},
                {"code": "E4", "title": "Dose-Response Studies", "summary": "Design and analysis of dose-response studies."},
                {"code": "E6(R2)", "title": "Good Clinical Practice (GCP)", "summary": "ICH GCP requirements for clinical trials."},
                {"code": "E7", "title": "Studies in Support of Special Populations", "summary": "Geriatric and pediatric study requirements."},
                {"code": "E8(R1)", "title": "General Considerations for Clinical Studies", "summary": "Study design principles, quality by design in clinical."},
                {"code": "E9(R1)", "title": "Statistical Principles for Clinical Trials", "summary": "Estimands framework, missing data handling, multiplicity."},
                {"code": "E10", "title": "Choice of Control Group", "summary": "Placebo, active, historical controls. Assay sensitivity."},
                {"code": "E11(R1)", "title": "Clinical Investigation of Medicinal Products in Pediatric Population", "summary": "Pediatric study requirements and extrapolation."},
                {"code": "E14/S7B", "title": "QT/QTc Prolongation", "summary": "Thorough QT study design and cardiac safety assessment."},
            ],
        }

        if category and category in guidelines:
            return {"success": True, "category": category, "guidelines": guidelines[category], "count": len(guidelines[category])}
        elif not category:
            return {"success": True, "categories": list(guidelines.keys()), "total": sum(len(v) for v in guidelines.values())}
        else:
            return {"error": f"Unknown category: {category}. Available: {list(guidelines.keys())}"}

    def _stability_planner(self, input):
        """ICH stability study conditions planner.
        
        Returns recommended conditions, time points, and acceptance criteria.
        Reference: ICH Q1A(R2), Q1B.
        """
        product_type = input.get("product_type", "solid")  # solid, liquid, semisolid, biological
        storage_condition = input.get("storage_condition", "standard")  # standard, accelerated, stress

        conditions = {
            "standard": [
                {"condition": "25°C ± 2°C / 60% RH ± 5%", "region": "ICH Zone I/II", "months": [0, 3, 6, 9, 12, 18, 24, 36], "purpose": "Long-term (primary)"},
                {"condition": "30°C ± 2°C / 65% RH ± 5%", "region": "ICH Zone III", "months": [0, 3, 6, 9, 12, 18, 24], "purpose": "Long-term (Zone III)"},
                {"condition": "40°C ± 2°C / 75% RH ± 5%", "region": "Accelerated", "months": [0, 3, 6], "purpose": "Accelerated (6 months)"},
            ],
            "accelerated": [
                {"condition": "40°C ± 2°C / 75% RH ± 5%", "region": "ICH Q1A", "months": [0, 1, 2, 3, 6], "purpose": "Accelerated stability"},
                {"condition": "50°C ± 2°C / ambient RH", "region": "Stress", "months": [0, 1, 2], "purpose": "Stress testing (extreme)"},
            ],
            "photostability": [
                {"condition": "D65 fluorescent lamp ≥ 1.2 million lux·hours", "region": "ICH Q1B", "purpose": "Visible light photostability"},
                {"condition": "UV light ≥ 200 W·hours/m²", "region": "ICH Q1B", "purpose": "UV photostability"},
            ],
            "biological": [
                {"condition": "5°C ± 3°C", "region": "Refrigerated", "months": [0, 3, 6, 12, 18, 24], "purpose": "Long-term (biological)"},
                {"condition": "25°C ± 2°C", "region": "Accelerated (biological)", "months": [0, 1, 3, 6], "purpose": "Accelerated for biologics"},
                {"condition": "-20°C ± 5°C", "region": "Frozen", "months": [0, 6, 12, 24], "purpose": "Frozen storage validation"},
            ],
        }

        key = storage_condition
        if product_type == "biological" and storage_condition == "standard":
            key = "biological"

        return {
            "success": True,
            "product_type": product_type,
            "storage_condition": storage_condition,
            "conditions": conditions.get(key, conditions["standard"]),
            "reference": "ICH Q1A(R2), Q1B",
            "testing_parameters": {
                "solid": ["Appearance", "Assay", "Impurities", "Dissolution", "Water content", "Microbial limits"],
                "liquid": ["Appearance", "pH", "Assay", "Impurities", "Particulate matter", "Preservative content", "Microbial limits"],
                "semisolid": ["Appearance", "pH", "Assay", "Impurities", "Viscosity", "Microbial limits"],
                "biological": ["Appearance", "pH", "Assay", "Aggregation", "Fragmentation", "Potency", "Sterility"],
            }.get(product_type, ["Appearance", "Assay", "Impurities"]),
        }

    def _be_report(self, input):
        """Bioequivalence study report generator.
        
        Calculates 90% CI for Cmax and AUC ratio (FDA/EMA guidelines).
        Reference: FDA Guidance: Statistical Approaches to BE, 2001.
        """
        test_cmax = input.get("test_cmax", [])
        ref_cmax = input.get("ref_cmax", [])
        test_auc = input.get("test_auc", [])
        ref_auc = input.get("ref_auc", [])

        if not test_cmax or not ref_cmax:
            return {"error": "test_cmax and ref_cmax arrays required"}

        result = {"success": True, "reference": "FDA Guidance: Statistical Approaches to BE 2001"}

        for param_name, test_vals, ref_vals in [("Cmax", test_cmax, ref_cmax), ("AUC", test_auc, ref_auc)]:
            if not test_vals or not ref_vals:
                continue

            test_log = np.log(np.array(test_vals, dtype=float))
            ref_log = np.log(np.array(ref_vals, dtype=float))

            n_test = len(test_log)
            n_ref = len(ref_log)

            mean_diff = np.mean(test_log) - np.mean(ref_log)
            mse = (np.sum((test_log - np.mean(test_log))**2) + np.sum((ref_log - np.mean(ref_log))**2)) / (n_test + n_ref - 2)
            se = np.sqrt(mse * (1/n_test + 1/n_ref))

            # 90% CI for ratio
            from scipy import stats
            t_crit = stats.t.ppf(0.95, n_test + n_ref - 2)
            ci_lower = math.exp(mean_diff - t_crit * se) * 100
            ci_upper = math.exp(mean_diff + t_crit * se) * 100
            gmr = math.exp(mean_diff) * 100

            within_80_125 = ci_lower >= 80 and ci_upper <= 125

            result[param_name] = {
                "gmr_percent": round(gmr, 2),
                "ci_90_lower": round(ci_lower, 2),
                "ci_90_upper": round(ci_upper, 2),
                "within_80_125": within_80_125,
                "n_test": n_test,
                "n_ref": n_ref,
                "verdict": "BIOEQUIVALENT" if within_80_125 else "NOT BIOEQUIVALENT",
            }

        return result

    def _ind_nda_checklist(self, input):
        """IND/NDA submission checklist generator."""
        submission_type = input.get("type", "IND")  # IND, NDA, ANDA, 505(b)(2)

        checklists = {
            "IND": {
                "pre_ind": [
                    "Pre-IND meeting request and briefing document",
                    "Drug substance characterization (CMC)",
                    "Pharmacology data (in vitro + in vivo)",
                    "Toxicology data (single dose, repeat dose, genotoxicity)",
                    "Proposed clinical protocol",
                    "Investigator's Brochure (IB)",
                    "FDA Form 1571",
                    "FDA Form 1572 (Investigator)",
                    "Debarment certification",
                    "Financial disclosure forms",
                ],
                "phase_1": [
                    "First-in-human protocol (dose escalation)",
                    "IND safety reports (within 15 days for SAE)",
                    "Annual report",
                    "Updated IB as needed",
                ],
                "phase_2": [
                    "Efficacy protocol (dose-response)",
                    "Updated CMC section",
                    "Updated toxicology if new routes/doses",
                    "IND amendments for protocol changes",
                ],
                "phase_3": [
                    "Pivotal efficacy trials protocol",
                    "Complete CMC package",
                    "Full toxicology package",
                    "Draft labeling",
                    "Pediatric study plan (if applicable)",
                ],
            },
            "NDA": {
                "module_1": [
                    "FDA Form 356h",
                    "Prescribing information (draft labeling)",
                    "Patent information",
                    "Debarment certification",
                ],
                "module_2_3": [
                    "Quality Overall Summary (QOS)",
                    "Drug substance characterization",
                    "Drug product formulation and manufacturing",
                    "Stability data (minimum 12 months accelerated + long-term)",
                    "Container closure system validation",
                ],
                "module_4": [
                    "Complete nonclinical package",
                    "Pharmacology (primary + secondary)",
                    "Pharmacokinetics (ADME, bioavailability)",
                    "Toxicology (acute, repeat dose, genotox, reproductive, carcinogenicity)",
                ],
                "module_5": [
                    "Clinical study reports (all phases)",
                    "Pivotal efficacy + safety data",
                    "PK/PD studies",
                    "Drug interaction studies",
                    "Special population studies (renal, hepatic, elderly, pediatric)",
                    "Post-marketing commitments (if any)",
                ],
            },
            "ANDA": {
                "requirements": [
                    "Same active ingredient, dosage form, strength, route of administration, labeling",
                    "Bioequivalence study (90% CI: 80-125% for Cmax and AUC)",
                    "Pharmaceutical equivalence demonstration",
                    "Drug master file (DMF) access letter from API supplier",
                    "Stability data (3 batches, 12 months accelerated + long-term)",
                    "Container closure system",
                    "Labeling (RLD comparison)",
                    "Patent certification (Paragraph I, II, III, or IV)",
                ],
            },
            "505b2": {
                "requirements": [
                    "Full safety + efficacy reports (own studies OR literature)",
                    "Published literature to support safety/efficacy (if relying on)",
                    "BE study against RLD",
                    "CMC data",
                    "Labeling (may differ from RLD with justification)",
                    "Patent certification",
                ],
            },
        }

        if submission_type not in checklists:
            return {"error": f"Unknown type: {submission_type}. Available: {list(checklists.keys())}"}

        return {
            "success": True,
            "type": submission_type,
            "checklist": checklists[submission_type],
            "reference": "FDA 21 CFR Parts 312 (IND), 314 (NDA/ANDA)",
        }
