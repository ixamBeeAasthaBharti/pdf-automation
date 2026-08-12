"""
table_extractor.py
==================
Post-processing step that runs AFTER gemini_runner.py and BEFORE merger.py.

For every <img> in processed chunks:
  - Sends the image to Gemini with a focused "is this a table?" prompt.
  - If YES  -> replaces the <img> (or its parent <figure>) with full HTML:
              extracted-table-block > (headings) + table-responsive > table
  - If SKIP -> leaves the <img> untouched.

Backups:
  Each chunk is backed up to  processed/originals/chunk_NNN.html
  before any modification. Re-running with --force restores from backup first.

Usage:
  python scripts/table_extractor.py           # normal run (skips already-done chunks)
  python scripts/table_extractor.py --force   # restore backups & re-run everything
"""

from pathlib import Path
import os
import sys
import time
import shutil
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from google import genai
from google.genai import types

# =====================================================
# LOAD ENVIRONMENT
# =====================================================
load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise ValueError("GEMINI_API_KEY not found in .env")

client = genai.Client(api_key=API_KEY)

# =====================================================
# PATHS
# =====================================================
ROOT         = Path(__file__).parent.parent
PROCESSED_DIR = ROOT / "processed"
ORIGINALS_DIR = PROCESSED_DIR / "originals"   # backup location
IMAGE_DIR    = ROOT / "images"

# How many seconds to wait between API calls (free tier = 5 RPM)
RPM_DELAY = 13   # 60s / 5 = 12s; 13s gives a small buffer

# =====================================================
# PROMPT
# =====================================================
TABLE_PROMPT = """Look at this image carefully.

STEP 1 — CLASSIFY: Does this image contain a table (a grid with rows and columns)?

If NO: output exactly the word SKIP and nothing else.

If YES: proceed to STEP 2.

STEP 2 — EXTRACT EVERYTHING VISIBLE in the image in reading order, top to bottom:

A) Any text that appears ABOVE the table (titles, headings, numbered labels, topic names,
   chapter headings, italic captions, etc.) must be preserved. Wrap each line appropriately:
   - Bold heading or topic title          -> <h4 class="extracted-heading">...</h4>
   - Numbered label ("3. Women Directors related guidelines") -> <h4 class="extracted-heading">...</h4>
   - Italic or smaller subtitle/caption   -> <p class="extracted-subheading">...</p>

B) The table itself — wrap it in:
   <div class="table-responsive">
     <table>
       <thead><tr><th>...</th></tr></thead>
       <tbody><tr><td>...</td></tr></tbody>
     </table>
   </div>
   Rules:
   - Preserve every cell's content exactly.
   - Use <th> in <thead> for header rows.
   - Use colspan / rowspan for merged cells.
   - Preserve bullet points inside cells as <ul><li>.
   - Do not summarise or abbreviate anything.

C) Any text that appears BELOW the table -> <p class="extracted-note">...</p>

Wrap A + B + C together in ONE outer div:
<div class="extracted-table-block">
  ...headings...
  <div class="table-responsive"><table>...</table></div>
  ...footnotes...
</div>

Do NOT output markdown code fences.
Output only the HTML. No explanation.
"""


# =====================================================
# HELPERS
# =====================================================

def backup_chunk(chunk_file: Path) -> Path:
    """Copy the original processed file to originals/ before any modification."""
    ORIGINALS_DIR.mkdir(exist_ok=True)
    backup = ORIGINALS_DIR / chunk_file.name
    if not backup.exists():
        shutil.copy2(chunk_file, backup)
        print(f"  Backed up -> originals/{chunk_file.name}")
    return backup


def restore_from_backup(chunk_file: Path):
    """Overwrite the processed file with its original backup."""
    backup = ORIGINALS_DIR / chunk_file.name
    if backup.exists():
        shutil.copy2(backup, chunk_file)
        print(f"  Restored {chunk_file.name} from backup.")
    else:
        print(f"  No backup found for {chunk_file.name} — skipping restore.")


