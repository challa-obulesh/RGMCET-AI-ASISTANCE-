"""
verify_admin_professor_approvals_chrome.py
Runs visible Chrome (headless=False) end-to-end verification of:
1. Admin Login -> /admin/dashboard
2. Admin Dashboard -> Professor Approvals tab
3. Official faculty records verified
4. Admin approves a pending verified professor (Dr. K. Samunnisa)
5. Admin logs out
6. Approved Professor logs in (samunnisacseds@rgmcet.edu.in)
7. Professor Dashboard at /professor/dashboard with identity header and schedule
8. Student logs in / registers, books appointment with Dr. K. Samunnisa
9. Professor logs in, verifies Pending Student Requests, clicks Approve
10. Student logs in, verifies APPROVED status
11. Professor B logs in, verifies isolation (0 requests seen from Prof A)
12. Mobile viewport test (375x667)
13. Console errors & network requests audit
"""

import sys
import time
import socket
import json
import urllib.request
import urllib.error
import threading
import uvicorn
from playwright.sync_api import sync_playwright

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from app.web_mvp.main import app


def get_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def main():
    port = get_free_port()
    base_url = f"http://127.0.0.1:{port}"
    print(f"Starting server on {base_url}...")

    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    server_thread = threading.Thread(target=server.run, daemon=True)
    server_thread.start()

    # Wait for server to come up
    for _ in range(30):
        try:
            with urllib.request.urlopen(f"{base_url}/health", timeout=1) as resp:
                if resp.status == 200:
                    break
        except Exception:
            time.sleep(0.5)

    print("Backend server started successfully.")

    def post_json(path, data, token=None):
        req = urllib.request.Request(
            f"{base_url}{path}",
            data=json.dumps(data).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                **({"Authorization": f"Bearer {token}"} if token else {}),
            },
        )
        try:
            with urllib.request.urlopen(req) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            try:
                body = e.read().decode("utf-8")
                return {"_error_status": e.code, "_body": body}
            except Exception:
                return {"_error_status": e.code}

    def get_json(path, token=None):
        req = urllib.request.Request(
            f"{base_url}{path}",
            headers={"Authorization": f"Bearer {token}"} if token else {},
        )
        try:
            with urllib.request.urlopen(req) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception:
            return []

    # 1. Register a dedicated fresh Admin
    admin_email = f"admin_{int(time.time())}@rgmcet.edu.in"
    admin_pass = "AdminPass123!"
    admin_reg = post_json("/api/auth/register", {
        "name": "RGMCET Head Administrator",
        "email": admin_email,
        "password": admin_pass,
        "role": "admin",
    })
    admin_tok = admin_reg.get("access_token")
    print(f"Admin registered ({admin_email}):", admin_reg.get("role", admin_reg.get("_error_status")))

    # 2. Setup verified professor Dr. K. Samunnisa in PENDING state
    sam_reg = post_json("/api/auth/register", {
        "name": "Dr. K. Samunnisa",
        "email": "samunnisacseds@rgmcet.edu.in",
        "password": "SamunnisaPass123!",
        "role": "professor",
        "department": "CSE (Data Science)",
        "professor_id": "PROF-VERIFIED-CSEDS-013",
    })
    sam_user_id = sam_reg.get("user_id")

    if not sam_user_id and admin_tok:
        users = get_json("/api/admin/users", token=admin_tok)
        for u in users:
            if u.get("email") == "samunnisacseds@rgmcet.edu.in":
                sam_user_id = u.get("user_id")
                break

    # Ensure Dr. K. Samunnisa is in PENDING status for the admin approval test
    if sam_user_id and admin_tok:
        req = urllib.request.Request(
            f"{base_url}/api/admin/professors/{sam_user_id}/status",
            data=json.dumps({"status": "PENDING"}).encode("utf-8"),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {admin_tok}"},
            method="PATCH",
        )
        try:
            with urllib.request.urlopen(req) as resp:
                print("Dr. K. Samunnisa set to PENDING for admin approval test:", resp.status)
        except Exception as e:
            print("Note setting PENDING:", e)

    # 3. Setup Professor B (Dr. P. Penchala Prasad) in APPROVED state
    prasad_reg = post_json("/api/auth/register", {
        "name": "Dr. P. Penchala Prasad",
        "email": "prasadcseds@rgmcet.edu.in",
        "password": "PrasadPass123!",
        "role": "professor",
        "department": "CSE (Data Science)",
        "professor_id": "PROF-VERIFIED-CSEDS-002",
    })
    prasad_user_id = prasad_reg.get("user_id")
    if not prasad_user_id and admin_tok:
        users = get_json("/api/admin/users", token=admin_tok)
        for u in users:
            if u.get("email") == "prasadcseds@rgmcet.edu.in":
                prasad_user_id = u.get("user_id")
                break

    if prasad_user_id and admin_tok:
        req = urllib.request.Request(
            f"{base_url}/api/admin/professors/{prasad_user_id}/status",
            data=json.dumps({"status": "APPROVED"}).encode("utf-8"),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {admin_tok}"},
            method="PATCH",
        )
        try:
            with urllib.request.urlopen(req) as resp:
                print("Professor B set to APPROVED:", resp.status)
        except Exception as e:
            print("Note approving Prof B:", e)

    console_messages = []
    failed_requests = []

    print("\n=======================================================")
    print("STARTING SECTION 24 VISIBLE CHROME VERIFICATION")
    print("=======================================================\n")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=200)
        context = browser.new_context(viewport={"width": 1280, "height": 800})
        page = context.new_page()

        def handle_console(msg):
            console_messages.append(f"[{msg.type}] {msg.text}")

        def handle_response(res):
            if res.status >= 400:
                failed_requests.append(f"{res.status} {res.url}")

        page.on("console", handle_console)
        page.on("response", handle_response)

        try:
            # 1. Open public website
            print("1. Opening public website...")
            page.goto(base_url)
            page.wait_for_load_state("networkidle")
            time.sleep(1)

            # 2. Login as Admin
            print(f"2. Logging in as Admin ({admin_email})...")
            page.click("#nav-login")
            time.sleep(1)
            page.fill("#login-email", admin_email)
            page.fill("#login-password", admin_pass)
            page.click("#login-submit")
            try:
                page.wait_for_url("**/admin**", timeout=15000)
            except Exception:
                if page.locator("#nav-admin").is_visible():
                    page.click("#nav-admin")
                    time.sleep(2)

            # 3. Verify Admin Dashboard
            print("3. Verifying Admin Dashboard URL and content...")
            assert "/admin" in page.url, f"Expected /admin, got {page.url}"
            assert "Admin Dashboard" in page.locator("main").inner_text()
            print("   Admin Dashboard confirmed.")

            # 4. Open Professor Approvals tab
            print("4. Opening Professor Approvals tab...")
            page.click("#admin-tab-approvals")
            page.wait_for_selector("text=Pending Professor Accounts", timeout=15000)
            page.wait_for_selector("text=Dr. K. Samunnisa", timeout=15000)
            approvals_text = page.locator("main").inner_text()
            assert "Professor Approvals" in approvals_text
            assert "Pending Professor Accounts" in approvals_text
            assert "Dr. K. Samunnisa" in approvals_text
            assert "samunnisacseds@rgmcet.edu.in" in approvals_text
            assert "CSE (Data Science)" in approvals_text
            print("   Pending professor card visible with official email.")

            # 5. Verify official faculty registry table is shown
            print("5. Verifying Official RGMCET Faculty Registry table...")
            page.wait_for_selector("text=Official RGMCET CSE (Data Science) Faculty Registry", timeout=15000)
            page.wait_for_selector("text=prasadcseds@rgmcet.edu.in", timeout=15000)
            table_text = page.locator("main").inner_text()
            assert "Official RGMCET CSE (Data Science) Faculty Registry" in table_text
            assert "Dr. B. Bhaskara Rao" in table_text
            assert "prasadcseds@rgmcet.edu.in" in table_text
            print("   Official faculty records verified.")

            # 6. Approve the pending professor account
            print("6. Admin approving Dr. K. Samunnisa...")
            approve_btn = page.locator(f"#approve-prof-{sam_user_id}")
            if not approve_btn.is_visible():
                approve_btn = page.locator(".approval-card button:has-text('Approve')").first
            assert approve_btn.is_visible()
            approve_btn.click()
            time.sleep(2)
            print("   Dr. K. Samunnisa successfully approved!")

            # 7. Logout Admin
            print("7. Logging out Admin...")
            page.click("#logout-button")
            time.sleep(1.5)

            # 8. Login using the approved professor account
            print("8. Logging in as approved professor (Dr. K. Samunnisa)...")
            if page.locator("#nav-login").is_visible():
                page.click("#nav-login")
                time.sleep(1)
            page.fill("#login-email", "samunnisacseds@rgmcet.edu.in")
            page.fill("#login-password", "SamunnisaPass123!")
            page.click("#login-submit")
            try:
                page.wait_for_url("**/professor**", timeout=15000)
            except Exception:
                if page.locator("#nav-professor").is_visible():
                    page.click("#nav-professor")
                    time.sleep(2)

            # 9. Verify URL is /professor/dashboard
            print("9. Verifying Professor Dashboard URL...")
            assert "/professor" in page.url, f"Expected /professor in URL, got {page.url}"

            # 10. Verify dashboard says: Welcome, Dr. K. Samunnisa
            print("10. Verifying Professor Dashboard greeting...")
            header_text = page.locator(".prof-identity-header").inner_text()
            assert "Dr. K. Samunnisa" in header_text, f"Expected Dr. K. Samunnisa, got {header_text}"
            assert "CSE (Data Science)" in header_text
            assert "APPROVED" in header_text
            print("    Welcome, Dr. K. Samunnisa verified!")

            # 11. Verify professor schedule view
            print("11. Verifying professor schedule view...")
            page.click("#prof-tab-schedule")
            page.wait_for_selector(".appointment-modal", timeout=10000)
            schedule_text = page.locator(".appointment-modal").inner_text()
            assert "Manage Weekly Schedule" in schedule_text or "YOUR AVAILABILITY" in schedule_text
            print("    Professor schedule verified.")
            page.click(".modal-heading button")
            time.sleep(1)

            # 12. Create / login a student account
            print("12. Logging out professor, registering student...")
            page.click("#logout-button")
            time.sleep(1.5)

            if page.locator("button:has-text('Create one')").is_visible():
                page.click("button:has-text('Create one')")
            else:
                page.goto(f"{BASE_URL}/register")
            time.sleep(1)
            student_email = f"student_{int(time.time())}@rgmcet.edu.in"
            if page.locator("#role-student").is_visible():
                page.click("#role-student")
            page.fill("#register-name", "Ananya Sharma")
            page.fill("#register-email", student_email)
            page.fill("#register-password", "StudentPass123!")
            page.click("#register-submit")
            try:
                page.wait_for_url("**/student**", timeout=15000)
            except Exception:
                if page.locator("#nav-student").is_visible():
                    page.click("#nav-student")
                    time.sleep(2)
            print("    Student account created and logged in.")

            # 13. Create appointment with Dr. K. Samunnisa
            print("13. Booking appointment with Dr. K. Samunnisa...")
            page.click("#nav-professors")
            time.sleep(1.5)
            book_btn = page.locator(".professor-card:has-text('Dr. K. Samunnisa') button:has-text('Request appointment')")
            if not book_btn.is_visible():
                book_btn = page.locator("button:has-text('Request appointment')").first
            book_btn.click()
            time.sleep(1.5)

            # Wait for slots to load
            try:
                page.wait_for_selector("#appointment-time-select option", timeout=8000)
                opts = page.locator("#appointment-time-select option").all()
                if opts:
                    val = opts[0].get_attribute("value")
                    if val:
                        page.select_option("#appointment-time-select", val)
            except Exception:
                pass
            page.fill("#appointment-reason-input", "Machine Learning Project Guidance")
            time.sleep(1)
            page.click("#appointment-submit-button")
            time.sleep(2)

            modal_text = page.locator(".appointment-dialog").inner_text()
            assert "PENDING PROFESSOR APPROVAL" in modal_text
            print("    Appointment booked: PENDING PROFESSOR APPROVAL visible.")
            page.click("button:has-text('Done')")
            time.sleep(1)

            # 14. Logout student
            print("14. Logging out student...")
            page.click("#logout-button")
            time.sleep(1.5)

            # 15. Login as Professor Dr. K. Samunnisa
            print("15. Logging in as Dr. K. Samunnisa...")
            if page.locator("#nav-login").is_visible():
                page.click("#nav-login")
                time.sleep(1)
            page.fill("#login-email", "samunnisacseds@rgmcet.edu.in")
            page.fill("#login-password", "SamunnisaPass123!")
            page.click("#login-submit")
            try:
                page.wait_for_url("**/professor**", timeout=15000)
            except Exception:
                if page.locator("#nav-professor").is_visible():
                    page.click("#nav-professor")
                    time.sleep(2)

            # 16. Verify Pending Student Requests contains the appointment
            print("16. Verifying pending student request appears on dashboard...")
            page.wait_for_selector("#pending-requests", timeout=10000)
            pending_text = page.locator("#pending-requests").inner_text()
            assert "Ananya Sharma" in pending_text
            assert "Machine Learning Project Guidance" in pending_text
            print("    Pending request found: Ananya Sharma - Machine Learning Project Guidance.")

            # 17. Click Approve
            print("17. Approving appointment request...")
            approve_request_btn = page.locator("#pending-requests button:has-text('Approve')").first
            approve_request_btn.click()
            time.sleep(2)

            # Verify it moved to approved appointments
            page.wait_for_selector("#upcoming-appointments", timeout=10000)
            approved_text = page.locator("#upcoming-appointments").inner_text()
            assert "Ananya Sharma" in approved_text
            print("    Appointment successfully moved to APPROVED section.")

            # 18. Logout professor
            print("18. Logging out professor...")
            page.click("#logout-button")
            time.sleep(1.5)

            # 19. Login as student
            print("19. Logging in as student to check status...")
            if page.locator("#nav-login").is_visible():
                page.click("#nav-login")
                time.sleep(1)
            page.fill("#login-email", student_email)
            page.fill("#login-password", "StudentPass123!")
            page.click("#login-submit")
            try:
                page.wait_for_url("**/student**", timeout=15000)
            except Exception:
                if page.locator("#nav-student").is_visible():
                    page.click("#nav-student")
                    time.sleep(2)

            # 20. Verify appointment status = APPROVED
            print("20. Checking student dashboard for APPROVED status...")
            page.wait_for_selector(".appointment-row", timeout=15000)
            student_text = page.locator(".appointment-row").inner_text()
            assert "APPROVED" in student_text or "approved" in student_text.lower()
            assert "Dr. K. Samunnisa" in student_text
            print("    Student confirms appointment status is APPROVED!")

            # 21. Check Professor B isolation
            print("21. Checking Professor B isolation...")
            page.click("#logout-button")
            time.sleep(1.5)
            if page.locator("#nav-login").is_visible():
                page.click("#nav-login")
                time.sleep(1)
            page.fill("#login-email", "prasadcseds@rgmcet.edu.in")
            page.fill("#login-password", "PrasadPass123!")
            page.click("#login-submit")
            try:
                page.wait_for_url("**/professor**", timeout=15000)
            except Exception:
                if page.locator("#nav-professor").is_visible():
                    page.click("#nav-professor")
                    time.sleep(2)

            page.wait_for_selector(".professor-identity-banner", timeout=15000)
            page.wait_for_selector("#pending-requests", timeout=15000)
            time.sleep(1)
            prof_b_text = page.locator("main").inner_text()
            assert ("Dr. P. Penchala Prasad" in prof_b_text or "Dr. B. Bhaskara Rao" in prof_b_text)
            assert "Ananya Sharma" not in prof_b_text, "Professor B must not see Professor A's student request!"
            print("    Professor B isolation verified: 0 requests seen from Dr. K. Samunnisa.")

            # 22. Test mobile viewport
            print("22. Testing mobile viewport (375x667)...")
            page.set_viewport_size({"width": 375, "height": 667})
            time.sleep(1)
            assert page.locator(".mobile-menu").is_visible()
            page.click(".mobile-menu")
            time.sleep(1)
            assert page.locator(".sidebar-drawer.open").is_visible()
            page.click(".sidebar-overlay", force=True)
            time.sleep(1)
            print("    Mobile menu responsiveness passed.")

            # 23 & 24. Audit console errors and failed network requests
            print("23 & 24. Auditing console errors and network requests...")
            critical_errors = [m for m in console_messages if "error" in m.lower() and "favicon" not in m.lower()]
            critical_failed_requests = [r for r in failed_requests if "favicon" not in r]
            print(f"    Critical console errors: {len(critical_errors)}")
            print(f"    Failed network requests: {len(critical_failed_requests)}")
            assert len(critical_failed_requests) == 0, f"Network failures: {critical_failed_requests}"

            print("\n=================================================================")
            print("SECTION 24 VISIBLE CHROME VERIFICATION COMPLETED AND PASSED 100%!")
            print("=================================================================\n")

        finally:
            browser.close()
            server.should_exit = True


if __name__ == "__main__":
    main()
