#!/usr/bin/env python3
"""
Antigravity Autonomous Job Search & Application Pipeline
Specialized for Funded Tech Startups across Dubai, Singapore, India & Global Hubs.
Focusing on Mid-Level Software Engineering Roles.
"""
import sys
import argparse
from typing import List, Dict, Any, Optional
from rich.console import Console

from config.settings import load_profile
from database.db import (
    init_db, 
    save_job, 
    get_unscored_jobs, 
    update_job_score, 
    get_jobs_ready_for_application, 
    log_application_attempt,
    get_statistics
)
from harvesters.greenhouse_harvester import GreenhouseHarvester
from harvesters.lever_harvester import LeverHarvester
from harvesters.jobspy_harvester import JobSpyHarvester
from harvesters.startup_harvester import StartupHarvester, STARTUP_REGISTRY
from agents.matcher import MatcherAgent
from agents.appliers.greenhouse_applier import GreenhouseApplier
from agents.appliers.lever_applier import LeverApplier
from tracker.crm import CRMTracker

console = Console()

def run_harvest(
    source: str = "all", 
    region: str = "all",
    search_term: str = "Software Engineer", 
    remote_only: bool = False, 
    limit: int = 40
):
    """
    Harvest mid-level software engineering roles from funded tech startups
    across Dubai, Singapore, India, and Global hubs.
    """
    console.print(f"[bold cyan]🔍 Starting Job Harvesting...[/bold cyan] (Region: '{region}', Term: '{search_term}')")
    all_found: List[Dict[str, Any]] = []

    # 1. Dubai & Middle East Startups & Portals
    if region in ("all", "dubai", "uae") or source == "dubai":
        console.print("[yellow]Scraping Dubai / UAE Tech Startups (Careem, Tamara, Rain)...[/yellow]")
        sh_dubai = StartupHarvester(region_filter="Dubai")
        d_jobs = sh_dubai.harvest(search_term=search_term, remote_only=remote_only, limit=limit)
        console.print(f"  -> Found {len(d_jobs)} mid-level roles at Dubai startups.")
        all_found.extend(d_jobs)

        try:
            from jobspy import scrape_jobs
            console.print("[yellow]Scraping Dubai LinkedIn for Mid-Level Software Engineers...[/yellow]")
            df_dubai = scrape_jobs(
                site_name=["linkedin"],
                search_term=search_term,
                location="Dubai",
                results_wanted=min(limit, 10)
            )
            if df_dubai is not None and not df_dubai.empty:
                for _, row in df_dubai.iterrows():
                    all_found.append({
                        "title": str(row.get("title", "")),
                        "company": str(row.get("company", "")),
                        "location": "Dubai, UAE",
                        "is_remote": bool(row.get("is_remote", False)),
                        "job_url": str(row.get("job_url", "")),
                        "source": "linkedin_dubai",
                        "ats_type": "direct",
                        "description": str(row.get("description", "")),
                        "funding_info": "[Dubai, UAE] Tech Company / Startup in Dubai",
                        "company_summary": f"Dubai-based tech hiring for {row.get('title')}"
                    })
                console.print(f"  -> Found {len(df_dubai)} jobs in Dubai via LinkedIn.")
        except Exception:
            pass

    # 2. Singapore Startups & Portals
    if region in ("all", "singapore", "sg") or source == "singapore":
        console.print("[yellow]Scraping Singapore Tech Startups (Ninja Van, Nansen)...[/yellow]")
        sh_sg = StartupHarvester(region_filter="Singapore")
        sg_jobs = sh_sg.harvest(search_term=search_term, remote_only=remote_only, limit=limit)
        console.print(f"  -> Found {len(sg_jobs)} mid-level roles at Singapore startups.")
        all_found.extend(sg_jobs)

        try:
            from jobspy import scrape_jobs
            console.print("[yellow]Scraping Singapore Glassdoor & LinkedIn...[/yellow]")
            df_sg = scrape_jobs(
                site_name=["glassdoor"],
                search_term=search_term,
                location="Singapore",
                country_indeed="Singapore",
                results_wanted=min(limit, 10)
            )
            if df_sg is not None and not df_sg.empty:
                for _, row in df_sg.iterrows():
                    all_found.append({
                        "title": str(row.get("title", "")),
                        "company": str(row.get("company", "")),
                        "location": "Singapore",
                        "is_remote": bool(row.get("is_remote", False)),
                        "job_url": str(row.get("job_url", "")),
                        "source": "glassdoor_singapore",
                        "ats_type": "direct",
                        "description": str(row.get("description", "")),
                        "funding_info": "[Singapore] Southeast Asia Tech Startup",
                        "company_summary": f"Singapore tech ecosystem hiring for {row.get('title')}"
                    })
                console.print(f"  -> Found {len(df_sg)} jobs in Singapore via Glassdoor.")
        except Exception:
            pass

    # 3. Funded Remote Tech Startups (India & Global)
    if region in ("all", "india", "global") or source in ("all", "startups"):
        console.print("[yellow]Scraping India & Global Funded Startups (SigNoz, Atlan, Linear, Supabase, Hasura, Vercel)...[/yellow]")
        sh_global = StartupHarvester()
        g_jobs = sh_global.harvest(search_term=search_term, remote_only=remote_only, limit=limit)
        console.print(f"  -> Found {len(g_jobs)} jobs at global / Indian funded startups.")
        all_found.extend(g_jobs)

    # Ingest into DB
    new_count = 0
    for job in all_found:
        if save_job(job):
            new_count += 1

    console.print(f"[bold green]✨ Harvesting Complete:[/bold green] Found {len(all_found)} jobs, {new_count} newly saved to database.\n")

