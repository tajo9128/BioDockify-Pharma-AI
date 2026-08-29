"""Structure Draw API — in-browser 2D editor (JSME) + RDKit engine + optional ChemCanvas bridge.

Draw molecules, PubChem lookup, import/export (mol/sdf/smi/cdxml), clean 2D,
depict SVG, properties, Send-To pipeline. If the ChemCanvas desktop app is
installed it can be launched with a library file for native editing.
"""
from helpers.api import ApiHandler, Request, Response
import asyncio
import json
import logging
import os
import re
import shutil
import sys
import urllib.parse
import urllib.request

log = logging.getLogger("api.chem_canvas")

STRUCTURES_DIR = os.path.join("usr", "structures")
LAUNCHER_OVERRIDE = os.path.join(STRUCTURES_DIR, ".launcher.txt")
SAFE_NAME = re.compile(r"^[\w][\w.\- ]{0,80}$")
READABLE_EXT = {"mol", "sdf", "smi", "smiles", "cdxml", "rxn"}
LISTABLE_EXT = READABLE_EXT | {"mrv", "ccdx", "svg"}

PUBCHEM_PROPS = "CanonicalSMILES,IUPACName,MolecularFormula,MolecularWeight"


def _structures_dir() -> str:
    os.makedirs(STRUCTURES_DIR, exist_ok=True)
    return STRUCTURES_DIR


def _safe_filename(name: str, ext: str) -> str:
    name = (name or "structure").strip().replace("/", "_").replace("\\", "_")
    if not SAFE_NAME.match(name):
        raise ValueError("Invalid structure name")
    return f"{name}.{ext.lstrip('.')}"


def _in_docker() -> bool:
    return os.path.exists("/.dockerenv")


def _detect_launcher() -> list | None:
    """Find the ChemCanvas desktop launcher (Windows/Linux). Returns argv list or None."""
    override = ""
    try:
        with open(LAUNCHER_OVERRIDE, encoding="utf-8") as f:
            override = f.read().strip()
    except Exception:
        pass
    if override:
        return override.split()

    which = shutil.which("chemcanvas")
    if which:
        return [which]

    if sys.platform == "win32":
        candidates = [
            os.path.expandvars(r"%LOCALAPPDATA%\Programs\ChemCanvas\chemcanvas.exe"),
            os.path.expandvars(r"%LOCALAPPDATA%\Programs\ChemCanvas\ChemCanvas.exe"),
            os.path.expandvars(r"%PROGRAMFILES%\ChemCanvas\chemcanvas.exe"),
            os.path.expandvars(r"%PROGRAMFILES%\ChemCanvas\ChemCanvas.exe"),
        ]
        for c in candidates:
            if c and os.path.isfile(c):
                return [c]
    else:
        home_apps = os.path.expanduser("~/Applications")
        if os.path.isdir(home_apps):
            for f in sorted(os.listdir(home_apps)):
                if "chemcanvas" in f.lower() and f.endswith(".AppImage"):
                    return [os.path.join(home_apps, f)]
        # only claim installed if the app is actually present — a flatpak/snap
        # runtime alone is not the app (avoids false "installed" on stock Linux)
        flatpak_dirs = (
            os.path.expanduser("~/.local/share/flatpak/app/io.github.ksharindam.chemcanvas"),
            "/var/lib/flatpak/app/io.github.ksharindam.chemcanvas",
        )
        if any(os.path.isdir(fd) for fd in flatpak_dirs):
            return ["flatpak", "run", "io.github.ksharindam.chemcanvas"]
        if os.path.isdir("/snap/chemcanvas"):
            return ["snap", "run", "chemcanvas"]
        return None


def _mol_from_text(text: str, ext: str):
    """Parse a structure file body by extension. Returns (mol, kind, note)."""
    from rdkit import Chem

    ext = ext.lower().lstrip(".")
    if ext in ("smi", "smiles"):
        first = text.strip().splitlines()[0].strip()
        smi = first.split()[0] if first else ""
        return Chem.MolFromSmiles(smi), "smiles", None
    if ext == "cdxml":
        mol = Chem.MolFromCDXML(text)
        return mol, "cdxml", None
    if ext == "rxn":
        from rdkit.Chem import RDLogs
        RDLogs.DisableLog("rdApp.warning")
        rxn = Chem.ReactionFromRxnBlock(text)
        if rxn is None:
            return None, "rxn", "Could not parse reaction"
        prod = rxn.GetProducts()[0] if rxn.GetProductNum() > 0 else None
        return prod, "rxn", f"{rxn.GetReactantNum()} reactants -> {rxn.GetProductNum()} products"
    # mol / sdf (first record)
    return Chem.MolFromMolBlock(text), "mol", None


