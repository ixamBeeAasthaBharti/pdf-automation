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
import re
import os
from pathlib import Path
from collections import Counter

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
{css_link}
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

# Default inline CSS fallback if no standalone reader.css link is supplied
DEFAULT_INLINE_CSS = """
<style>
  body {
    margin: 0;
    padding: 40px 20px;
    background-color: #f7f9fa;
    font-family: 'Literata', 'Lora', Georgia, serif;
    color: #1a1a1a;
    line-height: 1.65;
  }
  .container {
    max-width: 800px;
    margin: 0 auto;
    background: #ffffff;
    padding: 40px;
    border-radius: 8px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
  }
  .pdf-page {
    margin-bottom: 40px;
    border-bottom: 1px dashed #e1e8ed;
    padding-bottom: 40px;
  }
  .pdf-page:last-child {
    margin-bottom: 0;
    border-bottom: none;
    padding-bottom: 0;
  }
  h1, h2, h3, h4 {
    color: #0b2240;
    font-family: 'Outfit', sans-serif;
    font-weight: 700;
    margin-top: 1.8em;
    margin-bottom: 0.6em;
  }
  h1 {
    font-size: 2.2rem;
    border-bottom: 2px solid #e1e8ed;
    padding-bottom: 10px;
    margin-top: 0;
  }
  h2 {
    font-size: 1.8rem;
    border-bottom: 1px solid #ecf0f1;
    padding-bottom: 8px;
  }
  h3 {
    font-size: 1.4rem;
  }
  h4 {
    font-size: 1.15rem;
  }
  p {
    margin-top: 0;
    margin-bottom: 1.2em;
    text-align: justify;
  }
  ul {
    margin-top: 0;
    margin-bottom: 1.2em;
    padding-left: 24px;
  }
  li {
    margin-bottom: 0.6em;
  }
  table {
    width: 100%;
    border-collapse: collapse;
    margin: 24px 0;
    font-size: 0.95rem;
  }
  th, td {
    padding: 12px 15px;
    text-align: left;
    border-bottom: 1px solid #e1e8ed;
  }
  th {
    background-color: #f4f6f8;
    color: #0b2240;
    font-weight: 600;
  }
  tr:hover {
    background-color: #fcfdfe;
  }
  .table-responsive {
    overflow-x: auto;
    margin: 24px 0;
  }
  img {
    max-width: 100%;
    height: auto;
    display: block;
    margin: 24px auto;
    border-radius: 4px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.06);
  }
  .info-card {
    border: 2px solid #e36c0a;
    border-radius: 8px;
    background-color: #fdfaf6;
    padding: 15px 20px;
    margin: 20px auto;
    max-width: 85%;
    text-align: center;
  }
  .info-card p {
    margin: 0;
    text-align: center;
    color: #e36c0a;
    font-size: 0.95rem;
    line-height: 1.65;
  }
  .info-card strong {
    color: #e36c0a !important;
    font-weight: 700;
  }
</style>
"""

# Global configuration flags
CSS_HREF = None
IMAGE_DIR = None
DEBUG_MODE = False

# Scanned ignore sets for running headers, footers and logos
IGNORED_HEADERS = set()
IGNORED_FOOTERS = set()
IGNORED_LOGOS = set()

