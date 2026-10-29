import time
from pathlib import Path
from typing import Dict, Any, Optional
from agents.appliers.base_applier import BaseApplier, ApplicationResult

class GreenhouseApplier(BaseApplier):
    """
    Automates Greenhouse application form filling via Playwright.
    Dynamically identifies fields from their labels and answers them using AnswerAgent.
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
        job_id = job_data.get("id", "job")
        
        screenshot_dir = Path(__file__).parent.parent.parent / "data" / "screenshots"
        screenshot_dir.mkdir(parents=True, exist_ok=True)
        screenshot_path = str(screenshot_dir / f"greenhouse_{job_id}_{'preview' if dry_run else 'submitted'}.png")

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                    viewport={"width": 1280, "height": 1100}
                )
                page = context.new_page()

                # Navigate to job posting
                page.goto(job_url, timeout=35000)
                page.wait_for_load_state("networkidle", timeout=15000)

                # Scroll to application form if present
                for form_sel in ["#application_form", "#apply", "form[action*='jobs']", "form"]:
                    if page.locator(form_sel).count() > 0:
                        page.locator(form_sel).first.scroll_into_view_if_needed()
                        break

                # 1. Standard Fields
                # First Name
                for sel in ["#first_name", "input[name*='first_name']", "input[autocomplete*='given-name']"]:
                    if page.locator(sel).is_visible():
                        page.locator(sel).fill(self.profile.personal_info.first_name)
                        break

                # Last Name
                for sel in ["#last_name", "input[name*='last_name']", "input[autocomplete*='family-name']"]:
                    if page.locator(sel).is_visible():
                        page.locator(sel).fill(self.profile.personal_info.last_name)
                        break

                # Email
                for sel in ["#email", "input[name*='email']", "input[type='email']"]:
                    if page.locator(sel).is_visible():
                        page.locator(sel).fill(self.profile.personal_info.email)
                        break

                # Phone
                for sel in ["#phone", "input[name*='phone']", "input[type='tel']"]:
                    if page.locator(sel).is_visible():
                        page.locator(sel).fill(self.profile.personal_info.phone)
                        break

                # Location (City)
                for sel in ["#candidate-location", "#job_application_location", "input[name*='location']"]:
                    loc_el = page.locator(sel)
                    if loc_el.is_visible():
                        if "select__input" in (loc_el.get_attribute("class") or ""):
                            loc_el.click()
                            loc_el.press_sequentially("Ahmedabad", delay=120)
                            page.wait_for_timeout(1200)
                            opt = page.locator("[id*='candidate-location-option'], [class*='option']:has-text('Ahmedabad')").first
                            if opt.is_visible():
                                opt.click()
                            else:
                                page.keyboard.press("ArrowDown")
                                page.keyboard.press("Enter")
                        else:
                            loc_el.fill(self.profile.personal_info.location)
                        break

                # 2. Attach Tailored Resume
                tailored_resume = job_data.get("tailored_resume_path")
                if not tailored_resume or not Path(tailored_resume).exists():
                    try:
                        from agents.resume_builder import ResumeBuilder
                        rb = ResumeBuilder(self.profile)
                        tailored_resume = rb.build_resume_pdf(job_data)
                    except Exception as e:
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
                    file_input = page.locator("input[type='file']")
                    if file_input.count() > 0:
                        file_input.first.set_input_files(str(res_path.resolve()))
                        try:
                            file_input.first.dispatch_event("change")
                        except Exception:
                            pass
                        page.wait_for_timeout(1000)

                # 3. Dynamic Custom Questions & Form Fields
                # Find all questions with labels
                labels = page.locator("label")
                count = labels.count()
                for i in range(count):
                    try:
                        lbl = labels.nth(i)
                        lbl_text = (lbl.inner_text() or "").strip()
                        if not lbl_text:
                            continue
                        
                        target_id = lbl.get_attribute("for")
                        target = page.locator(f"#{target_id}") if target_id else lbl.locator("..").locator("input, select, textarea").first

                        if target.count() == 0 or not target.is_visible():
                            continue

                        tag_name = target.evaluate("el => el.tagName.toLowerCase()")
                        input_type = target.evaluate("el => el.getAttribute('type') || ''").lower()

                        is_react_select = (
                            target.get_attribute("role") == "combobox"
                            or "select__input" in (target.get_attribute("class") or "")
                        )
                        if is_react_select:
                            if any(k in lbl_text.lower() for k in ["relocate", "relocation", "willing", "authorized", "authorization"]):
                                target.focus()
                                target.press_sequentially("Yes", delay=80)
                                page.keyboard.press("Enter")
                                page.wait_for_timeout(300)
                            elif "sponsor" in lbl_text.lower():
                                target.focus()
                                target.press_sequentially("No", delay=80)
                                page.keyboard.press("Enter")
                                page.wait_for_timeout(300)
                            else:
                                target.focus()
                                target.press_sequentially("Yes", delay=80)
                                page.keyboard.press("Enter")
                                page.wait_for_timeout(300)

                        # If text input or textarea
                        elif tag_name in ["textarea"] or (tag_name == "input" and input_type in ["text", "url", ""]):
                            current_val = target.input_value()
                            if not current_val:
                                ans = self.answer_agent.answer_question(lbl_text)
                                if ans and ans != "Not specified":
                                    target.fill(ans)
                                elif "linkedin" in lbl_text.lower():
                                    target.fill(self.profile.personal_info.linkedin_url or "")
                                elif "github" in lbl_text.lower():
                                    target.fill(self.profile.personal_info.github_url or "")
                                elif "website" in lbl_text.lower() or "portfolio" in lbl_text.lower():
                                    target.fill(self.profile.personal_info.portfolio_url or "")
                                elif "hear about" in lbl_text.lower():
                                    target.fill("Company Careers / LinkedIn")

                        # If checkbox (e.g. privacy terms)
                        elif input_type == "checkbox":
                            if not target.is_checked():
                                target.check()

                        # If select dropdown
                        elif tag_name == "select":
                            options = target.locator("option").all_inner_texts()
                            lower_opts = [o.lower() for o in options]
                            # Try matching Yes/No or Work Authorization
                            if "sponsorship" in lbl_text.lower():
                                for opt in options:
                                    if "no" in opt.lower():
                                        target.select_option(label=opt)
                                        break
                            elif "authorized" in lbl_text.lower() or "authorization" in lbl_text.lower():
                                for opt in options:
                                    if "authorized" in opt.lower() or "citizen" in opt.lower() or "yes" in opt.lower():
                                        target.select_option(label=opt)
                                        break
                            elif "relocate" in lbl_text.lower() or "relocation" in lbl_text.lower() or "willing" in lbl_text.lower():
                                for opt in options:
                                    if "yes" in opt.lower():
                                        target.select_option(label=opt)
                                        break
                            elif "access control" in lbl_text.lower() or "oauth" in lbl_text.lower():
                                for opt in options:
                                    if "yes" in opt.lower():
                                        target.select_option(label=opt)
                                        break
                    except Exception:
                        continue

                # Also handle custom Greenhouse comboboxes / dropdown buttons
                for btn in page.locator("button[role='combobox'], div[role='combobox']").all():
                    try:
                        aria_lbl = (btn.get_attribute("aria-label") or "").lower()
                        parent_text = (btn.locator("..").inner_text() or "").lower()
                        if "relocate" in aria_lbl or "relocate" in parent_text or "relocation" in parent_text:
                            btn.click()
                            page.wait_for_timeout(300)
                            yes_opt = page.locator("[role='option']:has-text('Yes'), li:has-text('Yes')").first
                            if yes_opt.is_visible():
                                yes_opt.click()
                    except Exception:
                        pass

                # Final wait and screenshot
                page.wait_for_timeout(2000)
                page.screenshot(path=screenshot_path, full_page=True)

                if dry_run:
                    browser.close()
                    return ApplicationResult(
                        success=True,
                        status="PREVIEW_READY",
                        screenshot_path=screenshot_path,
                        details="Filled Greenhouse form in dry-run mode. Full verification screenshot captured."
                    )

                # Live submit if enabled
                submit_btn = page.locator("#submit_app, input[type='submit'], button[type='submit']:has-text('Submit')").first
                if submit_btn.is_visible():
                    submit_btn.click()
                    page.wait_for_timeout(5000)
                    page.screenshot(path=screenshot_path, full_page=True)
                    browser.close()
                    return ApplicationResult(
                        success=True,
                        status="SUBMITTED",
                        screenshot_path=screenshot_path,
                        details="Application submitted successfully."
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
