from typing import List, Optional
from harvesters.base import BaseHarvester, ScrapedJob

class JobSpyHarvester(BaseHarvester):
    """
    Harvests jobs from LinkedIn, Indeed, Glassdoor, and ZipRecruiter using JobSpy.
    """

    def __init__(self, sites: Optional[List[str]] = None):
        # Default sites to scrape
        self.sites = sites or ["linkedin", "indeed", "glassdoor"]

    def harvest(
        self, 
        search_term: str = "Software Engineer", 
        remote_only: bool = True, 
        limit: int = 25
    ) -> List[ScrapedJob]:
        try:
            from jobspy import scrape_jobs
        except ImportError:
            print("JobSpy is not yet installed or importable.")
            return []

        jobs: List[ScrapedJob] = []

        try:
            # JobSpy scrape_jobs call
            df = scrape_jobs(
                site_name=self.sites,
                search_term=search_term,
                location="United States" if remote_only else "",
                is_remote=remote_only,
                results_wanted=limit,
                hours_old=72, # Last 3 days
                country_indeed="USA"
            )

            if df is None or df.empty:
                return jobs

            for _, row in df.iterrows():
                # Detect ATS type from job_url if possible
                job_url = str(row.get("job_url", "") or "")
                ats_type = "direct"
                if "greenhouse.io" in job_url:
                    ats_type = "greenhouse"
                elif "lever.co" in job_url:
                    ats_type = "lever"
                elif "ashbyhq.com" in job_url:
                    ats_type = "ashby"
                elif "myworkdayjobs.com" in job_url:
                    ats_type = "workday"

                jobs.append(ScrapedJob(
                    title=str(row.get("title", "")),
                    company=str(row.get("company", "")),
                    location=str(row.get("location", "Remote")),
                    is_remote=bool(row.get("is_remote", True)),
                    job_url=job_url,
                    source=str(row.get("site", "jobspy")),
                    ats_type=ats_type,
                    min_salary=float(row.get("min_amount")) if row.get("min_amount") and not str(row.get("min_amount")).lower() == "nan" else None,
                    max_salary=float(row.get("max_amount")) if row.get("max_amount") and not str(row.get("max_amount")).lower() == "nan" else None,
                    description=str(row.get("description", ""))
                ))

        except Exception as e:
            print(f"Error during JobSpy harvesting: {e}")

        return jobs
