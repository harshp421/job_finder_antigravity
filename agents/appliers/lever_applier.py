import time
from pathlib import Path
from typing import Dict, Any, Optional
from agents.appliers.base_applier import BaseApplier, ApplicationResult

class LeverApplier(BaseApplier):
    """
    Automates Lever application form filling via Playwright.
    Supports dry-run preview mode (fills form & screenshots without submitting).
    """

    def apply(self, job_data: Dict[str, Any], dry_run: bool = True) -> ApplicationResult:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            return ApplicationResult(
                success=False,
                status="FAILED",
                error_message="Playwright is not installed."
            )

        job_url = job_data.get("job_url", "")
        # In Lever, /apply is appended to the job posting URL to access the application form
        if not job_url.endswith("/apply"):
            form_url = f"{job_url.rstrip('/')}/apply"
        else:
            form_url = job_url

        job_id = job_data.get("id", "job")
        screenshot_dir = Path(__file__).parent.parent.parent / "data" / "screenshots"
        screenshot_dir.mkdir(parents=True, exist_ok=True)
        screenshot_path = str(screenshot_dir / f"lever_{job_id}_{'preview' if dry_run else 'submitted'}.png")

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                    viewport={"width": 1280, "height": 900}
                )
                page = context.new_page()
                page.goto(form_url, timeout=30000)
                page.wait_for_load_state("networkidle", timeout=15000)

                # Fill Full Name
                if page.locator("input[name='name']").is_visible():
                    page.locator("input[name='name']").fill(self.profile.personal_info.full_name)

                # Fill Email
                if page.locator("input[name='email']").is_visible():
                    page.locator("input[name='email']").fill(self.profile.personal_info.email)

                # Fill Phone
                if page.locator("input[name='phone']").is_visible():
                    page.locator("input[name='phone']").fill(self.profile.personal_info.phone)

                # Fill Current Company / Location
                if page.locator("input[name='org']").is_visible():
                    page.locator("input[name='org']").fill(self.profile.experience_highlights[0].company if self.profile.experience_highlights else "")

                # Fill URLs
                if page.locator("input[name*='urls[LinkedIn]']").is_visible():
                    page.locator("input[name*='urls[LinkedIn]']").fill(self.profile.personal_info.linkedin_url or "")

                if page.locator("input[name*='urls[GitHub]']").is_visible():
                    page.locator("input[name*='urls[GitHub]']").fill(self.profile.personal_info.github_url or "")

                if page.locator("input[name*='urls[Portfolio]']").is_visible():
                    page.locator("input[name*='urls[Portfolio]']").fill(self.profile.personal_info.portfolio_url or "")

                # 2. Attach Tailored Resume
                tailored_resume = job_data.get("tailored_resume_path")
                if not tailored_resume or not Path(tailored_resume).exists():
                    try:
                        from agents.resume_builder import ResumeBuilder
                        rb = ResumeBuilder(self.profile)
                        tailored_resume = rb.build_resume_pdf(job_data)
                    except Exception:
                        tailored_resume = None

                res_path = None
                if tailored_resume and Path(tailored_resume).exists():
                    res_path = Path(tailored_resume)
                elif self.profile.personal_info.resume_path:
                    p = Path(__file__).parent.parent.parent / self.profile.personal_info.resume_path
                    if p.exists():
                        res_path = p
                    elif Path(self.profile.personal_info.resume_path).exists():
                        res_path = Path(self.profile.personal_info.resume_path)

                if res_path and res_path.exists():
                    file_input = page.locator("input[type='file'][name='resume'], input[type='file']")
                    if file_input.count() > 0:
                        file_input.first.set_input_files(str(res_path.resolve()))

                # Capture preview screenshot
                page.screenshot(path=screenshot_path, full_page=True)

                if dry_run:
                    browser.close()
                    return ApplicationResult(
                        success=True,
                        status="PREVIEW_READY",
                        screenshot_path=screenshot_path,
                        details="Filled Lever form in dry-run mode. Screenshot saved."
                    )

                # Submit
                submit_btn = page.locator("button#btn-submit, button[type='submit']")
                if submit_btn.is_visible():
                    submit_btn.click()
                    page.wait_for_timeout(4000)
                    page.screenshot(path=screenshot_path, full_page=True)
                    browser.close()
                    return ApplicationResult(
                        success=True,
                        status="SUBMITTED",
                        screenshot_path=screenshot_path,
                        details="Application submitted successfully to Lever."
                    )
                else:
                    browser.close()
                    return ApplicationResult(
                        success=False,
                        status="FAILED",
                        screenshot_path=screenshot_path,
                        error_message="Submit button not found."
                    )

        except Exception as e:
            return ApplicationResult(
                success=False,
                status="FAILED",
                error_message=str(e),
                screenshot_path=screenshot_path if Path(screenshot_path).exists() else None
            )
