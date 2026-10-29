import httpx
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
from harvesters.base import BaseHarvester, ScrapedJob

# Popular tech companies with active public Greenhouse job boards
DEFAULT_GREENHOUSE_COMPANIES = [
    "gitlab", "supabase", "vercel", "cloudflare", "datadog", 
    "retool", "brex", "ramp", "figma", "zapier", 
    "stripe", "discord", "airtable", "dbtlabs", "hashicorp"
]

class GreenhouseHarvester(BaseHarvester):
    """
    Harvests software engineering jobs from public Greenhouse boards.
    Endpoint: https://boards-api.greenhouse.io/v1/boards/{company}/jobs?content=true
    """

    def __init__(self, target_companies: Optional[List[str]] = None):
        self.companies = target_companies or DEFAULT_GREENHOUSE_COMPANIES

    def _clean_html(self, html_content: str) -> str:
        """Strip HTML tags to extract clean text."""
        if not html_content:
            return ""
        soup = BeautifulSoup(html_content, "html.parser")
        return soup.get_text(separator="\n").strip()

    def harvest_company(self, company_slug: str, search_terms: List[str], remote_only: bool = True) -> List[ScrapedJob]:
        """Fetch jobs for a specific company board."""
        url = f"https://boards-api.greenhouse.io/v1/boards/{company_slug}/jobs?content=true"
        jobs: List[ScrapedJob] = []
        
        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.get(url)
                if resp.status_code != 200:
                    return jobs
                
                data = resp.json()
                raw_jobs = data.get("jobs", [])
                
                for item in raw_jobs:
                    title = item.get("title", "")
                    location_name = (item.get("location") or {}).get("name", "")
                    
                    # Filter for software engineering roles
                    is_engineering = any(term.lower() in title.lower() for term in search_terms)
                    if not is_engineering:
                        continue
                    
                    # Filter for remote
                    is_remote = "remote" in location_name.lower() or "anywhere" in location_name.lower() or "distributed" in location_name.lower()
                    if remote_only and not is_remote:
                        continue
                    
                    clean_description = self._clean_html(item.get("content", ""))
                    
                    jobs.append(ScrapedJob(
                        title=title,
                        company=company_slug.capitalize(),
                        location=location_name or "Remote",
                        is_remote=is_remote,
                        job_url=item.get("absolute_url", ""),
                        source="greenhouse",
                        ats_type="greenhouse",
                        description=clean_description
                    ))
        except Exception as e:
            # Continue on individual company failure without crashing
            pass

        return jobs

    def harvest(self, search_term: str = "Software Engineer", remote_only: bool = True, limit: int = 50) -> List[ScrapedJob]:
        """Harvest across all configured Greenhouse companies."""
        search_terms = [search_term, "engineer", "developer"]
        all_jobs: List[ScrapedJob] = []

        for company in self.companies:
            if len(all_jobs) >= limit:
                break
            found = self.harvest_company(company, search_terms=search_terms, remote_only=remote_only)
            all_jobs.extend(found)

        return all_jobs[:limit]
