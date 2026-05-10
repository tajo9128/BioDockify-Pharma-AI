"""
BioDockify Lab Interface Module
Provides protocol and report generation capabilities
"""

from .sila_generator import LiquidHandlerSiLA, generate_sila_protocol
from .report_generator import ResearchReportGenerator, generate_report

__all__ = [
    'LiquidHandlerSiLA',
    'generate_sila_protocol',
    'ResearchReportGenerator',
    'generate_report',
]
