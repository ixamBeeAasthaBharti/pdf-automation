from pathlib import Path
import fitz
import json

# =====================================================
# PATHS  (legacy defaults — used when called standalone)
# =====================================================

ROOT = Path(__file__).parent.parent

_DEFAULT_INPUT_DIR = ROOT / "input"
_DEFAULT_IMAGE_DIR = ROOT / "images"
_DEFAULT_IMAGE_MAP = ROOT / "image_map.json"


import re
from collections import Counter

def compute_body_size(doc) -> float:
    counts = Counter()
    for page in doc:
        for block in page.get_text("dict").get("blocks", []):
            if block.get("type") == 0:
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        text = span.get("text", "").strip()
                        if text:
                            counts[round(span.get("size", 12))] += len(text)
    return counts.most_common(1)[0][0] if counts else 12

def is_cover_page(page, body_size: float) -> bool:
    """
    Analyzes the first page to heuristically determine if it is a cover page.
    A cover page is characterized by:
      - Low content density (low total character count)
      - Dominance of large title/heading text rather than body text
      - Absence of standard structured elements like tables, bullets, numbered questions,
        or multi-line paragraph text blocks.
    """
    # 1. Quick-reject if tables are present (almost never on cover pages)
    try:
        tables = page.find_tables()
        if tables and len(tables.tables) > 0:
            return False
    except Exception:
        pass

    text_dict = page.get_text("dict")
    blocks = text_dict.get("blocks", [])
    
    # Filter for blocks that actually contain visible text
    text_blocks = []
    for b in blocks:
        if b.get("type", 0) == 0:
            # Reconstruct the string in the block
            block_text = "".join(
                "".join(s.get("text", "") for s in line.get("spans", []))
                for line in b.get("lines", [])
            ).strip()
            if block_text:
                text_blocks.append((b, block_text))
                
    if not text_blocks:
        return True  # Empty/purely graphical first page is treated as a cover

    # 2. Extract layout and character-level signals
    total_chars = 0
    body_chars = 0
    header_chars = 0
    line_count = 0
    
    has_bullets = False
    has_questions = False
    has_long_paragraphs = False
    
    # Check for question prefixes (e.g. "Q1.", "Ques 2.") or ending question marks
    question_pattern = re.compile(r'(^(q|ques|question|प्रश्|प्रश्न)\s*\d+[\.\s\:\-]|[\?？][\s]*$)', re.IGNORECASE)

    for block, block_text in text_blocks:
        lines = block.get("lines", [])
        
        # Check if the block represents normal paragraph content
        visible_line_count = sum(1 for l in lines if "".join(s.get("text", "") for s in l.get("spans", [])).strip())
        if len(block_text) > 150 and visible_line_count >= 3:
            has_long_paragraphs = True
            
        if question_pattern.search(block_text):
            has_questions = True

        for line in lines:
            spans = [s for s in line.get("spans", []) if s.get("text", "").strip()]
            if not spans:
                continue
                
            line_count += 1
            
            # Check for bullet symbols
            first_char = spans[0].get("text", "").strip()
            first_font = spans[0].get("font", "")
            if "wingdings" in first_font.lower() or "webdings" in first_font.lower() or first_char in ("•", "·", "◆", "▪", "▸", "►", "‣", "–", "—", "✓", "✔", "ü"):
                has_bullets = True

            for span in spans:
                text = span.get("text", "")
                length = len(text)
                total_chars += length
                size = span.get("size", 12)
                
                # Compare font sizes to estimate headers vs body text
                if abs(size - body_size) <= 1.5:
                    body_chars += length
                elif size > body_size + 2.0:
                    header_chars += length

    # 3. Rule Evaluation (Signal combination)
    # If standard page components exist, it's not a cover page
    if has_long_paragraphs or has_bullets or has_questions:
        return False

    # High line density or high block counts imply a content page
    if line_count > 25 or len(text_blocks) > 8:
        return False

    # Significant amount of body text implies a content page
    if body_chars > 300:
        return False

    # Large amount of overall text content implies a content page
    if total_chars > 800:
        return False

    # Cover pages typically have high proportion of headers/titles
    if total_chars > 0 and (header_chars / total_chars) > 0.5:
        return True

    # Very sparse pages (< 500 characters) are treated as cover pages
    if total_chars < 500:
        return True

    return False


