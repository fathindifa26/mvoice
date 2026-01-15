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

# Ensure downloads directory exists
DOWNLOADS_DIR.mkdir(exist_ok=True)

# AI Platform settings
AI_URL = "https://imagine.wpp.ai/chat/zepYR9RpFQid3NJY7I7MY/foundational"

# Default prompt template (can be customized)
DEFAULT_PROMPT = """Please analyze the video based on the following metrics and provide the results in a table format with two columns: 'Metrics' and 'Value'.
 
Metrics:
 
Business Unit: [e.g., Beauty & Wellbeing, Food & Beverage] Category: [e.g., Ice Cream, Skincare] Brand: [e.g., AICE, Dove] Platform: [e.g., Facebook, Instagram, YouTube] Creative Link: [Full URL of the creative] Period: [Date of the creative] Brand Presence // First Product Appearance (Seconds): [Time in seconds when the product with the logo first appears] Brand Presence // First Product Appearance (%): [(First Product Appearance Seconds / Total Creative Duration) * 100] Brand Presence // First Standalone Logo Appearance (Seconds): [Time in seconds when the standalone logo first appears] Brand Presence // First Standalone Logo Appearance (%): [(First Standalone Logo Appearance Seconds / Total Creative Duration) * 100] Brand Presence // Brand Logo Visibility - Standalone: [Yes/No] Brand Presence // Brand Logo Visibility - On Product: [Yes/No] Brand Presence // Brand Prominence: [High/Medium/Low] Brand Presence // Brand Appearance Count: [Numerical count] Brand Presence // Other Brands Present: [List any other brands featured, if applicable] Visuals // Visual Style: [Human/Cartoon/Mix/Product Showcase/Other (specify)] Visuals // Color Palette: [Describe dominant colors and overall palette] Visuals // Creative Duration (Seconds): [Duration in seconds] Visuals // Animation/CGI Used: [Yes/No] Visuals // Production Quality: [High/Medium/Low] Visuals // Setting: [Urban/Rural/Mix/Indoor/Outdoor/Home/Studio/Other (specify)] Visuals // Nature Setting: [Yes/No] Visuals // Scientific Setting: [Yes/No] Visuals // Real Life vs. Staged: [Real Life/Set/Mix] Visuals // Individual vs. Group Focus: [Individual/Group/Mix] Visuals // On-Screen Text: [Yes/No] Visuals // Text Style: [Bold/Plain/Mix] Visuals // Text Size: [Big/Small/Medium] Visuals // Beauty Appeal: [High/Medium/Low/Not Applicable] Visuals // Ingredient Visual: [Yes/No] Visuals // Horizontal vs. Vertical: [Horizontal/Vertical/Square] Audio // Audio Type: [Original Music/Known Music/No Music/Dialogue/Sound Effects/Other (specify)] Audio // Voiceover vs. Talent: [Voiceover/Talent/Both/Neither] Audio // Localized Language: [Yes/No] Audio // Sound Effects Usage: [Heavy/Light/None] Talent // Talent Type: [Known Celebrity/Influencer/KOL/Actor/Model/Everyday People/Cartoon Characters/No Talent/Other (specify)] Talent // Number of KOLs: [Numerical count] Talent // Brand Ambassador Used: [Yes/No] Messaging // Messaging Summary: [Write a concise summary of the creative's message in at least 20 words] Messaging // Emotional Tone: [List primary emotions evoked, e.g., Joyful, Inspiring, Humorous] Messaging // Key Product Benefit Highlighted: [Briefly summarize the main benefit emphasized] Messaging // Emotional Appeal: [High/Medium/Low] Messaging // Storytelling Used: [Yes/No] Messaging // Call to Action (CTA): [Describe the CTA] Meaningful & Different // Social Impact: [Yes/No; If Yes, briefly describe the social impact] Meaningful & Different // Emotional Depth: [Check all that apply: Heartwarming, Inspiring, Thought-Provoking, Humorous, Nostalgic, Empowering, Relatable, Other (specify)] Meaningful & Different // Authenticity: [High/Medium/Low] Meaningful & Different // Uniqueness of Concept: [1 (Clichéd) to 5 (Highly Original)] Meaningful & Different // Execution Style (Unique Elements): [Describe any distinctive visual or audio elements] Meaningful & Different // Target Surprise: [Yes/No; If Yes, explain how the target audience or messaging is unexpected]"""

# Playwright settings
BROWSER_HEADLESS = False  # Set to True for headless mode
SLOW_MO = 100  # Milliseconds between actions (for debugging)
TIMEOUT = 60000  # Default timeout in milliseconds

# Download settings
MAX_RETRIES = 3
DOWNLOAD_TIMEOUT = 120  # Seconds

# Supported platforms
SUPPORTED_PLATFORMS = ["tiktok", "instagram"]
