"""
Convert a PDF to HTML with high layout fidelity using PyMuPDF.
 
Each page is rendered as an absolutely-positioned HTML block that mirrors
the PDF's text placement, fonts and embedded images, so the output looks
close to the original document rather than a plain text dump.
 
Install dependency:
    pip install pymupdf
 
Usage:
    1) Edit PDF_PATH below to point at your PDF.
    2) Run:  python3 pdf_to_html.py
    The converted .html file is saved into OUTPUT_DIR, named after the PDF.
 
    Optional CLI override (same behaviour, explicit paths):
    python3 pdf_to_html.py input.pdf output.html --start 1 --end 5
"""
 
import argparse
import base64
import html
import sys
from pathlib import Path
 
import pymupdf as fitz
 
# ====== EDIT THESE TWO LINES ======
PDF_PATH =  "C:/Users/AASTHA/Desktop/pdf automation/storage/queue/37556/document.pdf"
OUTPUT_DIR = "C:/Users/AASTHA/Desktop/pdf automation/storage/queue/37556/"
# ===================================
 
# Adobe "Symbol" font built-in encoding -> real Unicode.
# PyMuPDF returns these chars as U+F000 + code (Private Use Area), which has
# no glyph in normal fonts and renders as a tofu box. Map them back to the
# actual Greek letters / math symbols the Symbol font represents.
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
<section class="pdf-page" style="width:{width}px;height:{height}px;">
{content}
</section>
""".strip()
 
DOC_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>
  body {{
    margin: 0;
    padding: 24px;
    background: #e8e8e8;
    font-family: sans-serif;
  }}
  .pdf-page {{
    position: relative;
    margin: 0 auto 24px auto;
    background: #ffffff;
    box-shadow: 0 1px 4px rgba(0,0,0,0.3);
    overflow: hidden;
  }}
  .pdf-page img {{
    position: absolute;
  }}
  .pdf-block {{
    position: absolute;
    white-space: pre;
    line-height: 1;
    margin: 0;
    padding: 0;
    font-size: inherit;
    font-weight: normal;
    font-style: normal;
    color: inherit;
  }}
  ul.pdf-list {{
    position: static;
    margin: 0;
    padding: 0;
    list-style: none;
  }}
  li.pdf-block::before {{
    content: "\\2022  ";
  }}
</style>
</head>
<body>
{pages}
</body>
</html>
"""
 
 
def compute_body_size(doc: fitz.Document) -> float:
    """Most common font size (weighted by character count) across the doc.
 
    Used to tell body text apart from headings: a bold, standalone line
    whose size is close to (or bigger than) this is treated as a heading.
    """
    from collections import Counter
 
    counts: Counter = Counter()
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
 
 
def decode_span_text(span: dict) -> str:
    text = span.get("text", "")
    font = span.get("font", "")
    if "Symbol" in font:
        return decode_symbol_font(text)
    if "Wingdings" in font or "Webdings" in font:
        # These fonts are used exclusively as bullet-marker glyphs in
        # practice; PyMuPDF returns their private-use codepoints, which
        # have no glyph in a normal font and render as nothing. Normalise
        # every glyph from these fonts to a plain bullet.
        return "•" * len(text)
    return text
 
 
def render_span(span: dict, line_max_size: float) -> str:
    text = decode_span_text(span)
    if not text:
        return ""
    font = span.get("font", "sans-serif")
    size = span.get("size", 12)
    color = "#{:06x}".format(span.get("color", 0))
    weight = "bold" if "Bold" in font else "normal"
    style = "italic" if "Italic" in font or "Oblique" in font else "normal"
    valign = "vertical-align:super;" if size < line_max_size * 0.8 else ""
    return (
        '<span style="font-size:{size:.2f}px;font-family:\'{font}\',\'DejaVu Sans\',\'Noto Sans\',Arial,sans-serif;'
        'color:{color};font-weight:{weight};font-style:{style};{valign}">{text}</span>'.format(
            size=size,
            font=escape_font(font),
            color=color,
            weight=weight,
            style=style,
            valign=valign,
            text=html.escape(text),
        )
    )
 
 
def render_line_inline(spans: list) -> str:
    max_size = max((s.get("size", 12) for s in spans), default=12)
    return "".join(render_span(s, max_size) for s in spans)
 
 
