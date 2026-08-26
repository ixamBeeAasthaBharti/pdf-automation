"""
Convert a PDF to clean, semantic, flowable HTML using PyMuPDF.

This script parses a PDF directly, extracts layout structure (headings, lists,
paragraphs, tables, images), ignores header/footer elements, and outputs a 
fully responsive, semantic HTML5 document.

Usage:
    python scripts/pdf_html.py input.pdf output.html --start 1 --end 5
"""

import argparse
import base64
import html
import sys
from pathlib import Path

import re
import pymupdf as fitz

# ====== EDIT THESE TWO LINES ======
PDF_PATH = "C:/Users/AASTHA/Desktop/pdf automation/storage/queue/37556/document.pdf"
OUTPUT_DIR = "C:/Users/AASTHA/Desktop/pdf automation/storage/"
# ===================================

# Adobe "Symbol" font built-in encoding -> real Unicode.
SYMBOL_FONT_MAP = {
    0x20: " ", 0x21: "!", 0x23: "#", 0x25: "%", 0x26: "&",
    0x28: "(", 0x29: ")", 0x2A: "∗", 0x2B: "+", 0x2C: ",",
    0x2D: "−", 0x2E: ".", 0x2F: "/",
    0x3A: ":", 0x3B: ";", 0x3C: "<", 0x3D: "=", 0x3E: ">", 0x3F: "?",
    0x40: "≅",
    0x41: "Α", 0x42: "Β", 0x43: "Χ", 0x44: "∆",
    0x45: "Ε", 0x46: "Φ", 0x47: "Γ", 0x48: "Η",
    0x49: "Ι", 0x4A: "ϑ", 0x4B: "Κ", 0x4C: "Λ",
    0x4D: "Μ", 0x4E: "Ν", 0x4F: "Ο",
    0x50: "Π", 0x51: "Θ", 0x52: "Ρ", 0x53: "Σ",
    0x54: "Τ", 0x55: "Υ", 0x56: "ς", 0x57: "Ω",
    0x58: "Ξ", 0x59: "Ψ", 0x5A: "Ζ",
    0x5B: "[", 0x5C: "∴", 0x5D: "]", 0x5E: "⊥", 0x5F: "_",
    0x61: "α", 0x62: "β", 0x63: "χ", 0x64: "δ",
    0x65: "ε", 0x66: "φ", 0x67: "γ", 0x68: "η",
    0x69: "ι", 0x6A: "ϕ", 0x6B: "κ", 0x6C: "λ",
    0x6D: "μ", 0x6E: "ν", 0x6F: "ο",
    0x70: "π", 0x71: "θ", 0x72: "ρ", 0x73: "σ",
    0x74: "τ", 0x75: "υ", 0x76: "ϖ", 0x77: "ω",
    0x78: "ξ", 0x79: "ψ", 0x7A: "ζ",
    0x7B: "{", 0x7C: "|", 0x7D: "}", 0x7E: "∼",
    0xA1: "ϒ", 0xA2: "′", 0xA3: "≤", 0xA4: "⁄",
    0xA5: "∞", 0xA6: "ƒ", 0xA7: "♣", 0xA8: "♦",
    0xA9: "♥", 0xAA: "♠", 0xAB: "↔", 0xAC: "←",
    0xAD: "↑", 0xAE: "→", 0xAF: "↓",
    0xB0: "°", 0xB1: "±", 0xB2: "″", 0xB3: "≥",
    0xB4: "×", 0xB5: "∝", 0xB6: "∂", 0xB7: "•",
    0xB8: "÷", 0xB9: "≠", 0xBA: "≡", 0xBB: "≈",
    0xBC: "…",
    0xD1: "∇", 0xD2: "®", 0xD3: "©", 0xD4: "™",
    0xD5: "∏", 0xD6: "√", 0xD7: "⋅", 0xD8: "¬",
    0xD9: "∧", 0xDA: "∨",
    0xE0: "◊",
    0xE5: "∑",
    0xF2: "∫",
    # Wingdings check mark (U+F0FC -> offset 0xFC)
    0xFC: "✓",
}

def decode_symbol_font(text: str) -> str:
    return "".join(SYMBOL_FONT_MAP.get(ord(c) - 0xF000, c) for c in text)

PAGE_TEMPLATE = """
<section class="pdf-page">
{content}
</section>
""".strip()