def _depict_svg(smiles: str, size: int = 320) -> str:
    from rdkit import Chem
    from rdkit.Chem import rdDepictor, AllChem
    from rdkit.Chem.Draw import rdMolDraw2D

    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise ValueError("Invalid SMILES")
    AllChem.Compute2DCoords(mol)
    drawer = rdMolDraw2D.MolDraw2DSVG(size, size)
    rdMolDraw2D.PrepareAndDrawMolecule(drawer, mol)
    drawer.FinishDrawing()
    return drawer.GetDrawingText()


class ChemCanvasHandler(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict:
        action = input.get("action", "")

        if action == "status":
            return self._status(input)
        elif action == "launch":
            return await self._launch(input)
        elif action == "files":
            return self._files()
        elif action == "import_file":
            return self._import_file(input)
        elif action == "export_file":
            return self._export_file(input)
        elif action == "depict":
            return self._depict(input)
        elif action == "pubchem_lookup":
            return await self._pubchem_lookup(input)
        elif action == "clean2d":
            return self._clean2d(input)
        elif action == "convert":
            return self._convert(input)
        elif action == "validate":
            return self._validate(input)
        elif action == "save_to_kb":
            return self._save_to_kb(input)
        else:
            return {
                "actions": ["status", "launch", "files", "import_file", "export_file",
                            "depict", "pubchem_lookup", "clean2d", "convert", "validate", "save_to_kb"],
                "hint": "Structure Draw: JSME editor + RDKit engine + ChemCanvas bridge",
            }

    # --- ChemCanvas desktop bridge -------------------------------------

    def _status(self, input: dict) -> dict:
        launcher = _detect_launcher()
        override = ""
        try:
            with open(LAUNCHER_OVERRIDE, encoding="utf-8") as f:
                override = f.read().strip()
        except Exception:
            pass
        return {
            "installed": launcher is not None,
            "launcher": launcher,
            "launcher_overridden": bool(override),
            "platform": sys.platform,
            "in_docker": _in_docker(),
            "structures_dir": os.path.abspath(_structures_dir()),
        }

    async def _launch(self, input: dict) -> dict:
        launcher = _detect_launcher()
        if launcher is None:
            return {"error": "ChemCanvas not found. Install it (Windows .exe / Linux flatpak, snap, AppImage or .deb) or save a launcher path via status.launcher file."}
        if _in_docker():
            return {"error": "GUI apps cannot start inside the Docker container. Install ChemCanvas on the host and share the structures folder, or use the JSME editor in the Draw tab."}

        file_arg = input.get("file", "")
        argv = list(launcher)
        if file_arg:
            fname = os.path.basename(str(file_arg))
            path = os.path.join(_structures_dir(), fname)
            if os.path.exists(path):
                argv.append(path)

        kwargs = {}
        if sys.platform == "win32":
            kwargs["creationflags"] = 0x00000008 | 0x00000200  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
        try:
            proc = await asyncio.create_subprocess_exec(*argv, **kwargs)
        except Exception as e:
            log.error("ChemCanvas launch failed: %s", e)
            return {"error": f"Launch failed: {e}"}
        return {"ok": True, "pid": proc.pid, "launched": argv}

    # --- structure library ----------------------------------------------

    def _files(self) -> dict:
        d = _structures_dir()
        out = []
        for f in sorted(os.listdir(d)):
            if f.startswith("."):
                continue
            ext = f.rsplit(".", 1)[-1].lower() if "." in f else ""
            if ext not in LISTABLE_EXT:
                continue
            st = os.stat(os.path.join(d, f))
            out.append({
                "name": f,
                "ext": ext,
                "readable": ext in READABLE_EXT,
                "size": st.st_size,
                "modified": st.st_mtime,
            })
        return {"dir": os.path.abspath(d), "files": out, "count": len(out)}

    def _import_file(self, input: dict) -> dict:
        fname = os.path.basename(str(input.get("file", "")))
        ext = fname.rsplit(".", 1)[-1].lower() if "." in fname else ""
        path = os.path.join(_structures_dir(), fname)
        if not fname or not os.path.isfile(path):
            return {"error": f"File not found: {fname}"}
        if ext not in READABLE_EXT:
            return {"error": f".{ext} files are ChemCanvas-native; open them in the desktop app (Open in ChemCanvas)"}
        try:
            with open(path, encoding="utf-8", errors="replace") as f:
                text = f.read()
        except Exception as e:
            return {"error": f"Read failed: {e}"}

        from rdkit import Chem
        mol, kind, note = _mol_from_text(text, ext)
        if mol is None:
            return {"error": f"Could not parse {fname} ({kind})"}
        smiles = Chem.MolToSmiles(mol)
        result = {"file": fname, "kind": kind, "smiles": smiles, "molblock": Chem.MolToMolBlock(mol), "svg": _depict_svg(smiles)}
        if note:
            result["note"] = note
        try:
            from modules.molecular.rdkit_descriptors import calculate_all_descriptors
            result["properties"] = calculate_all_descriptors(mol)
        except Exception as e:
            log.warning("descriptors failed: %s", e)
        return result

    def _export_file(self, input: dict) -> dict:
        smiles = str(input.get("smiles", "")).strip()
        name = str(input.get("name", "")).strip() or "structure"
        ext = str(input.get("ext", "mol")).strip().lower()
        if not smiles:
            return {"error": "smiles required"}
        if ext not in ("mol", "smi"):
            return {"error": "ext must be mol or smi"}

        from rdkit import Chem
        from rdkit.Chem import AllChem
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return {"error": "Invalid SMILES"}
        AllChem.Compute2DCoords(mol)

        try:
            fname = _safe_filename(name, ext)
        except ValueError as e:
            return {"error": str(e)}
        path = os.path.join(_structures_dir(), fname)
        content = Chem.MolToMolBlock(mol) if ext == "mol" else f"{Chem.MolToSmiles(mol)} {name}\n"
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return {"ok": True, "file": fname, "path": os.path.abspath(path), "smiles": Chem.MolToSmiles(mol)}

    # --- cheminformatics -------------------------------------------------

    def _depict(self, input: dict) -> dict:
        smiles = str(input.get("smiles", "")).strip()
        if not smiles:
            return {"error": "smiles required"}
        try:
            return {"smiles": smiles, "svg": _depict_svg(smiles, int(input.get("size", 320)))}
        except ValueError as e:
            return {"error": str(e)}

    async def _pubchem_lookup(self, input: dict) -> dict:
        """Name (or CAS/common name) -> structure, mirroring ChemCanvas's PubChem template search."""
        query = str(input.get("name", "")).strip()
        if not query:
            return {"error": "name required (e.g. 'aspirin', 'ibuprofen')"}
        url = ("https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/"
               + urllib.parse.quote(query) + "/property/" + PUBCHEM_PROPS + "/JSON")
        try:
            def fetch():
                req = urllib.request.Request(url, headers={"User-Agent": "BioDockify-AI/7.27"})
                with urllib.request.urlopen(req, timeout=15) as r:
                    return json.loads(r.read().decode())
            data = await asyncio.to_thread(fetch)
        except Exception as e:
            return {"error": f"PubChem lookup failed (offline?): {e}"}

        props = (data.get("PropertyTable", {}).get("Properties") or [{}])[0]
        # PubChem renamed CanonicalSMILES -> ConnectivitySMILES in PUG REST;
        # accept either (plus raw SMILES) so lookups survive future renames
        smiles = (props.get("CanonicalSMILES") or props.get("ConnectivitySMILES")
                  or props.get("SMILES") or "")
        if not smiles:
            return {"error": f"'{query}' not found on PubChem"}
        result = {"query": query, "cid": props.get("CID"), "smiles": smiles,
                  "iupac": props.get("IUPACName", ""), "formula": props.get("MolecularFormula", ""),
                  "mw": props.get("MolecularWeight", 0), "svg": _depict_svg(smiles)}
        return result

    def _clean2d(self, input: dict) -> dict:
        """Recompute 2D coordinates (RDKit) -> molblock to reload into the editor."""
        smiles = str(input.get("smiles", "")).strip()
        if not smiles:
            return {"error": "smiles required"}
        from rdkit import Chem
        from rdkit.Chem import AllChem
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return {"error": "Invalid SMILES"}
        try:
            from rdkit.Chem import rdDepictor
            rdDepictor.SetPreferCoordGen(True)
        except Exception:
            pass
        AllChem.Compute2DCoords(mol)
        return {"smiles": Chem.MolToSmiles(mol), "molblock": Chem.MolToMolBlock(mol)}

    def _convert(self, input: dict) -> dict:
        from rdkit import Chem
        from rdkit.Chem import AllChem, Descriptors, inchi

        # NOTE: no leading strip — molfile line 1 is an (often empty) title line
        molblock = str(input.get("molblock", "") or "").rstrip()
        smiles = str(input.get("smiles", "")).strip()
        if molblock and ("V2000" in molblock or "V3000" in molblock):
            mol = Chem.MolFromMolBlock(molblock)
        elif smiles:
            mol = Chem.MolFromSmiles(smiles)
        else:
            return {"error": "smiles or molblock required"}
        if mol is None:
            return {"error": "Cannot parse structure"}
        AllChem.Compute2DCoords(mol)
        inchi_str = inchi_key = ""
        try:
            inchi_str = inchi.MolToInchi(mol)
            inchi_key = inchi.InchiToInchiKey(inchi_str)
        except Exception:
            pass
        return {
            "smiles": smiles or Chem.MolToSmiles(mol),
            "canonical": Chem.MolToSmiles(mol),
            "inchi": inchi_str,
            "inchikey": inchi_key,
            "formula": Chem.rdMolDescriptors.CalcMolFormula(mol),
            "mw": round(Descriptors.MolWt(mol), 2),
            "molblock": Chem.MolToMolBlock(mol),
        }

    def _validate(self, input: dict) -> dict:
        """SketChem-style live structure check: valence/sanitization errors, implicit H, formula, stereo."""
        smiles = str(input.get("smiles", "")).strip()
        if not smiles:
            return {"error": "smiles required"}
        from rdkit import Chem
        from rdkit.Chem import rdMolDescriptors

        mol = Chem.MolFromSmiles(smiles, sanitize=False)
        if mol is None:
            return {"valid": False, "errors": ["Cannot parse SMILES"]}
        mol.UpdatePropertyCache(strict=False)  # populate implicit valence even when sanitization will fail
        errors = []
        try:
            Chem.SanitizeMol(mol)
        except Exception as e:
            errors.append(f"Valence/sanitization: {e}")
        try:
            Chem.AssignStereochemistry(mol)
        except Exception:
            pass

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "num_atoms": mol.GetNumAtoms(),
            "num_bonds": mol.GetNumBonds(),
            "implicit_h": sum(a.GetNumImplicitHs() for a in mol.GetAtoms()),
            "formula": rdMolDescriptors.CalcMolFormula(mol),
            "stereocenters": rdMolDescriptors.CalcNumAtomStereoCenters(mol),
            "num_unspecified_stereo": rdMolDescriptors.CalcNumUnspecifiedAtomStereoCenters(mol),
            "charge": Chem.GetFormalCharge(mol),
        }

    def _save_to_kb(self, input: dict) -> dict:
        smiles = str(input.get("smiles", "")).strip()
        name = str(input.get("name", "")).strip() or smiles[:30]
        if not smiles:
            return {"error": "smiles required"}
        from rdkit import Chem
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return {"error": "Invalid SMILES"}
        try:
            svg = _depict_svg(smiles, 400)
        except Exception:
            svg = ""
        content = (f"# {name}\n\nSMILES: `{smiles}`\n\n"
                   f"Formula: {Chem.rdMolDescriptors.CalcMolFormula(mol)}\n\n"
                   f"MW: {Chem.Descriptors.MolWt(mol):.2f}\n\n{svg}\n")
        try:
            from modules.knowledge.auto_store import auto_store
            auto_store("chem_canvas", f"Structure: {name}", content,
                       source="Structure Draw", tags=["structure", "drawing"], category="drug_design")
        except Exception as e:
            log.warning("KB store failed: %s", e)
            return {"error": f"KB store failed: {e}"}
        return {"ok": True, "stored": name}
