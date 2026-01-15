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


def log_failed_url(url: str, reason: str, file_path: Path = OUTPUT_FILE):
    """
    Log a failed URL to output CSV with error reason.
    
    Args:
        url: Video URL that failed
        reason: Reason for failure
        file_path: Output file path
    """
    file_exists = file_path.exists()
    
    try:
        with open(file_path, 'a', newline='', encoding='utf-8') as f:
            fieldnames = ['url', 'message']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            
            if not file_exists:
                writer.writeheader()
            
            writer.writerow({'url': url, 'message': f'FAILED: {reason}'})
        logger.warning(f"Logged failed URL: {url} - {reason}")
    except Exception as e:
        logger.error(f"Error logging failed URL: {e}")


# Define all metrics columns in order
METRICS_COLUMNS = [
    "Business Unit",
    "Category", 
    "Brand",
    "Platform",
    "Creative Link",
    "Period",
    "Brand Presence // First Product Appearance (Seconds)",
    "Brand Presence // First Product Appearance (%)",
    "Brand Presence // First Standalone Logo Appearance (Seconds)",
    "Brand Presence // First Standalone Logo Appearance (%)",
    "Brand Presence // Brand Logo Visibility - Standalone",
    "Brand Presence // Brand Logo Visibility - On Product",
    "Brand Presence // Brand Prominence",
    "Brand Presence // Brand Appearance Count",
    "Brand Presence // Other Brands Present",
    "Visuals // Visual Style",
    "Visuals // Color Palette",
    "Visuals // Creative Duration (Seconds)",
    "Visuals // Animation/CGI Used",
    "Visuals // Production Quality",
    "Visuals // Setting",
    "Visuals // Nature Setting",
    "Visuals // Scientific Setting",
    "Visuals // Real Life vs. Staged",
    "Visuals // Individual vs. Group Focus",
    "Visuals // On-Screen Text",
    "Visuals // Text Style",
    "Visuals // Text Size",
    "Visuals // Beauty Appeal",
    "Visuals // Ingredient Visual",
    "Visuals // Horizontal vs. Vertical",
    "Audio // Audio Type",
    "Audio // Voiceover vs. Talent",
    "Audio // Localized Language",
    "Audio // Sound Effects Usage",
    "Talent // Talent Type",
    "Talent // Number of KOLs",
    "Talent // Brand Ambassador Used",
    "Messaging // Messaging Summary",
    "Messaging // Emotional Tone",
    "Messaging // Key Product Benefit Highlighted",
    "Messaging // Emotional Appeal",
    "Messaging // Storytelling Used",
    "Messaging // Call to Action (CTA)",
    "Meaningful & Different // Social Impact",
    "Meaningful & Different // Emotional Depth",
    "Meaningful & Different // Authenticity",
    "Meaningful & Different // Uniqueness of Concept",
    "Meaningful & Different // Execution Style",
    "Meaningful & Different // Target Surprise",
]


def parse_message_to_dict(message: str) -> Dict[str, str]:
    """
    Parse AI response message into a dictionary of metrics.
    
    Args:
        message: Raw message from AI (flattened table format)
        
    Returns:
        Dictionary with metric names as keys and values
    """
    result = {}
    
    # Clean the message
    text = message.strip()
    
    # Remove common prefixes like "AI", "My thought process", "MetricsValue"
    prefixes_to_remove = [
        r'^AI\s*',
        r'My thought process\s*',
        r'MetricsValue\s*',
        r'Metrics\s*Value\s*',
        r'\|\s*Metrics\s*\|\s*Value\s*\|',
        r'\|[-\s]+\|[-\s]+\|',
    ]
    for prefix in prefixes_to_remove:
        text = re.sub(prefix, '', text, flags=re.IGNORECASE)
    
    # Try to extract values for each metric
    for i, metric in enumerate(METRICS_COLUMNS):
        # Escape special regex characters in metric name
        escaped_metric = re.escape(metric)
        
        # Determine the next metric for boundary
        if i < len(METRICS_COLUMNS) - 1:
            next_metric = re.escape(METRICS_COLUMNS[i + 1])
            # Pattern: metric name followed by value, ending before next metric
            pattern = rf'{escaped_metric}\s*[:\|]?\s*(.+?)(?={next_metric}|$)'
        else:
            # Last metric - capture everything after it
            pattern = rf'{escaped_metric}\s*[:\|]?\s*(.+?)$'
        
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            value = match.group(1).strip()
            # Clean up pipe characters and extra whitespace
            value = re.sub(r'\s*\|\s*', '', value)
            value = re.sub(r'\s+', ' ', value)
            result[metric] = value
        else:
            result[metric] = ""
    
    return result


def append_result_to_csv_parsed(url: str, message: str, file_path: Path = OUTPUT_FILE):
    """
    Parse message and append as structured columns to CSV file.
    
    Args:
        url: Video URL
        message: AI generated message
        file_path: Output file path
    """
    file_exists = file_path.exists()
    
    # Parse message into metrics dictionary
    metrics = parse_message_to_dict(message)
    
    # Create row with url + all metrics
    row = {'url': url}
    row.update(metrics)
    
    # All fieldnames
    fieldnames = ['url'] + METRICS_COLUMNS
    
    try:
        with open(file_path, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            
            if not file_exists:
                writer.writeheader()
            
            writer.writerow(row)
        logger.info(f"Appended parsed result for {url}")
    except Exception as e:
        logger.error(f"Error appending result: {e}")
        raise


def migrate_old_output_format(old_file: Path = OUTPUT_FILE, backup: bool = True):
    """
    Check if output.csv is in old format (url, message) and convert to parsed format.
    This runs automatically on startup.
    
    Args:
        old_file: Path to output file
        backup: Whether to backup old file
        
    Returns:
        True if migration was done, False if not needed
    """
    if not old_file.exists():
        return False
    
    # Check if file is in old format by reading header
    try:
        with open(old_file, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            header = next(reader, None)
            
            if not header:
                return False
            
            # Old format has only 'url' and 'message' columns
            if header == ['url', 'message']:
                logger.info("Detected old output format, migrating to parsed format...")
                
                # Read all old data
                f.seek(0)
                dict_reader = csv.DictReader(f)
                rows = list(dict_reader)
                
                if not rows:
                    return False
                
                # Backup old file
                if backup:
                    backup_path = old_file.with_suffix('.csv.bak')
                    import shutil
                    shutil.copy(old_file, backup_path)
                    logger.info(f"Backed up old file to {backup_path}")
                
                # Convert to new format
                parsed_rows = []
                for row in rows:
                    url = row.get('url', '')
                    message = row.get('message', '')
                    metrics = parse_message_to_dict(message)
                    new_row = {'url': url}
                    new_row.update(metrics)
                    parsed_rows.append(new_row)
                
                # Write new format
                fieldnames = ['url'] + METRICS_COLUMNS
                with open(old_file, 'w', newline='', encoding='utf-8') as out_f:
                    writer = csv.DictWriter(out_f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(parsed_rows)
                
                logger.info(f"✓ Migrated {len(parsed_rows)} rows to parsed format")
                return True
            
            # Already in new format
            return False
            
    except Exception as e:
        logger.error(f"Error checking/migrating output format: {e}")
        return False