def pre_scan_document(doc: fitz.Document, start_idx: int, end_idx: int):
    """
    IMPROVEMENT: Pre-scan documents to dynamically identify repeated logos/images
    and running text headers/footers to skip them safely across pages.
    """
    global IGNORED_HEADERS, IGNORED_FOOTERS, IGNORED_LOGOS
    header_counts = Counter()
    footer_counts = Counter()
    logo_counts = Counter()
    
    # We scan all normal content pages to build frequency maps
    for page_idx in range(start_idx, end_idx):
        if page_idx >= doc.page_count:
            break
        page = doc[page_idx]
        page_h = page.rect.height
        
        # 1. Repeated Text Headers/Footers
        try:
            blocks = page.get_text("dict").get("blocks", [])
            for b in blocks:
                if b.get("type") != 0:
                    continue
                for line in b.get("lines", []):
                    ly0, ly1 = line["bbox"][1], line["bbox"][3]
                    txt = "".join(s.get("text", "") for s in line.get("spans", [])).strip()
                    if not txt:
                        continue
                    # Normalize text: strip digits, page numbers, trailing spaces
                    norm = re.sub(r'\d+', '', txt).strip().lower()
                    if len(norm) < 4:
                        continue
                    if ly1 < 80:
                        header_counts[norm] += 1
                    elif ly0 > page_h - 80:
                        footer_counts[norm] += 1
        except Exception:
            pass
            
        # 2. Repeated Logo Images in Header/Footer Regions
        try:
            img_info = page.get_image_info(xrefs=True)
            for info in img_info:
                bbox = info.get("bbox")
                if bbox and len(bbox) == 4:
                    x0, y0, x1, y1 = bbox
                    w = round(x1 - x0, 1)
                    h = round(y1 - y0, 1)
                    if y1 < 95 or y0 > page_h - 95:
                        # Index by dimension and horizontal start coordinate
                        logo_counts[(w, h, round(x0, 0))] += 1
        except Exception:
            pass
            
    # Compile final sets of assets that repeat on 3 or more pages
    for text, count in header_counts.items():
        if count >= 3:
            IGNORED_HEADERS.add(text)
    for text, count in footer_counts.items():
        if count >= 3:
            IGNORED_FOOTERS.add(text)
    for sig, count in logo_counts.items():
        if count >= 3:
            IGNORED_LOGOS.add(sig)

def looks_like_visual_fragment(text: str) -> bool:
    """
    IMPROVEMENT: Identify equations, bonds, isolated operators, chemical structures,
    and diagram label fragments so they are not misclassified as headings.
    """
    text_clean = text.strip()
    if not text_clean:
        return False
        
    # Standard isolated mathematical characters or operator markers
    if text_clean in ["||", "==", "|", "/", "\\", "=", "-", "+", "->", "=>"]:
        return True
        
    # Very short strings consisting entirely of symbols, chemical labels or digit variables
    if len(text_clean) <= 6:
        if re.match(r'^[A-Z0-9a-z\+\-\=\|\/\\\(\)\[\]\s\*\•\·\→\←\↑\↓\↔\⇒\⇐\⇄\⇆\-\–\—\=\≡\≈\≥\≤\≠\±]+$', text_clean):
            # Exclude standard short words
            if not re.search(r'\b(?:and|the|for|is|are|of|in|to|with|or|on|at|by|an|a|be)\b', text_clean, re.IGNORECASE):
                return True
                
    # Chemical structure drawing fragments, e.g. 'R-C-H' or high density of caps/bonds
    if len(text_clean) < 40:
        symbols_digits = sum(1 for c in text_clean if c in "+-=|/\\()[]_<>~")
        caps = sum(1 for c in text_clean if c.isupper())
        digits = sum(1 for c in text_clean if c.isdigit())
        total_len = len(text_clean)
        if total_len > 0 and (symbols_digits + caps + digits) / total_len > 0.8:
            return True
            
    return False

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
    font = span.get("font", "")
    if "Symbol" in font:
        return decode_symbol_font(text)
    if "Wingdings" in font or "Webdings" in font:
        return "•" * len(text)
    return text

def render_span_semantic(span: dict) -> str:
    text = decode_span_text(span)
    if not text.strip():
        return ""
    font = span.get("font", "")
    is_bold = "Bold" in font
    is_italic = "Italic" in font or "Oblique" in font
    escaped_text = html.escape(text)
    
    if is_bold:
        escaped_text = f"<strong>{escaped_text}</strong>"
    if is_italic:
        escaped_text = f"<em>{escaped_text}</em>"
    return escaped_text

def is_bullet_span(span: dict) -> bool:
    font = span.get("font", "")
    if "Wingdings" in font or "Webdings" in font:
        return True
    decoded = decode_span_text(span).strip()
    return decoded in ("•", "·", "◆", "▪", "▸", "►", "‣", "–", "—")

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
    """
    Splits fitz block dictionaries semantically.
    IMPROVEMENT: Integrated the heading scoring model and visual fragment skips.
    """
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
        
        # Heading checks using the unified classification function
        is_heading = classify_heading([line], 12.0) is not None
        
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

