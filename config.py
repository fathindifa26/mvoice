"""
Configuration settings for MVoice Automation
"""
import os
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).parent
DOWNLOADS_DIR = BASE_DIR / "downloads"
DATA_FILE = BASE_DIR / "data.csv"
OUTPUT_FILE = BASE_DIR / "output.csv"
AUTH_STATE_FILE = BASE_DIR / "auth_state.json"  # Saved login session

# Ensure downloads directory exists
DOWNLOADS_DIR.mkdir(exist_ok=True)

# AI Platform settings
AI_URL = "https://imagine.wpp.ai/chat/zepYR9RpFQid3NJY7I7MY/foundational"

# Default prompt template (can be customized)
DEFAULT_PROMPT = """Analyze this video and output ONLY a single JSON object (no surrounding text, no markdown, no explanation).

Rules:
- Output must be valid JSON parseable with `json.loads()`.
- The JSON object keys must exactly match the metric names used in the pipeline (use empty string "" for unknown/missing values).
- Do NOT include any commentary, code fences, or additional fields.

Example output (all keys must be present; values may be empty strings):
{
	"Business Unit": "",
	"Category": "",
	"Brand": "",
	"Platform": "",
	"Creative Link": "",
	"Period": "",
	"Brand Presence // First Product Appearance (Seconds)": "",
	"Brand Presence // First Product Appearance (%)": "",
	"Brand Presence // First Standalone Logo Appearance (Seconds)": "",
	"Brand Presence // First Standalone Logo Appearance (%)": "",
	"Brand Presence // Brand Logo Visibility - Standalone": "",
	"Brand Presence // Brand Logo Visibility - On Product": "",
	"Brand Presence // Brand Prominence": "",
	"Brand Presence // Brand Appearance Count": "",
	"Brand Presence // Other Brands Present": "",
	"Visuals // Visual Style": "",
	"Visuals // Color Palette": "",
	"Visuals // Creative Duration (Seconds)": "",
	"Visuals // Animation/CGI Used": "",
	"Visuals // Production Quality": "",
	"Visuals // Setting": "",
	"Visuals // Nature Setting": "",
	"Visuals // Scientific Setting": "",
	"Visuals // Real Life vs. Staged": "",
	"Visuals // Individual vs. Group Focus": "",
	"Visuals // On-Screen Text": "",
	"Visuals // Text Style": "",
	"Visuals // Text Size": "",
	"Visuals // Beauty Appeal": "",
	"Visuals // Ingredient Visual": "",
	"Visuals // Horizontal vs. Vertical": "",
	"Audio // Audio Type": "",
	"Audio // Voiceover vs. Talent": "",
	"Audio // Localized Language": "",
	"Audio // Sound Effects Usage": "",
	"Talent // Talent Type": "",
	"Talent // Number of KOLs": "",
	"Talent // Brand Ambassador Used": "",
	"Messaging // Messaging Summary": "",
	"Messaging // Emotional Tone": "",
	"Messaging // Key Product Benefit Highlighted": "",
	"Messaging // Emotional Appeal": "",
	"Messaging // Storytelling Used": "",
	"Messaging // Call to Action (CTA)": "",
	"Meaningful & Different // Social Impact": "",
	"Meaningful & Different // Emotional Depth": "",
	"Meaningful & Different // Authenticity": "",
	"Meaningful & Different // Uniqueness of Concept": "",
	"Meaningful & Different // Execution Style": "",
	"Meaningful & Different // Target Surprise": ""
}
"""

# Playwright settings
BROWSER_HEADLESS = False  # Set to True for headless mode
SLOW_MO = 100  # Milliseconds between actions (for debugging)
TIMEOUT = 60000  # Default timeout in milliseconds

# Download settings
MAX_RETRIES = 3
DOWNLOAD_TIMEOUT = 120  # Seconds
BATCH_SIZE = 5  # Number of videos to download per batch
DELETE_AFTER_UPLOAD = True  # Delete video file after successful AI upload

# Supported platforms
SUPPORTED_PLATFORMS = ["tiktok", "instagram"]
