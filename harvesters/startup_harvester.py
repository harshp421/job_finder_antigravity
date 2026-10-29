import httpx
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
from harvesters.base import BaseHarvester, ScrapedJob

# Curated Intelligence Database of Funded Tech Startups in Dubai, Singapore, India & Global Hubs
STARTUP_REGISTRY: Dict[str, Dict[str, Any]] = {
    # --- Dubai & UAE Startups ---
    "careem": {
        "name": "Careem",
        "board_type": "greenhouse",
        "url_slug": "careem",
        "region": "Dubai, UAE",
        "funding": "$500M+ (Uber Subsidiary / e& investment) | MENA Super-App",
        "summary": "Leading multi-service platform in the Middle East offering mobility, fintech (Careem Pay), food delivery, and digital services.",
        "remote_friendly_india": True
    },
    "tamara": {
        "name": "Tamara",
        "board_type": "greenhouse",
        "url_slug": "tamara",
        "region": "Dubai, UAE & Riyadh",
        "funding": "Series C ($340M) | $1B Unicorn | Sanabil, Checkout.com, Goldman Sachs debt",
        "summary": "First fintech unicorn in the Gulf region, providing consumer payment and BNPL shopping infrastructure.",
        "remote_friendly_india": True
    },
    "rain": {
        "name": "Rain",
        "board_type": "ashby",
        "url_slug": "rain",
        "region": "Dubai & Abu Dhabi, UAE",
        "funding": "Series B ($110M) | Paradigm, Kleiner Perkins, Coinbase Ventures",
        "summary": "Regulated crypto and digital asset exchange platform operating under Abu Dhabi Global Market (ADGM) & Central Bank regulation.",
        "remote_friendly_india": True
    },

    # --- Singapore Startups ---
    "ninjavan": {
        "name": "Ninja Van",
        "board_type": "lever",
        "url_slug": "ninjavan",
        "region": "Singapore (Southeast Asia)",
        "funding": "Series E ($578M) | $1B+ Unicorn | Geopost/DPDgroup, B Capital Group, Monk's Hill",
        "summary": "Tech-enabled express logistics platform powering e-commerce supply chains across 6 Southeast Asian countries.",
        "remote_friendly_india": True
    },
    "nansen": {
        "name": "Nansen",
        "board_type": "greenhouse",
        "url_slug": "nansen",
        "region": "Singapore (Remote Worldwide)",
        "funding": "Series B ($75M) | Accel, a16z, Tiger Global, Mechanism Capital",
        "summary": "Blockchain and on-chain analytics platform combining on-chain data with millions of wallet labels and AI signals.",
        "remote_friendly_india": True
    },

    # --- India & Global Remote Funded Startups ---
    "signoz": {
        "name": "SigNoz",
        "board_type": "ashby",
        "url_slug": "signoz",
        "region": "India / Remote Worldwide",
        "funding": "YC S21 | $6.5M Series A | Uncorrelated Ventures, Accel scout",
        "summary": "Open-source observability and APM platform built on OpenTelemetry and ClickHouse. Alternative to Datadog.",
        "remote_friendly_india": True
    },
    "atlan": {
        "name": "Atlan",
        "board_type": "ashby",
        "url_slug": "atlan",
        "region": "India / Remote Worldwide",
        "funding": "Series C ($105M) | Insight Partners, Salesforce Ventures, Peak XV",
        "summary": "Pioneering Active Metadata platform for modern data teams and enterprise AI governance.",
        "remote_friendly_india": True
    },
    "linear": {
        "name": "Linear",
        "board_type": "ashby",
        "url_slug": "linear",
        "region": "Remote Worldwide",
        "funding": "Series B ($35M) | Accel, Sequoia Capital",
        "summary": "The standard issue tracking and product planning tool for high-performing software teams.",
        "remote_friendly_india": True
    },
    "supabase": {
        "name": "Supabase",
        "board_type": "greenhouse",
        "url_slug": "supabase",
        "region": "Remote Worldwide",
        "funding": "YC W20 | Series B ($116M) | Coatue, Felicis Ventures",
        "summary": "Open-source Firebase alternative built around PostgreSQL, real-time engines, and AI vectors.",
        "remote_friendly_india": True
    },
    "hasura": {
        "name": "Hasura",
        "board_type": "greenhouse",
        "url_slug": "hasura",
        "region": "India / Remote Worldwide",
        "funding": "Series C ($100M) | Greenoaks, Lightspeed, Nexus Venture Partners",
        "summary": "Instant GraphQL and REST API engine connecting directly to enterprise databases.",
        "remote_friendly_india": True
    },
    "postman": {
        "name": "Postman",
        "board_type": "greenhouse",
        "url_slug": "postman",
        "region": "India / Remote Worldwide",
        "funding": "Series D ($225M) | Insight Partners, Nexus, CRV ($5.6B Valuation)",
        "summary": "Industry-standard API development, testing, and collaboration platform used by 30M+ developers.",
        "remote_friendly_india": True
    },
    "vercel": {
        "name": "Vercel",
        "board_type": "greenhouse",
        "url_slug": "vercel",
        "region": "Remote Worldwide",
        "funding": "Series E ($250M) | Accel, CRV, GV ($3.25B Valuation)",
        "summary": "Frontend cloud platform and creator of Next.js, empowering developers to ship fast web applications.",
        "remote_friendly_india": True
    },
    "gitlab": {
        "name": "GitLab",
        "board_type": "greenhouse",
        "url_slug": "gitlab",
        "region": "Remote Worldwide",
        "funding": "YC W15 | Public ($GTLB)",
        "summary": "Complete AI-powered DevSecOps platform built on an all-remote global workforce model.",
        "remote_friendly_india": True
    }
}

