"""
MVoice Automation Pipeline

This module combines the downloader and AI uploader modules
to create a complete end-to-end automation pipeline.

Usage:
    python pipeline.py [--download-only] [--upload-only] [--prompt PROMPT] [--headless]
"""
import asyncio
import argparse
from datetime import datetime

from config import DEFAULT_PROMPT, OUTPUT_FILE
from utils import logger, get_unique_urls, get_processed_urls, get_video_path
from downloader import VideoDownloader
from ai_uploader import AIUploader


class MVoicePipeline:
    """
    Complete automation pipeline for MVoice.
    """
    
    def __init__(
        self, 
        headless: bool = False, 
        prompt: str = DEFAULT_PROMPT,
        download_only: bool = False,
        upload_only: bool = False
    ):
        self.headless = headless
        self.prompt = prompt
        self.download_only = download_only
        self.upload_only = upload_only
        self.stats = {
            'start_time': None,
            'end_time': None,
            'download': {'successful': 0, 'failed': 0, 'skipped': 0},
            'upload': {'successful': 0, 'failed': 0, 'skipped': 0}
        }
    
    async def run(self):
        """
        Run the complete pipeline.
        """
        self.stats['start_time'] = datetime.now()
        logger.info("="*60)
        logger.info("MVOICE AUTOMATION PIPELINE STARTED")
        logger.info("="*60)
        
        urls = get_unique_urls()
        logger.info(f"Total unique URLs to process: {len(urls)}")
        
        # Step 1: Download videos
        if not self.upload_only:
            await self._download_phase(urls)
        
        # Step 2: Upload to AI and get responses
        if not self.download_only:
            await self._upload_phase(urls)
        
        self.stats['end_time'] = datetime.now()
        self._print_summary()
    
    async def _download_phase(self, urls: list):
        """
        Execute the download phase.
        """
        logger.info("-"*60)
        logger.info("PHASE 1: DOWNLOADING VIDEOS")
        logger.info("-"*60)
        
        async with VideoDownloader(headless=self.headless) as downloader:
            results = await downloader.download_all(urls)
        
        self.stats['download']['successful'] = len(results['successful'])
        self.stats['download']['failed'] = len(results['failed'])
        self.stats['download']['skipped'] = len(results['skipped'])
        
        logger.info(f"Download phase complete: {len(results['successful'])} successful, "
                   f"{len(results['failed'])} failed, {len(results['skipped'])} skipped")
    
    async def _upload_phase(self, urls: list):
        """
        Execute the upload and AI processing phase.
        """
        logger.info("-"*60)
        logger.info("PHASE 2: UPLOADING TO AI PLATFORM")
        logger.info("-"*60)
        
        async with AIUploader(headless=self.headless, prompt=self.prompt) as uploader:
            results = await uploader.process_all_pending()
        
        self.stats['upload']['successful'] = len(results['successful'])
        self.stats['upload']['failed'] = len(results['failed'])
        self.stats['upload']['skipped'] = len(results['skipped'])
        
        logger.info(f"Upload phase complete: {len(results['successful'])} successful, "
                   f"{len(results['failed'])} failed, {len(results['skipped'])} skipped")
    
    def _print_summary(self):
        """Print final summary."""
        duration = self.stats['end_time'] - self.stats['start_time']
        
        print("\n")
        print("="*60)
        print("MVOICE AUTOMATION PIPELINE - FINAL SUMMARY")
        print("="*60)
        print(f"Duration: {duration}")
        print()
        
        if not self.upload_only:
            print("DOWNLOAD PHASE:")
            print(f"  ✓ Successful: {self.stats['download']['successful']}")
            print(f"  ✗ Failed: {self.stats['download']['failed']}")
            print(f"  ⊘ Skipped: {self.stats['download']['skipped']}")
            print()
        
        if not self.download_only:
            print("AI PROCESSING PHASE:")
            print(f"  ✓ Successful: {self.stats['upload']['successful']}")
            print(f"  ✗ Failed: {self.stats['upload']['failed']}")
            print(f"  ⊘ Skipped: {self.stats['upload']['skipped']}")
            print()
        
        print(f"Results saved to: {OUTPUT_FILE}")
        print("="*60)


async def interactive_mode():
    """
    Run pipeline in interactive mode with user prompts.
    """
    print("\n" + "="*60)
    print("MVOICE AUTOMATION - INTERACTIVE MODE")
    print("="*60)
    
    # Ask for mode
    print("\nSelect mode:")
    print("1. Full pipeline (download + AI processing)")
    print("2. Download only")
    print("3. AI processing only")
    
    choice = input("\nEnter choice (1/2/3): ").strip()
    
    download_only = choice == "2"
    upload_only = choice == "3"
    
    # Ask for prompt if doing AI processing
    prompt = DEFAULT_PROMPT
    if not download_only:
        print(f"\nDefault prompt: {DEFAULT_PROMPT[:100]}...")
        custom = input("\nEnter custom prompt (or press Enter to use default): ").strip()
        if custom:
            prompt = custom
    
    # Ask for headless mode
    headless = input("\nRun in headless mode? (y/N): ").strip().lower() == 'y'
    
    # Confirm
    print("\n" + "-"*60)
    print("Configuration:")
    print(f"  Mode: {'Download only' if download_only else 'AI only' if upload_only else 'Full pipeline'}")
    print(f"  Headless: {headless}")
    if not download_only:
        print(f"  Prompt: {prompt[:50]}...")
    print("-"*60)
    
    confirm = input("\nProceed? (Y/n): ").strip().lower()
    if confirm == 'n':
        print("Cancelled.")
        return
    
    # Run pipeline
    pipeline = MVoicePipeline(
        headless=headless,
        prompt=prompt,
        download_only=download_only,
        upload_only=upload_only
    )
    await pipeline.run()


async def main():
    """Main function for standalone execution."""
    parser = argparse.ArgumentParser(
        description='MVoice Automation Pipeline - Download videos and process with AI'
    )
    parser.add_argument(
        '--download-only', 
        action='store_true', 
        help='Only download videos, skip AI processing'
    )
    parser.add_argument(
        '--upload-only', 
        action='store_true', 
        help='Only process with AI, skip downloading'
    )
    parser.add_argument(
        '--prompt', 
        type=str, 
        default=DEFAULT_PROMPT, 
        help='Custom prompt for AI analysis'
    )
    parser.add_argument(
        '--headless', 
        action='store_true', 
        help='Run browser in headless mode'
    )
    parser.add_argument(
        '--interactive', 
        '-i',
        action='store_true', 
        help='Run in interactive mode'
    )
    
    args = parser.parse_args()
    
    if args.interactive:
        await interactive_mode()
    else:
        pipeline = MVoicePipeline(
            headless=args.headless,
            prompt=args.prompt,
            download_only=args.download_only,
            upload_only=args.upload_only
        )
        await pipeline.run()


if __name__ == "__main__":
    asyncio.run(main())
