from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class ScrapedJob(BaseModel):
    title: str
    company: str
    location: Optional[str] = "Remote"
    is_remote: bool = True
    job_url: str
    source: str # linkedin, indeed, greenhouse, lever, etc.
    ats_type: Optional[str] = None
    salary_raw: Optional[str] = None
    min_salary: Optional[float] = None
    max_salary: Optional[float] = None
    description: Optional[str] = ""

class BaseHarvester(ABC):
    """Abstract Base Class for all Job Harvesters."""
    
    @abstractmethod
    def harvest(self, search_term: str, remote_only: bool = True, limit: int = 20) -> List[ScrapedJob]:
        """Harvest job postings matching the criteria."""
        pass
