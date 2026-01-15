"""
AI Uploader Module for MVoice Automation

This module handles uploading videos to the AI platform and getting responses.
Can be run independently.

Usage:
    python ai_uploader.py [--video VIDEO_PATH] [--prompt PROMPT] [--all] [--headless]
"""
import asyncio
import argparse
from pathlib import Path
from typing import Optional, List, Tuple

from playwright.async_api import async_playwright, Page, Browser

from config import (
    AI_URL,
    DEFAULT_PROMPT,
    BROWSER_HEADLESS,
    SLOW_MO,
    TIMEOUT,
    DOWNLOADS_DIR,
    AUTH_STATE_FILE
)
from utils import (
    logger,
    append_result_to_csv_parsed,
    get_downloaded_videos,
    get_processed_urls,
    clean_message,
    get_unique_urls,
    get_video_path,
    migrate_old_output_format
)


class AIUploader:
    """
    Handles uploading videos to AI platform and extracting responses.
    """
    
    def __init__(self, headless: bool = BROWSER_HEADLESS, prompt: str = DEFAULT_PROMPT):
        self.headless = headless
        self.prompt = prompt
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.context = None
        
    async def __aenter__(self):
        await self.start()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
        
    async def start(self):
        """Initialize the browser and load saved session if available."""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            slow_mo=SLOW_MO
        )
        
        # Load saved auth state if exists
        if AUTH_STATE_FILE.exists():
            logger.info("Loading saved login session...")
            self.context = await self.browser.new_context(storage_state=str(AUTH_STATE_FILE))
        else:
            logger.info("No saved session found, will need to login")
            self.context = await self.browser.new_context()
        
        self.page = await self.context.new_page()
        logger.info("Browser started for AI upload")
        
    async def close(self):
        """Close the browser."""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        logger.info("Browser closed")
    
    async def save_session(self):
        """Save current browser session/cookies for future use."""
        if self.context:
            await self.context.storage_state(path=str(AUTH_STATE_FILE))
            logger.info(f"Session saved to {AUTH_STATE_FILE}")
    
    async def login(self):
        """
        Navigate to AI platform and wait for user to complete Okta login.
        After login, save the session for future use.
        """
        logger.info("Starting login process...")
        logger.info(f"Navigating to {AI_URL}")
        
        await self.page.goto(AI_URL, timeout=TIMEOUT * 2)
        
        print("\n" + "="*60)
        print("LOGIN REQUIRED")
        print("="*60)
        print("Browser telah dibuka. Silakan login via Okta.")
        print("Setelah berhasil login dan halaman AI terbuka,")
        print("tekan ENTER di terminal ini untuk menyimpan session...")
        print("="*60 + "\n")
        
        # Wait for user to complete login
        input("Tekan ENTER setelah login berhasil...")
        
        # Save the session
        await self.save_session()
        
        print("\n✓ Session berhasil disimpan!")
        print("  Selanjutnya tidak perlu login lagi.\n")
        
        return True
    
    async def check_login_status(self) -> bool:
        """
        Check if we're logged in by navigating to AI URL and checking for login page.
        
        Returns:
            True if logged in, False if need to login
        """
        try:
            await self.page.goto(AI_URL, timeout=TIMEOUT)
            await self.page.wait_for_timeout(3000)
            
            # Check for common login page indicators
            login_indicators = [
                'okta',
                'login',
                'sign in',
                'sign-in',
                'authenticate'
            ]
            
            current_url = self.page.url.lower()
            
            # If URL contains login indicators, we need to login
            for indicator in login_indicators:
                if indicator in current_url:
                    logger.info("Login required - redirected to login page")
                    return False
            
            # Also check page content for login forms
            try:
                login_form = await self.page.locator('input[type="password"]').is_visible(timeout=2000)
                if login_form:
                    logger.info("Login required - password field detected")
                    return False
            except Exception:
                pass
            
            logger.info("Already logged in!")
            return True
            
        except Exception as e:
            logger.warning(f"Error checking login status: {e}")
            return False
    
    async def navigate_to_ai(self):
        """Navigate to the AI platform."""
        logger.info(f"Navigating to {AI_URL}")
        await self.page.goto(AI_URL, timeout=TIMEOUT)
        await self.page.wait_for_load_state("networkidle", timeout=TIMEOUT)
        logger.info("AI platform loaded")
    
    async def set_reasoning_minimal(self) -> bool:
        """
        Set reasoning level to Minimal for faster responses.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info("Setting reasoning level to Minimal...")
            
            # Click on "Reasoning Level" button (brain icon)
            # Using specific attributes from the actual button
            reasoning_selectors = [
                '#reasoning-selector-button',
                '[data-testid="reasoning-selector-trigger-button"]',
                '[aria-label="Reasoning level"]',
                'button[id="reasoning-selector-button"]',
            ]
            
            clicked = False
            for selector in reasoning_selectors:
                try:
                    element = self.page.locator(selector).first
                    if await element.is_visible(timeout=2000):
                        await element.click()
                        clicked = True
                        logger.info("Clicked Reasoning Level button")
                        await self.page.wait_for_timeout(1000)
                        break
                except Exception:
                    continue
            
            if not clicked:
                logger.warning("Could not find Reasoning Level button")
                return False
            
            # Click on "Minimal" option in the dropdown
            minimal_selectors = [
                '[data-testid*="minimal"]',
                'div:has-text("Minimal")',
                'span:has-text("Minimal")',
                '[role="option"]:has-text("Minimal")',
                '[role="menuitem"]:has-text("Minimal")',
                'button:has-text("Minimal")',
                'li:has-text("Minimal")',
                'label:has-text("Minimal")',
            ]
            
            for selector in minimal_selectors:
                try:
                    elements = self.page.locator(selector)
                    count = await elements.count()
                    for i in range(count):
                        element = elements.nth(i)
                        if await element.is_visible(timeout=1000):
                            await element.click()
                            logger.info("✓ Set reasoning to Minimal")
                            await self.page.wait_for_timeout(500)
                            return True
                except Exception:
                    continue
            
            # Close dropdown if Minimal not found
            logger.warning("Could not find Minimal option")
            await self.page.keyboard.press("Escape")
            return False
            
        except Exception as e:
            logger.error(f"Error setting reasoning level: {e}")
            return False
    
    async def upload_video(self, video_path: Path) -> bool:
        """
        Upload a video file to the AI platform.
        
        Args:
            video_path: Path to video file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Look for upload button/area
            upload_selectors = [
                'button:has-text("upload")',
                'button:has-text("Upload")',
                '[aria-label*="upload"]',
                '[aria-label*="Upload"]',
                'input[type="file"]',
                '.upload-button',
                '[data-testid="upload"]',
                'label:has-text("Upload")',
                'div:has-text("Upload files")'
            ]
            
            # First try to find and click upload button
            for selector in upload_selectors:
                try:
                    element = self.page.locator(selector).first
                    if await element.is_visible(timeout=2000):
                        # Check if it's a file input
                        if selector == 'input[type="file"]':
                            await element.set_input_files(str(video_path))
                            logger.info(f"Uploaded video via file input: {video_path}")
                            return True
                        else:
                            await element.click()
                            await self.page.wait_for_timeout(1000)
                            break
                except Exception:
                    continue
            
            # After clicking upload button, look for file input
            file_input = self.page.locator('input[type="file"]').first
            if await file_input.count() > 0:
                await file_input.set_input_files(str(video_path))
                logger.info(f"Uploaded video: {video_path}")
                return True
            
            logger.warning("Could not find upload mechanism")
            return False
            
        except Exception as e:
            logger.error(f"Error uploading video: {e}")
            return False
    
    async def send_prompt(self, prompt: str) -> bool:
        """
        Send a prompt to the AI.
        
        Args:
            prompt: Text prompt to send
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Look for text input/textarea
            input_selectors = [
                'textarea',
                'input[type="text"]',
                '[contenteditable="true"]',
                '.message-input',
                '[placeholder*="message"]',
                '[placeholder*="Message"]',
                '[data-testid="text-input"]'
            ]
            
            for selector in input_selectors:
                try:
                    element = self.page.locator(selector).first
                    if await element.is_visible(timeout=2000):
                        await element.fill(prompt)
                        logger.info("Prompt entered")
                        
                        # Look for send button
                        send_selectors = [
                            'button[type="submit"]',
                            'button:has-text("Send")',
                            'button:has-text("send")',
                            '[aria-label*="send"]',
                            '[aria-label*="Send"]',
                            '.send-button',
                            'button svg',  # Icon button
                        ]
                        
                        for send_selector in send_selectors:
                            try:
                                send_btn = self.page.locator(send_selector).first
                                if await send_btn.is_visible(timeout=1000):
                                    await send_btn.click()
                                    logger.info("Prompt sent")
                                    return True
                            except Exception:
                                continue
                        
                        # Try pressing Enter if no button found
                        await element.press("Enter")
                        logger.info("Prompt sent via Enter key")
                        return True
                        
                except Exception:
                    continue
            
            logger.warning("Could not find prompt input")
            return False
            
        except Exception as e:
            logger.error(f"Error sending prompt: {e}")
            return False
    
    async def wait_for_response(self, timeout: int = 180000) -> Optional[str]:
        """
        Wait for and extract AI response.
        
        Args:
            timeout: Maximum wait time in milliseconds
            
        Returns:
            AI response text or None
        """
        try:
            # Wait for response to appear
            logger.info("Waiting for AI response...")
            
            # Placeholder/loading texts to ignore
            loading_texts = [
                'ai reasoning',
                'thinking',
                'generating',
                'loading',
                'processing',
            ]
            
            # Incomplete response indicators (table header without data)
            incomplete_indicators = [
                'metricsvalue',  # Table header without separator
                'metrics value',
                'here\'s the analysis of the video: metricsvalue',
                'here\'s the analysis',
            ]
            
            # End indicators - response should contain these to be considered complete
            end_indicators = [
                'target surprise',  # Last metric in the prompt
                'uniqueness of concept',
                'execution style',
                'messaging // messaging summary',
                'meaningful & different',
            ]
            
            # Look for response container
            response_selectors = [
                '.assistant-message',
                '.ai-response',
                '.message-content',
                '[data-role="assistant"]',
                '.response-text',
                '.chat-message:last-child',
                'div[class*="response"]',
                'div[class*="message"]:last-of-type',
                '[class*="markdown"]',
                '[class*="prose"]',
            ]
            
            # Wait for initial response to appear
            await self.page.wait_for_timeout(5000)
            
            # Track response stability
            last_text = ""
            stable_count = 0
            required_stable = 5  # Response must be stable for 5 consecutive checks (10 seconds)
            
            # Poll until we get actual content (not loading text)
            max_attempts = 300  # 10 minutes max (300 * 2 seconds)
            
            for attempt in range(max_attempts):
                current_text = ""
                
                # Try each selector
                for selector in response_selectors:
                    try:
                        elements = self.page.locator(selector)
                        count = await elements.count()
                        
                        if count > 0:
                            # Get the last element (most recent response)
                            last_element = elements.last
                            text = await last_element.text_content()
                            
                            if text and len(text) > len(current_text):
                                current_text = text
                                    
                    except Exception:
                        continue
                
                if current_text:
                    text_lower = current_text.lower().strip()
                    
                    # Check if it's still loading/reasoning
                    is_loading = any(lt in text_lower for lt in loading_texts)
                    
                    # Check if response is incomplete (just header, no data)
                    is_incomplete = any(inc in text_lower for inc in incomplete_indicators) and len(current_text.strip()) < 200
                    
                    # Check if response contains end indicators (complete response)
                    has_end_indicator = any(end in text_lower for end in end_indicators)
                    
                    # Check if response is stable (same as last check)
                    if current_text == last_text and len(current_text) > 500:
                        stable_count += 1
                    else:
                        stable_count = 0
                    
                    last_text = current_text
                    
                    # Response is complete if:
                    # 1. Not loading
                    # 2. Not incomplete header only
                    # 3. Has end indicator OR is stable for several checks
                    # 4. Minimum length
                    is_complete = (
                        not is_loading and 
                        not is_incomplete and 
                        len(current_text.strip()) > 800 and  # Substantial response
                        (has_end_indicator or stable_count >= required_stable)
                    )
                    
                    if is_complete:
                        logger.info(f"Response complete (attempt {attempt + 1}, {len(current_text)} chars, stable={stable_count})")
                        return clean_message(current_text)
                
                # Log progress every 10 attempts
                if attempt % 10 == 0 and attempt > 0:
                    logger.info(f"Waiting for complete response... (attempt {attempt}, chars={len(current_text)}, stable={stable_count})")
                
                await self.page.wait_for_timeout(2000)
            
            # Timeout reached - get whatever we have but warn
            logger.warning("Timeout waiting for complete response, getting available content...")
            
            if last_text and len(last_text) > 500:
                logger.warning(f"Returning potentially incomplete response ({len(last_text)} chars)")
                return clean_message(last_text)
            
            logger.warning("Could not extract response")
            return None
            
        except Exception as e:
            logger.error(f"Error waiting for response: {e}")
            return None
    
    async def is_response_complete(self, text: str) -> bool:
        """
        Check if response appears complete.
        
        Args:
            text: Response text
            
        Returns:
            True if response appears complete
        """
        if not text:
            return False
        
        # If response is very long, consider it complete (AI finished generating)
        if len(text) > 2000:
            return True
        
        if len(text) < 500:
            return False
        
        text_lower = text.lower()
        
        # Check for end indicators
        end_indicators = [
            'target surprise',
            'uniqueness of concept', 
            'execution style',
            'meaningful & different',
            'authenticity',
        ]
        
        has_end = any(ind in text_lower for ind in end_indicators)
        
        # Check for truncation indicators
        truncation_signs = [
            text.rstrip().endswith('-'),
            text.rstrip().endswith('**'),
            text.rstrip().endswith(':'),
        ]
        
        is_truncated = any(truncation_signs)
        
        # Complete if has end indicator and not truncated, OR if long enough
        return (has_end and not is_truncated) or len(text) > 1500
    
    async def process_video(self, url: str, video_path: Path, max_retries: int = 2) -> Optional[str]:
        """
        Process a single video: upload, prompt, and get response.
        
        Args:
            url: Original video URL
            video_path: Path to downloaded video
            max_retries: Maximum number of retries if response is incomplete
            
        Returns:
            AI response message or None
        """
        for retry in range(max_retries + 1):
            try:
                if retry > 0:
                    logger.info(f"Retry {retry}/{max_retries} for {video_path.name}")
                
                # Navigate to fresh page
                await self.navigate_to_ai()
                await self.page.wait_for_timeout(2000)
                
                # Set reasoning level to Minimal for faster response
                await self.set_reasoning_minimal()
                await self.page.wait_for_timeout(500)
                
                # Upload video
                success = await self.upload_video(video_path)
                if not success:
                    logger.error(f"Failed to upload video: {video_path}")
                    continue
                
                # Wait for upload to complete
                await self.page.wait_for_timeout(3000)
                
                # Send prompt
                success = await self.send_prompt(self.prompt)
                if not success:
                    logger.error("Failed to send prompt")
                    continue
                
                # Wait for response
                response = await self.wait_for_response()
                
                if response:
                    # Check if response is complete
                    if await self.is_response_complete(response):
                        # Save result (parsed into columns)
                        append_result_to_csv_parsed(url, response)
                        logger.info(f"✓ Processed video: {url}")
                        return response
                    else:
                        logger.warning(f"Response appears incomplete ({len(response)} chars), will retry...")
                        if retry < max_retries:
                            continue
                        else:
                            # Last retry - save whatever we have
                            logger.warning("Max retries reached, saving potentially incomplete response")
                            append_result_to_csv_parsed(url, response)
                            return response
                
            except Exception as e:
                logger.error(f"Error processing video {video_path}: {e}")
                if retry < max_retries:
                    await asyncio.sleep(3)
                    continue
        
        logger.error(f"Failed to process video after {max_retries + 1} attempts: {url}")
        return None
    
    async def process_all_pending(self) -> dict:
        """
        Process all downloaded videos that haven't been processed yet.
        
        Returns:
            Dictionary with results
        """
        results = {
            'successful': [],
            'failed': [],
            'skipped': []
        }
        
        # Get all URLs and their corresponding video paths
        all_urls = get_unique_urls()
        processed_urls = get_processed_urls()
        
        pending = []
        for i, url in enumerate(all_urls):
            if url in processed_urls:
                results['skipped'].append(url)
                continue
            
            video_path = get_video_path(url, i)
            if video_path.exists():
                pending.append((url, video_path))
            else:
                logger.warning(f"Video not downloaded for: {url}")
        
        logger.info(f"Processing {len(pending)} pending videos")
        
        for url, video_path in pending:
            response = await self.process_video(url, video_path)
            
            if response:
                results['successful'].append({
                    'url': url,
                    'message': response[:100] + '...' if len(response) > 100 else response
                })
            else:
                results['failed'].append(url)
            
            # Rate limiting
            await asyncio.sleep(5)
        
        return results


async def main():
    """Main function for standalone execution."""
    parser = argparse.ArgumentParser(description='Upload videos to AI platform and get responses')
    parser.add_argument('--video', type=str, help='Specific video file to process')
    parser.add_argument('--url', type=str, help='Original URL for the video')
    parser.add_argument('--prompt', type=str, default=DEFAULT_PROMPT, help='Custom prompt for AI')
    parser.add_argument('--all', action='store_true', help='Process all pending videos')
    parser.add_argument('--headless', action='store_true', help='Run browser in headless mode')
    parser.add_argument('--login', action='store_true', help='Force login and save session')
    parser.add_argument('--clear-session', action='store_true', help='Clear saved session')
    
    args = parser.parse_args()
    
    # Migrate old output format if needed (runs once automatically)
    migrate_old_output_format()
    
    # Clear session if requested
    if args.clear_session:
        if AUTH_STATE_FILE.exists():
            AUTH_STATE_FILE.unlink()
            print("✓ Session cleared!")
        else:
            print("No session to clear.")
        return
    
    # Force non-headless for login
    headless = False if args.login else args.headless
    
    async with AIUploader(headless=headless, prompt=args.prompt) as uploader:
        
        # Login mode
        if args.login:
            await uploader.login()
            return
        
        # Check if we need to login first
        is_logged_in = await uploader.check_login_status()
        
        if not is_logged_in:
            print("\n" + "="*60)
            print("SESSION EXPIRED atau BELUM LOGIN")
            print("="*60)
            print("Jalankan dulu: python ai_uploader.py --login")
            print("="*60 + "\n")
            return
        
        if args.video:
            # Process single video
            video_path = Path(args.video)
            if not video_path.exists():
                logger.error(f"Video file not found: {args.video}")
                return
            
            url = args.url or str(video_path)
            response = await uploader.process_video(url, video_path)
            
            if response:
                print("\n" + "="*50)
                print("AI RESPONSE")
                print("="*50)
                print(response)
                print("="*50)
        else:
            # Process all pending
            results = await uploader.process_all_pending()
            
            # Print summary
            print("\n" + "="*50)
            print("PROCESSING SUMMARY")
            print("="*50)
            print(f"Successful: {len(results['successful'])}")
            print(f"Failed: {len(results['failed'])}")
            print(f"Skipped (already processed): {len(results['skipped'])}")
            print("="*50)


if __name__ == "__main__":
    asyncio.run(main())