def classify_heading(visible_lines: list, body_size: float, page_context: dict = None) -> str | None:
    """
    IMPROVEMENT: Scoring Model for Heading Classification (Requirement 14).
    Uses font-size, bold weight, spacing context, length, and formula negative weights.
    """
    if not visible_lines:
        return None
        
    # Standalone headings typically span 1 or occasionally 2 lines
    if len(visible_lines) > 2:
        return None
        
    spans_all = [s for line in visible_lines for s in line.get("spans", []) if s.get("text", "").strip()]
    if not spans_all:
        return None
        
    text_content = "".join(decode_span_text(s) for s in spans_all).strip()
    if len(text_content) < 3 or text_content.isdigit():
        return None
        
    # Exclude list bullets
    if is_bullet_span(spans_all[0]):
        return None
        
    # Exclude visual/equation fragments
    if looks_like_visual_fragment(text_content):
        return None
        
    score = 0
    max_size = max(s.get("size", 12) for s in spans_all)
    ratio = max_size / body_size if body_size else 1.0
    
    # 1. Font size ratio weightings
    if ratio >= 1.6:
        score += 5
    elif ratio >= 1.25:
        score += 3
    elif ratio >= 1.0:
        score += 1
    elif ratio < 0.95:
        score -= 3
        
    # 2. Bold weight signals
    is_all_bold = all("Bold" in s.get("font", "") for s in spans_all)
    is_any_bold = any("Bold" in s.get("font", "") for s in spans_all)
    if is_all_bold:
        score += 3
    elif is_any_bold:
        score += 1
    else:
        score -= 2
        
    # 3. Punctuation checks (Sentence structures)
    if text_content.endswith(".") and len(text_content) > 30:
        score -= 4
        
    # 4. Heading formatting structure / Case
    if text_content.isupper():
        score += 2
    elif text_content[0].isupper():
        score += 1
        
    # 5. Length penalty
    if len(text_content) > 80:
        score -= 3
        
    # 6. Context Look-ahead: Heading followed by nested lists
    if page_context and page_context.get("is_followed_by_list"):
        score += 3
        
    # 7. Common decimal or numbering conventions
    if re.match(r'^(?:[A-Z0-9]+\.|\d+\.\d+|\b(?:Chapter|Section|Unit|Part|Figure|Table)\b)', text_content, re.IGNORECASE):
        score += 2
        
    if score >= 5:
        if ratio >= 1.5:
            return "h2"
        elif ratio >= 1.2:
            return "h3"
        else:
            return "h4"
            
    return None

def is_inside_table(bbox, tables) -> bool:
    bx0, by0, bx1, by1 = bbox
    cx = (bx0 + bx1) / 2
    cy = (by0 + by1) / 2
    for t in tables:
        tx0, ty0, tx1, ty1 = t.bbox
        if tx0 <= cx <= tx1 and ty0 <= cy <= ty1:
            return True
    return False

def render_table(table_data) -> str:
    """
    IMPROVEMENT: Enhanced table extraction (Requirement 9).
    Filters empty/None columns, handles multi-line/colspan items, and detects headers dynamically.
    """
    if not table_data:
        return ""
        
    # Remove entirely empty or None columns
    num_cols = len(table_data[0]) if table_data else 0
    non_empty_cols = []
    for col_idx in range(num_cols):
        has_content = False
        for row in table_data:
            if row[col_idx] is not None and str(row[col_idx]).strip() != "":
                has_content = True
                break
        if has_content:
            non_empty_cols.append(col_idx)
            
    if not non_empty_cols:
        return ""
        
    filtered_table = []
    for row in table_data:
        filtered_row = [row[idx] for idx in non_empty_cols]
        filtered_table.append(filtered_row)
        
    html_lines = ['<div class="table-responsive">', '<table class="notes-table">']
    
    # <thead> detection using cell contents
    use_first_as_header = False
    if len(filtered_table) > 1:
        first_row = filtered_table[0]
        non_empty = all(c is not None and str(c).strip() != "" for c in first_row)
        if non_empty:
            use_first_as_header = True
            
    if use_first_as_header:
        html_lines.append('<thead>')
        html_lines.append('<tr>')
        for h in filtered_table[0]:
            val = html.escape(str(h or "").strip())
            html_lines.append(f'<th>{val}</th>')
        html_lines.append('</tr>')
        html_lines.append('</thead>')
        body_rows = filtered_table[1:]
    else:
        body_rows = filtered_table
        
    if body_rows:
        html_lines.append('<tbody>')
        for row in body_rows:
            # Skip empty rows
            if not any(c is not None and str(c).strip() != "" for c in row):
                continue
            html_lines.append('<tr>')
            for cell in row:
                val = html.escape(str(cell or "").strip())
                html_lines.append(f'<td>{val}</td>')
            html_lines.append('</tr>')
        html_lines.append('</tbody>')
        
    html_lines.append('</table>')
    html_lines.append('</div>')
    return "\n".join(html_lines)

