import asyncio
from playwright.async_api import async_playwright
from config import AI_URL, AUTH_STATE_FILE

async def debug():
    p = await async_playwright().start()
    browser = await p.chromium.launch(headless=False)
    context = await browser.new_context(storage_state=str(AUTH_STATE_FILE))
    page = await context.new_page()
    
    await page.goto(AI_URL)
    await page.wait_for_load_state('networkidle')
    await page.wait_for_timeout(3000)
    
    # Find ALL clickable elements near bottom of page (where input area is)
    print('=== ALL BUTTONS (full list) ===')
    buttons = await page.locator('button').all()
    for i, btn in enumerate(buttons):
        try:
            text = await btn.text_content()
            aria = await btn.get_attribute('aria-label')
            title = await btn.get_attribute('title')
            print(f'{i}: text="{text.strip()[:40] if text else ""}" aria="{aria}" title="{title}"')
        except: pass
    
    print('\n=== ELEMENTS NEAR GEMINI BUTTON ===')
    # Find elements near Gemini button (siblings/nearby)
    gemini_btn = page.locator('button:has-text("Gemini")').first
    try:
        parent = gemini_btn.locator('..')
        siblings = await parent.locator('button, div[role="button"], span[role="button"]').all()
        print(f'Found {len(siblings)} sibling elements:')
        for i, sib in enumerate(siblings):
            text = await sib.text_content()
            print(f'  {i}: "{text.strip()[:50] if text else ""}"')
    except Exception as e:
        print(f'Error: {e}')
    
    print('\n=== SEARCH: tools, setting, level ===')
    for kw in ['tool', 'setting', 'level', 'reason']:
        elements = page.locator(f'button:has-text("{kw}"), div:has-text("{kw}"), span:has-text("{kw}")')
        count = await elements.count()
        print(f'"{kw}": {count} elements')
        for i in range(min(count, 3)):
            el = elements.nth(i)
            text = await el.text_content()
            tag = await el.evaluate('el => el.tagName')
            print(f'  {tag}: "{text.strip()[:60] if text else ""}"')
    
    print('\n\nBrowser tetap terbuka untuk manual inspect.')
    input('Press Enter to close...')
    
    await browser.close()
    await p.stop()

asyncio.run(debug())