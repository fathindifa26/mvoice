"""
Video Downloader Module for MVoice Automation

This module handles downloading videos from TikTok and Instagram.
Can be run independently.

Usage:
    python downloader.py [--urls URL1 URL2 ...] [--all] [--headless]
"""
import asyncio
import argparse
import time
from pathlib import Path
from typing import List, Optional

from playwright.async_api import async_playwright, Page, Browser

from config import (
    DOWNLOADS_DIR, 
    BROWSER_HEADLESS, 
    SLOW_MO, 
    TIMEOUT,
    MAX_RETRIES,
    DOWNLOAD_TIMEOUT
)
from utils import (
    logger, 
    get_unique_urls, 
    detect_platform, 
    get_video_path,
    generate_filename
)


class VideoDownloader:
    """
    Handles video downloading from various platforms.
    """
    
    def __init__(self, headless: bool = BROWSER_HEADLESS):
        self.headless = headless
        self.browser: Optional[Browser] = None
        self.downloads_dir = DOWNLOADS_DIR
        
    async def __aenter__(self):
        await self.start()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
        
    async def start(self):
        """Initialize the browser."""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            slow_mo=SLOW_MO
        )
        logger.info("Browser started for downloading")
        
    async def close(self):
        """Close the browser."""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        logger.info("Browser closed")
    
    async def _close_ads(self, page: Page):
        """
        Close any ads or popups that appear on the page.
        
        Args:
            page: Playwright page instance
        """
        logger.info("Attempting to close ads/popups...")
        
        # Simple approach: Click multiple times anywhere on the page to dismiss ads
        viewport = page.viewport_size
        if viewport:
            # Click 3-5 times at the right side of the page
            click_positions = [
                {"x": viewport["width"] - 100, "y": viewport["height"] // 2},      # Right middle
                {"x": viewport["width"] - 150, "y": viewport["height"] // 3},      # Right upper
                {"x": viewport["width"] - 100, "y": viewport["height"] // 2 + 50}, # Right middle lower
            ]
            
            for i, pos in enumerate(click_positions):
                try:
                    logger.info(f"Click {i + 1}/3 at position: ({pos['x']}, {pos['y']})")
                    await page.mouse.click(pos["x"], pos["y"])
                    await page.wait_for_timeout(500)
                except Exception as e:
                    logger.debug(f"Click failed: {e}")
        
        # Also try pressing Escape
        try:
            await page.keyboard.press("Escape")
            await page.wait_for_timeout(300)
        except:
            pass
        
        # Close any new tabs/popups that might have opened
        try:
            pages = page.context.pages
            if len(pages) > 1:
                logger.info(f"Found {len(pages)} tabs, closing extra tabs...")
                for p in pages[1:]:
                    await p.close()
                    logger.info("Closed popup tab")
        except:
            pass
        
        logger.info("Ad close attempts completed")
    
    async def download_tiktok(self, url: str, output_path: Path) -> bool:
        """
        Download TikTok video using third-party downloader.
        
        Args:
            url: TikTok video URL
            output_path: Path to save video
            
        Returns:
            True if successful, False otherwise
        """
        context = await self.browser.new_context(
            accept_downloads=True
        )
        page = await context.new_page()
        
        try:
            # Use snaptik as downloader
            downloader_url = "https://snaptik.app/"
            logger.info(f"Navigating to {downloader_url}")
            await page.goto(downloader_url, timeout=TIMEOUT)
            
            # Wait for page to load (use domcontentloaded instead of networkidle to avoid timeout from ads)
            logger.info("Waiting for page to load...")
            await page.wait_for_load_state("domcontentloaded", timeout=TIMEOUT)
            
            # Find input field and enter URL
            logger.info("Looking for input field...")
            input_selector = 'input[name="url"], input[type="text"], #url'
            await page.wait_for_selector(input_selector, timeout=TIMEOUT)
            logger.info(f"Filling URL: {url}")
            await page.fill(input_selector, url)
            
            # Click download button
            logger.info("Clicking submit button...")
            submit_selector = 'button[type="submit"], .button-go, #submiturl'
            await page.click(submit_selector)
            
            # Wait longer for page to process and ads to appear
            logger.info("Waiting for page to process (5 seconds)...")
            await page.wait_for_timeout(5000)
            
            # Look for download link
            download_selectors = [
                'a[href*="download"]',
                'a.download-file',
                '.video-links a',
                'a:has-text("Download")',
                'a:has-text("Server")'
            ]
            
            for selector in download_selectors:
                try:
                    download_link = page.locator(selector).first
                    if await download_link.is_visible(timeout=3000):
                        logger.info(f"Found download link with selector: {selector}")
                        
                        # Use Playwright's expect_download with event handler
                        download_done = False
                        
                        async def on_download(download):
                            nonlocal download_done
                            logger.info(f"Download started: {download.suggested_filename}")
                            await download.save_as(output_path)
                            logger.info(f"Download saved to: {output_path}")
                            download_done = True
                        
                        page.on("download", on_download)
                        
                        # Click download button (this triggers ads)
                        await download_link.click()
                        logger.info("Clicked download button, waiting for ads...")
                        
                        # Wait for ads to appear
                        await page.wait_for_timeout(2000)
                        
                        # Try to close ads by clicking multiple times
                        for attempt in range(5):
                            if download_done:
                                logger.info("Download already completed!")
                                return True
                            logger.info(f"Ad closing attempt {attempt + 1}/5")
                            await self._close_ads(page)
                            await page.wait_for_timeout(800)
                        
                        # Wait for download to complete
                        logger.info("Waiting for download to complete...")
                        for _ in range(DOWNLOAD_TIMEOUT):
                            if download_done or output_path.exists():
                                logger.info(f"Saved TikTok video: {output_path}")
                                return True
                            await page.wait_for_timeout(1000)
                        
                        logger.warning(f"Download timeout for {url}")
                        continue
                except Exception as e:
                    logger.debug(f"Error with selector {selector}: {e}")
                    continue
            
            logger.warning(f"Could not find download link for {url}")
            return False
            
        except Exception as e:
            logger.error(f"Error downloading TikTok {url}: {e}")
            return False
        finally:
            await context.close()
    
    async def download_instagram(self, url: str, output_path: Path) -> bool:
        """
        Download Instagram video using third-party downloader.
        
        Args:
            url: Instagram video URL
            output_path: Path to save video
            
        Returns:
            True if successful, False otherwise
        """
        context = await self.browser.new_context(
            accept_downloads=True
        )
        page = await context.new_page()
        
        try:
            # Use snapinsta as downloader
            downloader_url = "https://snapvideo.app/en"
            logger.info(f"Navigating to {downloader_url}")
            await page.goto(downloader_url, timeout=TIMEOUT)
            
            # Wait for page to load (use domcontentloaded instead of networkidle to avoid timeout from ads)
            logger.info("Waiting for page to load...")
            await page.wait_for_load_state("domcontentloaded", timeout=TIMEOUT)
            
            # Find input field and enter URL
            logger.info("Looking for input field...")
            input_selector = 'input[name="url"], input[type="text"], #url'
            await page.wait_for_selector(input_selector, timeout=TIMEOUT)
            logger.info(f"Filling URL: {url}")
            await page.fill(input_selector, url)
            
            # Click download button
            logger.info("Clicking Download button...")
            submit_selector = 'button:has-text("Download"), .btn-download, #download-btn, button[type="submit"]'
            await page.click(submit_selector)
            
            # Wait longer for page to process and ads to appear
            logger.info("Waiting for page to process (10 seconds)...")
            await page.wait_for_timeout(10000)
            
            # Look for download link
            download_selectors = [
                'a[href*="download"]',
                'a.download-btn',
                '.download-items a',
                'a:has-text("Download")',
                'a:has-text("Video")'
            ]
            
            for selector in download_selectors:
                try:
                    download_link = page.locator(selector).first
                    if await download_link.is_visible(timeout=3000):
                        logger.info(f"Found download link with selector: {selector}")
                        
                        # Use Playwright's download event handler
                        download_done = False
                        
                        async def on_download(download):
                            nonlocal download_done
                            logger.info(f"Download started: {download.suggested_filename}")
                            await download.save_as(output_path)
                            logger.info(f"Download saved to: {output_path}")
                            download_done = True
                        
                        page.on("download", on_download)
                        
                        # Click download button (this triggers ads)
                        await download_link.click()
                        logger.info("Clicked download button, waiting for ads...")
                        
                        # Wait for ads to appear
                        await page.wait_for_timeout(2000)
                        
                        # Try to close ads by clicking multiple times
                        for attempt in range(5):
                            if download_done:
                                logger.info("Download already completed!")
                                return True
                            logger.info(f"Ad closing attempt {attempt + 1}/5")
                            await self._close_ads(page)
                            await page.wait_for_timeout(800)
                        
                        # Wait for download to complete
                        logger.info("Waiting for download to complete...")
                        for _ in range(DOWNLOAD_TIMEOUT):
                            if download_done or output_path.exists():
                                logger.info(f"Saved Instagram video: {output_path}")
                                return True
                            await page.wait_for_timeout(1000)
                        
                        logger.warning(f"Download timeout for {url}")
                        continue
                except Exception as e:
                    logger.debug(f"Error with selector {selector}: {e}")
                    continue
            
            logger.warning(f"Could not find download link for {url}")
            return False
            
        except Exception as e:
            logger.error(f"Error downloading Instagram {url}: {e}")
            return False
        finally:
            await context.close()
    
    async def download_video(self, url: str, index: int = 0) -> Optional[Path]:
        """
        Download video from URL (auto-detect platform).
        
        Args:
            url: Video URL
            index: Index for filename
            
        Returns:
            Path to downloaded video or None if failed
        """
        platform = detect_platform(url)
        output_path = get_video_path(url, index)
        
        # Skip if already downloaded
        if output_path.exists():
            logger.info(f"Video already exists: {output_path}")
            return output_path
        
        logger.info(f"Downloading {platform} video: {url}")
        
        success = False
        for attempt in range(MAX_RETRIES):
            try:
                if platform == 'tiktok':
                    success = await self.download_tiktok(url, output_path)
                elif platform == 'instagram':
                    success = await self.download_instagram(url, output_path)
                else:
                    logger.warning(f"Unsupported platform for URL: {url}")
                    return None
                
                if success:
                    return output_path
                    
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed: {e}")
                await asyncio.sleep(2)
        
        logger.error(f"Failed to download after {MAX_RETRIES} attempts: {url}")
        return None
    
    async def download_all(self, urls: List[str]) -> dict:
        """
        Download all videos from list of URLs.
        
        Args:
            urls: List of video URLs
            
        Returns:
            Dictionary with results
        """
        results = {
            'successful': [],
            'failed': [],
            'skipped': []
        }
        
        for i, url in enumerate(urls):
            logger.info(f"Processing {i + 1}/{len(urls)}: {url}")
            
            output_path = get_video_path(url, i)
            if output_path.exists():
                results['skipped'].append(url)
                continue
            
            path = await self.download_video(url, i)
            
            if path:
                results['successful'].append({'url': url, 'path': str(path)})
            else:
                results['failed'].append(url)
            
            # Rate limiting
            await asyncio.sleep(2)
        
        return results


async def main():
    """Main function for standalone execution."""
    parser = argparse.ArgumentParser(description='Download videos from TikTok/Instagram')
    parser.add_argument('--urls', nargs='+', help='Specific URLs to download')
    parser.add_argument('--all', action='store_true', help='Download all URLs from data.csv')
    parser.add_argument('--headless', action='store_true', help='Run browser in headless mode')
    
    args = parser.parse_args()
    
    if args.urls:
        urls = args.urls
    elif args.all:
        urls = get_unique_urls()
    else:
        # Default: download all
        urls = get_unique_urls()
    
    if not urls:
        logger.warning("No URLs to download")
        return
    
    logger.info(f"Starting download of {len(urls)} videos")
    
    async with VideoDownloader(headless=args.headless) as downloader:
        results = await downloader.download_all(urls)
    
    # Print summary
    print("\n" + "="*50)
    print("DOWNLOAD SUMMARY")
    print("="*50)
    print(f"Successful: {len(results['successful'])}")
    print(f"Failed: {len(results['failed'])}")
    print(f"Skipped (already exists): {len(results['skipped'])}")
    print("="*50)


if __name__ == "__main__":
    asyncio.run(main())