DOC_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{title}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Literata:ital,opsz,wght@0,7..72,200..900;1,7..72,200..900&family=Outfit:wght@400;600;700&display=swap" rel="stylesheet">
</head>
<body>
<article>
<main>
{pages}
</main>
</article>
</body>
</html>
"""

def compute_body_size(doc: fitz.Document) -> float:
    """Most common font size (weighted by character count) across the doc.
    Used to tell body text apart from headings.
    """
    from collections import Counter
    counts = Counter()
    for page in doc:
        for block in page.get_text("dict").get("blocks", []):
            if block.get("type") != 0:
                continue
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    text = span.get("text", "")
                    if not text.strip():
                        continue
                    counts[round(span.get("size", 12))] += len(text)
    return counts.most_common(1)[0][0] if counts else 12

def decode_span_text(span: dict) -> str:
    text = span.get("text", "")
    if not text:
        return ""
    # Clean CID encoding quotes artifacts (e.g. low double quotes „ -> ", high curly quotes “ ” -> ")
    text = text.replace("„", '"').replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")
    font = span.get("font", "")
    if "Symbol" in font:
        return decode_symbol_font(text)
    if "Wingdings" in font or "Webdings" in font:
        res = []
        for c in text:
            val = ord(c)
            if val == 0xF0FC or val == 0xFC or val == 0x2713 or val == 0x2714:
                res.append("✓")
            else:
                res.append("•")
        return "".join(res)
    return text


def render_span_semantic(span: dict) -> str:
    text = decode_span_text(span)
    if not text.strip():
        return ""
    font = span.get("font", "")
    flags = span.get("flags", 0)
    is_bold = "Bold" in font or bool(flags & 1)
    is_italic = "Italic" in font or "Oblique" in font or bool(flags & 2)
    is_underline = "Underline" in font or bool(flags & 4) or span.get("is_underline", False)
    escaped_text = html.escape(text)
    
    if is_underline:
        escaped_text = f"<u>{escaped_text}</u>"
    if is_bold:
        escaped_text = f"<strong>{escaped_text}</strong>"
    if is_italic:
        escaped_text = f"<em>{escaped_text}</em>"
    return escaped_text


def is_cover_page(page: fitz.Page, body_size: float) -> bool:
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

COMMON_WORD_ABBREVS = {
    "ibid", "etc", "note", "vol", "no", "vs", "dr", "mr", "ms", "inc",
    "ltd", "co", "fig", "page", "total", "ref", "sec", "art", "para", "ver"
}

def is_alphanumeric_prefix(text: str) -> bool:
    """Return True if text is a valid list prefix like '1.', 'a.', 'i.', '(a)', 'b)'."""
    if not text:
        return False
    text_clean = text.strip()

    # Match numeric list prefix e.g. "1.", "(1)", "1)"
    if re.match(r'^(\(?\d{1,3}\)[\.\)]?|\d{1,3}[\.\)])$', text_clean):
        return True

    # Match letter / roman numeral list prefix e.g. "a.", "(a)", "a)", "i.", "ii)", "(iii)"
    m = re.match(r'^(\(?([a-zA-Z]{1,3}|[IVXivx]{1,4})\)[\.\)]?|([a-zA-Z]{1,3}|[IVXivx]{1,4})[\.\)])$', text_clean)
    if m:
        raw_letters = (m.group(2) or m.group(3) or "").lower()
        if raw_letters in COMMON_WORD_ABBREVS:
            return False
        return True

    return False


def is_bullet_span(span: dict) -> bool:

    font = span.get("font", "")
    if "Wingdings" in font or "Webdings" in font:
        return True
    decoded = decode_span_text(span).strip()
    if decoded in ("-", "–", "—", "•", "·", "◆", "▪", "▸", "►", "‣", "✓", "✔", "ü", "\u2713", "\u2714", "\uf0fc"):
        return True

    if "Courier" in font and decoded == "o":
        return True
    
    # Check for standalone numbered/lettered list prefixes (e.g. "1.", "a.", "(i)", "b)")
    import re
    pattern = r'^(\(?([0-9]+|[a-z]+|[IVX]+)\)[\.\)]?|([0-9]+|[a-z]+|[IVX]+)[\.\)])$'
    if re.match(pattern, decoded):
        return True
        
    return False

def is_standalone_line_prefix(text: str) -> bool:
    """Check if a line text starts an MCQ option, explanation, passage, question header, or dash bullet."""
    if not text:
        return False
    text_clean = text.strip()
    # Dash bullet lines e.g. "- ", "– ", "— "
    if re.match(r'^[-–—]\s+', text_clean):
        return True
    # MCQ options e.g. "A. ", "B. ", "C. ", "D. ", "E. ", "(A)", "(B)", "a)", "b)"
    if re.match(r'^(?:[A-E]\.|\([A-E]\)|[a-e]\))\s*', text_clean):
        return True
    # Explanation / Passage / Question prefixes e.g. "Explanation-", "Explanation:", "Passage -", "Passage:"
    if re.match(r'^(Explanation|Passage|Note|Solution)\b', text_clean, re.IGNORECASE):
        return True
    # Question numbers e.g. "6. ", "15. ", "Q1. ", "Q.1 "
    if re.match(r'^(?:Q(?:ues)?\.?\s*\d+|\d{1,3}\.)\s+[A-Z]', text_clean):
        return True
    return False


def format_paragraph_dashes_and_spaces(para_text: str) -> str:
    """Return paragraph text as-is without replacing dashes with arrows."""
    return para_text





def is_pink_heading_block(bbox, page) -> bool:

    if page is None:
        return False
    bx0, by0, bx1, by1 = bbox
    cx = (bx0 + bx1) / 2
    cy = (by0 + by1) / 2
    for d in page.get_drawings():
        fill = d.get("fill")
        if fill and len(fill) == 3:
            r, g, b = fill
            if 0.94 <= r <= 0.96 and 0.84 <= g <= 0.88 and 0.84 <= b <= 0.88:
                rect = d.get("rect")
                if rect:
                    if rect.x0 - 5 <= cx <= rect.x1 + 5 and rect.y0 - 5 <= cy <= rect.y1 + 5:
                        return True
    return False

def split_block_semantically(block: dict) -> list:
    lines = block.get("lines", [])
    if not lines:
        return []
        
    split_blocks = []
    current_lines = []
    
    for line in lines:
        spans = [s for s in line.get("spans", []) if s.get("text", "").strip()]
        if not spans:
            continue
            
        is_bullet = is_bullet_span(spans[0])
        is_all_bold = all("Bold" in s.get("font", "") for s in spans)
        text_content = "".join(decode_span_text(s) for s in spans).strip()
        is_heading = is_all_bold and not is_bullet and len(text_content) < 80 and not text_content.endswith(".")
        
        # If it's a bullet or a heading, it marks the start of a new section.
        # So we flush the previous section (if any) first.
        if is_bullet or is_heading:
            if current_lines:
                new_block = block.copy()
                new_block["lines"] = current_lines
                sx0 = min(l["bbox"][0] for l in current_lines)
                sy0 = min(l["bbox"][1] for l in current_lines)
                sx1 = max(l["bbox"][2] for l in current_lines)
                sy1 = max(l["bbox"][3] for l in current_lines)
                new_block["bbox"] = (sx0, sy0, sx1, sy1)
                split_blocks.append(new_block)
                current_lines = []
                
        current_lines.append(line)
            
    if current_lines:
        new_block = block.copy()
        new_block["lines"] = current_lines
        sx0 = min(l["bbox"][0] for l in current_lines)
        sy0 = min(l["bbox"][1] for l in current_lines)
        sx1 = max(l["bbox"][2] for l in current_lines)
        sy1 = max(l["bbox"][3] for l in current_lines)
        new_block["bbox"] = (sx0, sy0, sx1, sy1)
        split_blocks.append(new_block)
        
    return split_blocks

def classify_heading(visible_lines: list, body_size: float):
    """Return 'h2' or 'h3' if block reads as a genuine standalone heading."""
    if len(visible_lines) != 1:
        return None
    spans = [s for s in visible_lines[0].get("spans", []) if s.get("text", "").strip()]
    if not spans:
        return None
    if is_bullet_span(spans[0]):
        return None
    if not all("Bold" in s.get("font", "") for s in spans):
        return None
    text = "".join(decode_span_text(s) for s in spans).strip()
    if len(text) <= 2 or text.isdigit():
        return None

    # Full sentences ending with periods are paragraphs, not headings
    if text.endswith(".") and len(text) > 40:
        return None

    max_size = max(s.get("size", 12) for s in spans)
    ratio = max_size / body_size if body_size else 1
    if ratio >= 1.18:
        return "h2"
    if ratio >= 1.08 and len(text) <= 100:
        return "h3"
    return None


def is_inside_table(bbox, tables) -> bool:
    """
    Return True only when the center of a text block falls inside a
    *validated* table bbox.

    Important: this function must never be used with raw page.find_tables()
    results because PyMuPDF can occasionally produce a false-positive table
    covering a large portion of the page.
    """
    bx0, by0, bx1, by1 = bbox
    cx = (bx0 + bx1) / 2
    cy = (by0 + by1) / 2

    for t in tables:
        tx0, ty0, tx1, ty1 = t.bbox
        if tx0 <= cx <= tx1 and ty0 <= cy <= ty1:
            return True
    return False


def image_overlaps_table(bbox, tables, threshold=0.50) -> bool:
    """
    Return True when the overlap between an image bbox and any validated table
    bbox is greater than or equal to the specified threshold (default 50%).
    """
    img_rect = fitz.Rect(bbox)
    img_area = img_rect.width * img_rect.height
    if img_area <= 0:
        return False

    for t in tables:
        tbl_rect = fitz.Rect(t.bbox)
        intersection = img_rect & tbl_rect
        if not intersection.is_empty:
            intersection_area = intersection.width * intersection.height
            if (intersection_area / img_area) >= threshold:
                return True
    return False


def is_watermark_text(text: str) -> bool:
    """Check if a text string is a watermark (e.g. www.ixambee.com)."""
    if not text:
        return False
    norm = text.strip().lower().replace(" ", "")
    if "www.ixambee.com" in norm or "ixambee.com" in norm or "www.ixambee" in norm:
        return True
    if norm in ("ixambee", "prepare50%faster"):
        return True
    return False


def is_watermark_image(block: dict, page: fitz.Page) -> bool:
    """Check if an image block is a full-page or background watermark image."""
    bbox = block.get("bbox", (0, 0, 0, 0))
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    page_w = page.rect.width
    page_h = page.rect.height

    # Large background watermark spanning >45% page width and >35% page height near center
    if w > page_w * 0.45 and h > page_h * 0.35:
        cx = (bbox[0] + bbox[2]) / 2
        cy = (bbox[1] + bbox[3]) / 2
        if abs(cx - page_w / 2) < 100 and abs(cy - page_h / 2) < 120:
            return True

    return False


def is_valid_vector_diagram(cluster: fitz.Rect, page: fitz.Page, text_dict: dict, valid_tables: list) -> bool:
    """
    Determine whether a candidate drawing cluster is a genuine vector diagram/flowchart
    vs. a decorative background text region or watermark.
    """
    # 1. Dimension check
    if cluster.width < 50 or cluster.height < 30:
        print(f"  [DIAGRAM REJECT] bbox={tuple(cluster)} reason=too_small", file=sys.stderr)
        return False

    cluster_area = cluster.width * cluster.height

    # 2. Table overlap check
    for t in valid_tables:
        tb = fitz.Rect(t.bbox)
        intersect = cluster & tb
        if not intersect.is_empty:
            if (intersect.width * intersect.height) / cluster_area > 0.2:
                print(f"  [DIAGRAM REJECT] bbox={tuple(cluster)} reason=overlaps_table", file=sys.stderr)
                return False

    # 3. Inspect vector drawings inside the cluster
    all_drawings = page.get_drawings()
    total_drawings = 0
    meaningful_drawings = 0

    for d in all_drawings:
        r = fitz.Rect(d["rect"])
        if cluster.x0 - 5 <= r.x0 and r.x1 <= cluster.x1 + 5 and cluster.y0 - 5 <= r.y0 and r.y1 <= cluster.y1 + 5:
            total_drawings += 1
            fill = d.get("fill")
            # Skip light gray watermark fills
            if fill and len(fill) == 3:
                r_val, g_val, b_val = fill
                if abs(r_val - g_val) < 0.02 and abs(g_val - b_val) < 0.02 and 0.7 <= r_val <= 0.9:
                    continue

            # Simple decorative rectangular background fills (wide/shallow rectangles used as text highlights)
            items = d.get("items", [])
            is_simple_bg_rect = False
            if len(items) <= 2 and fill is not None:
                if r.width > 60 and r.height < 35:
                    is_simple_bg_rect = True
                elif r.width > cluster.width * 0.8 and r.height < cluster.height * 0.5:
                    is_simple_bg_rect = True

            if not is_simple_bg_rect:
                meaningful_drawings += 1

    # 4. Inspect selectable text inside the cluster
    text_blocks_count = 0
    text_line_count = 0
    total_text_area = 0.0

    for tb in text_dict.get("blocks", []):
        if tb.get("type", 0) != 0:
            continue
        tb_bbox = tb.get("bbox", (0, 0, 0, 0))
        tb_rect = fitz.Rect(tb_bbox)
        tb_area = tb_rect.width * tb_rect.height
        if tb_area <= 0:
            continue

        intersect = cluster & tb_rect
        if not intersect.is_empty:
            inter_area = intersect.width * intersect.height
            if (inter_area / tb_area) >= 0.3:
                text_blocks_count += 1
                lines = tb.get("lines", [])
                text_line_count += len(lines)
                total_text_area += inter_area

    text_coverage_ratio = total_text_area / cluster_area if cluster_area > 0 else 0.0

    # 5. Check text density signal:
    # A cluster that contains paragraph/list text AND has few meaningful drawing shapes (< 4)
    # is a text section with decorative vector highlights, NOT a flowchart/diagram.
    # Genuine flowcharts (like multi-stage chevrons/boxes) contain >= 4 vector shapes.
    if text_line_count >= 3 and text_coverage_ratio >= 0.12 and meaningful_drawings < 4:
        print(
            f"  [DIAGRAM REJECT] bbox={tuple(cluster)} total_drawings={total_drawings} "
            f"meaningful_drawings={meaningful_drawings} text_lines={text_line_count} "
            f"text_coverage={text_coverage_ratio:.3f} reason=text_dense_decorative_cluster",
            file=sys.stderr
        )
        return False

    # 6. Genuine diagram check:
    # Genuine diagrams/flowcharts/chemical structures must have at least 2 meaningful vector drawing elements.
    if meaningful_drawings < 2:
        print(
            f"  [DIAGRAM REJECT] bbox={tuple(cluster)} total_drawings={total_drawings} "
            f"meaningful_drawings={meaningful_drawings} text_lines={text_line_count} "
            f"text_coverage={text_coverage_ratio:.3f} reason=insufficient_meaningful_vector_geometry",
            file=sys.stderr
        )
        return False

    print(
        f"  [DIAGRAM ACCEPT] bbox={tuple(cluster)} total_drawings={total_drawings} "
        f"meaningful_drawings={meaningful_drawings} text_lines={text_line_count} "
        f"text_coverage={text_coverage_ratio:.3f}",
        file=sys.stderr
    )
    return True





def _table_cell_text(cell) -> str:
    text = str(cell or "").strip()
    # Table extraction does not retain span/font metadata, so decode common
    # Adobe Symbol/Wingdings private-use characters directly when present.
    return "".join(
        SYMBOL_FONT_MAP.get(ord(ch) - 0xF000, ch)
        if 0xF000 <= ord(ch) <= 0xF0FF else ch
        for ch in text
    ).strip()


def _table_quality_score(table, page) -> float:
    """
    Score a PyMuPDF table candidate.

    This is intentionally conservative. A PDF table detector is allowed to
    miss an unusual table; it must NOT be allowed to swallow a whole page of
    normal text and turn it into a giant table.

    Strong signals:
      - at least two real rows/columns
      - multiple non-empty cells
      - reasonable cell occupancy
      - no single cell containing almost all of the extracted text
      - header geometry agrees with the detected column count
    """
    try:
        data = table.extract()
    except Exception:
        return -1.0

    if not data:
        return -1.0

    row_count = len(data)
    col_count = max((len(row) for row in data), default=0)

    if row_count < 2 or col_count < 2:
        return -1.0

    # Normalise rows to the detected column count.
    rows = [
        list(row) + [None] * (col_count - len(row))
        for row in data
    ]

    texts = [
        _table_cell_text(cell)
        for row in rows
        for cell in row
    ]
    non_empty = [text for text in texts if text]

    if len(non_empty) < 3:
        return -1.0

    total_chars = sum(len(text) for text in non_empty)
    max_chars = max(len(text) for text in non_empty)

    if total_chars == 0:
        return -1.0

    # A real table should not put almost all text into one cell.
    concentration = max_chars / total_chars
    if concentration > 0.82:
        return -1.0

    occupancy = len(non_empty) / (row_count * col_count)

    # Very sparse structures are commonly false positives.
    if occupancy < 0.30:
        return -1.0

    # Column Content Distribution Check:
    # A genuine multi-column table should have meaningful content distributed across columns.
    col_cell_counts = [
        sum(1 for row in rows if col < len(row) and _table_cell_text(row[col]))
        for col in range(col_count)
    ]
    col_char_counts = [
        sum(len(_table_cell_text(row[col])) for row in rows if col < len(row) and row[col])
        for col in range(col_count)
    ]
    total_non_empty = len(non_empty)

    if col_count >= 2 and total_non_empty > 0:
        max_col_cells = max(col_cell_counts)
        min_col_cells = min(col_cell_counts)
        max_col_chars = max(col_char_counts)
        min_col_chars = min(col_char_counts)

        # Reject if >= 85% of non-empty cells are in 1 column while another column has <= 1 cell
        if (max_col_cells / total_non_empty) >= 0.85 and min_col_cells <= 1 and col_count == 2:
            print(
                f"  [TABLE REJECT] bbox={table.bbox} rows={row_count} cols={col_count} "
                f"col_cells={col_cell_counts} col_chars={col_char_counts} reason=extreme_cell_column_concentration",
                file=sys.stderr
            )
            return -1.0

        # Reject if >= 85% of text characters are in 1 column while another column has <= 1 non-empty cell (or <= 20 chars)
        if total_chars > 0 and (max_col_chars / total_chars) >= 0.85 and (min_col_cells <= 1 or min_col_chars <= 20) and col_count == 2:
            print(
                f"  [TABLE REJECT] bbox={table.bbox} rows={row_count} cols={col_count} "
                f"col_cells={col_cell_counts} col_chars={col_char_counts} reason=extreme_char_column_concentration",
                file=sys.stderr
            )
            return -1.0


    # Inspect PyMuPDF's header metadata when available. In the bad
    # "Sectors of Economy" case, find_tables(lines) reports 10 columns but
    # only ONE actual header cell. That is a very strong false-positive
    # signal.
    header = getattr(table, "header", None)
    if header is not None:
        header_cells = getattr(header, "cells", None) or []
        real_header_cells = sum(cell is not None for cell in header_cells)

        if real_header_cells == 1 and col_count >= 3:
            return -1.0

        if real_header_cells >= 2:
            # If there is header geometry, its real cell count should not
            # wildly disagree with the extracted column count.
            if col_count >= 4 and real_header_cells < max(2, col_count // 2):
                return -1.0

    # Reject candidates that consume almost the entire page unless their
    # extracted structure is genuinely dense and multi-column.
    px0, py0, px1, py1 = page.rect
    page_area = max((px1 - px0) * (py1 - py0), 1)
    tx0, ty0, tx1, ty1 = table.bbox
    table_area = max((tx1 - tx0) * (ty1 - ty0), 0)
    area_ratio = table_area / page_area

    if area_ratio > 0.65 and col_count > 4:
        return -1.0

    # Reasonable table score. The caller may still apply stricter checks.
    score = 0.0
    score += min(non_empty.__len__() / 10.0, 1.0)
    score += min(occupancy, 1.0)
    score += min(col_count / 4.0, 1.0)

    print(
        f"  [TABLE ACCEPT] bbox={table.bbox} rows={row_count} cols={col_count} "
        f"col_cells={col_cell_counts} col_chars={col_char_counts} score={score:.2f}",
        file=sys.stderr
    )

    return score



def find_valid_tables(page):
    """
    Find tables conservatively.

    First use `lines_strict`, which requires actual vector lines and avoids
    treating text/background geometry as table borders. This is important for
    PDFs where the normal `lines` strategy can merge a large text region with
    a real table.

    If strict detection finds no useful table, fall back to `lines`, but only
    accept candidates that pass the structural validation above.

    Footer/page-number tables are ignored separately.
    """
    page_height = page.rect.height

    def collect(strategy):
        try:
            finder = page.find_tables(strategy=strategy)
            candidates = getattr(finder, "tables", []) or []
        except Exception as exc:
            print(
                f"Warning: table detection failed with strategy={strategy}: {exc}",
                file=sys.stderr,
            )
            return []

        valid = []

        for table in candidates:
            tx0, ty0, tx1, ty1 = table.bbox
            table_height = ty1 - ty0

            # Ignore footer/page-number regions and false-positive footer rules.
            if ty1 < 90 or ty0 > page_height - 75:
                continue
            if ty1 > page_height - 130 and table_height < 60:
                continue

            quality = _table_quality_score(table, page)
            if quality < 0:
                continue

            valid.append(table)

        return valid

    # Prefer strict line detection.
    strict_tables = collect("lines_strict")
    if strict_tables:
        return strict_tables

    # Conservative fallback for tables that contain less strict line
    # geometry. Raw `lines` results are NEVER accepted without validation.
    return collect("lines")


def render_table(table) -> str:
    """
    Render a validated PyMuPDF table while preserving its column geometry.

    The function deliberately does NOT delete empty columns. Empty cells can
    represent real table structure, merged cells, or extraction geometry.
    """
    try:
        table_data = table.extract()
    except Exception:
        return ""

    if not table_data:
        return ""

    num_cols = max((len(row) for row in table_data), default=0)
    if num_cols < 2:
        return ""

    rows = [
        list(row) + [None] * (num_cols - len(row))
        for row in table_data
    ]

    # Prefer PyMuPDF's detected header names when available.
    header = getattr(table, "header", None)
    header_names = list(getattr(header, "names", []) or []) if header else []

    # If PyMuPDF explicitly detected a header, use it. Otherwise retain the
    # existing behaviour of treating the first row as the header.
    use_header = len(header_names) == num_cols and any(
        _table_cell_text(value) for value in header_names
    )

    if use_header:
        header_row = header_names
        # The extracted data still contains the same first row, so do not
        # render it twice when PyMuPDF has already supplied header.names.
        body_rows = rows[1:]
    else:
        header_row = rows[0]
        body_rows = rows[1:]

    html_lines = [
        '<div class="table-responsive">',
        '<table class="notes-table">',
        '<thead>',
        '<tr>',
    ]

    for value in header_row:
        text = html.escape(_table_cell_text(value))
        html_lines.append(f"<th>{text}</th>")

    html_lines.extend(["</tr>", "</thead>"])

    if body_rows:
        html_lines.append("<tbody>")

        for row in body_rows:
            if not any(_table_cell_text(cell) for cell in row):
                continue

            html_lines.append("<tr>")

            for cell in row:
                cell_text = _table_cell_text(cell)

                if not cell_text:
                    html_lines.append("<td></td>")
                    continue

                # Preserve line-separated table items (e.g. the check-mark
                # lists in the Sectors of Economy PDF) instead of allowing
                # the browser to collapse all newlines into one paragraph.
                parts = [
                    part.strip()
                    for part in cell_text.splitlines()
                    if part.strip()
                ]

                if len(parts) > 1:
                    inner = "".join(
                        f'<div class="table-cell-line">{html.escape(part)}</div>'
                        for part in parts
                    )
                else:
                    inner = html.escape(cell_text)

                html_lines.append(f"<td>{inner}</td>")

            html_lines.append("</tr>")

        html_lines.append("</tbody>")

    html_lines.extend(["</table>", "</div>"])
    return "\n".join(html_lines)

def is_color_block(block: dict, target_color: int) -> bool:
    for line in block.get("lines", []):
        for span in line.get("spans", []):
            if span.get("text", "").strip():
                if span.get("color", 0) == target_color:
                    return True
    return False

def render_text_block_semantic(block: dict, body_size: float, page: fitz.Page = None) -> str:
    # Filter out running headers based on content and small font size
    text_spans = []
    for l in block.get("lines", []):
        text_spans.extend(l.get("spans", []))
    
    is_note_block = False
    is_figure_caption = False
    if text_spans:
        text_content = "".join(s.get("text", "") for s in text_spans).strip()
        is_note_block = bool(re.match(r'^(note\s*[:-]|नोट\s*[:-]|note\b)', text_content, re.IGNORECASE))
        is_figure_caption = bool(re.match(r'^figure\b', text_content, re.IGNORECASE))
        normalized_text = text_content.lower().replace(" ", "").replace("-", "")
        if normalized_text in ["economyintroduction", "studynotes"]:
            max_size = max(s.get("size", 12) for s in text_spans)
            if max_size < 15:
                return ""

    lines = block.get("lines", [])
    visible_lines = []
    for line in lines:
        spans = [s for s in line.get("spans", []) if s.get("text", "").strip()]
        if spans:
            line_copy = line.copy()
            line_copy["spans"] = spans
            visible_lines.append(line_copy)
            
    if not visible_lines:
        return ""
        
    if is_figure_caption:
        para_spans = []
        for line in visible_lines:
            spans = line["spans"]
            if para_spans and not para_spans[-1].get("text", "").endswith(" ") and not spans[0].get("text", "").startswith(" "):
                para_spans.append({"text": " ", "font": spans[0].get("font", ""), "size": spans[0].get("size", 12), "color": spans[0].get("color", 0)})
            para_spans.extend(spans)
        inner = "".join(render_span_semantic(s) for s in para_spans)
        inner = inner.replace("<strong>", "").replace("</strong>", "").replace("<em>", "").replace("</em>", "")
        return f"<figcaption>{inner}</figcaption>"
        
    # Check if this block is an info card (disabled to preserve semantic paragraphs/lists)
    if False and is_color_block(block, 0xe36c0a):
        para_spans = []
        for line in visible_lines:
            spans = line["spans"]
            if para_spans and not para_spans[-1].get("text", "").endswith(" ") and not spans[0].get("text", "").startswith(" "):
                para_spans.append({"text": " ", "font": spans[0].get("font", ""), "size": spans[0].get("size", 12), "color": spans[0].get("color", 0)})
            para_spans.extend(spans)
        inner = "".join(render_span_semantic(s) for s in para_spans)
        return f'<div class="info-card"><p>{inner}</p></div>'

        
    # Consolidate lines where a bullet character is split from its text on the same visual row
    merged_lines = []
    i = 0
    while i < len(visible_lines):
        line = visible_lines[i]
        spans = line["spans"]
        
        if i + 1 < len(visible_lines) and len(spans) == 1 and is_bullet_span(spans[0]):
            next_line = visible_lines[i + 1]
            y_diff = abs(next_line["bbox"][1] - line["bbox"][1])
            x_diff = next_line["bbox"][0] - line["bbox"][2]
            
            if y_diff < 10 and x_diff >= 0:
                merged_line = line.copy()
                merged_line["spans"] = spans + next_line["spans"]
                merged_line["bbox"] = [
                    min(line["bbox"][0], next_line["bbox"][0]),
                    min(line["bbox"][1], next_line["bbox"][1]),
                    max(line["bbox"][2], next_line["bbox"][2]),
                    max(line["bbox"][3], next_line["bbox"][3])
                ]
                merged_lines.append(merged_line)
                i += 2
                continue
                
        merged_lines.append(line)
        i += 1
        
    visible_lines = merged_lines
        
    # Check for pink heading
    is_pink = False
    bbox = block.get("bbox", (0, 0, 0, 0))
    if page:
        is_pink = is_pink_heading_block(bbox, page)
        
    heading_tag = classify_heading(visible_lines, body_size)
    if is_pink:
        heading_tag = "h2"
        
    res = ""
    if heading_tag:
        line = visible_lines[0]
        spans = line["spans"]
        inner = "".join(render_span_semantic(s) for s in spans)
        if is_pink:
            heading_tag = "h2"
            # Strip both strong and em from h2
            inner = inner.replace("<em>", "").replace("</em>", "").replace("<strong>", "").replace("</strong>", "")
        else:
            heading_tag = "h3"
            # Strip both strong and em from h3
            inner = inner.replace("<em>", "").replace("</em>", "").replace("<strong>", "").replace("</strong>", "")
        res = f"<{heading_tag}>{inner}</{heading_tag}>"
    else:
        html_out = []
        active_lists = []  # Stack of bullet x-coordinates
        current_para_spans = []
        
        for line in visible_lines:
            spans = line["spans"]
            if is_bullet_span(spans[0]):
                # Flush existing paragraph content
                if current_para_spans:
                    para_text = "".join(render_span_semantic(s) for s in current_para_spans)
                    html_out.append(f"<p>{para_text}</p>")
                    current_para_spans = []
                x_bullet = spans[0]["bbox"][0]
                bullet_char = decode_span_text(spans[0]).strip()
                is_alphanumeric = bool(re.match(r'^(\(?([0-9]+|[a-z]+|[IVX]+)\)[\.\)]?|([0-9]+|[a-z]+|[IVX]+)[\.\)])$', bullet_char))
                cls_extra = " list-alphanumeric" if is_alphanumeric else ""
                
                if not active_lists:
                    is_checkmark = bullet_char in ("✓", "✔", "ü", "\u2713", "\u2714", "\uf0fc")
                    if is_checkmark:
                        html_out.append(f'<ul class="notes-sub{cls_extra}">')
                        active_lists.append(x_bullet - 20)  # Dummy parent level
                        active_lists.append(x_bullet)
                    else:
                        html_out.append(f'<ul class="notes-list{cls_extra}">')
                        active_lists.append(x_bullet)
                else:
                    if x_bullet > active_lists[-1] + 5:
                        level = len(active_lists)
                        cls_name = "notes-sub" if level == 1 else "notes-subsub"
                        html_out.append(f'<ul class="{cls_name}{cls_extra}">')
                        active_lists.append(x_bullet)
                    elif x_bullet < active_lists[-1] - 5:
                        while active_lists and x_bullet < active_lists[-1] - 5:
                            html_out.append("</li></ul>")
                            active_lists.pop()
                        if not active_lists:
                            html_out.append(f'<ul class="notes-list{cls_extra}">')
                            active_lists.append(x_bullet)
                        else:
                            html_out.append("</li>")
                    else:
                        html_out.append("</li>")
                
                if is_alphanumeric:
                    prefix_html = render_span_semantic(spans[0])
                    rest_html = "".join(render_span_semantic(s) for s in spans[1:])
                    if not prefix_html.endswith(" ") and not rest_html.startswith(" "):
                        inner = prefix_html + " " + rest_html
                    else:
                        inner = prefix_html + rest_html
                else:
                    content_spans = spans[1:]
                    if content_spans:
                        inner = "".join(render_span_semantic(s) for s in content_spans)
                    else:
                        inner = ""
                html_out.append(f"<li>{inner}")


            else:
                if active_lists:
                    inner = "".join(render_span_semantic(s) for s in spans)
                    if html_out:
                        last_item = html_out[-1]
                        if not last_item.endswith(" ") and not inner.startswith(" "):
                            html_out[-1] = last_item + " " + inner
                        else:
                            html_out[-1] = last_item + inner
                else:
                    line_text = "".join(decode_span_text(s) for s in spans).strip()
                    # If this line starts an MCQ option (e.g. A., B.), Explanation, Question number, or Dash bullet, start a new paragraph
                    if current_para_spans and is_standalone_line_prefix(line_text):
                        para_text = "".join(render_span_semantic(s) for s in current_para_spans)
                        para_text = format_paragraph_dashes_and_spaces(para_text)
                        html_out.append(f"<p>{para_text}</p>")
                        current_para_spans = []

                    # Append to running paragraph list, keeping word spacing clean
                    if current_para_spans and not current_para_spans[-1].get("text", "").endswith(" ") and not spans[0].get("text", "").startswith(" "):
                        current_para_spans.append({"text": " ", "font": spans[0].get("font", ""), "size": spans[0].get("size", 12), "color": spans[0].get("color", 0)})
                    current_para_spans.extend(spans)

                
        # Flush remaining paragraph or list wraps
        if current_para_spans:
            para_text = "".join(render_span_semantic(s) for s in current_para_spans)
            para_text = format_paragraph_dashes_and_spaces(para_text)
            html_out.append(f"<p>{para_text}</p>")

        
        while active_lists:
            html_out.append("</li></ul>")
            active_lists.pop()
            
        res = "\n".join(html_out)

    if is_note_block:
        pattern = re.compile(
            r'^((?:<[a-z0-9]+>)*(?:<strong>|<em>)*)(note\s*[:-]|नोट\s*[:-]|note\b)((?:</strong>|</em>)*)(\s*)',
            re.IGNORECASE
        )
        match = pattern.match(res)
        if match:
            before = match.group(1)
            prefix = match.group(2)
            after = match.group(3)
            spacing = match.group(4)
            wrapped = f'<span class="note-title">{prefix}</span>'
            res = before + wrapped + after + spacing + res[match.end():]
        return f'<div class="content-note">\n{res}\n</div>'
    return res

def extract_page_elements(doc: fitz.Document, page: fitz.Page, body_size: float) -> list:
    rect = page.rect
    page_height = rect.height
    
    # 1. Find and VALIDATE tables before excluding any text from the page.
    # Never use raw page.find_tables() results here.
    valid_tables = find_valid_tables(page)
    
    # 1.5 Detect vector diagrams/flowcharts/chemical structures conservatively
    page_w, page_h = rect.width, rect.height
    draw_rects = []
    for d in page.get_drawings():
        r = d["rect"]
        # Skip rule lines (headers/footers) and page borders
        if r.width > page_w * 0.9 and r.height < 5:
            continue
        if r.height > page_h * 0.9 and r.width < 5:
            continue
        if r.width > page_w * 0.95 and r.height > page_h * 0.95:
            continue
        if r.width == 0 and r.height == 0:
            continue
        # Skip drawings in header/footer zones
        if r.y1 < 80 or r.y0 > page_h - 75:
            continue
        # Skip light gray watermark fills
        fill = d.get("fill")
        if fill and len(fill) == 3:
            r_val, g_val, b_val = fill
            if abs(r_val - g_val) < 0.02 and abs(g_val - b_val) < 0.02 and 0.7 <= r_val <= 0.9:
                continue
        draw_rects.append(r)

    # Cluster drawings
    diagram_clusters = []
    for r in draw_rects:
        merged = False
        for idx_c, c in enumerate(diagram_clusters):
            dx = max(0, c.x0 - r.x1, r.x0 - c.x1)
            dy = max(0, c.y0 - r.y1, r.y0 - c.y1)
            if dx < 80 and dy < 80:
                diagram_clusters[idx_c] = fitz.Rect(
                    min(r.x0, c.x0), min(r.y0, c.y0),
                    max(r.x1, c.x1), max(r.y1, c.y1)
                )
                merged = True
                break
        if not merged:
            diagram_clusters.append(fitz.Rect(r))

    # Re-merge clusters
    changed = True
    while changed:
        changed = False
        for i_c in range(len(diagram_clusters)):
            for j_c in range(i_c + 1, len(diagram_clusters)):
                c1, c2 = diagram_clusters[i_c], diagram_clusters[j_c]
                dx = max(0, c2.x0 - c1.x1, c1.x0 - c2.x1)
                dy = max(0, c2.y0 - c1.y1, c1.y0 - c2.y1)
                if dx < 80 and dy < 80:
                    diagram_clusters[i_c] = fitz.Rect(
                        min(c1.x0, c2.x0), min(c1.y0, c2.y0),
                        max(c1.x1, c2.x1), max(c1.y1, c2.y1)
                      )
                    diagram_clusters.pop(j_c)
                    changed = True
                    break
            if changed:
                break

    # Extract page text dictionary early for diagram validation
    text_dict = page.get_text("dict")

    # Validate vector diagram candidates with conservative geometry & text density rules
    valid_diagram_rects = []
    for c in diagram_clusters:
        # Skip header diagrams/logos sitting in top running header zone (y0 < 110 or y1 < 125)
        if c.y0 < 110 or c.y1 < 125 or c.y0 > page_height - 75:
            continue
        if is_valid_vector_diagram(c, page, text_dict, valid_tables):
            valid_diagram_rects.append(c)


    
    # Pre-process spans to split merged list prefixes (e.g. "- text" -> "-" and " text", "a. text" -> "a." and " text")
    import re
    dash_prefix_pattern = re.compile(r'^([-–—•·◆▪▸►‣])\s+(.*)')
    prefix_pattern = re.compile(r'^(\(?([0-9]+|[a-z]+|[IVX]+)\)[\.\)]?|([0-9]+|[a-z]+|[IVX]+)[\.\)])(\s+)')
    for block in text_dict.get("blocks", []):
        if block.get("type", 0) == 0:
            for line in block.get("lines", []):
                spans = line.get("spans", [])
                if spans:
                    first_span = spans[0]
                    text_val = first_span.get("text", "")

                    # 1. Check dash / bullet prefix e.g. "- In June 2022..."
                    dash_match = dash_prefix_pattern.match(text_val.strip())
                    if dash_match:
                        prefix = dash_match.group(1)
                        idx_p = text_val.find(prefix)
                        rest = text_val[idx_p + len(prefix):]
                        if rest.strip():
                            prefix_span = first_span.copy()
                            prefix_span["text"] = prefix
                            first_span["text"] = rest
                            line["spans"] = [prefix_span] + spans
                            continue

                    # 2. Check alphanumeric prefix
                    match = prefix_pattern.match(text_val)
                    if match:
                        prefix = match.group(1)
                        spacing = match.group(4)
                        rest = text_val[match.end():]
                        if rest.strip() and is_alphanumeric_prefix(prefix):
                            prefix_span = first_span.copy()
                            prefix_span["text"] = prefix
                            first_span["text"] = spacing + rest
                            line["spans"] = [prefix_span] + spans

                            
    raw_lines = []
    
    for block in text_dict.get("blocks", []):
        block_type = block.get("type", 0)
        if block_type != 0:  # Skip images here, handled below
            continue
            
        bbox = block.get("bbox", (0, 0, 0, 0))
        # Skip blocks inside tables
        if is_inside_table(bbox, valid_tables):
            continue
            
        # Skip blocks inside diagrams (require at least 60% of block area to be inside diagram)
        bx0, by0, bx1, by1 = bbox
        block_area = max(1.0, (bx1 - bx0) * (by1 - by0))
        inside_diagram = False
        for dr in valid_diagram_rects:
            inter_x0 = max(bx0, dr.x0)
            inter_y0 = max(by0, dr.y0)
            inter_x1 = min(bx1, dr.x1)
            inter_y1 = min(by1, dr.y1)
            if inter_x1 > inter_x0 and inter_y1 > inter_y0:
                inter_area = (inter_x1 - inter_x0) * (inter_y1 - inter_y0)
                if (inter_area / block_area) >= 0.60:
                    inside_diagram = True
                    break
        if inside_diagram:
            continue

            
        for line in block.get("lines", []):
            ly0 = line["bbox"][1]
            ly1 = line["bbox"][3]
            
            # Skip header and footer zones (ly1 < 75 skips running headers)
            if ly1 < 75 or ly0 > page_height - 75:
                continue
                
            line_text = "".join(s.get("text", "") for s in line.get("spans", [])).strip()
            if is_watermark_text(line_text):
                continue

            # Skip running headers at top of page (e.g. "ESI- RBI_2018")
            if ly1 < 95:
                norm_line = line_text.lower().replace(" ", "").replace("-", "").replace("_", "")
                if norm_line in ("esirbi2018", "rbigradeb2018", "wwwixambeecom", "ixambee"):
                    continue


            raw_lines.append(line)
            
    # Sort all lines on the page top-to-bottom
    raw_lines.sort(key=lambda l: l["bbox"][1])
    
    # Consolidate lines where a bullet character is split from its text on the same visual row
    merged_raw_lines = []
    i = 0
    while i < len(raw_lines):
        line = raw_lines[i]
        spans = [s for s in line.get("spans", []) if s.get("text", "").strip()]
        if i + 1 < len(raw_lines) and len(spans) == 1 and is_bullet_span(spans[0]):
            next_line = raw_lines[i + 1]
            next_spans = [s for s in next_line.get("spans", []) if s.get("text", "").strip()]
            y_diff = abs(next_line["bbox"][1] - line["bbox"][1])
            x_diff = next_line["bbox"][0] - line["bbox"][2]
            if y_diff < 8 and x_diff >= 0:
                merged_line = line.copy()
                merged_line["spans"] = spans + next_spans
                merged_line["bbox"] = [
                    min(line["bbox"][0], next_line["bbox"][0]),
                    min(line["bbox"][1], next_line["bbox"][1]),
                    max(line["bbox"][2], next_line["bbox"][2]),
                    max(line["bbox"][3], next_line["bbox"][3])
                ]
                merged_raw_lines.append(merged_line)
                i += 2
                continue
        merged_raw_lines.append(line)
        i += 1
    raw_lines = merged_raw_lines
    
    # 3. Group lines semantically from scratch
    semantic_blocks = []
    current_lines = []
    
    for line in raw_lines:
        spans = [s for s in line.get("spans", []) if s.get("text", "").strip()]
        if not spans:
            continue
            
        is_bullet = is_bullet_span(spans[0])
        is_all_bold = all("Bold" in s.get("font", "") for s in spans)
        text_content = "".join(decode_span_text(s) for s in spans).strip()
        is_heading = is_all_bold and not is_bullet and len(text_content) < 80 and not text_content.endswith(".")
        if is_heading and current_lines:
            prev_line = current_lines[-1]
            prev_spans = [s for s in prev_line.get("spans", []) if s.get("text", "").strip()]
            if prev_spans:
                prev_text = "".join(decode_span_text(s) for s in prev_spans).strip()
                gap = line["bbox"][1] - prev_line["bbox"][3]
                if gap < 16 and prev_text and not prev_text[-1] in (".", "?", "!", ":", ";"):
                    is_heading = False
        is_pink = is_pink_heading_block(line["bbox"], page)
        
        # Flush if: heading, pink block, or transitioning between bullet list and normal paragraph
        should_flush = (is_heading or is_pink)
        if not should_flush and current_lines:
            has_bullet_in_block = False
            for l in current_lines:
                l_spans = [s for s in l.get("spans", []) if s.get("text", "").strip()]
                if l_spans and is_bullet_span(l_spans[0]):
                    has_bullet_in_block = True
                    break
                    
            if has_bullet_in_block:
                if not is_bullet:
                    # Current block has bullets, new line is text. Check if it's a continuation.
                    is_continuation = False
                    prev_line = current_lines[-1]
                    gap = line["bbox"][1] - prev_line["bbox"][3]
                    line_x0 = line["bbox"][0]
                    # Find the last bullet line in current_lines to get text offset
                    last_bullet_x0 = current_lines[0]["bbox"][0]
                    for l in reversed(current_lines):
                        l_spans = [s for s in l.get("spans", []) if s.get("text", "").strip()]
                        if l_spans and is_bullet_span(l_spans[0]):
                            last_bullet_x0 = l["bbox"][0]
                            break
                    if gap < 16 and line_x0 > last_bullet_x0 + 8:
                        is_continuation = True
                    if not is_continuation:
                        should_flush = True
            else:
                # Current block is normal text. Flush if it contains a heading.
                is_current_heading = False
                if len(current_lines) == 1:
                    prev_line = current_lines[0]
                    prev_spans = [s for s in prev_line.get("spans", []) if s.get("text", "").strip()]
                    if prev_spans:
                        prev_bold = all("Bold" in s.get("font", "") for s in prev_spans)
                        prev_text = "".join(decode_span_text(s) for s in prev_spans).strip()
                        if prev_bold and len(prev_text) < 80 and not prev_text.endswith("."):
                            is_current_heading = True
                if is_current_heading:
                    should_flush = True
                elif is_bullet:
                    should_flush = True
                    
        if should_flush:
            if current_lines:
                semantic_blocks.append({
                    "type": "text",
                    "bbox": (
                        min(l["bbox"][0] for l in current_lines),
                        min(l["bbox"][1] for l in current_lines),
                        max(l["bbox"][2] for l in current_lines),
                        max(l["bbox"][3] for l in current_lines)
                    ),
                    "lines": current_lines
                })
                current_lines = []
        else:
            # If the current line is a normal text line, check if it's a continuation
            if current_lines:
                prev_line = current_lines[-1]
                gap = line["bbox"][1] - prev_line["bbox"][3]
                limit = 14.0 if is_bullet else 7.0

                if gap >= limit:
                    semantic_blocks.append({
                        "type": "text",
                        "bbox": (
                            min(l["bbox"][0] for l in current_lines),
                            min(l["bbox"][1] for l in current_lines),
                            max(l["bbox"][2] for l in current_lines),
                            max(l["bbox"][3] for l in current_lines)
                        ),
                        "lines": current_lines
                    })
                    current_lines = []
                    
        current_lines.append(line)
        
    if current_lines:
        semantic_blocks.append({
            "type": "text",
            "bbox": (
                min(l["bbox"][0] for l in current_lines),
                min(l["bbox"][1] for l in current_lines),
                max(l["bbox"][2] for l in current_lines),
                max(l["bbox"][3] for l in current_lines)
            ),
            "lines": current_lines
        })
        
    # 4. Extract other block types (tables and images)
    page_elements = []
    
    # Add text blocks
    for sb in semantic_blocks:
        page_elements.append({
            "type": "text",
            "bbox": sb["bbox"],
            "data": sb
        })
        
    # Add image blocks from the page (skipping cover page images, top running header logos, and footers)
    for block in text_dict.get("blocks", []):
        if block.get("type") == 1:  # Image block
            bbox = block.get("bbox", (0, 0, 0, 0))
            # Skip cover page images, running header logos in top zone (bbox[1] < 110 or bbox[3] < 125), and footers
            if page.number == 0 or bbox[1] < 110 or bbox[3] < 125 or bbox[1] > page_height - 75:
                continue
            if is_watermark_image(block, page):
                continue
            if image_overlaps_table(bbox, valid_tables):
                continue
            page_elements.append({
                "type": "image",
                "bbox": bbox,
                "data": block
            })



            
    # Add only validated table blocks. Keep the Table object so render_table()
    # can use PyMuPDF's detected header geometry/names.
    for t in valid_tables:
        page_elements.append({
            "type": "table",
            "bbox": t.bbox,
            "data": t
        })
        
    # Add detected vector diagrams/flowcharts to render in-place
    for dr in valid_diagram_rects:
        page_elements.append({
            "type": "diagram",
            "bbox": (dr.x0, dr.y0, dr.x1, dr.y1),
            "data": dr
        })

    # Deduplicate images: skip smaller sub-images contained inside a diagram or larger graphic
    diagram_bboxes = [e["bbox"] for e in page_elements if e["type"] == "diagram"]
    filtered_elements = []
    for el in page_elements:
        if el["type"] == "image":
            ibox = el["bbox"]
            is_sub = False
            for dbox in diagram_bboxes:
                inter_x0 = max(ibox[0], dbox[0])
                inter_y0 = max(ibox[1], dbox[1])
                inter_x1 = min(ibox[2], dbox[2])
                inter_y1 = min(ibox[3], dbox[3])
                if inter_x1 > inter_x0 and inter_y1 > inter_y0:
                    inter_area = (inter_x1 - inter_x0) * (inter_y1 - inter_y0)
                    iarea = max(1, (ibox[2] - ibox[0]) * (ibox[3] - ibox[1]))
                    darea = max(1, (dbox[2] - dbox[0]) * (dbox[3] - dbox[1]))
                    if iarea < darea * 0.95 and (inter_area / iarea) > 0.4:
                        is_sub = True
                        break
            if is_sub:
                continue
        filtered_elements.append(el)
    page_elements = filtered_elements
        
    # Sort all elements on page top-to-bottom
    page_elements.sort(key=lambda e: e["bbox"][1])

    
    # 5. Merge info cards (consecutive blocks with color 0xe36c0a)
    merged_elements = []
    i = 0
    while i < len(page_elements):
        el = page_elements[i]
        if el["type"] == "text" and is_color_block(el["data"], 0xe36c0a):
            merged_lines = list(el["data"]["lines"])
            j = i + 1
            while j < len(page_elements):
                next_el = page_elements[j]
                if next_el["type"] == "text" and is_color_block(next_el["data"], 0xe36c0a):
                    gap = next_el["bbox"][1] - el["bbox"][3]
                    if gap < 20:
                        merged_lines.extend(next_el["data"]["lines"])
                        el["bbox"] = [
                            min(el["bbox"][0], next_el["bbox"][0]),
                            min(el["bbox"][1], next_el["bbox"][1]),
                            max(el["bbox"][2], next_el["bbox"][2]),
                            max(el["bbox"][3], next_el["bbox"][3])
                        ]
                        j += 1
                        continue
                break
            el["data"]["lines"] = merged_lines
            merged_elements.append(el)
            i = j
        else:
            merged_elements.append(el)
            i += 1
            
    page_elements = merged_elements
    
    # 5.5 Detect and merge captions for images/diagrams
    merged_elements = []
    i = 0
    while i < len(page_elements):
        el = page_elements[i]
        if el["type"] in ("image", "diagram"):
            if i + 1 < len(page_elements):
                next_el = page_elements[i + 1]
                if next_el["type"] == "text":
                    lines = next_el["data"].get("lines", [])
                    if len(lines) == 1:
                        txt_spans = lines[0].get("spans", [])
                        txt_content = "".join(decode_span_text(s) for s in txt_spans).strip()
                        gap = next_el["bbox"][1] - el["bbox"][3]
                        is_next_heading = False
                        if all("Bold" in s.get("font", "") for s in txt_spans):
                            is_next_heading = True
                        elif re.match(r"^\d+[\.\s]", txt_content):
                            is_next_heading = True

                        if 0 <= gap < 45 and len(txt_content) < 120 and not is_next_heading:
                            el["caption"] = txt_content
                            merged_elements.append(el)
                            i += 2
                            continue
        merged_elements.append(el)
        i += 1
    page_elements = merged_elements
    return page_elements

def render_page_elements(page: fitz.Page, page_elements: list, body_size: float, html_path: Path = None) -> str:
    # 6. Render elements to HTML
    images_dir = None
    if html_path:
        images_dir = html_path.parent / "images"
        images_dir.mkdir(parents=True, exist_ok=True)

    elements_html = []
    image_counter = 0
    for element in page_elements:
        el_type = element["type"]
        if el_type == "table":
            elements_html.append(render_table(element["data"]))
        elif el_type == "image":
            bbox = element["bbox"]
            clip_rect = fitz.Rect(bbox)
            if clip_rect.width > 0 and clip_rect.height > 0:
                try:
                    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), clip=clip_rect)
                    img_bytes = pix.tobytes("png")
                    if images_dir:
                        img_filename = f"page_{page.number + 1}_img_{image_counter}.png"
                        (images_dir / img_filename).write_bytes(img_bytes)
                        image_counter += 1
                        img_tag = f'<img src="images/{img_filename}" alt="Extracted Graphic" />'
                    else:
                        b64 = base64.b64encode(img_bytes).decode("ascii")
                        img_tag = f'<img src="data:image/png;base64,{b64}" alt="Extracted Graphic" />'
                    if "caption" in element:
                        caption_tag = f'<figcaption>{html.escape(element["caption"])}</figcaption>'
                        elements_html.append(f'<figure>{img_tag}\n{caption_tag}</figure>')
                    else:
                        elements_html.append(f'<figure>{img_tag}</figure>')
                except Exception as e:
                    print(f"Error extracting image block: {e}", file=sys.stderr)
        elif el_type == "diagram":
            bbox = element["bbox"]
            clip_rect = fitz.Rect(bbox)
            if clip_rect.width > 0 and clip_rect.height > 0:
                try:
                    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), clip=clip_rect)
                    img_bytes = pix.tobytes("png")
                    if images_dir:
                        img_filename = f"page_{page.number + 1}_diag_{image_counter}.png"
                        (images_dir / img_filename).write_bytes(img_bytes)
                        image_counter += 1
                        img_tag = f'<img src="images/{img_filename}" alt="Diagram/Flowchart" />'
                    else:
                        b64 = base64.b64encode(img_bytes).decode("ascii")
                        img_tag = f'<img src="data:image/png;base64,{b64}" alt="Diagram/Flowchart" />'
                    if "caption" in element:
                        caption_tag = f'<figcaption>{html.escape(element["caption"])}</figcaption>'
                        elements_html.append(f'<figure>{img_tag}\n{caption_tag}</figure>')
                    else:
                        elements_html.append(f'<figure>{img_tag}</figure>')
                except Exception as e:
                    print(f"Error extracting diagram block: {e}", file=sys.stderr)
        elif el_type == "text":
            text_html = render_text_block_semantic(element["data"], body_size, page)
            if text_html:
                elements_html.append(text_html)
                
    content = "\n".join(elements_html)
    return PAGE_TEMPLATE.format(content=content)

def render_page(doc: fitz.Document, page: fitz.Page, body_size: float, html_path: Path = None) -> str:
    elements = extract_page_elements(doc, page, body_size)
    return render_page_elements(page, elements, body_size, html_path)

def extract_pdf_title(doc: fitz.Document) -> str:
    if len(doc) == 0:
        return "Document"
    page = doc[0]
    blocks = page.get_text("dict")["blocks"]
    
    spans = []
    for b in blocks:
        if b["type"] == 0:
            for l in b["lines"]:
                spans.extend(l["spans"])
                
    if not spans:
        return Path(doc.name).stem
        
    # Find non-generic spans
    non_generic_spans = []
    for s in spans:
        text = s.get("text", "").strip()
        if text and text.lower() not in ["study notes", "studynotes"]:
            non_generic_spans.append(s)
            
    if not non_generic_spans:
        return spans[0].get("text", "").strip() if spans else "Document"
        
    # Find maximum font size among non-generic spans
    max_size = max(s.get("size", 0) for s in non_generic_spans)
    
    # Collect all non-generic spans with size close to max_size (within 1.0px)
    title_spans = []
    for s in non_generic_spans:
        if abs(s.get("size", 0) - max_size) <= 1.0:
            title_spans.append(s)
            
    # Sort top-to-bottom, then left-to-right
    title_spans.sort(key=lambda s: (s["bbox"][1], s["bbox"][0]))
    
    # Join distinct parts
    title_parts = []
    for s in title_spans:
        t = s.get("text", "").strip()
        if t and t not in title_parts:
            title_parts.append(t)
            
    if title_parts:
        return " ".join(title_parts)
        
    return "Document"

def merge_split_pages(all_pages_elements: list) -> None:
    for idx in range(len(all_pages_elements) - 1):
        prev_elements = all_pages_elements[idx]
        next_elements = all_pages_elements[idx + 1]
        if not prev_elements or not next_elements:
            continue
            
        el_prev = prev_elements[-1]
        el_next = next_elements[0]
        
        if el_prev["type"] == "text" and el_next["type"] == "text":
            lines_prev = el_prev["data"].get("lines", [])
            lines_next = el_next["data"].get("lines", [])
            if not lines_prev or not lines_next:
                continue
                
            # Get last line text of prev element
            last_line = lines_prev[-1]
            last_spans = [s for s in last_line.get("spans", []) if s.get("text", "").strip()]
            if not last_spans:
                continue
            last_text = "".join(decode_span_text(s) for s in last_spans).strip()
            
            # If last text does not end with sentence-ending punctuation
            if last_text and not last_text[-1] in (".", "?", "!", ":", ";", "”", '"'):
                # Check if first line of next element is a bullet
                first_line = lines_next[0]
                first_spans = [s for s in first_line.get("spans", []) if s.get("text", "").strip()]
                if not first_spans:
                    continue
                is_first_bullet = is_bullet_span(first_spans[0])
                
                if not is_first_bullet:
                    # Merge el_next's lines into el_prev
                    lines_prev.extend(lines_next)
                    el_prev["data"]["lines"] = lines_prev
                    # Update bbox of el_prev (extend vertically)
                    el_prev["bbox"] = [
                        min(el_prev["bbox"][0], el_next["bbox"][0]),
                        min(el_prev["bbox"][1], el_next["bbox"][1]),
                        max(el_prev["bbox"][2], el_next["bbox"][2]),
                        max(el_prev["bbox"][3], el_next["bbox"][3])
                    ]
                    # Remove the first element from next page
                    next_elements.pop(0)

def convert(pdf_path: Path, html_path: Path, start: int = None, end: int = None) -> None:
    doc = fitz.open(pdf_path)
    try:
        page_count = doc.page_count
        
        # Auto-extract title from the first page of the PDF
        pdf_title = extract_pdf_title(doc)
        
        body_size = compute_body_size(doc)
        
        # Auto-detect cover page if start page is not explicitly passed
        if start is None:
            if is_cover_page(doc[0], body_size):
                start_idx = 1  # Skip cover page
            else:
                start_idx = 0  # Start from Page 1
        else:
            start_idx = max(0, start - 1)

        end_idx = min(page_count, end or page_count)

        all_pages_elements = []
        for page_index in range(start_idx, end_idx):
            page = doc[page_index]
            all_pages_elements.append(extract_page_elements(doc, page, body_size))
            
        merge_split_pages(all_pages_elements)
        
        pages_html = []
        if start_idx == 0:
            pages_html.append("<!-- NO_COVER_PAGE -->")

        for i, page_index in enumerate(range(start_idx, end_idx)):
            page = doc[page_index]
            pages_html.append(render_page_elements(page, all_pages_elements[i], body_size, html_path))

        html_path.write_text(
            DOC_TEMPLATE.format(
                title=html.escape(pdf_title),
                pages="\n".join(pages_html),
            ),
            encoding="utf-8",
        )
    finally:
        doc.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert a PDF to a semantic HTML file.")
    parser.add_argument("pdf", type=Path, nargs="?", default=Path(PDF_PATH), help="Path to the input PDF file")
    parser.add_argument("html", type=Path, nargs="?", default=None, help="Path to write the output HTML file")
    parser.add_argument("--start", type=int, default=2, help="First page to convert (1-based, default 2 to skip cover)")
    parser.add_argument("--end", type=int, default=None, help="Last page to convert (default: last page)")
    args = parser.parse_args()
 
    pdf_path = args.pdf
    
    # If the input looks like a numeric MySQL ID, try to resolve it from the queue
    if str(pdf_path).isdigit():
        mysql_id = int(str(pdf_path))
        queue_pdf = Path(__file__).parent.parent / "storage" / "queue" / str(mysql_id) / "document.pdf"
        if queue_pdf.exists():
            pdf_path = queue_pdf
            if args.html is None:
                args.html = Path(__file__).parent.parent / "storage" / "queue" / str(mysql_id) / "document.html"

    if not pdf_path.exists():
        print(f"Input PDF not found: {pdf_path}", file=sys.stderr)
        sys.exit(1)
 
    output_dir = Path(OUTPUT_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)
    html_path = args.html if args.html is not None else output_dir / f"{pdf_path.stem}.html"
 
    convert(pdf_path, html_path, args.start, args.end)
    print(f"Wrote {html_path}")

if __name__ == "__main__":
    main()