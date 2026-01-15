"""
MVoice Automation Pipeline - Streaming Batch Version

This module implements an optimized pipeline for processing thousands of videos:
- Batch downloading (configurable batch size)
- Sequential AI upload (1 video at a time)
- Delete after upload (saves disk space)
- Resume support
- Real-time progress tracking

Usage:
    python pipeline.py [--batch-size N] [--no-delete] [--headless]
    python pipeline.py --download-only [--batch-size N]
    python pipeline.py --upload-only
    python pipeline.py -i  # Interactive mode
"""
import asyncio
import argparse
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

from config import (
    DEFAULT_PROMPT, 
    OUTPUT_FILE, 
    BATCH_SIZE, 
    DELETE_AFTER_UPLOAD,
    DOWNLOADS_DIR
)
from utils import (
    logger, 
    get_unique_urls, 
    get_processed_urls, 
    get_video_path, 
    migrate_old_output_format,
    detect_platform,
    log_failed_url
)
from downloader import VideoDownloader

from ai_uploader import AIUploader
from ai_upload_check import should_attempt_ai_upload


class StreamingPipeline:
    """
    Optimized streaming batch pipeline for large-scale video processing.
    
    Flow:
    1. Download batch of N videos
    2. Upload each to AI (sequential, ~1 min each)
    3. Delete video after successful upload
    4. Repeat until done
    """
    
    def __init__(
        self, 
        headless: bool = False, 
        prompt: str = DEFAULT_PROMPT,
        batch_size: int = BATCH_SIZE,
        delete_after_upload: bool = DELETE_AFTER_UPLOAD,
        download_only: bool = False,
        upload_only: bool = False
    ):
        self.headless = headless
        self.prompt = prompt
        self.batch_size = batch_size
        self.delete_after_upload = delete_after_upload
        self.download_only = download_only
        self.upload_only = upload_only
        
        self.stats = {
            'start_time': None,
            'end_time': None,
            'total_urls': 0,
            'download': {'successful': 0, 'failed': 0, 'skipped': 0},
            'upload': {'successful': 0, 'failed': 0, 'skipped': 0},
            'deleted': 0
        }
        
        # Track progress
        self.current_batch = 0
        self.total_batches = 0
    
    def _print_progress(self):
        """Print current progress."""
        total = self.stats['total_urls']
        downloaded = self.stats['download']['successful'] + self.stats['download']['skipped']
        uploaded = self.stats['upload']['successful'] + self.stats['upload']['skipped']
        
        print(f"\r[Batch {self.current_batch}/{self.total_batches}] "
              f"Downloaded: {downloaded}/{total} | "
              f"Uploaded: {uploaded}/{total} | "
              f"Deleted: {self.stats['deleted']}", end="", flush=True)
    
    async def run(self):
        """Run the streaming batch pipeline."""
        self.stats['start_time'] = datetime.now()
        
        print("\n" + "="*60)
        print("MVOICE STREAMING BATCH PIPELINE")
        print("="*60)
        print(f"Batch Size: {self.batch_size}")
        print(f"Delete After Upload: {self.delete_after_upload}")
        print(f"Mode: {'Download Only' if self.download_only else 'Upload Only' if self.upload_only else 'Full Pipeline'}")
        print("="*60 + "\n")
        
        # Get all URLs and filter already processed
        all_urls = get_unique_urls()
        processed_urls = get_processed_urls()
        
        # Filter out already processed
        pending_urls = [url for url in all_urls if url not in processed_urls]
        
        self.stats['total_urls'] = len(pending_urls)
        self.total_batches = (len(pending_urls) + self.batch_size - 1) // self.batch_size
        
        logger.info(f"Total URLs: {len(all_urls)}")
        logger.info(f"Already processed: {len(processed_urls)}")
        logger.info(f"Pending: {len(pending_urls)}")
        logger.info(f"Batches to process: {self.total_batches}")
        
        if not pending_urls:
            print("\n✓ All videos already processed!")
            self.stats['end_time'] = datetime.now()
            return
        
        # Create URL index mapping for get_video_path
        url_indices = {url: i for i, url in enumerate(all_urls)}
        
        if self.upload_only:
            await self._upload_only_mode(pending_urls, url_indices)
        elif self.download_only:
            await self._download_only_mode(pending_urls, url_indices)
        else:
            await self._streaming_mode(pending_urls, url_indices)
        
        self.stats['end_time'] = datetime.now()
        self._print_summary()
    
    async def _download_only_mode(self, urls: List[str], url_indices: Dict[str, int]):
        """Download all videos in batches."""
        logger.info("Running in DOWNLOAD ONLY mode")
        
        async with VideoDownloader(headless=self.headless) as downloader:
            for batch_start in range(0, len(urls), self.batch_size):
                self.current_batch += 1
                batch = urls[batch_start:batch_start + self.batch_size]
                
                logger.info(f"\n--- Batch {self.current_batch}/{self.total_batches} ---")
                
                for url in batch:
                    index = url_indices.get(url, 0)
                    output_path = get_video_path(url, index)
                    
                    if output_path.exists():
                        self.stats['download']['skipped'] += 1
                        continue
                    
                    path = await downloader.download_video(url, index)
                    
                    if path:
                        self.stats['download']['successful'] += 1
                    else:
                        self.stats['download']['failed'] += 1
                        log_failed_url(url, "Download failed or timeout")
                    
                    self._print_progress()
                    await asyncio.sleep(1)
    
    async def _upload_only_mode(self, urls: List[str], url_indices: Dict[str, int]):
        """Upload already downloaded videos to AI."""
        logger.info("Running in UPLOAD ONLY mode")
        
        async with AIUploader(headless=self.headless, prompt=self.prompt) as uploader:
            # Check login first
            is_logged_in = await uploader.check_login_status()
            if not is_logged_in:
                print("\n" + "="*60)
                print("SESSION EXPIRED atau BELUM LOGIN")
                print("="*60)
                print("Jalankan dulu: python ai_uploader.py --login")
                print("="*60 + "\n")
                return
            
            for i, url in enumerate(urls):
                self.current_batch = (i // self.batch_size) + 1
                index = url_indices.get(url, 0)
                video_path = get_video_path(url, index)
                
                if not video_path.exists():
                    logger.warning(f"Video not found: {video_path}")
                    self.stats['upload']['failed'] += 1
                    log_failed_url(url, "Video file not found")
                    continue

                # Only upload if output.csv row is empty or header-like
                if not should_attempt_ai_upload(url, OUTPUT_FILE):
                    logger.info(f"Skipping upload for {url} (already has valid AI result)")
                    self.stats['upload']['skipped'] += 1
                    continue
                
                response = await uploader.process_video(url, video_path, max_retries=5)
                
                if response:
                    self.stats['upload']['successful'] += 1
                    
                    # Delete after successful upload
                    if self.delete_after_upload:
                        try:
                            video_path.unlink()
                            self.stats['deleted'] += 1
                            logger.info(f"Deleted: {video_path}")
                        except Exception as e:
                            logger.warning(f"Failed to delete {video_path}: {e}")
                else:
                    self.stats['upload']['failed'] += 1
                    log_failed_url(url, "AI upload failed")
                
                self._print_progress()
                await asyncio.sleep(2)
    
    async def _streaming_mode(self, urls: List[str], url_indices: Dict[str, int]):
        """
        Main streaming mode: Download batch → Upload one by one → Delete → Repeat
        """
        logger.info("Running in STREAMING mode")
        
        async with VideoDownloader(headless=self.headless) as downloader:
            async with AIUploader(headless=self.headless, prompt=self.prompt) as uploader:
                # Check login first
                is_logged_in = await uploader.check_login_status()
                if not is_logged_in:
                    print("\n" + "="*60)
                    print("SESSION EXPIRED atau BELUM LOGIN")
                    print("="*60)
                    print("Jalankan dulu: python ai_uploader.py --login")
                    print("="*60 + "\n")
                    return
                
                # Process in batches
                for batch_start in range(0, len(urls), self.batch_size):
                    self.current_batch += 1
                    batch = urls[batch_start:batch_start + self.batch_size]
                    
                    print(f"\n\n{'='*60}")
                    print(f"BATCH {self.current_batch}/{self.total_batches}")
                    print(f"{'='*60}\n")
                    
                    # Step 1: Download this batch
                    logger.info(f"Downloading batch {self.current_batch}...")
                    downloaded_videos = []
                    
                    for url in batch:
                        index = url_indices.get(url, 0)
                        output_path = get_video_path(url, index)
                        
                        if output_path.exists():
                            self.stats['download']['skipped'] += 1
                            downloaded_videos.append((url, output_path))
                            continue
                        
                        path = await downloader.download_video(url, index)
                        
                        if path:
                            self.stats['download']['successful'] += 1
                            downloaded_videos.append((url, path))
                        else:
                            self.stats['download']['failed'] += 1
                            # Log failed download to output.csv
                            log_failed_url(url, "Download failed or timeout")
                        
                        self._print_progress()
                        await asyncio.sleep(1)
                    
                    # Step 2: Upload each video to AI
                    logger.info(f"\nUploading {len(downloaded_videos)} videos to AI...")
                    
                    for url, video_path in downloaded_videos:
                        logger.info(f"Processing: {video_path.name}")

                        # Only upload if output.csv row is empty or header-like
                        if not should_attempt_ai_upload(url, OUTPUT_FILE):
                            logger.info(f"Skipping upload for {url} (already has valid AI result)")
                            self.stats['upload']['skipped'] += 1
                            continue

                        response = await uploader.process_video(url, video_path, max_retries=5)

                        if response:
                            self.stats['upload']['successful'] += 1
                            # Step 3: Delete after successful upload
                            if self.delete_after_upload:
                                try:
                                    video_path.unlink()
                                    self.stats['deleted'] += 1
                                    logger.info(f"Deleted: {video_path.name}")
                                except Exception as e:
                                    logger.warning(f"Failed to delete {video_path}: {e}")
                        else:
                            self.stats['upload']['failed'] += 1
                            # Log failed upload to output.csv
                            log_failed_url(url, "AI upload failed")

                        self._print_progress()
                        await asyncio.sleep(2)
                    
                    # Batch complete
                    print(f"\n✓ Batch {self.current_batch} complete!")
    
    def _print_summary(self):
        """Print final summary."""
        duration = self.stats['end_time'] - self.stats['start_time']
        
        print("\n\n" + "="*60)
        print("PIPELINE COMPLETE - FINAL SUMMARY")
        print("="*60)
        print(f"Duration: {duration}")
        print(f"Total URLs: {self.stats['total_urls']}")
        print()
        
        if not self.upload_only:
            print("DOWNLOADS:")
            print(f"  ✓ Successful: {self.stats['download']['successful']}")
            print(f"  ✗ Failed: {self.stats['download']['failed']}")
            print(f"  ⊘ Skipped (exists): {self.stats['download']['skipped']}")
            print()
        
        if not self.download_only:
            print("AI UPLOADS:")
            print(f"  ✓ Successful: {self.stats['upload']['successful']}")
            print(f"  ✗ Failed: {self.stats['upload']['failed']}")
            print(f"  ⊘ Skipped (processed): {self.stats['upload']['skipped']}")
            print()
        
        if self.delete_after_upload and not self.download_only:
            print(f"CLEANUP:")
            print(f"  🗑 Deleted: {self.stats['deleted']} files")
            print()
        
        print(f"Results saved to: {OUTPUT_FILE}")
        print("="*60)


# Legacy class for backward compatibility
class MVoicePipeline(StreamingPipeline):
    """Legacy pipeline class - now uses StreamingPipeline."""
    pass


async def interactive_mode():
    """Run pipeline in interactive mode with user prompts."""
    print("\n" + "="*60)
    print("MVOICE AUTOMATION - INTERACTIVE MODE")
    print("="*60)
    
    # Ask for mode
    print("\nSelect mode:")
    print("1. Full pipeline (streaming batch)")
    print("2. Download only")
    print("3. AI processing only")
    
    choice = input("\nEnter choice (1/2/3): ").strip()
    
    download_only = choice == "2"
    upload_only = choice == "3"
    
    # Ask for batch size
    batch_size = BATCH_SIZE
    if not upload_only:
        batch_input = input(f"\nBatch size (default {BATCH_SIZE}): ").strip()
        if batch_input.isdigit():
            batch_size = int(batch_input)
    
    # Ask for delete after upload
    delete_after = DELETE_AFTER_UPLOAD
    if not download_only:
        delete_input = input(f"\nDelete video after upload? (Y/n): ").strip().lower()
        delete_after = delete_input != 'n'
    
    # Ask for prompt if doing AI processing
    prompt = DEFAULT_PROMPT
    if not download_only:
        print(f"\nDefault prompt: {DEFAULT_PROMPT[:80]}...")
        custom = input("\nEnter custom prompt (or press Enter to use default): ").strip()
        if custom:
            prompt = custom
    
    # Ask for headless mode
    headless = input("\nRun in headless mode? (y/N): ").strip().lower() == 'y'
    
    # Confirm
    print("\n" + "-"*60)
    print("Configuration:")
    print(f"  Mode: {'Download only' if download_only else 'AI only' if upload_only else 'Streaming batch'}")
    print(f"  Batch Size: {batch_size}")
    print(f"  Delete After Upload: {delete_after}")
    print(f"  Headless: {headless}")
    if not download_only:
        print(f"  Prompt: {prompt[:50]}...")
    print("-"*60)
    
    confirm = input("\nProceed? (Y/n): ").strip().lower()
    if confirm == 'n':
        print("Cancelled.")
        return
    
    # Run pipeline
    pipeline = StreamingPipeline(
        headless=headless,
        prompt=prompt,
        batch_size=batch_size,
        delete_after_upload=delete_after,
        download_only=download_only,
        upload_only=upload_only
    )
    await pipeline.run()


async def main():
    """Main function for standalone execution."""
    parser = argparse.ArgumentParser(
        description='MVoice Streaming Batch Pipeline - Optimized for large-scale processing'
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
        '--batch-size',
        type=int,
        default=BATCH_SIZE,
        help=f'Number of videos per batch (default: {BATCH_SIZE})'
    )
    parser.add_argument(
        '--no-delete',
        action='store_true',
        help='Do not delete videos after successful upload'
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
    
    # Migrate old output format if needed
    migrate_old_output_format()
    
    if args.interactive:
        await interactive_mode()
    else:
        pipeline = StreamingPipeline(
            headless=args.headless,
            prompt=args.prompt,
            batch_size=args.batch_size,
            delete_after_upload=not args.no_delete,
            download_only=args.download_only,
            upload_only=args.upload_only
        )
        await pipeline.run()


if __name__ == "__main__":
    asyncio.run(main())
