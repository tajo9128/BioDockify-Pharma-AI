"""
Slides Generation Module
Generates professional presentations from Knowledge Base content.
"""

from .slide_generator import SlideGenerator
from .slide_styles import SLIDE_STYLES, get_style_template

__all__ = ['SlideGenerator', 'SLIDE_STYLES', 'get_style_template']
