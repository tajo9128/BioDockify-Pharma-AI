"""
PDF Processor Module
--------------------
Tools for parsing text and images from scientific PDF documents.
"""

from .parser import parse_pdf_text, extract_images, get_pdf_info, PDFParserError

__all__ = ['parse_pdf_text', 'extract_images', 'get_pdf_info', 'PDFParserError']
