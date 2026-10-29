import httpx
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
from harvesters.base import BaseHarvester, ScrapedJob

# Tech companies known to use Lever for hiring
DEFAULT_LEVER_COMPANIES = [
    "netflix", "atlassian", "palantir", "auth0", "ironclad", 
    "benchling", "postman", "coupa", "affirm"
]

class LeverHarvester(BaseHarvester):
    """
    Harvests software engineering jobs from public Lever boards.
    Endpoint: https://api.lever.co/v0/postings/{company}?mode=json
    """

    def __init__(self, target_companies: Optional[List[str]] = None):
        self.companies = target_companies or DEFAULT_LEVER_COMPANIES

    def _clean_html(self, html_content: str) -> str:
        if not html_content:
            return ""
        soup = BeautifulSoup(html_content, "html.parser")
        return soup.get_text(separator="\n").strip()

    def harvest_company(self, company_slug: str, search_terms: List[str], remote_only: bool = True) -> List[ScrapedJob]:
        url = f"https://api.lever.co/v0/postings/{company_slug}?mode=json"
        jobs: List[ScrapedJob] = []

        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.get(url)
                if resp.status_code != 200:
                    return jobs

                raw_jobs = resp.json()
                for item in raw_jobs:
                    title = item.get("text", "")
                    categories = item.get("categories", {})
                    location_name = categories.get("location", "")
                    workplace_type = item.get("workplaceType", "")

                    is_engineering = any(term.lower() in title.lower() for term in search_terms)
                    if not is_engineering:
                        continue

                    is_remote = (
                        "remote" in location_name.lower() or 
                        "remote" in workplace_type.lower() or
                        "anywhere" in location_name.lower()
                    )
                    if remote_only and not is_remote:
                        continue

                    desc = self._clean_html(item.get("descriptionPlain", "") or item.get("description", ""))

                    jobs.append(ScrapedJob(
                        title=title,
                        company=company_slug.capitalize(),
                        location=location_name or "Remote",
                        is_remote=is_remote,
                        job_url=item.get("hostedUrl", ""),
                        source="lever",
                        ats_type="lever",
                        description=desc
                    ))
        except Exception:
            pass

        return jobs

    def harvest(self, search_term: str = "Software Engineer", remote_only: bool = True, limit: int = 50) -> List[ScrapedJob]:
        search_terms = [search_term, "engineer", "developer"]
        all_jobs: List[ScrapedJob] = []

        for company in self.companies:
            if len(all_jobs) >= limit:
                break
            found = self.harvest_company(company, search_terms=search_terms, remote_only=remote_only)
            all_jobs.extend(found)

        return all_jobs[:limit]
