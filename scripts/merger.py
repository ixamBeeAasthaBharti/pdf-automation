from pathlib import Path
from bs4 import BeautifulSoup
import json

# =====================================================
# PATHS
# =====================================================

ROOT = Path(__file__).parent.parent

PROCESSED_DIR  = ROOT / "processed"
OUTPUT_DIR     = ROOT / "output"
OUTPUT_FILE    = OUTPUT_DIR / "output.html"
ASSETS_DIR     = ROOT / "assets"
LOGO_FILE      = ASSETS_DIR / "logo.png"          # drop your logo here once
IMAGE_MAP_FILE = ROOT / "image_map.json"

OUTPUT_DIR.mkdir(exist_ok=True)


# =====================================================
# COVER PAGE BUILDER
# =====================================================

def build_cover(soup: BeautifulSoup) -> None:
    """
    Replaces the <article><header> Gemini generates with a proper
    cover page that mirrors the branded PDF title page.

    Structure extracted from the header:
      h1  → "Study Notes"  (green label on the cover)
      h2  → document title (large navy heading)
      p   → contact line   (shown at the bottom of the cover)

    The logo is read from  assets/logo.png  — drop any PNG/JPG there
    once and every PDF run will pick it up automatically.
    """

    article = soup.find("article")
    if not article:
        return

    header = article.find("header")
    if not header:
        return

    # --- Extract text from the existing header ---
    h1_tag  = header.find("h1")
    h2_tag  = header.find("h2")
    p_tag   = header.find("p")

    study_notes_text = h1_tag.get_text(strip=True) if h1_tag else "Study Notes"
    doc_title_text   = h2_tag.get_text(strip=True) if h2_tag else ""
    contact_html     = str(p_tag) if p_tag else ""

    # --- Logo img tag (relative to output/output.html) ---
    if LOGO_FILE.exists():
        logo_html = (
            '<div class="cover-logo-wrap">'
            '<img src="../assets/logo.png" alt="ixamBee" class="cover-logo-img"/>'
            '</div>'
        )
    else:
        logo_html = ""     # cover still looks fine without a logo

    # --- Build cover HTML as a separate article ---
    cover_article_html = f"""
<article class="cover-article">
  <div class="cover-page">
    {logo_html}
    <div class="cover-body">
      <p class="cover-study-notes">{study_notes_text}</p>
      <h1 class="cover-title">{doc_title_text}</h1>
    </div>
    <div class="cover-contact">
      {contact_html}
    </div>
  </div>
</article>
"""

    # Insert the cover article before the main article
    cover_soup = BeautifulSoup(cover_article_html, "html.parser")
    article.insert_before(cover_soup)

    # Decompose the original header from the content article
    header.decompose()

    # Update the <title> tag to the actual document name
    title_tag = soup.find("title")
    if title_tag and doc_title_text:
        title_tag.string = f"{study_notes_text} – {doc_title_text}"


# =====================================================
# IMAGE SIZE FIXER
# =====================================================

def fix_image_sizes(soup: BeautifulSoup) -> None:
    """
    Reads image_map.json and stamps width/height (in CSS pixels) onto
    every <img> whose src matches a known extracted image.

    This is needed because the processed chunks Gemini returns do not
    carry width/height — without this step images render at their full
    4x-oversampled PNG resolution.

    Conversion: 1 PDF point * (96 px / 72 pt) = 1.333 px
    """

    if not IMAGE_MAP_FILE.exists():
        return

    image_map = json.loads(IMAGE_MAP_FILE.read_text(encoding="utf-8"))

    PT_TO_PX = 96 / 72

    # Build lookup: filename -> (width_px, height_px)
    size_map = {}
    for entry in image_map:
        x0, y0, x1, y1 = entry["bbox"]
        size_map[entry["filename"]] = (
            round((x1 - x0) * PT_TO_PX),
            round((y1 - y0) * PT_TO_PX),
        )

    fixed = 0
    for img_tag in soup.find_all("img"):
        src = img_tag.get("src", "")
        filename = Path(src).name
        if filename in size_map:
            w, h = size_map[filename]
            img_tag["width"]  = w
            img_tag["height"] = h
            fixed += 1

    print(f"Image sizes fixed : {fixed}")


# =====================================================
# MERGE
# =====================================================

def merge_chunks():

    chunk_files = sorted(PROCESSED_DIR.glob("chunk_*.html"))

    if not chunk_files:
        raise FileNotFoundError("No processed chunks found.")

    merged_body = []

    for chunk in chunk_files:

        print(f"Reading {chunk.name}")

        html = chunk.read_text(encoding="utf-8")

        soup = BeautifulSoup(html, "lxml")

        body = soup.body

        if body:
            for child in body.contents:
                merged_body.append(str(child))
        else:
            merged_body.append(str(soup))

    # --------------------------------------------------
    # Assemble the raw HTML shell
    # --------------------------------------------------

    raw_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Study Notes</title>
<link rel="preconnect" href="https://fonts.googleapis.com"/>
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin/>
<link href="https://fonts.googleapis.com/css2?family=Lora:ital,wght@0,400;0,600;0,700;1,400;1,600&display=swap" rel="stylesheet"/>
<link rel="stylesheet" href="../styles/reader.css"/>
</head>
<body>

{''.join(merged_body)}

</body>
</html>
"""

    # Fix image src paths (chunks may still have relative "images/..." paths)
    raw_html = raw_html.replace('src="images/', 'src="../images/')

    # --------------------------------------------------
    # Post-process: inject cover page
    # --------------------------------------------------

    soup = BeautifulSoup(raw_html, "lxml")

    build_cover(soup)

    fix_image_sizes(soup)

    final_html = str(soup)

    OUTPUT_FILE.write_text(final_html, encoding="utf-8")

    logo_status = "yes" if LOGO_FILE.exists() else "no (drop assets/logo.png to add one)"

    print("\n========================================")
    print("Merge Complete")
    print(f"Chunks merged : {len(chunk_files)}")
    print(f"Logo included : {logo_status}")
    print(f"Output file   : {OUTPUT_FILE}")
    print(f"Characters    : {len(final_html):,}")
    print("========================================")


if __name__ == "__main__":
    merge_chunks()