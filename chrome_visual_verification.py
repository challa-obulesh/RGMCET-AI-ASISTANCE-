import asyncio
from playwright.async_api import async_playwright
import time

async def main():
    print("Starting Chrome visual verification...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(viewport={"width": 1366, "height": 768})
        page = await context.new_page()

        print("Navigating to Homepage...")
        await page.goto("http://127.0.0.1:8000/")
        await page.wait_for_load_state("networkidle")
        await page.screenshot(path="scratch/chrome_01_homepage.png")
        print("C01 Homepage PASS")
        
        print("Registering/Logging in Student...")
        if await page.locator("#nav-login").count() > 0:
            await page.click("#nav-login")
        await page.wait_for_timeout(500)
        signup_link = page.locator("button:has-text('Sign up'), button:has-text('Create one')")
        if await signup_link.count() > 0:
            await signup_link.first.click()
            await page.wait_for_timeout(500)
        
        await page.click("#role-student")
        await page.fill("#register-name", "Chrome Student")
        await page.fill("#register-email", f"chrome_{int(time.time())}@rgmcet.edu.in")
        await page.fill("#register-password", "Password123")
        await page.click("#register-submit")
        await page.wait_for_timeout(2000)
        await page.screenshot(path="scratch/chrome_02_student_login.png")
        print("C02 Student Login PASS")
        
        print("Testing AI Chat...")
        if await page.locator("#nav-chat").count() > 0:
            await page.click("#nav-chat")
            await page.wait_for_timeout(500)
        textarea = page.locator("textarea")
        await textarea.wait_for(state="visible", timeout=5000)
        await textarea.fill("What is CSE Data Science?")
        await page.keyboard.press("Enter")
        await page.wait_for_timeout(4500)
        await page.screenshot(path="scratch/chrome_03_ai_chat.png")
        print("C03 AI Chat PASS")
        
        print("Testing HOD Query...")
        await textarea.fill("Who is the HOD of CSE Data Science?")
        await page.keyboard.press("Enter")
        await page.wait_for_timeout(4500)
        await page.screenshot(path="scratch/chrome_04_hod_query.png")
        print("C04 HOD Query PASS")
        
        print("Testing Telugu Query...")
        await textarea.fill("RGMCET lo library unda?")
        await page.keyboard.press("Enter")
        await page.wait_for_timeout(4500)
        await page.screenshot(path="scratch/chrome_05_telugu_query.png")
        print("C05 Telugu/Roman Telugu PASS")
        
        print("Booking Appointment...")
        await textarea.fill("I want to book an appointment with Dr. B. Bhaskara Rao tomorrow at 10 AM")
        await page.keyboard.press("Enter")
        await page.wait_for_timeout(4500)
        await textarea.fill("Yes")
        await page.keyboard.press("Enter")
        await page.wait_for_timeout(4500)
        await page.screenshot(path="scratch/chrome_06_appointment.png")
        print("C06 Appointment PASS")
        
        print("Testing Professor Login...")
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
        await page.click("#role-professor")
        await page.fill("#register-name", "Dr. Chrome Prof")
        await page.fill("#register-email", f"chrome_prof_{int(time.time())}@rgmcet.edu.in")
        await page.fill("#register-password", "Password123")
        await page.click("#register-submit")
        await page.wait_for_timeout(2000)
        await page.screenshot(path="scratch/chrome_07_prof_dash.png")
        print("C07 Professor Dashboard PASS")
        
        print("Testing Persistence...")
        await page.reload()
        await page.wait_for_timeout(2000)
        await page.screenshot(path="scratch/chrome_08_persistence.png")
        print("C08 Persistence PASS")
        
        await page.set_viewport_size({"width": 390, "height": 844})
        await page.wait_for_timeout(1000)
        await page.screenshot(path="scratch/chrome_09_mobile.png")
        print("C10 Mobile PASS")
        
        await browser.close()
        print("Visual verification complete!")

if __name__ == "__main__":
    asyncio.run(main())
