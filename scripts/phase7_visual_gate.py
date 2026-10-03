import asyncio
from playwright.async_api import async_playwright

async def run_visual_verification():
    print("Starting VISIBLE Chrome verification for Phase 7 Gate...")
    async with async_playwright() as p:
        # Launch visible Chrome
        browser = await p.chromium.launch(headless=False, slow_mo=500)
        page = await browser.new_page()
        
        print("Navigating to http://127.0.0.1:5173")
        await page.goto("http://127.0.0.1:5173")
        
        print("Logging in as student...")
        await page.fill('input[type="text"]', '21091A0501')
        await page.fill('input[type="password"]', 'pass')
        await page.click('button[type="submit"]')
        
        await page.wait_for_selector('.chat-view')
        print("Logged in successfully. Sending RAG query...")
        
        await page.fill('.composer textarea', 'What is CSE Data Science?')
        await page.click('.send-button')
        
        # Wait for the AI response and RAG sources to appear
        await page.wait_for_selector('.message.ai', timeout=15000)
        await page.wait_for_selector('.message-sources', timeout=15000)
        
        print("RAG sources rendered successfully! Taking proof screenshot...")
        await page.screenshot(path="phase7_rag_proof.png")
        
        print("Waiting a bit so the human can see it...")
        await asyncio.sleep(5)
        
        print("Sending Telugu query...")
        await page.fill('.composer textarea', 'college lo ye departments unnayi?')
        await page.click('.send-button')
        
        await asyncio.sleep(5)
        
        await browser.close()
        print("Verification complete. Proof saved to phase7_rag_proof.png.")

if __name__ == "__main__":
    asyncio.run(run_visual_verification())