def is_color_block(block: dict, target_color: int) -> bool:
    for line in block.get("lines", []):
        for span in line.get("spans", []):
            if span.get("text", "").strip():
                if span.get("color", 0) == target_color:
                    return True
    return False

def render_text_block_semantic(block: dict, body_size: float, page: fitz.Page = None, page_context: dict = None, median_gap: float = 12.0) -> str:
    # Filter out running headers based on content and small font size
    text_spans = []
    for l in block.get("lines", []):
        text_spans.extend(l.get("spans", []))
    
    if text_spans:
        text_content = "".join(s.get("text", "") for s in text_spans).strip()
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
        
    # Check if this block is an info card (colored 0xe36c0a)
    if is_color_block(block, 0xe36c0a):
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
        
    heading_tag = classify_heading(visible_lines, body_size, page_context)
    if is_pink:
        heading_tag = "h2"
        
    if heading_tag:
        line = visible_lines[0]
        spans = line["spans"]
        # Convert custom colored (#17365d) headers or explicit "introduction" text or pink bg headers to h2
        color = spans[0].get("color", 0)
        inner = "".join(render_span_semantic(s) for s in spans)
        if color == 0x17365d or inner.strip().lower() == "introduction" or inner.strip().lower() == "economy- introduction" or is_pink:
            heading_tag = "h2"
            # Strip both strong and em from h2
            inner = inner.replace("<em>", "").replace("</em>", "").replace("<strong>", "").replace("</strong>", "")
        else:
            # Strip only em from other subheadings (keep strong for navy color)
            inner = inner.replace("<em>", "").replace("</em>", "")
        return f"<{heading_tag}>{inner}</{heading_tag}>"
        
    html_out = []
    active_lists = []  # Stack of bullet x-coordinates
    current_para_spans = []
    li_content_x = None # Track text start position of active list item for wrapped lines
    prev_line_y3 = None
    
    def close_all_lists():
        nonlocal li_content_x
        while active_lists:
            html_out.append("</li></ul>")
            active_lists.pop()
        li_content_x = None
        
    for line in visible_lines:
        spans = line["spans"]
        
        # Check if line looks like visual formula fragment (Requirement 3)
        line_text = "".join(decode_span_text(s) for s in spans).strip()
        is_visual = looks_like_visual_fragment(line_text)
        
        if is_bullet_span(spans[0]) and not is_visual:
            # Flush existing paragraph content
            if current_para_spans:
                para_text = "".join(render_span_semantic(s) for s in current_para_spans)
                html_out.append(f"<p>{para_text}</p>")
                current_para_spans = []
                
            x_bullet = spans[0]["bbox"][0]
            
            if not active_lists:
                html_out.append('<ul class="notes-list">')
                active_lists.append(x_bullet)
            else:
                if x_bullet > active_lists[-1] + 5:
                    level = len(active_lists)
                    cls_name = "notes-sub" if level == 1 else "notes-subsub"
                    html_out.append(f'<ul class="{cls_name}">')
                    active_lists.append(x_bullet)
                elif x_bullet < active_lists[-1] - 5:
                    while active_lists and x_bullet < active_lists[-1] - 5:
                        html_out.append("</li></ul>")
                        active_lists.pop()
                    if not active_lists:
                        html_out.append('<ul class="notes-list">')
                        active_lists.append(x_bullet)
                    else:
                        html_out.append("</li>")
                else:
                    html_out.append("</li>")
            
            content_spans = spans[1:]
            if content_spans:
                li_content_x = content_spans[0]["bbox"][0]
                inner = "".join(render_span_semantic(s) for s in content_spans)
            else:
                li_content_x = spans[0]["bbox"][2] + 4
                inner = ""
            html_out.append(f"<li>{inner}")
        else:
            # Check if this line is a continuation of the current bullet item (Requirement 5)
            is_continuation = False
            if active_lists and li_content_x is not None:
                line_x = spans[0]["bbox"][0]
                line_gap = (line["bbox"][1] - prev_line_y3) if prev_line_y3 is not None else 999
                # If x matches the bullet content and vertical distance is small
                if abs(line_x - li_content_x) < 20 and line_gap < (median_gap * 1.5):
                    is_continuation = True
                    
            if is_continuation:
                inner = "".join(render_span_semantic(s) for s in spans)
                if html_out:
                    last_item = html_out[-1]
                    gap_char = "" if last_item.endswith(" ") or inner.startswith(" ") else " "
                    html_out[-1] = last_item + gap_char + inner
            else:
                # Close lists and treat as standard paragraph
                close_all_lists()
                # Append to running paragraph list, keeping word spacing clean
                if current_para_spans and not current_para_spans[-1].get("text", "").endswith(" ") and not spans[0].get("text", "").startswith(" "):
                    current_para_spans.append({"text": " ", "font": spans[0].get("font", ""), "size": spans[0].get("size", 12), "color": spans[0].get("color", 0)})
                current_para_spans.extend(spans)
                
        prev_line_y3 = line["bbox"][3]
            
    # Flush remaining paragraph or list wraps
    if current_para_spans:
        para_text = "".join(render_span_semantic(s) for s in current_para_spans)
        html_out.append(f"<p>{para_text}</p>")
    
    close_all_lists()
    return "\n".join(html_out)

