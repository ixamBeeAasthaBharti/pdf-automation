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
<style>
  body {{
    margin: 0;
    padding: 40px 20px;
    background-color: #f7f9fa;
    font-family: 'Literata', 'Lora', Georgia, serif;
    color: #1a1a1a;
    line-height: 1.65;
  }}
  .container {{
    max-width: 800px;
    margin: 0 auto;
    background: #ffffff;
    padding: 40px;
    border-radius: 8px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
  }}
  .pdf-page {{
    margin-bottom: 40px;
    border-bottom: 1px dashed #e1e8ed;
    padding-bottom: 40px;
  }}
  .pdf-page:last-child {{
    margin-bottom: 0;
    border-bottom: none;
    padding-bottom: 0;
  }}
  h1, h2, h3, h4 {{
    color: #0b2240;
    font-family: 'Outfit', sans-serif;
    font-weight: 700;
    margin-top: 1.8em;
    margin-bottom: 0.6em;
  }}
  h1 {{
    font-size: 2.2rem;
    border-bottom: 2px solid #e1e8ed;
    padding-bottom: 10px;
    margin-top: 0;
  }}
  h2 {{
    font-size: 1.8rem;
    border-bottom: 1px solid #ecf0f1;
    padding-bottom: 8px;
  }}
  h3 {{
    font-size: 1.4rem;
  }}
  h4 {{
    font-size: 1.15rem;
  }}
  p {{
    margin-top: 0;
    margin-bottom: 1.2em;
    text-align: justify;
  }}
  ul {{
    margin-top: 0;
    margin-bottom: 1.2em;
    padding-left: 24px;
  }}
  li {{
    margin-bottom: 0.6em;
  }}
  table {{
    width: 100%;
    border-collapse: collapse;
    margin: 24px 0;
    font-size: 0.95rem;
  }}
  th, td {{
    padding: 12px 15px;
    text-align: left;
    border-bottom: 1px solid #e1e8ed;
    vertical-align: top;
  }}
  .table-cell-line {{
    margin: 0 0 4px;
  }}
  .table-cell-line:last-child {{
    margin-bottom: 0;
  }}
  th {{
    background-color: #f4f6f8;
    color: #0b2240;
    font-weight: 600;
  }}
  tr:hover {{
    background-color: #fcfdfe;
  }}
  .table-responsive {{
    overflow-x: auto;
    margin: 24px 0;
  }}
  img {{
    max-width: 100%;
    height: auto;
    display: block;
    margin: 24px auto;
    border-radius: 4px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.06);
  }}
  .info-card {{
    border: 2px solid #e36c0a;
    border-radius: 8px;
    background-color: #fdfaf6;
    padding: 15px 20px;
    margin: 20px auto;
    max-width: 85%;
    text-align: center;
  }}
  .info-card p {{
    margin: 0;
    text-align: center;
    color: #e36c0a;
    font-size: 0.95rem;
    line-height: 1.65;
  }}
  .info-card strong {{
    color: #e36c0a !important;
    font-weight: 700;
  }}
</style>
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
    return decoded in ("•", "·", "◆", "▪", "▸", "►", "‣", "–", "—", "✓", "✔", "ü", "\u2713", "\u2714", "\uf0fc")

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
    """Return 'h2'..'h4' if block reads as a standalone heading."""
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
    max_size = max(s.get("size", 12) for s in spans)
    ratio = max_size / body_size if body_size else 1
    if ratio >= 1.6:
        return "h2"
    if ratio >= 1.3:
        return "h3"
    return "h4"

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

            # Ignore footer/page-number regions.
            if ty1 < 90 or ty0 > page_height - 75:
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
        
    heading_tag = classify_heading(visible_lines, body_size)
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
    
    for line in visible_lines:
        spans = line["spans"]
        if is_bullet_span(spans[0]):
            # Flush existing paragraph content
            if current_para_spans:
                para_text = "".join(render_span_semantic(s) for s in current_para_spans)
                html_out.append(f"<p>{para_text}</p>")
                current_para_spans = []
                
            x_bullet = spans[0]["bbox"][0]
            
            if not active_lists:
                bullet_char = decode_span_text(spans[0]).strip()
                is_checkmark = bullet_char in ("✓", "✔", "ü", "\u2713", "\u2714", "\uf0fc")
                if is_checkmark:
                    html_out.append('<ul class="notes-sub">')
                    active_lists.append(x_bullet - 20)  # Dummy parent level
                    active_lists.append(x_bullet)
                else:
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
                # Append to running paragraph list, keeping word spacing clean
                if current_para_spans and not current_para_spans[-1].get("text", "").endswith(" ") and not spans[0].get("text", "").startswith(" "):
                    current_para_spans.append({"text": " ", "font": spans[0].get("font", ""), "size": spans[0].get("size", 12), "color": spans[0].get("color", 0)})
                current_para_spans.extend(spans)
            
    # Flush remaining paragraph or list wraps
    if current_para_spans:
        para_text = "".join(render_span_semantic(s) for s in current_para_spans)
        html_out.append(f"<p>{para_text}</p>")
    
    while active_lists:
        html_out.append("</li></ul>")
        active_lists.pop()
        
    return "\n".join(html_out)

def render_page(doc: fitz.Document, page: fitz.Page, body_size: float) -> str:
    rect = page.rect
    page_height = rect.height
    
    # 1. Find and VALIDATE tables before excluding any text from the page.
    # Never use raw page.find_tables() results here.
    valid_tables = find_valid_tables(page)
        
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
            
            # Skip header and footer zones (ly1 < 68 skips running headers)
            if ly1 < 68 or ly0 > page_height - 75:
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
                # Current block is normal text. Flush if new line is a bullet.
                if is_bullet:
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
                limit = 28.0 if is_bullet else 16.0
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
        
    # Add image blocks from the page
    for block in text_dict.get("blocks", []):
        if block.get("type") == 1:  # Image block
            bbox = block.get("bbox", (0, 0, 0, 0))
            if page.number == 0 or bbox[3] < 90 or bbox[1] > page_height - 75:
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
            elements_html.append(render_table(element["data"]))
        elif el_type == "image":
            bbox = element["bbox"]
            clip_rect = fitz.Rect(bbox)
            if clip_rect.width > 0 and clip_rect.height > 0:
                try:
                    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), clip=clip_rect)
                    img_bytes = pix.tobytes("png")
                    b64 = base64.b64encode(img_bytes).decode("ascii")
                    elements_html.append(
                        f'<img src="data:image/png;base64,{b64}" alt="Extracted Graphic" />'
                    )
                except Exception as e:
                    print(f"Error extracting image block: {e}", file=sys.stderr)
        elif el_type == "text":
            text_html = render_text_block_semantic(element["data"], body_size, page)
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
 
    pages_html = []
    for page_index in range(start_idx, end_idx):
        page = doc[page_index]
        pages_html.append(render_page(doc, page, body_size))
 
    html_path.write_text(
        DOC_TEMPLATE.format(
            title=html.escape(pdf_title),
            pages="\n".join(pages_html),
        ),
        encoding="utf-8",
    )
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