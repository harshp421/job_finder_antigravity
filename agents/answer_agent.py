import re
from typing import Optional
from config.settings import CandidateProfile

class AnswerAgent:
    """
    Intelligently answers application questions based on candidate profile data.
    """

    def __init__(self, profile: CandidateProfile):
        self.profile = profile

    def answer_question(self, question: str) -> str:
        """
        Match question intent and return an appropriate answer.
        """
        q = question.lower().strip()

        # 1. Sponsorship / Authorization
        if "sponsorship" in q or "require sponsorship" in q or "visa" in q:
            return "No" if not self.profile.work_authorization.requires_visa_sponsorship else "Yes"

        if "authorized" in q or "legally authorized" in q or "eligible to work" in q:
            return "Yes" if self.profile.work_authorization.authorized_to_work_in_target_country else "No"

        # 2. Compensation
        if "salary" in q or "compensation" in q or "desired pay" in q:
            return self.profile.standard_question_answers.salary_expectation_usd

        # 3. Notice Period / Availability
        if "notice period" in q or "when can you start" in q or "start date" in q:
            return self.profile.standard_question_answers.available_start_date

        # 4. Years of experience (e.g. "How many years of experience with Python?")
        yoe_match = re.search(r"years of experience (?:with|in)?\s*([a-zA-Z0-9#+.]+)", q)
        if yoe_match:
            tech = yoe_match.group(1).lower()
            all_tech = [t.lower() for t in (
                self.profile.tech_stack.primary_languages +
                self.profile.tech_stack.frameworks_and_libraries
            )]
            if any(tech in t for t in all_tech):
                return str(self.profile.tech_stack.years_of_experience)
            return "2" # default familiarity

        # 5. URLs
        if "linkedin" in q:
            return self.profile.personal_info.linkedin_url or ""
        if "github" in q:
            return self.profile.personal_info.github_url or ""
        if "portfolio" in q or "website" in q:
            return self.profile.personal_info.portfolio_url or ""

        # 6. Why us / Personal Statement
        if "why do you want" in q or "why us" in q or "why join" in q or "interest" in q:
            return self.profile.standard_question_answers.why_join_us_template

        # 7. Proud project / achievement
        if "proud" in q or "accomplishment" in q or "project you worked on" in q:
            return self.profile.standard_question_answers.proud_project_template

        # Fallback
        return "Not specified"
