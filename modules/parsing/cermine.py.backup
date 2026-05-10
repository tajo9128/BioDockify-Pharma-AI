"""
BioDockify Parsing Module: CERMINE Integration
Legacy-grade bibliography extraction and validation using a local CERMINE JAR.
Critical for checking reference list integrity.
"""

import subprocess
import logging
from pathlib import Path
from typing import List, Dict, Optional
import xml.etree.ElementTree as ET
import shutil

logger = logging.getLogger(__name__)

class CermineWrapper:
    """
    Wraps the CERMINE Java Content Extractor.
    Requires 'cermine-impl-1.13-jar-with-dependencies.jar' in the lib/ folder.
    """
    
    def __init__(self, lib_dir: Path):
        self.jar_path = lib_dir / "cermine-impl-1.13-jar-with-dependencies.jar"
        # Check if java is available
        self.java_available = shutil.which("java") is not None
        
    def extract_metadata(self, pdf_path: Path) -> Optional[Dict]:
        """
        Runs CERMINE on a PDF to extract structured metadata (NLM JATS XML format).
        Returns parsed dictionary of title, authors, and references.
        """
        if not self.java_available:
            logger.warning("Java runtime not found. Skipping CERMINE.")
            return None
            
        if not self.jar_path.exists():
            logger.warning(f"CERMINE JAR not found at {self.jar_path}")
            return None
            
        try:
            # CERMINE writes output to the same directory as input
            # Command: java -cp cermine.jar pl.edu.icm.cermine.ContentExtractor -path input.pdf
            cmd = [
                "java", "-cp", str(self.jar_path),
                "pl.edu.icm.cermine.ContentExtractor",
                "-path", str(pdf_path)
            ]
            
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120)
            
            # Output is input.cermine.xml
            xml_path = pdf_path.with_suffix(".cermine.xml")
            
            if xml_path.exists():
                data = self._parse_cermine_xml(xml_path)
                return data
            else:
                return None
                
        except Exception as e:
            logger.error(f"CERMINE extraction failed for {pdf_path}: {str(e)}")
            return None
            
    def _parse_cermine_xml(self, xml_path: Path) -> Dict:
        """
        Parses the NLM JATS XML output from CERMINE.
        """
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
            
            # Extract references
            refs = []
            for ref in root.findall(".//ref"):
                citation = "".join(ref.itertext()).strip()
                refs.append(citation)
                
            return {
                "source": "CERMINE",
                "references": refs,
                "reference_count": len(refs)
            }
        except Exception as e:
            logger.error(f"XML parsing failed: {e}")
            return {}
