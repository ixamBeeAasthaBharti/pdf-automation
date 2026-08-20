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
    return decode_span_text(span).strip() == "•"

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
    bx0, by0, bx1, by1 = bbox
    cx = (bx0 + bx1) / 2
    cy = (by0 + by1) / 2
    for t in tables:
        tx0, ty0, tx1, ty1 = t.bbox
        if tx0 <= cx <= tx1 and ty0 <= cy <= ty1:
            return True
    return False

def render_table(table_data) -> str:
    if not table_data:
        return ""
    html_lines = ['<div class="table-responsive">', '<table>']
    
    if len(table_data) > 0:
        headers = table_data[0]
        html_lines.append('<thead>')
        html_lines.append('<tr>')
        for h in headers:
            val = html.escape(str(h or "").strip())
            html_lines.append(f'<th>{val}</th>')
        html_lines.append('</tr>')
        html_lines.append('</thead>')
        
    if len(table_data) > 1:
        html_lines.append('<tbody>')
        for row in table_data[1:]:
            if not any(row):
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

def render_text_block_semantic(block: dict, body_size: float) -> str:
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
        
    heading_tag = classify_heading(visible_lines, body_size)
    if heading_tag:
        line = visible_lines[0]
        spans = line["spans"]
        # Convert custom colored (#17365d) headers or explicit "introduction" text to h2
        color = spans[0].get("color", 0)
        inner = "".join(render_span_semantic(s) for s in spans)
        if color == 0x17365d or inner.strip().lower() == "introduction" or inner.strip().lower() == "economy- introduction":
            heading_tag = "h2"
        return f"<{heading_tag}>{inner}</{heading_tag}>"
        
    html_out = []
    in_list = False
    current_para_spans = []
    
    for line in visible_lines:
        spans = line["spans"]
        if is_bullet_span(spans[0]):
            # Flush existing paragraph content
            if current_para_spans:
                para_text = "".join(render_span_semantic(s) for s in current_para_spans)
                html_out.append(f"<p>{para_text}</p>")
                current_para_spans = []
                
            if not in_list:
                html_out.append("<ul>")
                in_list = True
            content_spans = spans[1:]
            if content_spans:
                inner = "".join(render_span_semantic(s) for s in content_spans)
            else:
                inner = ""
            html_out.append(f"<li>{inner}</li>")
        else:
            if in_list:
                html_out.append("</ul>")
                in_list = False
            # Append to running paragraph list, keeping word spacing clean
            if current_para_spans and not current_para_spans[-1].get("text", "").endswith(" ") and not spans[0].get("text", "").startswith(" "):
                current_para_spans.append({"text": " ", "font": spans[0].get("font", ""), "size": spans[0].get("size", 12), "color": spans[0].get("color", 0)})
            current_para_spans.extend(spans)
            
    # Flush remaining paragraph or list wraps
    if current_para_spans:
        para_text = "".join(render_span_semantic(s) for s in current_para_spans)
        html_out.append(f"<p>{para_text}</p>")
    elif in_list:
        html_out.append("</ul>")
        
    return "\n".join(html_out)

def render_page(doc: fitz.Document, page: fitz.Page, body_size: float) -> str:
    rect = page.rect
    page_height = rect.height
    
    # 1. Find tables on page
    tables = page.find_tables()
    valid_tables = []
    for t in tables:
        tx0, ty0, tx1, ty1 = t.bbox
        # Skip tables that lie in header/footer margin
        if ty1 < 90 or ty0 > page_height - 75:
            continue
        valid_tables.append(t)
        
    # 2. Extract elements
    text_dict = page.get_text("dict")
    page_elements = []
    
    for block in text_dict.get("blocks", []):
        bbox = block.get("bbox", (0, 0, 0, 0))
        bx0, by0, bx1, by1 = bbox
        block_type = block.get("type", 0)
        
        # Text blocks need 60 to keep headings, but image blocks need 90 to skip logo
        header_limit = 60 if block_type == 0 else 90
        
        # Skip header and footer zones
        if by1 < header_limit or by0 > page_height - 75:
            continue
            
        # Skip blocks inside tables
        if is_inside_table(bbox, valid_tables):
            continue
            
        block_type = block.get("type", 0)
        if block_type == 0:  # Text block
            page_elements.append({
                "type": "text",
                "bbox": bbox,
                "data": block
            })
        elif block_type == 1:  # Image block
            if page.number == 0:
                continue
            page_elements.append({
                "type": "image",
                "bbox": bbox,
                "data": block
            })
            
    for t in valid_tables:
        page_elements.append({
            "type": "table",
            "bbox": t.bbox,
            "data": t.extract()
        })
        
    # Sort elements by y0 (top coordinate) for natural document flow
    page_elements.sort(key=lambda e: e["bbox"][1])
    
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
            text_html = render_text_block_semantic(element["data"], body_size)
            if text_html:
                elements_html.append(text_html)
                
    content = "\n".join(elements_html)
    return PAGE_TEMPLATE.format(content=content)

def convert(pdf_path: Path, html_path: Path, start: int, end: int) -> None:
    doc = fitz.open(pdf_path)
    page_count = doc.page_count
    start_idx = max(0, (start or 1) - 1)
    end_idx = min(page_count, end or page_count)
    body_size = compute_body_size(doc)
 
    pages_html = []
    for page_index in range(start_idx, end_idx):
        page = doc[page_index]
        pages_html.append(render_page(doc, page, body_size))
 
    html_path.write_text(
        DOC_TEMPLATE.format(
            title=html.escape(pdf_path.stem),
            pages="\n".join(pages_html),
        ),
        encoding="utf-8",
    )
    doc.close()

def main() -> None:
    parser = argparse.ArgumentParser(description="Convert a PDF to a semantic HTML file.")
    parser.add_argument("pdf", type=Path, nargs="?", default=Path(PDF_PATH), help="Path to the input PDF file")
    parser.add_argument("html", type=Path, nargs="?", default=None, help="Path to write the output HTML file")
    parser.add_argument("--start", type=int, default=1, help="First page to convert (1-based, default 1)")
    parser.add_argument("--end", type=int, default=None, help="Last page to convert (default: last page)")
    args = parser.parse_args()
 
    pdf_path = args.pdf
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