def extract_images(
    pdf_file: Path = None,
    image_dir: Path = None,
    image_map_path: Path = None,
) -> bool:
    """
    Extract image blocks from a PDF and save them as PNGs.

    Parameters (all optional — falls back to legacy global paths):
        pdf_file       : Path to the source PDF (default: first PDF in input/)
        image_dir      : Directory to save extracted PNG images (default: images/)
        image_map_path : Path to write image_map.json (default: image_map.json at root)

    Returns:
        bool           : True if Page 1 is detected as a cover page, False otherwise.
    """
    # ------------------------------------------------------------------ #
    # Resolve paths                                                         #
    # ------------------------------------------------------------------ #
    if pdf_file is None:
        pdf_files = sorted(_DEFAULT_INPUT_DIR.glob("*.pdf"))
        if len(pdf_files) != 1:
            raise RuntimeError(
                f"Expected exactly one PDF in {_DEFAULT_INPUT_DIR}, "
                f"found {len(pdf_files)}."
            )
        pdf_file = pdf_files[0]

    if image_dir is None:
        image_dir = _DEFAULT_IMAGE_DIR

    if image_map_path is None:
        image_map_path = _DEFAULT_IMAGE_MAP

    pdf_file       = Path(pdf_file)
    image_dir      = Path(image_dir)
    image_map_path = Path(image_map_path)

    image_dir.mkdir(parents=True, exist_ok=True)

    # -------------------------------------------------
    # Cleanup previous images in this dir
    # -------------------------------------------------
    for f in image_dir.glob("*.png"):
        f.unlink()

    doc = fitz.open(pdf_file)

    image_map   = []
    image_count = 0

    # Auto-detect cover page
    body_size = compute_body_size(doc)
    skip_cover = is_cover_page(doc[0], body_size)
    if skip_cover:
        print("[pymupdf_image_extractor] Auto-detected cover page on Page 1. Skipping Page 1 image extraction.")
    else:
        print("[pymupdf_image_extractor] Page 1 is content (not a cover page). Extracting Page 1 images.")

    # -------------------------------------------------
    # Extract figures
    # -------------------------------------------------

    for page_number, page in enumerate(doc):

        print(f"Processing page {page_number + 1}")

        blocks = page.get_text("dict")["blocks"]

        # Get only image blocks from page
        image_blocks = [b for b in blocks if b["type"] == 1]

        # Skip cover page if detected
        if page_number == 0 and skip_cover:
            continue

        page_height = page.rect.height

        for block in image_blocks:

            x0, y0, x1, y1 = block["bbox"]

            # Skip header logos (top 90pt of page) and footer logos (bottom 50pt of page)
            if y0 < 90 or y1 > (page_height - 50):
                print(f"   Skipping header/footer logo on page {page_number + 1} at bbox ({x0:.1f}, {y0:.1f}, {x1:.1f}, {y1:.1f})")
                continue

            filename = f"page_{page_number+1:03d}_img_{image_count:03d}.png"

            try:
                # Normalize coordinates to handle inverted rectangles (e.g. x1 < x0 or y1 < y0)
                rect = fitz.Rect(x0, y0, x1, y1).normalize()
                # Intersect with the page rectangle to avoid cropping off-page content
                rect = rect.intersect(page.rect)
                
                # Skip empty or extremely small/invalid rectangles to avoid PyMuPDF bandwriter crashes
                if rect.is_empty or rect.width <= 2 or rect.height <= 2:
                    print(f"   Skipping empty/tiny image on page {page_number + 1} at bbox ({x0:.1f}, {y0:.1f}, {x1:.1f}, {y1:.1f})")
                    continue

                pix = page.get_pixmap(
                    matrix=fitz.Matrix(4, 4),
                    clip=rect,
                    alpha=True,
                )

                pix.save(image_dir / filename)

                image_map.append(
                    {
                        "id":       f"IMAGE_{image_count:03d}",
                        "page":     page_number + 1,
                        "filename": filename,
                        "bbox":     [x0, y0, x1, y1],
                    }
                )

                image_count += 1
            except Exception as e:
                print(f"   Warning: Skipping corrupt image on page {page_number + 1} due to error: {e}")

    # -------------------------------------------------
    # Save mapping
    # -------------------------------------------------

    image_map_path.parent.mkdir(parents=True, exist_ok=True)
    image_map_path.write_text(
        json.dumps(image_map, indent=4),
        encoding="utf-8",
    )

    print("\n===================================")
    print("Image Extraction Complete")
    print(f"Pages  : {len(doc)}")
    print(f"Images : {image_count}")
    print(f"Saved  : {image_dir}")
    print("===================================")
    
    doc.close()
    return skip_cover


if __name__ == "__main__":
    extract_images()