def render_page(doc: fitz.Document, page: fitz.Page, body_size: float, html_path: Path) -> str:
    rect = page.rect
    page_height = rect.height
    
    # 1. Find tables on page
    tables = page.find_tables()
    valid_tables = []
    for t in tables:
        tx0, ty0, tx1, ty1 = t.bbox
        if ty1 < 90 or ty0 > page_height - 75:
            continue
        valid_tables.append(t)
        
    # 2. Extract and filter text lines
    text_dict = page.get_text("dict")
    raw_lines = []
    
    for block in text_dict.get("blocks", []):
        block_type = block.get("type", 0)
        if block_type != 0:  # Skip images here, handled below
            continue
            
        bbox = block.get("bbox", (0, 0, 0, 0))
        # Skip blocks inside tables
        if is_inside_table(bbox, valid_tables):
            continue
            
        for line in block.get("lines", []):
            ly0 = line["bbox"][1]
            ly1 = line["bbox"][3]
            
            # Skip running headers and footers matching ignoring lists
            txt = "".join(s.get("text", "") for s in line.get("spans", [])).strip()
            norm_txt = re.sub(r'\d+', '', txt).strip().lower()
            
            # IMPROVEMENT: Dynamic running header/footer checks
            if page.number > 0: # Do not filter headers/footers on first cover page
                if ly1 < 80 and norm_txt in IGNORED_HEADERS:
                    continue
                if ly0 > page_height - 80 and norm_txt in IGNORED_FOOTERS:
                    continue
                # Fallback for extremely close margins
                if ly1 < 45 or ly0 > page_height - 45:
                    continue
                
            raw_lines.append(line)
            
    # Sort all lines on the page top-to-bottom
    raw_lines.sort(key=lambda l: l["bbox"][1])
    
    # IMPROVEMENT: Compute dynamic leading gaps on the page (Requirement 6)
    gaps = []
    for idx in range(len(raw_lines) - 1):
        prev_l = raw_lines[idx]
        curr_l = raw_lines[idx+1]
        gap = curr_l["bbox"][1] - prev_l["bbox"][3]
        if 0 < gap < 40:
            gaps.append(gap)
    median_gap = sorted(gaps)[len(gaps) // 2] if gaps else 12.0
    paragraph_split_threshold = max(1.4 * median_gap, 10.0)
    
    # 3. Group lines semantically from scratch
    semantic_blocks = []
    current_lines = []
    
    # Pre-build look-ahead mapping for context checks (Requirement 15)
    line_is_followed_by_list = {}
    for idx in range(len(raw_lines)):
        followed_by_list = False
        # Look ahead at the next few lines
        for j in range(idx + 1, min(idx + 4, len(raw_lines))):
            next_spans = [s for s in raw_lines[j].get("spans", []) if s.get("text", "").strip()]
            if next_spans:
                if is_bullet_span(next_spans[0]):
                    followed_by_list = True
                break
        line_is_followed_by_list[idx] = followed_by_list
    
    for idx, line in enumerate(raw_lines):
        spans = [s for s in line.get("spans", []) if s.get("text", "").strip()]
        if not spans:
            continue
            
        page_context = {"is_followed_by_list": line_is_followed_by_list.get(idx, False)}
        
        is_bullet = is_bullet_span(spans[0])
        is_heading = classify_heading([line], body_size, page_context) is not None
        is_pink = is_pink_heading_block(line["bbox"], page)
        
        # A new heading or bullet starts a new semantic block
        if is_bullet or is_heading or is_pink:
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
                # Dynamic paragraph separation gap
                if gap >= paragraph_split_threshold:
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
        
    # Add image blocks from the page
    img_idx = 1
    for block in text_dict.get("blocks", []):
        if block.get("type") == 1:  # Image block
            bbox = block.get("bbox", (0, 0, 0, 0))
            x0, y0, x1, y1 = bbox
            w = round(x1 - x0, 1)
            h = round(y1 - y0, 1)
            
            # Skip page headers/footers logo filtering (Requirement 7)
            if (w, h, round(x0, 0)) in IGNORED_LOGOS:
                continue
                
            if page.number > 0 and (y1 < 90 or y0 > page_height - 90) and (w, h, round(x0, 0)) in IGNORED_LOGOS:
                continue
                
            page_elements.append({
                "type": "image",
                "bbox": bbox,
                "data": block,
                "img_idx": img_idx
            })
            img_idx += 1
            
    # Add table blocks
    for t in valid_tables:
        page_elements.append({
            "type": "table",
            "bbox": t.bbox,
            "data": t.extract()
        })
        
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
    
    # 6. Render elements to HTML
    elements_html = []
    for element in page_elements:
        el_type = element["type"]
        if el_type == "table":
            if DEBUG_MODE:
                print(f"PAGE {page.number+1}: [TABLE] {len(element['data'])}x{len(element['data'][0]) if element['data'] else 0}", file=sys.stderr)
            elements_html.append(render_table(element["data"]))
        elif el_type == "image":
            bbox = element["bbox"]
            clip_rect = fitz.Rect(bbox)
            if clip_rect.width > 0 and clip_rect.height > 0:
                try:
                    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), clip=clip_rect)
                    img_bytes = pix.tobytes("png")
                    
                    # IMPROVEMENT: Image Output Directory (Requirement 18)
                    if IMAGE_DIR:
                        img_filename = f"page_{page.number + 1}_img_{element['img_idx']}.png"
                        img_dest = IMAGE_DIR / img_filename
                        img_dest.parent.mkdir(parents=True, exist_ok=True)
                        img_dest.write_bytes(img_bytes)
                        # Relative src reference in HTML
                        try:
                            src_ref = os.path.relpath(img_dest, html_path.parent).replace("\\", "/")
                        except Exception:
                            src_ref = f"images/{img_filename}"
                    else:
                        b64 = base64.b64encode(img_bytes).decode("ascii")
                        src_ref = f"data:image/png;base64,{b64}"
                        
                    if DEBUG_MODE:
                        print(f"PAGE {page.number+1}: [IMAGE] {src_ref}", file=sys.stderr)
                        
                    elements_html.append(
                        f'<figure><img src="{src_ref}" alt="Extracted Graphic" /></figure>'
                    )
                except Exception as e:
                    print(f"Error extracting image block: {e}", file=sys.stderr)
        elif el_type == "text":
            # For look-ahead context, find if next text block starts with list
            idx_in_raw = raw_lines.index(element["data"]["lines"][0]) if element["data"]["lines"] else 0
            page_context = {"is_followed_by_list": line_is_followed_by_list.get(idx_in_raw, False)}
            
            if DEBUG_MODE:
                tag = classify_heading(element["data"]["lines"], body_size, page_context)
                if tag:
                    print(f"PAGE {page.number+1}: [{tag.upper()}] {''.join(s.get('text','') for l in element['data']['lines'] for s in l.get('spans',[]))[:60]}", file=sys.stderr)
                else:
                    spans = [s for l in element["data"]["lines"] for s in l.get("spans", [])]
                    if spans and is_bullet_span(spans[0]):
                        print(f"PAGE {page.number+1}: [UL] {''.join(s.get('text','') for s in spans)[:60]}", file=sys.stderr)
                    else:
                        print(f"PAGE {page.number+1}: [P] {''.join(s.get('text','') for s in spans)[:60]}", file=sys.stderr)
                        
            text_html = render_text_block_semantic(element["data"], body_size, page, page_context, median_gap)
            if text_html:
                elements_html.append(text_html)
                
    content = "\n".join(elements_html)
    return PAGE_TEMPLATE.format(content=content)

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
        # Fallback to filename stem
        return Path(doc.name).stem
        
    # Sort spans by font size in descending order
    spans.sort(key=lambda s: s.get("size", 0), reverse=True)
    
    # Find the largest non-generic text
    for s in spans:
        text = s.get("text", "").strip()
        if text and text.lower() not in ["study notes", "studynotes"]:
            return text
            
    return spans[0].get("text", "").strip() if spans else "Document"

