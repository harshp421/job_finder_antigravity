from pathlib import Path
from typing import List, Optional, Dict, Any
import yaml
from pydantic import BaseModel, Field, ConfigDict

class PersonalInfo(BaseModel):
    full_name: str
    first_name: str
    last_name: str
    email: str
    phone: str
    location: str
    address: Optional[str] = ""
    linkedin_url: Optional[str] = ""
    github_url: Optional[str] = ""
    portfolio_url: Optional[str] = ""
    resume_path: Optional[str] = ""

class JobSearchPreferences(BaseModel):
    target_roles: List[str] = Field(default_factory=lambda: ["Software Engineer"])
    remote_only: bool = True
    preferred_locations: List[str] = Field(default_factory=lambda: ["Remote"])
    min_salary_usd: Optional[int] = 100000
    minimum_match_score: int = 70
    daily_application_limit: int = 25

class WorkAuthorization(BaseModel):
    authorized_to_work_in_target_country: bool = True
    requires_visa_sponsorship: bool = False
    citizenship: Optional[str] = "India"

class TechStack(BaseModel):
    primary_languages: List[str] = Field(default_factory=list)
    frameworks_and_libraries: List[str] = Field(default_factory=list)
    databases_and_cloud: List[str] = Field(default_factory=list)
    systems_and_architecture: List[str] = Field(default_factory=list)
    years_of_experience: int = 3

class ExperienceItem(BaseModel):
    role: str
    company: str
    duration: str
    highlights: List[str] = Field(default_factory=list)

class ProjectItem(BaseModel):
    name: str
    url: Optional[str] = ""
    stack: Optional[str] = ""
    highlights: List[str] = Field(default_factory=list)

class EducationInfo(BaseModel):
    degree: str
    institution: str
    graduation_year: str

class StandardQuestionAnswers(BaseModel):
    notice_period_weeks: int = 2
    available_start_date: str = "Immediately"
    preferred_work_type: str = "Full-time Remote"
    salary_expectation_usd: str = "80,000 - 120,000"
    why_join_us_template: str = ""
    proud_project_template: str = ""

class CandidateProfile(BaseModel):
    model_config = ConfigDict(extra="ignore")

    personal_info: PersonalInfo
    job_search_preferences: JobSearchPreferences
    work_authorization: WorkAuthorization
    tech_stack: TechStack
    experience_highlights: List[ExperienceItem] = Field(default_factory=list)
    projects: List[ProjectItem] = Field(default_factory=list)
    education: EducationInfo
    standard_question_answers: StandardQuestionAnswers

def load_profile(path: Optional[str] = None) -> CandidateProfile:
    """Load and validate candidate profile from YAML."""
    if path is None:
        path = str(Path(__file__).parent / "profile.yaml")
    
    with open(path, "r", encoding="utf-8") as f:
        raw_data = yaml.safe_load(f)
    
    return CandidateProfile(**raw_data)