EXCLUDED_TITLES = [
    "director", "vp ", "vice president", "head of", "chief", "manager", 
    "intern", "internship", "fellow", "trainee", "legal", "recruiter", "sales", "account executive"
]

class StartupHarvester(BaseHarvester):
    """
    Harvests mid-level software engineering jobs from funded tech startups
    across Dubai (UAE), Singapore, India, and Global hubs.
    Enriches each job with startup funding stage, background summary, and regional tags.
    """

    def __init__(self, target_startups: Optional[List[str]] = None, region_filter: Optional[str] = None):
        self.region_filter = region_filter
        if target_startups:
            self.startups = target_startups
        elif region_filter:
            reg_lower = region_filter.lower()
            self.startups = [k for k, v in STARTUP_REGISTRY.items() if reg_lower in v["region"].lower()]
        else:
            self.startups = list(STARTUP_REGISTRY.keys())

    def _clean_html(self, html_content: str) -> str:
        if not html_content:
            return ""
        soup = BeautifulSoup(html_content, "html.parser")
        return soup.get_text(separator="\n").strip()

    def _is_mid_level_software_role(self, title: str, search_terms: List[str]) -> bool:
        t_lower = title.lower()
        # Exclude management/executive or internships
        if any(bad in t_lower for bad in EXCLUDED_TITLES):
            return False
        # Must match software engineering keywords
        return any(term.lower() in t_lower for term in search_terms)

    def _harvest_ashby(self, meta: Dict[str, Any], search_terms: List[str], remote_only: bool = True) -> List[ScrapedJob]:
        slug = meta["url_slug"]
        url = f"https://api.ashbyhq.com/posting-api/job-board/{slug}"
        jobs: List[ScrapedJob] = []

        try:
            with httpx.Client(timeout=8.0) as client:
                resp = client.get(url)
                if resp.status_code != 200:
                    return jobs
                
                data = resp.json()
                for item in data.get("jobs", []):
                    title = item.get("title", "")
                    location = item.get("location", "")
                    is_remote = item.get("isRemote", True) or "remote" in location.lower() or "anywhere" in location.lower()
                    
                    if not self._is_mid_level_software_role(title, search_terms):
                        continue
                    
                    if remote_only and not is_remote:
                        continue

                    desc = self._clean_html(item.get("descriptionHtml", ""))
                    loc_display = location or meta["region"]

                    jobs.append(ScrapedJob(
                        title=title,
                        company=meta["name"],
                        location=loc_display,
                        is_remote=is_remote,
                        job_url=item.get("jobUrl", ""),
                        source=f"ashby_{meta['region'].split(',')[0].lower()}",
                        ats_type="ashby",
                        description=desc
                    ))
        except Exception:
            pass

        return jobs

    def _harvest_greenhouse(self, meta: Dict[str, Any], search_terms: List[str], remote_only: bool = True) -> List[ScrapedJob]:
        slug = meta["url_slug"]
        url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true"
        jobs: List[ScrapedJob] = []

        try:
            with httpx.Client(timeout=8.0) as client:
                resp = client.get(url)
                if resp.status_code != 200:
                    return jobs

                data = resp.json()
                for item in data.get("jobs", []):
                    title = item.get("title", "")
                    loc = (item.get("location") or {}).get("name", "")
                    loc_lower = loc.lower()
                    is_remote = "remote" in loc_lower or "anywhere" in loc_lower or "distributed" in loc_lower

                    if not self._is_mid_level_software_role(title, search_terms):
                        continue

                    if remote_only and not is_remote:
                        continue

                    desc = self._clean_html(item.get("content", ""))
                    loc_display = loc or meta["region"]

                    jobs.append(ScrapedJob(
                        title=title,
                        company=meta["name"],
                        location=loc_display,
                        is_remote=is_remote,
                        job_url=item.get("absolute_url", ""),
                        source=f"greenhouse_{meta['region'].split(',')[0].lower()}",
                        ats_type="greenhouse",
                        description=desc
                    ))
        except Exception:
            pass

        return jobs

    def _harvest_lever(self, meta: Dict[str, Any], search_terms: List[str], remote_only: bool = True) -> List[ScrapedJob]:
        slug = meta["url_slug"]
        url = f"https://api.lever.co/v0/postings/{slug}?mode=json"
        jobs: List[ScrapedJob] = []

        try:
            with httpx.Client(timeout=8.0) as client:
                resp = client.get(url)
                if resp.status_code != 200:
                    return jobs

                data = resp.json()
                for item in data:
                    title = item.get("text", "")
                    categories = item.get("categories", {})
                    location = categories.get("location", "")
                    workplace_type = item.get("workplaceType", "")
                    is_remote = "remote" in location.lower() or "remote" in workplace_type.lower() or "anywhere" in location.lower()

                    if not self._is_mid_level_software_role(title, search_terms):
                        continue

                    if remote_only and not is_remote:
                        continue

                    desc = self._clean_html(item.get("descriptionPlain", "") or item.get("description", ""))
                    loc_display = location or meta["region"]

                    jobs.append(ScrapedJob(
                        title=title,
                        company=meta["name"],
                        location=loc_display,
                        is_remote=is_remote,
                        job_url=item.get("hostedUrl", ""),
                        source=f"lever_{meta['region'].split(',')[0].lower()}",
                        ats_type="lever",
                        description=desc
                    ))
        except Exception:
            pass

        return jobs

    def harvest(
        self, 
        search_term: str = "Software Engineer", 
        remote_only: bool = False, 
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Harvest matching mid-level roles from Dubai, Singapore, and Global startups.
        """
        search_terms = [search_term, "engineer", "developer", "full stack", "frontend", "backend", "software"]
        results: List[Dict[str, Any]] = []

        for key in self.startups:
            if len(results) >= limit:
                break

            meta = STARTUP_REGISTRY[key]
            board_type = meta["board_type"]
            found: List[ScrapedJob] = []

            if board_type == "ashby":
                found = self._harvest_ashby(meta, search_terms, remote_only)
            elif board_type == "greenhouse":
                found = self._harvest_greenhouse(meta, search_terms, remote_only)
            elif board_type == "lever":
                found = self._harvest_lever(meta, search_terms, remote_only)

            for job in found:
                job_dict = job.model_dump()
                job_dict["company_summary"] = f"[{meta['region']}] {meta['summary']}"
                job_dict["funding_info"] = f"[{meta['region']}] {meta['funding']}"
                results.append(job_dict)

        return results[:limit]
