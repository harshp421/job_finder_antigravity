from typing import Dict, Any, List
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns
from database.db import get_statistics, get_jobs_ready_for_application, get_connection

console = Console()

class CRMTracker:
    """Manages application status visualization, statistics, and reports."""

    def print_dashboard(self):
        """Render a rich visual summary of all pipeline counters and breakdown."""
        stats = get_statistics()

        # Main summary counts
        panel_content = (
            f"[bold cyan]Discovered:[/bold cyan] {stats['total_discovered']}  |  "
            f"[bold magenta]Evaluated:[/bold magenta] {stats['total_evaluated']}  |  "
            f"[bold yellow]Queued (>=70%):[/bold yellow] {stats['total_queued']}  |  "
            f"[bold green]Applied:[/bold green] {stats['total_applied']}  |  "
            f"[bold red]Skipped (<70%):[/bold red] {stats.get('total_skipped', 0)}  |  "
            f"[bold blue]Avg Match:[/bold blue] {stats['average_match_score']}%"
        )
        console.print(Panel(panel_content, title="🚀 Antigravity Autonomous Pipeline Tracker", expand=False))

        # Sources & Startups breakdown table
        sources = stats.get("sources", {})
        companies = stats.get("companies", {})
        
        breakdown_table = Table(title="📊 Pipeline Source & Startup Distribution", show_header=True, header_style="bold cyan")
        breakdown_table.add_column("Source / Platform", style="white", width=22)
        breakdown_table.add_column("Count", justify="center", style="bold green", width=10)
        breakdown_table.add_column("Top Startups Hiring", style="yellow", width=36)
        breakdown_table.add_column("Active Roles", justify="center", style="bold cyan", width=12)

        src_items = list(sources.items())
        comp_items = list(companies.items())
        max_rows = max(len(src_items), len(comp_items), 1)

        for i in range(max_rows):
            s_name, s_count = src_items[i] if i < len(src_items) else ("", "")
            c_name, c_count = comp_items[i] if i < len(comp_items) else ("", "")
            breakdown_table.add_row(
                str(s_name).upper() if s_name else "",
                str(s_count) if s_count else "",
                str(c_name) if c_name else "",
                str(c_count) if c_count else ""
            )

        console.print(breakdown_table)

    def print_top_matches(self, limit: int = 10):
        """Print table of highest scored jobs ready for review or application, including funding stage."""
        jobs = get_jobs_ready_for_application(min_score=70, limit=limit)
        if not jobs:
            console.print("[dim]No high-matching jobs currently queued. Run harvesting to find more.[/dim]")
            return

        table = Table(title=f"🔥 Top Matched Startup Jobs Ready to Apply (Top {len(jobs)})", show_header=True, header_style="bold magenta")
        table.add_column("Score", justify="center", style="bold green", width=8)
        table.add_column("Startup", style="cyan", width=14)
        table.add_column("Funding / Backing", style="yellow", width=28)
        table.add_column("Role Title", style="white", width=28)
        table.add_column("Location / Remote", style="dim", width=20)
        table.add_column("Job Link", style="underline blue")

        for j in jobs:
            score_badge = f"{j.get('match_score', 0)}%"
            funding = j.get("funding_info") or "Funded Tech Startup"
            loc = j.get("location") or "Remote"
            table.add_row(
                score_badge,
                j.get("company", ""),
                funding[:26] + ("..." if len(funding) > 26 else ""),
                j.get("title", ""),
                loc[:18] + ("..." if len(loc) > 18 else ""),
                j.get("job_url", "")[:40] + "..."
            )

        console.print(table)

    def print_applied_history(self, limit: int = 15):
        """Print history of submitted applications."""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT j.company, j.title, a.status, a.submission_method, a.applied_at, a.screenshot_path
                FROM applications a
                JOIN jobs j ON a.job_id = j.id
                ORDER BY a.applied_at DESC
                LIMIT ?
                """,
                (limit,)
            )
            rows = cursor.fetchall()

        if not rows:
            console.print("[dim]No applications submitted yet.[/dim]")
            return

        table = Table(title="📋 Recent Application History", show_header=True, header_style="bold green")
        table.add_column("Date", style="dim", width=16)
        table.add_column("Company", style="cyan", width=20)
        table.add_column("Title", style="white", width=30)
        table.add_column("Status", justify="center", style="bold", width=12)
        table.add_column("Method", style="dim", width=15)

        for r in rows:
            status_style = "bold green" if r["status"] == "SUBMITTED" else "bold yellow"
            table.add_row(
                str(r["applied_at"])[:16],
                r["company"],
                r["title"],
                f"[{status_style}]{r['status']}[/{status_style}]",
                r["submission_method"] or "N/A"
            )

        console.print(table)
