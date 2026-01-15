"""
Utility functions for MVoice Automation
"""
import csv
import re
import logging
from pathlib import Path
from typing import List, Dict, Optional
from urllib.parse import urlparse

from config import DATA_FILE, OUTPUT_FILE, DOWNLOADS_DIR

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('mvoice.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def read_urls_from_csv(file_path: Path = DATA_FILE) -> List[str]:
    """
    Read URLs from the 'url' column in CSV file.
    
    Args:
        file_path: Path to CSV file
        
    Returns:
        List of URLs
    """
    urls = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if 'url' in row and row['url']:
                    urls.append(row['url'].strip())
        logger.info(f"Read {len(urls)} URLs from {file_path}")
    except Exception as e:
        logger.error(f"Error reading CSV: {e}")
        raise
    return urls


def get_unique_urls(file_path: Path = DATA_FILE) -> List[str]:
    """
    Get unique URLs from CSV file.
    
    Args:
        file_path: Path to CSV file
        
    Returns:
        List of unique URLs
    """
    urls = read_urls_from_csv(file_path)
    unique_urls = list(dict.fromkeys(urls))  # Preserve order
    logger.info(f"Found {len(unique_urls)} unique URLs out of {len(urls)} total")
    return unique_urls


def detect_platform(url: str) -> str:
    """
    Detect the platform from URL.
    
    Args:
        url: Video URL
        
    Returns:
        Platform name (tiktok, instagram, unknown)
    """
    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    
    if 'tiktok' in domain:
        return 'tiktok'
    elif 'instagram' in domain:
        return 'instagram'
    else:
        return 'unknown'


def generate_filename(url: str, index: int = 0) -> str:
    """
    Generate a filename for downloaded video.
    
    Args:
        url: Video URL
        index: Index number for uniqueness
        
    Returns:
        Filename string
    """
    platform = detect_platform(url)
    
    # Extract video ID from URL
    if platform == 'tiktok':
        match = re.search(r'/video/(\d+)', url)
        video_id = match.group(1) if match else str(index)
    elif platform == 'instagram':
        match = re.search(r'/p/([A-Za-z0-9_-]+)', url)
        video_id = match.group(1) if match else str(index)
    else:
        video_id = str(index)
    
    return f"{platform}_{video_id}.mp4"


def get_video_path(url: str, index: int = 0) -> Path:
    """
    Get the full path for a video file.
    
    Args:
        url: Video URL
        index: Index number
        
    Returns:
        Full path to video file
    """
    filename = generate_filename(url, index)
    return DOWNLOADS_DIR / filename


def save_results_to_csv(results: List[Dict], file_path: Path = OUTPUT_FILE):
    """
    Save results to CSV file.
    
    Args:
        results: List of dictionaries with 'url' and 'message' keys
        file_path: Output file path
    """
    try:
        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            fieldnames = ['url', 'message']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)
        logger.info(f"Saved {len(results)} results to {file_path}")
    except Exception as e:
        logger.error(f"Error saving results: {e}")
        raise


def append_result_to_csv(url: str, message: str, file_path: Path = OUTPUT_FILE):
    """
    Append a single result to CSV file.
    
    Args:
        url: Video URL
        message: AI generated message
        file_path: Output file path
    """
    file_exists = file_path.exists()
    
    try:
        with open(file_path, 'a', newline='', encoding='utf-8') as f:
            fieldnames = ['url', 'message']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            
            if not file_exists:
                writer.writeheader()
            
            writer.writerow({'url': url, 'message': message})
        logger.info(f"Appended result for {url}")
    except Exception as e:
        logger.error(f"Error appending result: {e}")
        raise


def get_downloaded_videos() -> List[Path]:
    """
    Get list of downloaded video files.
    
    Returns:
        List of video file paths
    """
    videos = list(DOWNLOADS_DIR.glob("*.mp4"))
    logger.info(f"Found {len(videos)} downloaded videos")
    return videos


def get_pending_videos(processed_urls: List[str]) -> List[tuple]:
    """
    Get videos that haven't been processed yet.
    
    Args:
        processed_urls: List of already processed URLs
        
    Returns:
        List of (url, video_path) tuples
    """
    all_urls = get_unique_urls()
    pending = []
    
    for url in all_urls:
        if url not in processed_urls:
            video_path = get_video_path(url)
            if video_path.exists():
                pending.append((url, video_path))
    
    logger.info(f"Found {len(pending)} pending videos to process")
    return pending


def get_processed_urls(file_path: Path = OUTPUT_FILE) -> List[str]:
    """
    Get list of already processed URLs from output file.
    
    Args:
        file_path: Output CSV file path
        
    Returns:
        List of processed URLs
    """
    if not file_path.exists():
        return []
    
    urls = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if 'url' in row:
                    urls.append(row['url'])
    except Exception as e:
        logger.warning(f"Error reading processed URLs: {e}")
    
    return urls


def clean_message(message: str) -> str:
    """
    Clean and format AI response message.
    
    Args:
        message: Raw message from AI
        
    Returns:
        Cleaned message
    """
    # Remove excessive whitespace
    message = re.sub(r'\s+', ' ', message)
    # Remove leading/trailing whitespace
    message = message.strip()
    return message
