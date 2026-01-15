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
    append_result_to_csv,
    get_downloaded_videos,
    get_processed_urls,
    clean_message,
    get_unique_urls,
    get_video_path
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
    
    async def wait_for_response(self, timeout: int = 120000) -> Optional[str]:
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
            
            # Look for response container
            response_selectors = [
                '.assistant-message',
                '.ai-response',
                '.message-content',
                '[data-role="assistant"]',
                '.response-text',
                '.chat-message:last-child',
                'div[class*="response"]',
                'div[class*="message"]:last-of-type'
            ]
            
            # Wait for loading to complete
            await self.page.wait_for_timeout(5000)  # Initial wait
            
            # Check for loading indicators
            loading_selectors = [
                '.loading',
                '[class*="loading"]',
                '[class*="spinner"]',
                '.typing-indicator'
            ]
            
            for _ in range(60):  # Wait up to 2 minutes
                is_loading = False
                for selector in loading_selectors:
                    try:
                        if await self.page.locator(selector).is_visible(timeout=500):
                            is_loading = True
                            break
                    except Exception:
                        pass
                
                if not is_loading:
                    break
                    
                await self.page.wait_for_timeout(2000)
            
            # Extract response text
            await self.page.wait_for_timeout(2000)  # Extra wait for rendering
            
            for selector in response_selectors:
                try:
                    elements = self.page.locator(selector)
                    count = await elements.count()
                    if count > 0:
                        # Get the last message (most recent response)
                        last_element = elements.last
                        text = await last_element.text_content()
                        if text and len(text) > 10:
                            logger.info("Response extracted successfully")
                            return clean_message(text)
                except Exception:
                    continue
            
            # Fallback: try to get any visible text that looks like a response
            try:
                body_text = await self.page.locator('main, .main-content, .chat-container').text_content()
                if body_text:
                    return clean_message(body_text[-5000:])  # Last 5000 chars
            except Exception:
                pass
            
            logger.warning("Could not extract response")
            return None
            
        except Exception as e:
            logger.error(f"Error waiting for response: {e}")
            return None
    
    async def process_video(self, url: str, video_path: Path) -> Optional[str]:
        """
        Process a single video: upload, prompt, and get response.
        
        Args:
            url: Original video URL
            video_path: Path to downloaded video
            
        Returns:
            AI response message or None
        """
        try:
            # Navigate to fresh page
            await self.navigate_to_ai()
            await self.page.wait_for_timeout(2000)
            
            # Upload video
            success = await self.upload_video(video_path)
            if not success:
                logger.error(f"Failed to upload video: {video_path}")
                return None
            
            # Wait for upload to complete
            await self.page.wait_for_timeout(3000)
            
            # Send prompt
            success = await self.send_prompt(self.prompt)
            if not success:
                logger.error("Failed to send prompt")
                return None
            
            # Wait for response
            response = await self.wait_for_response()
            
            if response:
                # Save result
                append_result_to_csv(url, response)
                logger.info(f"Processed video: {url}")
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing video {video_path}: {e}")
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
