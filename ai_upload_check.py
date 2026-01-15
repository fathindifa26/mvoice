from pathlib import Path
import csv
from utils import METRICS_COLUMNS

def is_row_empty_or_header(row: dict) -> bool:
    """
    Return True if all metric columns are empty or contain only header-like values (column names),
    meaning the row is not a valid AI result and should be retried.
    """
    # Check if all metric columns are empty or just echoing the column name
    for col in METRICS_COLUMNS:
        val = row.get(col, "").strip()
        if val and val.lower() != col.lower():
            return False  # At least one real value exists
    return True


def should_attempt_ai_upload(url: str, output_file: Path) -> bool:
    """
    Return True if the given URL in output.csv is missing, or its row is empty/just header-like.
    """
    if not output_file.exists():
        return True
    with open(output_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get('url', '').strip() == url.strip():
                # Found the row for this URL
                if is_row_empty_or_header(row):
                    return True  # Needs retry
                else:
                    return False  # Already has valid result
    return True  # Not found at all, so should attempt