def run_match(min_score: int = 70):
    """Run AI evaluation on all unscored jobs in database."""
    console.print("[bold cyan]🧠 Evaluating Unscored Jobs with Matcher Agent...[/bold cyan]")
    profile = load_profile()
    matcher = MatcherAgent(profile)
    unscored = get_unscored_jobs(limit=120)

    if not unscored:
        console.print("[dim]No unscored jobs found. All caught up![/dim]\n")
        return

    scored_count = 0
    queued_count = 0

    for job in unscored:
        score, rationale = matcher.evaluate_job(job)
        status = "QUEUED" if score >= min_score else "SKIPPED"
        update_job_score(job["id"], score, rationale, status)
        scored_count += 1
        if score >= min_score:
            queued_count += 1
            funding_tag = f"[{job.get('funding_info', 'Startup')[:24]}] " if job.get('funding_info') else ""
            console.print(f"  [bold green]✓ [{score}%][/bold green] {job['company']} - {job['title']} {funding_tag}(Queued)")
        else:
            console.print(f"  [dim]✗ [{score}%] {job['company']} - {job['title']} (Skipped)[/dim]")

    console.print(f"[bold green]🎯 Evaluation Complete:[/bold green] {scored_count} evaluated, {queued_count} queued for application (>= {min_score}%).\n")

def run_resume(job_id: Optional[str] = None) -> Optional[str]:
    """Generate a role- and country-tailored ATS PDF resume for a specific or top-queued job."""
    from database.db import get_job_by_id, get_jobs_ready_for_application
    from agents.resume_builder import ResumeBuilder

    job = None
    if job_id:
        job = get_job_by_id(job_id)
        if not job:
            console.print(f"[bold red]Error:[/bold red] Job with ID '{job_id}' not found.")
            return None
    else:
        queued = get_jobs_ready_for_application(min_score=70, limit=1)
        if queued:
            job = queued[0]
        else:
            console.print("[yellow]No queued jobs found. Harvest or specify --job-id.[/yellow]")
            return None

    console.print(f"[bold cyan]📄 Generating Tailored ATS Resume for:[/bold cyan] [bold white]{job['company']}[/bold white] - [yellow]{job['title']}[/yellow] ([green]{job['location']}[/green])")
    rb = ResumeBuilder()
    analysis = rb.analyze_role_and_region(job)
    console.print(f"  [cyan]Target Role Title:[/cyan] {analysis['tailored_title']}")
    console.print(f"  [cyan]Regional Framing:[/cyan] {analysis['region_badge']}")
    console.print(f"  [dim]Tailored Summary:[/dim] {analysis['summary'][:160]}...")

    pdf_path = rb.build_resume_pdf(job)
    console.print(f"[bold green]✓ Tailored PDF Generated:[/bold green] [underline white]{pdf_path}[/underline white]\n")
    return pdf_path