def convert(pdf_path: Path, html_path: Path, start: int, end: int) -> None:
    doc = fitz.open(pdf_path)
    page_count = doc.page_count
    
    # Auto-extract title from the first page of the PDF
    pdf_title = extract_pdf_title(doc)
    
    # If start page is not specified, default to 2 to skip the cover page
    start_idx = max(0, (start or 2) - 1)
    end_idx = min(page_count, end or page_count)
    body_size = compute_body_size(doc)
    
    # Pre-scan for Ignored Assets (Headers, Footers, Logos)
    pre_scan_document(doc, start_idx, end_idx)
 
    pages_html = []
    for page_index in range(start_idx, end_idx):
        page = doc[page_index]
        pages_html.append(render_page(doc, page, body_size, html_path))
 
    # CSS selection
    if CSS_HREF:
        # Standalone CSS link (Requirement 17)
        css_tag = f'<link rel="stylesheet" href="{CSS_HREF}">'
    else:
        css_tag = DEFAULT_INLINE_CSS
 
    html_path.write_text(
        DOC_TEMPLATE.format(
            title=html.escape(pdf_title),
            css_link=css_tag,
            pages="\n".join(pages_html),
        ),
        encoding="utf-8",
    )
    doc.close()

def main() -> None:
    global CSS_HREF, IMAGE_DIR, DEBUG_MODE
    
    parser = argparse.ArgumentParser(description="Convert a PDF to a semantic HTML file.")
    parser.add_argument("pdf", type=Path, nargs="?", default=Path(PDF_PATH), help="Path to the input PDF file")
    parser.add_argument("html", type=Path, nargs="?", default=None, help="Path to write the output HTML file")
    parser.add_argument("--start", type=int, default=2, help="First page to convert (1-based, default 2 to skip cover)")
    parser.add_argument("--end", type=int, default=None, help="Last page to convert (default: last page)")
    parser.add_argument("--css", type=str, default=None, help="Link to an external reader CSS file (disables inline fallback)")
    parser.add_argument("--image-dir", type=Path, default=None, help="Directory to save extracted images (disables base64 inline fallback)")
    parser.add_argument("--debug", action="store_true", help="Print debug/classification trace output to stderr")
    args = parser.parse_args()
 
    pdf_path = args.pdf
    
    # Setup global flags
    if args.css:
        CSS_HREF = args.css
    if args.image_dir:
        IMAGE_DIR = args.image_dir
    DEBUG_MODE = args.debug
    
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