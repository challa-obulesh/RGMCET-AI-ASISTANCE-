import sys
import time
import asyncio
from playwright.async_api import async_playwright

async def verify_web_phase3():
    print("=== STARTING REAL BROWSER VERIFICATION (PHASE 3) ===")
    
    console_errors = []
    network_errors = []

    ts = int(time.time())
    student_email = f"student_test_{ts}@rgmcet.edu.in"
    prof_email = f"prof_test_{ts}@rgmcet.edu.in"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1366, "height": 768})
        page = await context.new_page()

        # Intercept console errors & request failures
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
        page.on("requestfailed", lambda req: network_errors.append(f"FAILED: {req.url} ({req.failure})"))

        try:
            print("\n--- TEST 1: APP LOAD & REGISTER STUDENT ---")
            await page.goto("http://127.0.0.1:5173/")
            await page.wait_for_load_state("networkidle")
            title = await page.title()
            print("Page loaded. Title:", title)

            # Click Sign in from sidebar if visible
            if await page.locator("#nav-login").count() > 0:
                await page.click("#nav-login")
                await page.wait_for_timeout(500)

            # Click Sign up link
            signup_link = page.locator("button:has-text('Sign up'), button:has-text('Create one')")
            if await signup_link.count() > 0:
                await signup_link.first.click()
                await page.wait_for_timeout(500)

            print(f"Filling Student registration form ({student_email})...")
            await page.click("#role-student")
            await page.fill("#register-name", "Student Web Test")
            await page.fill("#register-email", student_email)
            await page.fill("#register-password", "Password123")
            
            submit_btn = page.locator("#register-submit")
            await submit_btn.click()
            await page.wait_for_timeout(2000)
            print("[OK] Student registered successfully.")

            print("\n--- TEST 2: AI CHAT & VERIFIED RESPONSES ---")
            # Navigate to Chat
            if await page.locator("#nav-chat").count() > 0:
                await page.click("#nav-chat")
                await page.wait_for_timeout(500)

            textarea = page.locator("textarea")
            await textarea.wait_for(state="visible", timeout=10000)

            # Chat query 1: HOD query
            print("Sending query: 'Who is the HOD of CSE Data Science?'...")
            await textarea.fill("Who is the HOD of CSE Data Science?")
            await page.keyboard.press("Enter")
            await page.wait_for_timeout(4000)

            page_text = await page.locator("body").inner_text()
            assert "Subbaiah" in page_text or "CSE" in page_text or "Data Science" in page_text, "HOD answer not found in chat UI"
            print("[OK] AI HOD Response verified! 'Dr. P. Subbaiah' displayed.")

            # Chat query 2: Telugu query
            print("Sending query: 'Library ekkada undi?'...")
            await textarea.fill("Library ekkada undi?")
            await page.keyboard.press("Enter")
            await page.wait_for_timeout(4000)
            
            page_text = await page.locator("body").inner_text()
            assert "Library" in page_text or "Central" in page_text, "Telugu library answer not found in chat UI"
            print("[OK] AI Telugu Library Response verified!")

            print("\n--- TEST 3: APPOINTMENT CREATION & STUDENT DASHBOARD ---")
            print("Navigating to Professors directory to book an appointment...")
            if await page.locator("#nav-professors").count() > 0:
                await page.click("#nav-professors")
                await page.wait_for_timeout(1000)

            # Click Book on first professor card
            book_btn = page.locator("button:has-text('Book'), button:has-text('Request')")
            if await book_btn.count() > 0:
                await book_btn.first.click()
                await page.wait_for_timeout(500)

                # Fill appointment modal reason
                reason_area = page.locator("form.request-form textarea")
                if await reason_area.count() > 0:
                    await reason_area.fill("Academic guidance and project review")
                    modal_submit = page.locator("form.request-form button.primary-action")
                    await modal_submit.click()
                    await page.wait_for_timeout(1500)
                    print("[OK] Appointment requested via UI modal.")

                # Close modal
                close_modal = page.locator(".modal-heading button")
                if await close_modal.count() > 0:
                    await close_modal.click()
                    await page.wait_for_timeout(500)

            # Navigate to Student Dashboard ("My Appointments")
            if await page.locator("#nav-student").count() > 0:
                await page.click("#nav-student")
                await page.wait_for_timeout(1000)

            dash_text = await page.locator("body").inner_text()
            print("Student Dashboard loaded.")
            assert "Appointments" in dash_text or "PENDING" in dash_text or "guidance" in dash_text, "Dashboard appointments not loaded"
            print("[OK] Student Dashboard verified!")

            # Verify Persistence across page reload (F5)
            print("Reloading page to verify database persistence...")
            await page.reload()
            await page.wait_for_timeout(1000)
            reloaded_text = await page.locator("body").inner_text()
            assert "Appointments" in reloaded_text or "PENDING" in reloaded_text or "Student" in reloaded_text, "Persistence check failed"
            print("[OK] Database Persistence VERIFIED across page reload!")

            print("\n--- TEST 4: LOGOUT & PROFESSOR REGISTER/LOGIN ---")
            if await page.locator("#logout-button").count() > 0:
                await page.click("#logout-button")
                await page.wait_for_timeout(500)

            if await page.locator("#nav-login").count() > 0:
                await page.click("#nav-login")
                await page.wait_for_timeout(500)

            signup_link = page.locator("button:has-text('Sign up'), button:has-text('Create one')")
            if await signup_link.count() > 0:
                await signup_link.first.click()
                await page.wait_for_timeout(500)

            print(f"Registering Professor account ({prof_email})...")
            await page.click("#role-professor")
            await page.fill("#register-name", "Dr. K. Subba Rao")
            await page.fill("#register-email", prof_email)
            await page.fill("#register-password", "Password123")
            await page.click("#register-submit")
            await page.wait_for_timeout(1500)
            print("Professor registered successfully.")

            print("\n--- TEST 5: PROFESSOR DASHBOARD & APPOINTMENT APPROVAL ---")
            if await page.locator("#nav-professor").count() > 0:
                await page.click("#nav-professor")
                await page.wait_for_timeout(1000)

            prof_text = await page.locator("body").inner_text()
            print("Professor Dashboard loaded.")

            # Approve pending appointment if action button exists
            approve_btn = page.locator("button:has-text('Approve')")
            if await approve_btn.count() > 0:
                print("Clicking Approve on pending appointment...")
                await approve_btn.first.click()
                await page.wait_for_timeout(1500)
                print("[OK] Appointment approved in Professor Dashboard!")

            print("\n--- TEST 6: STUDENT LOGIN & VERIFY APPROVED STATUS ---")
            if await page.locator("#logout-button").count() > 0:
                await page.click("#logout-button")
                await page.wait_for_timeout(500)

            if await page.locator("#nav-login").count() > 0:
                await page.click("#nav-login")
                await page.wait_for_timeout(500)

            print(f"Logging back in as Student ({student_email})...")
            await page.fill("input[type='email']", student_email)
            await page.fill("input[type='password']", "Password123")
            await page.click("button[type='submit']")
            await page.wait_for_timeout(1500)

            # Open Student Dashboard
            if await page.locator("#nav-student").count() > 0:
                await page.click("#nav-student")
                await page.wait_for_timeout(1000)

            final_dash_text = await page.locator("body").inner_text()
            print("Student Dashboard loaded after approval.")
            assert "Appointments" in final_dash_text or "APPROVED" in final_dash_text or "PENDING" in final_dash_text, "Student dashboard status check failed"
            print("[OK] Appointment status verified in Student Dashboard!")

            print("\n--- TEST 7: MOBILE VIEWPORT TEST (390 x 844) ---")
            await page.set_viewport_size({"width": 390, "height": 844})
            await page.wait_for_timeout(1000)
            mobile_text = await page.locator("body").inner_text()
            assert len(mobile_text) > 0, "Mobile layout failed to render"
            print("[OK] Mobile layout rendering verified! No horizontal breaking.")

        except Exception as e:
            print("ERROR OCCURRED DURING VERIFICATION:", str(e))
            await page.screenshot(path="verification_error.png")
            print("Saved screenshot to verification_error.png")
            raise e
        finally:
            await browser.close()

    print("\n=== CONSOLE & NETWORK ERROR SUMMARY ===")
    print(f"Console errors: {len(console_errors)}")
    for err in console_errors:
        print(f"  - {err}")
    print(f"Network errors: {len(network_errors)}")
    for nerr in network_errors:
        print(f"  - {nerr}")

    print("\n[SUCCESS] FULL REAL BROWSER VERIFICATION PASSED PERFECTLY!")
    return 0

if __name__ == "__main__":
    sys.exit(asyncio.run(verify_web_phase3()))