def run_email(job_id: Optional[str] = None, to_email: Optional[str] = None, live: bool = False):
    """Compose and send a tailored application email with tailored PDF resume attached via Gmail SMTP SSL."""
    from database.db import get_job_by_id, get_jobs_ready_for_application
    from agents.emailer import JobEmailer

    job = None
    if job_id:
        job = get_job_by_id(job_id)
        if not job:
            console.print(f"[bold red]Error:[/bold red] Job with ID '{job_id}' not found.")
            return
    else:
        queued = get_jobs_ready_for_application(min_score=70, limit=1)
        if queued:
            job = queued[0]
        else:
            console.print("[yellow]No queued jobs found. Harvest or specify --job-id.[/yellow]")
            return

    emailer = JobEmailer()
    if not emailer.is_configured():
        console.print("[bold red]Error:[/bold red] Gmail credentials not found in .env (GMAIL_USER & GMAIL_APP_PASSWORD).")
        return

    mode_label = "[bold red]LIVE OUTREACH[/bold red]" if live else "[bold yellow]PREVIEW MODE (Sent to candidate inbox)[/bold yellow]"
    console.print(f"[bold cyan]📧 Composing & Sending Application Email {mode_label}...[/bold cyan]")
    console.print(f"Target: [bold white]{job['company']}[/bold white] - [cyan]{job['title']}[/cyan] ({job['location']})")

    res = emailer.send_application_email(job, to_email=to_email, preview_mode=not live)

    if res.get("success"):
        console.print(f"  [bold green]✓ Success:[/bold green] {res['status']}")
        console.print(f"  [cyan]Recipient:[/cyan] {res['recipient']}")
        console.print(f"  [cyan]Subject:[/cyan] {res['subject']}")
        console.print(f"  [cyan]Attached PDF:[/cyan] {res['pdf_path']}")
        if not live:
            console.print("  [dim]Tip: Check your Gmail inbox (harshparmar0421@gmail.com) to review the exact formatted pitch and PDF attachment.[/dim]\n")
    else:
        console.print(f"  [bold red]✗ Failed:[/bold red] {res.get('error')}\n")

def run_apply(dry_run: bool = True, limit: int = 5, job_id: Optional[str] = None):
    """Run automated applications for queued jobs or a specific job."""
    from database.db import get_job_by_id
    mode_text = "[yellow](DRY RUN - PREVIEW ONLY)[/yellow]" if dry_run else "[bold red](LIVE SUBMIT)[/bold red]"
    console.print(f"[bold cyan]⚡ Running Application Pipeline {mode_text}...[/bold cyan]")
    profile = load_profile()

    if job_id:
        single_job = get_job_by_id(job_id)
        if not single_job:
            console.print(f"[bold red]Error:[/bold red] Job with ID '{job_id}' not found.")
            return
        jobs = [single_job]
    else:
        jobs = get_jobs_ready_for_application(min_score=profile.job_search_preferences.minimum_match_score, limit=limit)

    if not jobs:
        console.print("[dim]No queued jobs ready for application.[/dim]\n")
        return

    gh_applier = GreenhouseApplier(profile)
    lever_applier = LeverApplier(profile)

    for job in jobs:
        company = job["company"]
        title = job["title"]
        ats = (job.get("ats_type") or "").lower()

        console.print(f"\nProcessing: [bold white]{company}[/bold white] - [cyan]{title}[/cyan] ({ats})")

        if ats == "greenhouse":
            res = gh_applier.apply(job, dry_run=dry_run)
        elif ats == "lever":
            res = lever_applier.apply(job, dry_run=dry_run)
        else:
            console.print(f"  [yellow]Notice: ATS '{ats or 'direct'}' ({company}) requires browser extension or direct email outreach: {job['job_url']}[/yellow]")
            continue

        if res.success:
            console.print(f"  [bold green]Success:[/bold green] {res.status} | Screenshot: {res.screenshot_path}")
            log_application_attempt(
                job_id=job["id"],
                status=res.status,
                submission_method=f"PLAYWRIGHT_{ats.upper()}",
                screenshot_path=res.screenshot_path,
                response_payload=res.details
            )
        else:
            console.print(f"  [bold red]Failed:[/bold red] {res.error_message}")
            log_application_attempt(
                job_id=job["id"],
                status="FAILED",
                submission_method=f"PLAYWRIGHT_{ats.upper()}",
                screenshot_path=res.screenshot_path,
                error_message=res.error_message
            )

    console.print("\n[bold green]✨ Application run complete.[/bold green]\n")

