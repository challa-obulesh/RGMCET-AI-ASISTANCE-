"""
scripts/verify_phase7_chrome_full.py
Complete Phase 7 Visible Google Chrome Verification script.
Executes with headless=False, testing synthetic logins, normal enquiry, Stephen deterministic no-match,
appointment booking & approval, privacy redaction inspection, and RBAC boundaries.
"""

import sys
import time
import socket
import json
import urllib.request
import urllib.error
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.web_mvp.main import app
import uvicorn
from app.web_mvp import privacy_gateway
from playwright.sync_api import sync_playwright

SCRATCH = Path("scratch/phase7_chrome")
SCRATCH.mkdir(parents=True, exist_ok=True)


def get_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def make_request(base_url, path, data=None, token=None, method="GET"):
    url = f"{base_url}{path}"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(data).encode("utf-8") if data is not None else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            content = resp.read().decode("utf-8")
            return resp.status, json.loads(content) if content else {}
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode("utf-8"))
        except Exception:
            return e.code, {}


def main():
    print("=" * 80)
    print("PHASE 7 — VISIBLE GOOGLE CHROME VERIFICATION RUNNER")
    print("=" * 80)

    port = get_free_port()
    base_url = f"http://127.0.0.1:{port}"
    print(f"Starting uvicorn server on {base_url} ...")

    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    server_thread = threading.Thread(target=server.run, daemon=True)
    server_thread.start()

    # Wait for server to come up
    for _ in range(30):
        try:
            with urllib.request.urlopen(f"{base_url}/api/health", timeout=1) as resp:
                if resp.status == 200:
                    break
        except Exception:
            time.sleep(0.5)

    print("FastAPI Backend running successfully.")

    results = {}
    console_errors = []
    network_errors = []

    def pass_test(tid, msg):
        print(f"  [PASS] {tid}: {msg}")
        results[tid] = "PASS"

    def fail_test(tid, msg, err=""):
        print(f"  [FAIL] {tid}: {msg} -> {err}")
        results[tid] = f"FAIL: {err}"

    # Setup demo synthetic accounts
    admin_email = "admin@example.com"
    admin_pass = "AdminPass123!"
    prof_email = "hod.cse.ds@example.com"
    prof_pass = "ProfPass123!"
    student_email = "student1@example.com"
    student_pass = "StudentPass123!"

    # Ensure accounts exist in store
    # Admin
    make_request(base_url, "/api/auth/register", {
        "name": "RGMCET Administrator",
        "email": admin_email,
        "password": admin_pass,
        "role": "admin"
    }, method="POST")

    # Get admin token to approve professors
    _, adm_login = make_request(base_url, "/api/auth/login", {"email": admin_email, "password": admin_pass}, method="POST")
    adm_token = adm_login.get("access_token")

    # Professor
    s_prof, d_prof = make_request(base_url, "/api/auth/register", {
        "name": "Dr. B.Bhaskara Rao",
        "email": prof_email,
        "password": prof_pass,
        "role": "professor",
        "department": "CSE (Data Science)",
        "professor_id": "PROF-VERIFIED-CSEDS-002"
    }, method="POST")
    if adm_token:
        users = make_request(base_url, "/api/admin/users", token=adm_token)[1]
        for u in users:
            if u.get("email") == prof_email:
                make_request(base_url, f"/api/admin/professors/{u['user_id']}/status", {"status": "APPROVED"}, token=adm_token, method="PATCH")

    # Student
    make_request(base_url, "/api/auth/register", {
        "name": "Kavya Student",
        "email": student_email,
        "password": student_pass,
        "role": "student"
    }, method="POST")

    print("\nVerified synthetic demo accounts are ready:")
    print(f"  Admin: {admin_email}")
    print(f"  Professor: {prof_email}")
    print(f"  Student: {student_email}\n")

    # Start visible Playwright Chrome session
    with sync_playwright() as p:
        print("Launching visible Google Chrome with headless=False ...")
        browser = p.chromium.launch(headless=False, slow_mo=100)
        context = browser.new_context(viewport={"width": 1366, "height": 768})
        page = context.new_page()

        def on_console(msg):
            if msg.type == "error":
                text = msg.text
                if "favicon" not in text.lower():
                    console_errors.append(text)

        def on_response(res):
            if res.status >= 400:
                url = res.url
                if "favicon" not in url.lower() and "/api/auth/register" not in url:
                    network_errors.append(f"{res.status} {url}")

        page.on("console", on_console)
        page.on("response", on_response)

        try:
            # STEP 1: Open Application & Test Normal Enquiry
            print("\n>>> STEP 1: Normal RGMCET Enquiry (Central Library)")
            page.goto(base_url)
            page.wait_for_load_state("networkidle")
            time.sleep(1)
            page.screenshot(path=str(SCRATCH / "01_homepage.png"))

            # Type question in chat
            chat_input = page.locator(".composer textarea, textarea[placeholder*='Ask']")
            assert chat_input.is_visible(), "Chat textarea visible"

            chat_input.fill("Where is the Central Library?")
            page.click(".send-button")
            time.sleep(1)
            page.wait_for_selector(".message-row.assistant", timeout=25000)
            page.screenshot(path=str(SCRATCH / "02_normal_enquiry_library.png"))

            chat_text = page.locator("main").inner_text()
            assert "library" in chat_text.lower(), "Library answer returned"
            pass_test("01_Normal_Enquiry", "Normal RGMCET enquiry returned verified knowledge response")

            # STEP 2: Deterministic Faculty-Name Question (Stephen - No Match)
            print("\n>>> STEP 2: Deterministic Faculty Inquiry ('Stephen' in Data Science)")
            chat_input.fill("Is there any Data Science faculty member named Stephen?")
            page.click(".send-button")
            time.sleep(1)
            page.wait_for_selector(".message-row.assistant:has-text('Stephen')", timeout=25000)
            page.screenshot(path=str(SCRATCH / "03_stephen_deterministic_no_match.png"))

            all_chat = page.locator("main").inner_text()
            expected_phrase = "No matching faculty member named Stephen was found in the verified Data Science faculty records."
            assert expected_phrase in all_chat, f"Expected deterministic response not found in chat:\n{all_chat}"
            pass_test("02_Deterministic_Stephen_No_Match", "Deterministic response returned without hallucination")

            # STEP 3: Privacy Redaction Verification on Outbound Request
            print("\n>>> STEP 3: Privacy Gateway Outbound Redaction Check")
            sensitive_prompt = "Contact professor at test.faculty@rgmcet.edu.in or call +91 9876543210 regarding database password mongodb://admin:pass@db.rgmcet.edu:27017"
            clean_sys, clean_usr, stats = privacy_gateway.sanitize_request("System instructions", sensitive_prompt)
            print(f"   Original: {sensitive_prompt}")
            print(f"   Sanitized Outbound: {clean_usr}")
            assert "test.faculty@rgmcet.edu.in" not in clean_usr
            assert "+91 9876543210" not in clean_usr
            assert "mongodb://" not in clean_usr
            assert "[REDACTED_EMAIL]" in clean_usr
            assert "[REDACTED_PHONE]" in clean_usr
            assert "[REDACTED_DB_CONNECTION]" in clean_usr
            pass_test("03_Privacy_Gateway_Redaction", "Privacy Gateway strips emails, phones, and DB URIs before transmission")

            # STEP 4: Synthetic Student Login
            print("\n>>> STEP 4: Synthetic Student Login (student1@example.com)")
            if page.locator("#nav-login").is_visible():
                page.click("#nav-login")
            else:
                page.goto(f"{base_url}/login")
            time.sleep(1)

            page.fill("#login-email", student_email)
            page.fill("#login-password", student_pass)
            page.click("#login-submit")
            page.wait_for_url("**/student**", timeout=15000)
            page.screenshot(path=str(SCRATCH / "04_student_logged_in.png"))
            assert "/student" in page.url
            pass_test("04_Synthetic_Student_Login", "Synthetic student logged in and navigated to Student Portal")

            # STEP 5: Book Appointment with Dr. B.Bhaskara Rao
            print("\n>>> STEP 5: Student Books Appointment with Dr. B.Bhaskara Rao")
            page.click("#nav-professors")
            time.sleep(1)
            page.screenshot(path=str(SCRATCH / "05_professors_directory.png"))

            book_btn = page.locator(".professor-card:has-text('Dr. B.Bhaskara Rao') button:has-text('Request appointment'), .professor-card:has-text('Bhaskara Rao') button:has-text('Request appointment')").first
            if not book_btn.is_visible():
                book_btn = page.locator("button:has-text('Request appointment')").first
            book_btn.click()
            time.sleep(1.5)

            # Pick slot and submit
            page.fill("#appointment-reason-input", "Privacy & Data Architecture Review")
            page.click("#appointment-submit-button")
            time.sleep(2)
            page.screenshot(path=str(SCRATCH / "06_appointment_requested_pending.png"))

            dialog_text = page.locator(".appointment-dialog").inner_text()
            assert "PENDING PROFESSOR APPROVAL" in dialog_text or "Pending" in dialog_text or "PENDING" in dialog_text
            page.click("button:has-text('Done')")
            time.sleep(1)

            page.click("#nav-student")
            time.sleep(1)
            page.screenshot(path=str(SCRATCH / "07_student_dashboard_pending.png"))
            st_text = page.locator(".appointment-row").first.inner_text()
            assert "PENDING" in st_text.upper()
            pass_test("05_Student_Book_Appointment", "Appointment created and status is PENDING_APPROVAL")

            # Logout student
            page.click("#logout-button")
            time.sleep(1)

            # STEP 6: Synthetic Professor Login & Approval
            print("\n>>> STEP 6: Synthetic Professor Login (hod.cse.ds@example.com) & Approval")
            if page.locator("#nav-login").is_visible():
                page.click("#nav-login")
            else:
                page.goto(f"{base_url}/login")
            time.sleep(0.5)

            page.fill("#login-email", prof_email)
            page.fill("#login-password", prof_pass)
            page.click("#login-submit")
            page.wait_for_url("**/professor**", timeout=15000)
            page.screenshot(path=str(SCRATCH / "08_professor_dashboard.png"))

            page.wait_for_selector("#pending-requests", timeout=10000)
            pending_text = page.locator("#pending-requests").inner_text()
            assert "Privacy & Data Architecture Review" in pending_text

            # Approve the appointment
            approve_btn = page.locator("#pending-requests button:has-text('Approve')").first
            approve_btn.click()
            time.sleep(2)
            page.screenshot(path=str(SCRATCH / "09_professor_after_approval.png"))

            upcoming_text = page.locator("#upcoming-appointments").inner_text()
            assert "Privacy & Data Architecture Review" in upcoming_text
            pass_test("06_Professor_Approve_Appointment", "Professor approved appointment; moved to Upcoming Appointments")

            # Logout professor
            page.click("#logout-button")
            time.sleep(1)

            # STEP 7: Verify Student Sees Status APPROVED
            print("\n>>> STEP 7: Student Sees Appointment Status APPROVED")
            if page.locator("#nav-login").is_visible():
                page.click("#nav-login")
            page.fill("#login-email", student_email)
            page.fill("#login-password", student_pass)
            page.click("#login-submit")
            page.wait_for_url("**/student**", timeout=15000)
            time.sleep(1)
            page.screenshot(path=str(SCRATCH / "10_student_confirmed_approved.png"))

            st_row = page.locator(".appointment-row:has-text('Privacy & Data Architecture Review')").inner_text()
            assert "APPROVED" in st_row
            pass_test("07_Student_Confirmed_Approved", "Student verified status updated to APPROVED")

            # Logout student
            page.click("#logout-button")
            time.sleep(1)

            # STEP 8: Access Boundaries (RBAC)
            print("\n>>> STEP 8: Student & Professor RBAC Boundaries")
            # Student attempts to navigate to /admin/dashboard
            page.fill("#login-email", student_email)
            page.fill("#login-password", student_pass)
            page.click("#login-submit")
            page.wait_for_url("**/student**", timeout=15000)

            page.goto(f"{base_url}/admin/dashboard")
            time.sleep(1)
            page.screenshot(path=str(SCRATCH / "11_student_admin_denied.png"))
            assert page.locator("#admin-access-denied").is_visible() or "Access Denied" in page.locator("main").inner_text()
            pass_test("08_RBAC_Student_Admin_Blocked", "Student blocked from accessing Admin Dashboard")

            page.click("#logout-button")
            time.sleep(1)

            # STEP 9: Synthetic Admin Login
            print("\n>>> STEP 9: Synthetic Admin Login (admin@example.com)")
            if page.locator("#nav-login").is_visible():
                page.click("#nav-login")
            page.fill("#login-email", admin_email)
            page.fill("#login-password", admin_pass)
            page.click("#login-submit")
            page.wait_for_url("**/admin**", timeout=15000)
            page.screenshot(path=str(SCRATCH / "12_admin_dashboard.png"))
            assert "/admin" in page.url
            assert "Admin Dashboard" in page.locator("main").inner_text()
            pass_test("09_Synthetic_Admin_Login", "Synthetic Admin logged in successfully")

            # STEP 10: Audit Console Errors & Network Requests
            print("\n>>> STEP 10: Audit Console & Network")
            print(f"   Console errors detected: {len(console_errors)}")
            print(f"   Network 4xx/5xx errors detected: {len(network_errors)}")
            assert len(console_errors) == 0, f"Unexpected console errors: {console_errors}"
            assert len(network_errors) == 0, f"Unexpected network errors: {network_errors}"
            pass_test("10_Console_And_Network_Clean", "Zero critical console errors and zero unexpected network errors")

            print("\n" + "=" * 80)
            print("ALL 10 PHASE 7 VISIBLE CHROME VERIFICATION STEPS PASSED 100%!")
            print("=" * 80 + "\n")

        finally:
            browser.close()
            server.should_exit = True

    return results


if __name__ == "__main__":
    res = main()
    all_passed = all(v == "PASS" for v in res.values())
    sys.exit(0 if all_passed else 1)