def is_bullet_span(span: dict) -> bool:
    font = span.get("font", "")
    if "Wingdings" in font or "Webdings" in font:
        return True
    return decode_span_text(span).strip() == "•"
 
 
def classify_heading(visible_lines: list, body_size: float):
    """Return an 'h1'..'h3' tag name if this single-line block reads as a
    standalone heading (bold, sized up from body text, not a bullet/number),
    otherwise None."""
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
        return "h1"
    if ratio >= 1.3:
        return "h2"
    return "h3"
 
 
def render_page(doc: fitz.Document, page: fitz.Page, body_size: float) -> str:
    rect = page.rect
    image_html = []
    text_html = []
 
    text_dict = page.get_text("dict")
    for block in text_dict.get("blocks", []):
        if block.get("type") != 0:
            continue
        lines = block.get("lines", [])
        visible_lines = [
            ln for ln in lines if any(sp.get("text", "").strip() for sp in ln.get("spans", []))
        ]
        if not visible_lines:
            continue
 
        heading_tag = classify_heading(visible_lines, body_size)
        if heading_tag:
            line = visible_lines[0]
            spans = [s for s in line["spans"] if s.get("text", "").strip()]
            left, top = line["bbox"][0], line["bbox"][1]
            text_html.append(
                '<{tag} class="pdf-block" style="left:{left:.2f}px;top:{top:.2f}px;">{inner}</{tag}>'.format(
                    tag=heading_tag, left=left, top=top, inner=render_line_inline(spans)
                )
            )
            continue
 
        list_items = []
        for line in visible_lines:
            spans = [s for s in line["spans"] if s.get("text", "").strip()]
            if not spans:
                continue
            left, top = line["bbox"][0], line["bbox"][1]
            if is_bullet_span(spans[0]):
                inner = render_line_inline(spans[1:])
                list_items.append(
                    '<li class="pdf-block" style="left:{left:.2f}px;top:{top:.2f}px;">{inner}</li>'.format(
                        left=left, top=top, inner=inner
                    )
                )
            else:
                inner = render_line_inline(spans)
                text_html.append(
                    '<p class="pdf-block" style="left:{left:.2f}px;top:{top:.2f}px;">{inner}</p>'.format(
                        left=left, top=top, inner=inner
                    )
                )
        if list_items:
            text_html.append('<ul class="pdf-list">' + "".join(list_items) + "</ul>")
 
    # Images, positioned to match their original placement on the page.
    for img in page.get_images(full=True):
        xref, smask_xref = img[0], img[1]
        try:
            img_rects = page.get_image_rects(xref)
        except Exception:
            img_rects = []
        if not img_rects:
            continue
        try:
            pix = fitz.Pixmap(doc, xref)
            if pix.colorspace and pix.colorspace.n >= 4:  # CMYK -> RGB
                pix = fitz.Pixmap(fitz.csRGB, pix)
            if smask_xref:
                # fitz.Pixmap(doc, xref) does not reliably apply the PDF's
                # /SMask, which can leave transparent areas rendered as
                # solid black. Drop any bogus alpha and merge the real
                # soft-mask in as the alpha channel.
                if pix.alpha:
                    pix = fitz.Pixmap(pix, 0)
                mask = fitz.Pixmap(doc, smask_xref)
                pix = fitz.Pixmap(pix, mask)
            img_bytes = pix.tobytes("png")
        except Exception:
            continue
 
        b64 = base64.b64encode(img_bytes).decode("ascii")
        for r in img_rects:
            image_html.append(
                '<img src="data:image/png;base64,{data}" '
                'style="left:{left:.2f}px;top:{top:.2f}px;width:{w:.2f}px;height:{h:.2f}px;" />'.format(
                    data=b64,
                    left=r.x0,
                    top=r.y0,
                    w=r.width,
                    h=r.height,
                )
            )
 
    # Images are emitted before text in the DOM so they sit behind it
    # (matches how background/watermark images are drawn under text in the
    # original PDF) instead of covering the text on top.
    return PAGE_TEMPLATE.format(
        width=int(rect.width),
        height=int(rect.height),
        content="\n".join(image_html + text_html),
    )
 
 
def escape_font(font_name: str) -> str:
    return font_name.replace("'", "").replace('"', "")
 
 
def main() -> None:
    parser = argparse.ArgumentParser(description="Convert a PDF to a layout-accurate HTML file.")
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
 
 