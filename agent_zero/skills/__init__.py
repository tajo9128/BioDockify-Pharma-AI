"""
Agent Zero Skills Package
Browser automation, email messaging, and research automation.
"""

from .browser_scraper import BrowserScraper, get_browser_scraper
from .email_messenger import EmailMessenger, get_email_messenger
from .latte_review import LatteReviewSkill, get_latte_review
from .achademio import AchademioSkill, get_achademio
from .scholar_copilot import ScholarCopilotSkill, get_scholar_copilot
from .deep_drive import DeepDriveSkill, get_deep_drive
from .reviewer_agent import ReviewerAgentSkill, get_reviewer_agent
from .self_repair import SelfRepairSkill

__all__ = [
    "BrowserScraper",
    "get_browser_scraper",
    "EmailMessenger", 
    "get_email_messenger",
    "LatteReviewSkill",
    "get_latte_review",
    "AchademioSkill",
    "get_achademio",
    "ScholarCopilotSkill",
    "get_scholar_copilot",
    "DeepDriveSkill",
    "get_deep_drive",
    "ReviewerAgentSkill",
    "get_reviewer_agent",
    "SelfRepairSkill"
]
