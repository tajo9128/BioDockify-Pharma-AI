"""
PDF Processor Module - BioDockify Pharma Research AI
Handles parsing of PDF documents for text and image extraction.
Multi-backend support: pypdf (fast/default) and pdfminer.six (layout-aware).
"""

import os
import io
import logging
from typing import List, Dict, Optional, Union
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("BioDockify.PDF")

# Try imports
try:
    import pypdf
    PYPDF_AVAILABLE = True
except ImportError:
    PYPDF_AVAILABLE = False

try:
    from pdfminer.high_level import extract_text as pdfminer_extract
    PDFMINER_AVAILABLE = True
except ImportError:
    PDFMINER_AVAILABLE = False

class PDFParserError(Exception):
    """Custom exception for PDF parsing errors."""
    pass

def parse_pdf_text(filepath: str, use_pdfminer: bool = False) -> str:
    """
    Extract full text from a PDF file.
    
    Args:
        filepath: Path to the PDF file.
        use_pdfminer: If True, uses pdfminer.six (slower but better layout analysis).
                      Defaults to False (pypdf).
                      
    Returns:
        Extracted text as a single string.
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"PDF file not found: {filepath}")

    if use_pdfminer and PDFMINER_AVAILABLE:
        try:
            logger.info(f"Extracting text (pdfminer): {filepath}")
            return pdfminer_extract(filepath)
        except Exception as e:
            logger.error(f"pdfminer extraction failed: {e}")
            # Fallback to pypdf if available
            if PYPDF_AVAILABLE:
                logger.info("Falling back to pypdf...")
                return _parse_pypdf(filepath)
            raise PDFParserError(f"Extraction failed: {e}")
            
    if PYPDF_AVAILABLE:
        return _parse_pypdf(filepath)
    else:
        raise ImportError("No PDF libraries found. Install pypdf or pdfminer.six.")

def _parse_pypdf(filepath: str) -> str:
    """Internal helper for pypdf extraction."""
    try:
        logger.info(f"Extracting text (pypdf): {filepath}")
        text_content = []
        with open(filepath, 'rb') as f:
            reader = pypdf.PdfReader(f)
            for page in reader.pages:
                text_content.append(page.extract_text())
        return "\n".join(text_content)
    except Exception as e:
        logger.error(f"pypdf extraction failed: {e}")
        raise PDFParserError(f"pypdf failed: {e}")

def extract_images(filepath: str, output_dir: str, prefix: str = "img", format: str = "png") -> List[str]:
    """
    Extract embedded images from a PDF (useful for DECIMER structure recognition).
    
    Args:
        filepath: Source PDF.
        output_dir: Folder to save images.
        prefix: Filename prefix.
        format: Image format (png, jpg).
        
    Returns:
        List of saved image file paths.
    """
    if not PYPDF_AVAILABLE:
        logger.warning("pypdf not installed. Image extraction disabled.")
        return []

    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    saved_images = []
    
    try:
        with open(filepath, 'rb') as f:
            reader = pypdf.PdfReader(f)
            
            for page_idx, page in enumerate(reader.pages):
                for image_file_object in page.images:
                    # Construct output path
                    image_name = f"{prefix}_p{page_idx+1}_{image_file_object.name}"
                    output_path = os.path.join(output_dir, image_name)
                    
                    with open(output_path, "wb") as fp:
                        fp.write(image_file_object.data)
                    
                    saved_images.append(output_path)
                    
        logger.info(f"Extracted {len(saved_images)} images to {output_dir}")
        return saved_images

    except Exception as e:
        logger.error(f"Image extraction failed: {e}")
        return []

def get_pdf_info(filepath: str) -> Dict[str, Union[str, int]]:
    """Get PDF metadata."""
    if not PYPDF_AVAILABLE:
        return {}
    
    try:
        with open(filepath, 'rb') as f:
            reader = pypdf.PdfReader(f)
            info = reader.metadata
            return {
                "pages": len(reader.pages),
                "author": info.author if info else "Unknown",
                "title": info.title if info else "Unknown"
            }
    except Exception:
        return {}

if __name__ == "__main__":
    # Test
    print("PDF Processor Test")
    print(f"pypdf: {'OK' if PYPDF_AVAILABLE else 'MISSING'}")
    print(f"pdfminer: {'OK' if PDFMINER_AVAILABLE else 'MISSING'}")
