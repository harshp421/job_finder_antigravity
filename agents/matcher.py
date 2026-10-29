import os
import re
from typing import Dict, Any, Tuple
from config.settings import CandidateProfile

class MatcherAgent:
    """
    Evaluates job postings against the candidate profile.
    Supports both local rule-based semantic analysis and LLM-powered deep evaluation.
    """

    def __init__(self, profile: CandidateProfile):
        self.profile = profile
        self.gemini_key = os.getenv("GEMINI_API_KEY")

    def _local_evaluate(self, title: str, description: str, is_remote: bool, location: str) -> Tuple[int, str]:
        """
        Robust local evaluation based on candidate profile attributes:
        1. Role title alignment (Seniority + Domain)
        2. Remote compatibility
        3. Tech stack keyword overlap
        4. Experience level heuristics
        """
        score = 0
        reasons = []

        title_lower = title.lower()
        desc_lower = description.lower()

        # 1. Target Role Matching (max 25 pts)
        target_roles = [r.lower() for r in self.profile.job_search_preferences.target_roles]
        matched_roles = [r for r in target_roles if r in title_lower]
        if matched_roles:
            score += 25
            reasons.append(f"Target role match ({matched_roles[0]})")
        elif "engineer" in title_lower or "developer" in title_lower:
            score += 15
            reasons.append("General engineering title match")
        else:
            reasons.append("Non-standard engineering title")

        # 2. Location & Remote Compatibility (max 20 pts)
        preferred = [p.lower() for p in self.profile.job_search_preferences.preferred_locations]
        loc_lower = location.lower()
        
        is_pref_location = any(p in loc_lower or p in desc_lower for p in preferred if p != "remote")
        is_remote_confirmed = is_remote or "remote" in loc_lower or "remote" in desc_lower or "anywhere" in loc_lower or "distributed" in loc_lower
        
        if is_remote_confirmed:
            score += 20
            reasons.append("Remote position confirmed")
        elif is_pref_location:
            score += 20
            reasons.append(f"Target hub match ({location})")
        elif self.profile.job_search_preferences.remote_only:
            score -= 25
            reasons.append("Not remote and outside target hubs")
        else:
            score += 15
            reasons.append("Location accepted")

        # 3. Tech Stack Overlap (max 40 pts)
        all_skills = (
            self.profile.tech_stack.primary_languages +
            self.profile.tech_stack.frameworks_and_libraries +
            self.profile.tech_stack.databases_and_cloud +
            self.profile.tech_stack.systems_and_architecture
        )
        
        matched_skills = []
        for skill in all_skills:
            # Word boundary regex to avoid partial substring false positives (e.g. 'go' in 'good')
            pattern = rf"\b{re.escape(skill.lower())}\b"
            if re.search(pattern, desc_lower):
                matched_skills.append(skill)

        # Scale skills (up to 40 pts based on number of matches)
        skill_score = min(40, len(matched_skills) * 8)
        score += skill_score
        if matched_skills:
            reasons.append(f"Matched skills ({len(matched_skills)}): {', '.join(matched_skills[:5])}")

        # 4. Seniority / Experience fit (max 15 pts)
        user_yoe = self.profile.tech_stack.years_of_experience
        if "lead" in title_lower or "principal" in title_lower or "director" in title_lower:
            if user_yoe < 6:
                score -= 15
                reasons.append("Role is Principal/Lead level (high seniority requirement)")
        elif "senior" in title_lower:
            if user_yoe >= 3:
                score += 15
                reasons.append("Seniority aligns with experience")
            else:
                score += 5
        else:
            score += 15
            reasons.append("Mid-level / standard seniority match")

        final_score = max(0, min(100, score))
        rationale = " | ".join(reasons)
        return final_score, rationale

    def evaluate_job(self, job_data: Dict[str, Any]) -> Tuple[int, str]:
        """
        Evaluates a job and returns (score: int, rationale: str).
        """
        title = job_data.get("title", "")
        description = job_data.get("description", "")
        is_remote = bool(job_data.get("is_remote", True))
        location = job_data.get("location", "")

        return self._local_evaluate(title, description, is_remote, location)