def run_autonomous_pipeline(
    region: str = "all",
    search_term: str = "Software Engineer",
    harvest_limit: int = 30,
    apply_limit: int = 3,
    live: bool = False,
    skip_email: bool = False
):
    """
    Unified end-to-end autonomous pipeline:
    1. Harvests jobs from Dubai, Singapore, India, and Global hubs.
    2. Evaluates & scores jobs against your profile.
    3. For top matched jobs:
       - Generates dynamic role- and country-tailored ATS PDF resume.
       - Applies on company career site (Greenhouse / Lever) with form filling & verification screenshots.
       - Sends personalized application email with tailored PDF resume attached via Gmail SMTP SSL.
    4. Displays comprehensive CRM dashboard and statistics.
    """
    mode_text = "[bold red](LIVE SUBMISSIONS & EMAILS)[/bold red]" if live else "[yellow](DRY RUN & PREVIEWS)[/yellow]"
    console.print(f"\n[bold green]══════════════════════════════════════════════════════════════════════[/bold green]")
    console.print(f"[bold cyan]🚀 EXECUTING UNIFIED AUTONOMOUS JOB PIPELINE {mode_text}[/bold cyan]")
    console.print(f"[bold green]══════════════════════════════════════════════════════════════════════[/bold green]\n")

    profile = load_profile()
    crm = CRMTracker()

    # 1. Harvest
    console.print("[bold yellow]► STEP 1/4: HARVESTING STARTUP ROLES...[/bold yellow]")
    run_harvest(region=region, search_term=search_term, limit=harvest_limit)

    # 2. Match
    console.print("[bold yellow]► STEP 2/4: EVALUATING & SCORING JOBS...[/bold yellow]")
    run_match(min_score=profile.job_search_preferences.minimum_match_score)

    # 3. Execution on Top Queued Jobs
    console.print(f"\n[bold yellow]► STEP 3/4: TAILORING RESUMES, APPLYING ON CAREER SITES & SENDING EMAILS (Limit: {apply_limit})...[/bold yellow]")
    jobs = get_jobs_ready_for_application(min_score=profile.job_search_preferences.minimum_match_score, limit=apply_limit)

    if not jobs:
        console.print("[dim]No queued jobs ready for application.[/dim]\n")
    else:
        from agents.resume_builder import ResumeBuilder
        from agents.emailer import JobEmailer

        rb = ResumeBuilder(profile)
        emailer = JobEmailer(profile)
        gh_applier = GreenhouseApplier(profile)
        lever_applier = LeverApplier(profile)

        for idx, job in enumerate(jobs, 1):
            company = job["company"]
            title = job["title"]
            loc = job.get("location", "Remote")
            ats = (job.get("ats_type") or "").lower()

            console.print(f"\n[bold cyan]── [{idx}/{len(jobs)}] {company} — {title} ({loc}) ──[/bold cyan]")

            # A. Build tailored resume
            console.print("  [cyan]1. Tailoring Resume for Role & Region...[/cyan]")
            pdf_path = rb.build_resume_pdf(job)
            analysis = rb.analyze_role_and_region(job)
            console.print(f"     -> Title: [green]{analysis['tailored_title']}[/green] | Framing: [dim]{analysis['region_badge']}[/dim]")
            console.print(f"     -> PDF: [underline]{pdf_path}[/underline]")
            job["tailored_resume_path"] = pdf_path

            # B. Apply on company career site
            console.print(f"  [cyan]2. Applying on Career Site ({ats or 'direct'})...[/cyan]")
            res = None
            if ats == "greenhouse":
                res = gh_applier.apply(job, dry_run=not live)
            elif ats == "lever":
                res = lever_applier.apply(job, dry_run=not live)
            else:
                console.print(f"     [dim]Career page is '{ats or 'direct'}' ({company}): {job['job_url']}[/dim]")

            if res:
                if res.success:
                    console.print(f"     -> [bold green]Site Status:[/bold green] {res.status} | Screenshot: {res.screenshot_path}")
                    log_application_attempt(
                        job_id=job["id"],
                        status=res.status,
                        submission_method=f"PLAYWRIGHT_{ats.upper()}",
                        screenshot_path=res.screenshot_path,
                        response_payload=res.details
                    )
                else:
                    console.print(f"     -> [bold red]Site Failed:[/bold red] {res.error_message}")
                    log_application_attempt(
                        job_id=job["id"],
                        status="FAILED",
                        submission_method=f"PLAYWRIGHT_{ats.upper()}",
                        screenshot_path=res.screenshot_path,
                        error_message=res.error_message
                    )

            # C. Send Tailored Application Email
            if not skip_email and emailer.is_configured():
                console.print("  [cyan]3. Sending Tailored Application Email Outreach...[/cyan]")
                mail_res = emailer.send_application_email(job, preview_mode=not live)
                if mail_res.get("success"):
                    console.print(f"     -> [bold green]Email Sent:[/bold green] {mail_res['status']} to [white]{mail_res['recipient']}[/white]")
                    console.print(f"     -> Subject: [dim]{mail_res['subject']}[/dim]")
                else:
                    console.print(f"     -> [bold red]Email Failed:[/bold red] {mail_res.get('error')}")

    # 4. Final Dashboard
    console.print("\n[bold yellow]► STEP 4/4: PIPELINE DASHBOARD & AUDIT HISTORY[/bold yellow]")
    crm.print_dashboard()
    crm.print_applied_history(limit=8)