def call_gemini(image_bytes: bytes) -> str:
    """Call Gemini with the table prompt + image. Returns the stripped response text."""
    response = client.models.generate_content(
        model="gemini-3.5-flash",
        contents=[
            TABLE_PROMPT,
            types.Part.from_bytes(data=image_bytes, mime_type="image/png"),
        ],
        config=types.GenerateContentConfig(temperature=0),
    )
    result = response.text.strip()

    # Strip markdown fences if the model wrapped its output
    if result.startswith("```html"):
        result = result[7:].lstrip()
    elif result.startswith("```"):
        result = result[3:].lstrip()
    if result.endswith("```"):
        result = result[:-3].rstrip()

    return result.strip()


def build_replacement(result: str, block_soup: BeautifulSoup):
    """
    From the raw HTML string returned by Gemini, return a BeautifulSoup Tag
    that can be inserted into the document.

    Priority:
      1. <div class="extracted-table-block"> (new format — includes headings)
      2. <div class="table-responsive">      (old format — table only)
      3. bare <table>                        (last resort)
    """
    replacement = block_soup.find("div", class_="extracted-table-block")

    if not replacement:
        replacement = block_soup.find("div", class_="table-responsive")

    if not replacement:
        table = block_soup.find("table")
        if table:
            wrapper = block_soup.new_tag("div", attrs={"class": "table-responsive"})
            table.wrap(wrapper)
            outer = block_soup.new_tag("div", attrs={"class": "extracted-table-block"})
            wrapper.wrap(outer)
            replacement = outer

    return replacement  # None if nothing usable found


# =====================================================
# MAIN EXTRACTION
# =====================================================

def extract_tables_from_chunk(chunk_file: Path):
    backup_chunk(chunk_file)

    html = chunk_file.read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "lxml")

    images = soup.find_all("img")
    if not images:
        print("  No images found — nothing to do.")
        return False

    modified = False
    total = len(images)

    for idx, img in enumerate(images, 1):
        src = img.get("src", "")
        filename = Path(src).name
        img_path = IMAGE_DIR / filename

        if not img_path.exists():
            print(f"  [{idx}/{total}] Warning: {filename} not found on disk — skipping.")
            continue

        print(f"  [{idx}/{total}] Checking {filename} ...")

        image_bytes = img_path.read_bytes()

        for attempt in range(4):
            try:
                result = call_gemini(image_bytes)

                if result.upper() == "SKIP":
                    print("           -> Not a table.")
                else:
                    print("           -> Table detected! Replacing with HTML.")
                    block_soup = BeautifulSoup(result, "html.parser")
                    replacement = build_replacement(result, block_soup)

                    if replacement is None:
                        print("           -> Could not parse returned HTML — image kept.")
                        break

                    parent = img.parent
                    if parent and parent.name == "figure":
                        parent.replace_with(replacement)
                    else:
                        img.replace_with(replacement)

                    modified = True

                break  # Success — exit retry loop

            except Exception as e:
                err_str = str(e)
                print(f"           -> Attempt {attempt + 1} failed: {err_str[:120]}")

                if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                    wait = 30 * (attempt + 1)
                    print(f"           -> Rate limit. Waiting {wait}s ...")
                    time.sleep(wait)
                elif attempt >= 3:
                    print(f"           -> Giving up on {filename}.")
                else:
                    time.sleep(5)

        # Rate-limit delay between images to stay within free-tier RPM
        if idx < total:
            time.sleep(RPM_DELAY)

    if modified:
        chunk_file.write_text(str(soup), encoding="utf-8")
        print(f"  Saved {chunk_file.name}")
        return True

    return False


def run_table_extraction(force: bool = False):
    if not PROCESSED_DIR.exists():
        raise FileNotFoundError(f"Processed directory not found: {PROCESSED_DIR}")

    chunks = sorted(PROCESSED_DIR.glob("chunk_*.html"))
    print(f"\nFound {len(chunks)} chunks.\n")

    if force:
        print("--force mode: restoring originals first...\n")
        for chunk in chunks:
            restore_from_backup(chunk)

    total_modified = 0
    for chunk in chunks:
        print(f"\n{'=' * 56}")
        print(f"Chunk: {chunk.name}")
        print(f"{'=' * 56}")
        if extract_tables_from_chunk(chunk):
            total_modified += 1

    print(f"\n{'=' * 56}")
    print(f"Finished. Modified {total_modified}/{len(chunks)} chunks.")
    print(f"{'=' * 56}\n")


if __name__ == "__main__":
    force_flag = "--force" in sys.argv
    run_table_extraction(force=force_flag)
