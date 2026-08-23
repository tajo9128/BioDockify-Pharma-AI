"""Natural Products / Pharmacognosy API — phytochemical screening, extraction
efficiency, bioassay calculations, medicinal plant database, dereplication.

For pharmacognosy and natural products researchers.
"""
from helpers.api import ApiHandler, Request, Response
import logging, math
import numpy as np

log = logging.getLogger("natural_products")


def _kb_store(title, content, tags=None):
    try:
        from modules.knowledge.auto_store import auto_store
        auto_store("natural_products", title, content, source="Natural Products",
                   tags=tags or ["natural_products"], category="natural_products")
    except Exception:
        pass


class NaturalProductsHandler(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict:
        action = input.get("action", "")
        result = None
        if action == "phytochemical_screen": result = self._phytochemical_screen(input)
        elif action == "extraction_yield": result = self._extraction_yield(input)
        elif action == "ic50": result = self._ic50(input)
        elif action == "plant_database": result = self._plant_database(input)
        elif action == "dereplication": result = self._dereplication(input)
        elif action == "formula_analysis": result = self._formula_analysis(input)
        elif action == "dereplication_match": result = self._dereplication_match(input)
        elif action == "selectivity_index": result = self._selectivity_index(input)
        else:
            return {
                "actions": ["phytochemical_screen", "extraction_yield", "ic50", "plant_database", "dereplication", "formula_analysis", "dereplication_match", "selectivity_index"],
                "hint": "Natural products: phytochemical screening, extraction yields, IC50 calculation, plant database"
            }
        if result and not result.get("error"):
            _kb_store(f"Natural Products — {action.replace('_', ' ').title()}", result, ["natural_products", action])
        return result

    def _phytochemical_screen(self, input):
        """Standard phytochemical qualitative screening protocols.
        
        Returns the standard test reagents and expected results for each
        phytochemical class. Based on Sofowora, Trease & Evans, Harborne.
        """
        compound_class = input.get("class", "")

        screening_protocols = {
            "alkaloids": {
                "tests": [
                    {"name": "Mayer's test", "reagent": "Mercuric potassium iodide", "positive": "White/cream precipitate", "sensitivity": "High"},
                    {"name": "Dragendorff's test", "reagent": "Bismuth potassium iodide", "positive": "Orange/red precipitate", "sensitivity": "High"},
                    {"name": "Wagner's test", "reagent": "Iodine-potassium iodide", "positive": "Brown/reddish precipitate", "sensitivity": "Medium"},
                    {"name": "Hager's test", "reagent": "Picric acid", "positive": "Yellow precipitate", "sensitivity": "Low"},
                ],
                "extraction": "Acid-base extraction (dilute HCl → basify with NH₄OH → extract with CHCl₃)",
                "reference": "Harborne, Phytochemical Methods, 3rd ed."
            },
            "flavonoids": {
                "tests": [
                    {"name": "Shinoda test", "reagent": "Mg + HCl", "positive": "Pink/red color", "sensitivity": "High"},
                    {"name": "Alkaline reagent test", "reagent": "NaOH", "positive": "Yellow color (intense)", "sensitivity": "Medium"},
                    {"name": "Lead acetate test", "reagent": "Lead acetate solution", "positive": "Yellow precipitate", "sensitivity": "Medium"},
                    {"name": "Ferric chloride test", "reagent": "FeCl₃", "positive": "Dark green/blue color", "sensitivity": "Low"},
                ],
                "extraction": "Ethanol/methanol extraction, acid hydrolysis for aglycones",
                "reference": "Mabry et al., Systematic Identification of Flavonoids, 1970"
            },
            "tannins": {
                "tests": [
                    {"name": "Ferric chloride test", "reagent": "FeCl₃ (5%)", "positive": "Blue-black (hydrolyzable) or green (condensed)", "sensitivity": "High"},
                    {"name": "Gelatin test", "reagent": "Gelatin + NaCl", "positive": "White precipitate", "sensitivity": "High"},
                    {"name": "Lead acetate test", "reagent": "Lead acetate", "positive": "White precipitate", "sensitivity": "Medium"},
                    {"name": "Bromine water test", "reagent": "Bromine water", "positive": "Decolorization (condensed tannins)", "sensitivity": "Medium"},
                ],
                "extraction": "Aqueous acetone (70%) or aqueous methanol",
                "reference": "Trease & Evans, Pharmacognosy, 16th ed."
            },
            "saponins": {
                "tests": [
                    {"name": "Foam test", "reagent": "Water + shake", "positive": "Persistent foam (>10 min)", "sensitivity": "High"},
                    {"name": "Hemolysis test", "reagent": "Blood cells", "positive": "Hemolysis of red blood cells", "sensitivity": "High"},
                    {"name": "Liebermann-Burchard test", "reagent": "Acetic anhydride + H₂SO₄", "positive": "Green color", "sensitivity": "Medium"},
                ],
                "extraction": "Aqueous ethanol (70%), butanol extraction",
                "reference": "Hostettmann & Marston, Saponins, 1995"
            },
            "steroids": {
                "tests": [
                    {"name": "Liebermann-Burchard test", "reagent": "Acetic anhydride + H₂SO₄", "positive": "Blue-green ring", "sensitivity": "High"},
                    {"name": "Salkowski test", "reagent": "Conc. H₂SO₄ + CHCl₃", "positive": "Red-brown ring at interface", "sensitivity": "High"},
                    {"name": "Tortelli-Jaffe test", "reagent": "Bromine + CHCl₃", "positive": "Green color", "sensitivity": "Medium"},
                ],
                "extraction": "Hexane/ether extraction, saponification",
                "reference": "Evans, Trease and Evans' Pharmacognosy, 16th ed."
            },
            "terpenoids": {
                "tests": [
                    {"name": "Salkowski test", "reagent": "Conc. H₂SO₄", "positive": "Red-brown color", "sensitivity": "High"},
                    {"name": "Liebermann-Burchard test", "reagent": "Acetic anhydride + H₂SO₄", "positive": "Blue-green color", "sensitivity": "Medium"},
                ],
                "extraction": "Hexane/dichloromethane extraction",
                "reference": "Dewick, Medicinal Natural Products, 3rd ed."
            },
            "glycosides": {
                "tests": [
                    {"name": "Borntrager's test", "reagent": "Dilute H₂SO₄ + ether + NH₃", "positive": "Pink/red color (anthraquinone glycosides)", "sensitivity": "High"},
                    {"name": "Keller-Killiani test", "reagent": "Glacial acetic acid + FeCl₃ + H₂SO₄", "positive": "Brown ring at interface (cardiac glycosides)", "sensitivity": "High"},
                    {"name": "Legal's test", "reagent": "Sodium nitroprusside + NaOH", "positive": "Pink color (cardenolides)", "sensitivity": "Medium"},
                ],
                "extraction": "Aqueous ethanol, enzymatic hydrolysis for aglycones",
                "reference": "Bruneton, Pharmacognosy, Phytochemistry, Medicinal Plants, 2nd ed."
            },
        }

        if compound_class and compound_class in screening_protocols:
            return {"success": True, "class": compound_class, **screening_protocols[compound_class]}
        elif not compound_class:
            return {"success": True, "available_classes": list(screening_protocols.keys()), "total": len(screening_protocols)}
        else:
            return {"error": f"Unknown class: {compound_class}. Available: {list(screening_protocols.keys())}"}

    def _extraction_yield(self, input):
        """Calculate extraction efficiency.
        
        Yield% = (weight of extract / weight of raw material) × 100
        """
        raw_weight = input.get("raw_weight_g", 0)
        extract_weight = input.get("extract_weight_g", 0)
        method = input.get("method", "maceration")

        if not raw_weight or not extract_weight:
            return {"error": "raw_weight_g and extract_weight_g required"}

        yield_pct = (extract_weight / raw_weight) * 100

        method_info = {
            "soxhlet": {"solvent": "Ethanol/methanol", "time": "6-8 hours", "temp": "Solvent boiling point", "efficiency": "High"},
            "maceration": {"solvent": "Ethanol/water", "time": "3-7 days", "temp": "Room temperature", "efficiency": "Medium"},
            "ultrasound": {"solvent": "Ethanol/methanol", "time": "30-60 min", "temp": "Room temperature", "efficiency": "High"},
            "supercritical_co2": {"solvent": "CO₂ + co-solvent", "time": "1-4 hours", "temp": "40-60°C", "efficiency": "Very high"},
        }

        return {
            "success": True,
            "yield_percent": round(yield_pct, 2),
            "method": method,
            "method_info": method_info.get(method, {}),
            "classification": "High (>10%)" if yield_pct > 10 else ("Medium (3-10%)" if yield_pct > 3 else "Low (<3%)"),
        }

    def _ic50(self, input):
        """IC50/EC50 calculation from dose-response data.
        
        Uses 4-parameter logistic regression (Hill equation).
        Reference: Motulsky & Christopoulos, Fitting Models to Biological Data, 2004.
        """
        concentrations = input.get("concentrations", [])
        responses = input.get("responses", [])
        control_response = input.get("control_response", 100)

        if not concentrations or not responses:
            return {"error": "concentrations and responses arrays required"}

        concs = np.array(concentrations, dtype=float)
        resps = np.array(responses, dtype=float)

        # Normalize to % of control
        if control_response > 0:
            resps_norm = (resps / control_response) * 100
        else:
            resps_norm = resps

        # Simple IC50 estimation: find concentration at 50% response
        # Using linear interpolation
        try:
            # Sort by concentration
            sort_idx = np.argsort(concs)
            concs_s = concs[sort_idx]
            resps_s = resps_norm[sort_idx]

            # Find where response crosses 50%
            ic50 = None
            for i in range(len(resps_s) - 1):
                if (resps_s[i] <= 50 <= resps_s[i+1]) or (resps_s[i] >= 50 >= resps_s[i+1]):
                    # Linear interpolation
                    t = (50 - resps_s[i]) / (resps_s[i+1] - resps_s[i]) if resps_s[i+1] != resps_s[i] else 0
                    ic50 = concs_s[i] + t * (concs_s[i+1] - concs_s[i])
                    break

            # Also try 4-parameter logistic fit
            try:
                from scipy.optimize import curve_fit
                def logistic_4p(x, bottom, top, ic50, hill):
                    return bottom + (top - bottom) / (1 + (x / ic50) ** hill)

                popt, pcov = curve_fit(logistic_4p, concs_s, resps_s, 
                                       p0=[min(resps_s), max(resps_s), np.median(concs), 1],
                                       maxfev=10000)
                ic50_fitted = popt[2]
                hill = popt[3]
                r2 = 1 - np.sum((resps_s - logistic_4p(concs_s, *popt))**2) / np.sum((resps_s - np.mean(resps_s))**2)
                # Sanity check: IC50 should be within the tested concentration range
                conc_min, conc_max = min(concs_s), max(concs_s)
                if ic50_fitted < conc_min * 0.1 or ic50_fitted > conc_max * 10:
                    ic50_fitted = ic50  # fallback to interpolation
                    r2 = None
            except:
                ic50_fitted = ic50
                hill = None
                r2 = None

            return {
                "success": True,
                "ic50": round(float(ic50), 4) if ic50 else None,
                "ic50_fitted": round(float(ic50_fitted), 4) if ic50_fitted else None,
                "hill_coefficient": round(float(hill), 2) if hill else None,
                "r_squared": round(float(r2), 4) if r2 else None,
                "control_response": control_response,
                "data_points": len(concs),
            }
        except Exception as e:
            return {"error": f"IC50 calculation failed: {e}"}

    def _plant_database(self, input):
        """Common medicinal plants database with traditional uses and active compounds."""
        plant_name = input.get("name", "").lower()

        plants = {
            "evolvulus_alsinoides": {
                "common_name": "Shankhpushpi",
                "family": "Convolvulaceae",
                "traditional_use": "Nootropic, anxiolytic, memory enhancement (Ayurveda)",
                "active_compounds": ["Scopoletin", "Ursolic acid", "Quercetin", "Caffeic acid"],
                "pharmacological": "AChE inhibition, antioxidant, neuroprotective",
                "parts_used": "Whole plant",
                "reference": "Nahata et al., J Ethnopharmacol 2012"
            },
            "cinnamomum_verum": {
                "common_name": "Ceylon Cinnamon",
                "family": "Lauraceae",
                "traditional_use": "Anti-diabetic, digestive aid, anti-inflammatory",
                "active_compounds": ["Cinnamaldehyde", "Eugenol", "Cinnamic acid", "Linalool"],
                "pharmacological": "Anti-diabetic (insulin sensitivity), antimicrobial, antioxidant",
                "parts_used": "Bark, leaves",
                "reference": "Ranasinghe et al., BMC Complement Altern Med 2013"
            },
            "curcuma_longa": {
                "common_name": "Turmeric",
                "family": "Zingiberaceae",
                "traditional_use": "Anti-inflammatory, wound healing, digestive",
                "active_compounds": ["Curcumin", "Demethoxycurcumin", "Bisdemethoxycurcumin"],
                "pharmacological": "NF-κB inhibition, COX-2 inhibition, antioxidant",
                "parts_used": "Rhizome",
                "reference": "Hewlings & Kalman, Foods 2017"
            },
            "withania_somnifera": {
                "common_name": "Ashwagandha",
                "family": "Solanaceae",
                "traditional_use": "Adaptogen, stress relief, vitality (Ayurveda)",
                "active_compounds": ["Withanolide A", "Withaferin A", "Withanoside IV"],
                "pharmacological": "GABAergic, anti-cortisol, immunomodulatory",
                "parts_used": "Root, leaf",
                "reference": "Mikolai et al., J Int Soc Sports Nutr 2009"
            },
            "boswellia_serrata": {
                "common_name": "Indian Frankincense",
                "family": "Burseraceae",
                "traditional_use": "Anti-inflammatory, joint health (Ayurveda)",
                "active_compounds": ["Boswellic acid", "AKBA (3-O-acetyl-11-keto-β-boswellic acid)"],
                "pharmacological": "5-LOX inhibition, anti-inflammatory, anti-arthritic",
                "parts_used": "Resin/gum",
                "reference": "Siddiqui, Indian J Pharm Sci 2011"
            },
            "centella_asiatica": {
                "common_name": "Gotu Kola",
                "family": "Apiaceae",
                "traditional_use": "Wound healing, cognitive enhancement, longevity",
                "active_compounds": ["Asiaticoside", "Madecassoside", "Asiatic acid", "Madecassic acid"],
                "pharmacological": "Collagen synthesis, neuroprotective, anti-inflammatory",
                "parts_used": "Leaves",
                "reference": "Brinkhaus et al., Phytomedicine 2000"
            },
            "salix_alba": {
                "common_name": "White Willow Bark",
                "family": "Salicaceae",
                "traditional_use": "Analgesic, anti-inflammatory, antipyretic",
                "active_compounds": ["Salicin", "Salicylic acid", "Flavonoids"],
                "pharmacological": "COX inhibition (natural aspirin precursor)",
                "parts_used": "Bark",
                "reference": "Gao et al., J Tradit Complement Med 2020"
            },
            "gingko_biloba": {
                "common_name": "Ginkgo",
                "family": "Ginkgoaceae",
                "traditional_use": "Cognitive enhancement, peripheral circulation",
                "active_compounds": ["Ginkgolide A", "Ginkgolide B", "Bilobalide", "Flavonoids"],
                "pharmacological": "Neuroprotective, antiplatelet, antioxidant",
                "parts_used": "Leaves",
                "reference": "Tan et al., J Ethnopharmacol 2015"
            },
            "silybum_marianum": {
                "common_name": "Milk Thistle",
                "family": "Asteraceae",
                "traditional_use": "Liver protection, hepatoprotective",
                "active_compounds": ["Silymarin", "Silybin", "Isosilibinin"],
                "pharmacological": "Hepatoprotective, antioxidant, anti-inflammatory",
                "parts_used": "Seeds",
                "reference": "Federico et al., Molecules 2017"
            },
            "panax_ginseng": {
                "common_name": "Ginseng",
                "family": "Araliaceae",
                "traditional_use": "Adaptogen, vitality, cognitive enhancement",
                "active_compounds": ["Ginsenoside Rb1", "Ginsenoside Rg1", "Ginsenoside Rg3"],
                "pharmacological": "Immunomodulatory, anti-cancer, neuroprotective",
                "parts_used": "Root",
                "reference": "Liu et al., J Ginseng Res 2019"
            },
            "cannabis_sativa": {
                "common_name": "Hemp/Cannabis",
                "family": "Cannabaceae",
                "traditional_use": "Analgesic, anti-inflammatory, anxiolytic",
                "active_compounds": ["THC (Δ9-tetrahydrocannabinol)", "CBD (cannabidiol)", "CBG (cannabigerol)", "CBC (cannabichromene)"],
                "pharmacological": "CB1/CB2 receptor agonism/antagonism, 5-HT1A agonism (CBD)",
                "parts_used": "Flowers, leaves, resin",
                "reference": "Mechoulam et al., Nat Rev Neurosci 2020"
            },
        }

        if plant_name and plant_name in plants:
            return {"success": True, "plant": plants[plant_name]}
        elif not plant_name:
            return {"success": True, "available_plants": list(plants.keys()), "total": len(plants)}
        else:
            # Fuzzy search
            matches = [k for k in plants.keys() if plant_name.replace(" ", "_") in k or k.replace("_", " ") in plant_name]
            if matches:
                return {"success": True, "matches": [plants[m] for m in matches]}
            return {"error": f"Plant '{plant_name}' not in database. Available: {list(plants.keys())}"}

    def _dereplication(self, input):
        """Molecular formula-based dereplication.
        
        Calculates exact mass, degree of unsaturation, and common
        natural product classes from molecular formula.
        """
        formula = input.get("formula", "")

        if not formula:
            return {"error": "Molecular formula required (e.g., C20H24O5)"}

        # Parse formula
        import re
        elements = {}
        for match in re.finditer(r'([A-Z][a-z]?)(\d*)', formula):
            elem = match.group(1)
            count = int(match.group(2)) if match.group(2) else 1
            elements[elem] = count

        # Atomic masses
        masses = {'C': 12.011, 'H': 1.008, 'O': 15.999, 'N': 14.007, 'S': 32.065, 'P': 30.974}

        exact_mass = sum(elements.get(e, 0) * m for e, m in masses.items())

        # Degree of unsaturation (DBE)
        c = elements.get('C', 0)
        h = elements.get('H', 0)
        n = elements.get('N', 0)
        dbe = c - (h / 2) + (n / 2) + 1

        # Guess compound class
        class_hint = "Unknown"
        if 'N' in elements and elements.get('N', 0) >= 1:
            class_hint = "Alkaloid (contains nitrogen)"
        elif 'O' in elements and elements.get('O', 0) >= 4 and dbe >= 6:
            class_hint = "Flavonoid or polyphenol"
        elif dbe >= 8 and 'O' in elements:
            class_hint = "Terpenoid or polyketide"
        elif elements.get('C', 0) >= 20 and 'O' in elements:
            class_hint = "Steroid or triterpenoid"

        return {
            "success": True,
            "formula": formula,
            "exact_mass": round(exact_mass, 4),
            "degree_of_unsaturation": round(dbe, 1),
            "compound_class_hint": class_hint,
            "elements": elements,
        }

    def _selectivity_index(self, input):
        """Selectivity index = IC50(cancer) / IC50(normal).
        
        Higher SI = more selective (good). SI > 3 = potentially selective.
        """
        ic50_cancer = input.get("ic50_cancer", 0)
        ic50_normal = input.get("ic50_normal", 0)

        if not ic50_cancer or not ic50_normal:
            return {"error": "ic50_cancer and ic50_normal required"}

        si = ic50_normal / ic50_cancer

        return {
            "success": True,
            "selectivity_index": round(si, 2),
            "ic50_cancer": ic50_cancer,
            "ic50_normal": ic50_normal,
            "interpretation": "Highly selective (SI > 10)" if si > 10 else ("Selective (SI > 3)" if si > 3 else "Non-selective (SI < 3)"),
            "reference": "Badisa et al., Molecules 2020"
        }

    def _formula_analysis(self, input):
        """Full formula profile: monoisotopic mass, RDBE, NP class hints, adduct m/z table."""
        formula = input.get("formula", "")
        if not formula:
            return {"error": "formula required (e.g. C21H30O2)"}
        from modules.natural_products.dereplication import analyze_formula
        try:
            return analyze_formula(formula)
        except ValueError as e:
            return {"error": str(e)}

    def _dereplication_match(self, input):
        """Match observed m/z against reference compounds with ppm tolerance."""
        mz = input.get("observed_mz")
        references = input.get("references", [])
        if mz is None:
            return {"error": "observed_mz required"}
        from modules.natural_products.dereplication import match_candidates
        return match_candidates(mz, references,
                                tolerance_ppm=float(input.get("tolerance_ppm", 5.0)),
                                adduct=input.get("adduct", "[M+H]+"))