def main():
    parser = argparse.ArgumentParser(description="Antigravity Autonomous Job Search & Application Platform")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Unified Run / Pipeline command (Single command execution)
    p_run = subparsers.add_parser("run", aliases=["pipeline", "auto", "run-all"], help="Execute single-command autonomous pipeline (Harvest -> Match -> Tailor Resume -> Site Apply -> Send Email)")
    p_run.add_argument("--region", choices=["all", "dubai", "singapore", "india", "global"], default="all", help="Target region")
    p_run.add_argument("--term", default="Software Engineer", help="Role search term")
    p_run.add_argument("--limit", type=int, default=3, help="Max jobs to process end-to-end")
    p_run.add_argument("--live", action="store_true", help="Execute live site submission and email delivery (default is dry-run & preview)")
    p_run.add_argument("--skip-email", action="store_true", help="Skip sending emails")

    # Harvest command
    p_harvest = subparsers.add_parser("harvest", help="Harvest new jobs from Dubai, Singapore, and Global startups")
    p_harvest.add_argument("--region", choices=["all", "dubai", "singapore", "india", "global"], default="all", help="Target region")
    p_harvest.add_argument("--source", choices=["all", "startups", "dubai", "singapore", "india", "greenhouse", "lever", "jobspy"], default="all")
    p_harvest.add_argument("--term", default="Software Engineer", help="Role search term (e.g. 'Software Engineer', 'Full Stack')")
    p_harvest.add_argument("--remote-only", action="store_true", help="Filter for 100% remote positions only")
    p_harvest.add_argument("--limit", type=int, default=30, help="Max jobs to harvest per source")

    # Match command
    p_match = subparsers.add_parser("match", help="Score unscored jobs against profile")
    p_match.add_argument("--min-score", type=int, default=70, help="Minimum score to queue for application")

    # Resume command
    p_resume = subparsers.add_parser("resume", help="Generate role- and country-tailored ATS PDF resume")
    p_resume.add_argument("--job-id", type=str, help="Job ID (exact or prefix) to tailor the resume for")

    # Email command
    p_email = subparsers.add_parser("email", help="Send tailored application pitch & PDF resume via Gmail")
    p_email.add_argument("--job-id", type=str, help="Job ID (exact or prefix)")
    p_email.add_argument("--to", type=str, help="Target recipient email (defaults to preview to user's inbox)")
    p_email.add_argument("--live", action="store_true", help="Send live email directly to company/recipient")

    # Apply command
    p_apply = subparsers.add_parser("apply", help="Execute automated applications on company career sites")
    p_apply.add_argument("--job-id", type=str, help="Specific Job ID to apply to")
    p_apply.add_argument("--live", action="store_true", help="Execute live submission (default is dry-run)")
    p_apply.add_argument("--limit", type=int, default=5, help="Max jobs to apply to in this run")

    # Status / CRM command
    p_status = subparsers.add_parser("status", help="Display all pipeline counters and breakdown statistics")

    args = parser.parse_args()

    # Ensure DB is initialized with migrations
    init_db()

    crm = CRMTracker()

    if args.command in ("run", "pipeline", "auto", "run-all"):
        run_autonomous_pipeline(
            region=args.region,
            search_term=args.term,
            apply_limit=args.limit,
            live=args.live,
            skip_email=args.skip_email
        )
    elif args.command == "harvest":
        run_harvest(
            source=args.source, 
            region=args.region, 
            search_term=args.term, 
            remote_only=args.remote_only, 
            limit=args.limit
        )
    elif args.command == "match":
        run_match(min_score=args.min_score)
    elif args.command == "resume":
        run_resume(job_id=args.job_id)
    elif args.command == "email":
        run_email(job_id=args.job_id, to_email=args.to, live=args.live)
    elif args.command == "apply":
        run_apply(dry_run=not args.live, limit=args.limit, job_id=args.job_id)
    elif args.command == "status":
        crm.print_dashboard()
        crm.print_top_matches()
        crm.print_applied_history()
    else:
        # Default with no args: run unified pipeline
        run_autonomous_pipeline(region="all", search_term="Software Engineer", apply_limit=2)

if __name__ == "__main__":
    main()

