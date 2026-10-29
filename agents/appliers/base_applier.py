from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from pydantic import BaseModel
from config.settings import CandidateProfile
from agents.answer_agent import AnswerAgent

class ApplicationResult(BaseModel):
    success: bool
    status: str # "SUBMITTED", "PREVIEW_READY", "FAILED"
    screenshot_path: Optional[str] = None
    error_message: Optional[str] = None
    details: Optional[str] = None

class BaseApplier(ABC):
    """Abstract interface for ATS form appliers."""

    def __init__(self, profile: CandidateProfile):
        self.profile = profile
        self.answer_agent = AnswerAgent(profile)

    @abstractmethod
    def apply(self, job_data: Dict[str, Any], dry_run: bool = True) -> ApplicationResult:
        """
        Apply to a job.
        If dry_run is True, fill the form and capture a screenshot without clicking final submit.
        """
        pass
