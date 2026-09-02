# """
# Convert a PDF to clean, semantic, flowable HTML using PyMuPDF.

# This script parses a PDF directly, extracts layout structure (headings, lists,
# paragraphs, tables, images), ignores header/footer elements, and outputs a 
# fully responsive, semantic HTML5 document.

# Usage:
#     python scripts/pdf_html.py input.pdf output.html --start 1 --end 5
# """

# import argparse
# import base64
# import html
# import sys
# from pathlib import Path

# import re
# import pymupdf as fitz

# # ====== EDIT THESE TWO LINES ======
# PDF_PATH = "C:/Users/AASTHA/Desktop/pdf automation/storage/queue/37556/document.pdf"
# OUTPUT_DIR = "C:/Users/AASTHA/Desktop/pdf automation/storage/"
# # ===================================

# # Adobe "Symbol" font built-in encoding -> real Unicode.
# SYMBOL_FONT_MAP = {
#     0x20: " ", 0x21: "!", 0x23: "#", 0x25: "%", 0x26: "&",
#     0x28: "(", 0x29: ")", 0x2A: "∗", 0x2B: "+", 0x2C: ",",
#     0x2D: "−", 0x2E: ".", 0x2F: "/",
#     0x3A: ":", 0x3B: ";", 0x3C: "<", 0x3D: "=", 0x3E: ">", 0x3F: "?",
#     0x40: "≅",
#     0x41: "Α", 0x42: "Β", 0x43: "Χ", 0x44: "∆",
#     0x45: "Ε", 0x46: "Φ", 0x47: "Γ", 0x48: "Η",
#     0x49: "Ι", 0x4A: "ϑ", 0x4B: "Κ", 0x4C: "Λ",
#     0x4D: "Μ", 0x4E: "Ν", 0x4F: "Ο",
#     0x50: "Π", 0x51: "Θ", 0x52: "Ρ", 0x53: "Σ",
#     0x54: "Τ", 0x55: "Υ", 0x56: "ς", 0x57: "Ω",
#     0x58: "Ξ", 0x59: "Ψ", 0x5A: "Ζ",
#     0x5B: "[", 0x5C: "∴", 0x5D: "]", 0x5E: "⊥", 0x5F: "_",
#     0x61: "α", 0x62: "β", 0x63: "χ", 0x64: "δ",
#     0x65: "ε", 0x66: "φ", 0x67: "γ", 0x68: "η",
#     0x69: "ι", 0x6A: "ϕ", 0x6B: "κ", 0x6C: "λ",
#     0x6D: "μ", 0x6E: "ν", 0x6F: "ο",
#     0x70: "π", 0x71: "θ", 0x72: "ρ", 0x73: "σ",
#     0x74: "τ", 0x75: "υ", 0x76: "ϖ", 0x77: "ω",
#     0x78: "ξ", 0x79: "ψ", 0x7A: "ζ",
#     0x7B: "{", 0x7C: "|", 0x7D: "}", 0x7E: "∼",
#     0xA1: "ϒ", 0xA2: "′", 0xA3: "≤", 0xA4: "⁄",
#     0xA5: "∞", 0xA6: "ƒ", 0xA7: "♣", 0xA8: "♦",
#     0xA9: "♥", 0xAA: "♠", 0xAB: "↔", 0xAC: "←",
#     0xAD: "↑", 0xAE: "→", 0xAF: "↓",
#     0xB0: "°", 0xB1: "±", 0xB2: "″", 0xB3: "≥",
#     0xB4: "×", 0xB5: "∝", 0xB6: "∂", 0xB7: "•",
#     0xB8: "÷", 0xB9: "≠", 0xBA: "≡", 0xBB: "≈",
#     0xBC: "…",
#     0xD1: "∇", 0xD2: "®", 0xD3: "©", 0xD4: "™",
#     0xD5: "∏", 0xD6: "√", 0xD7: "⋅", 0xD8: "¬",
#     0xD9: "∧", 0xDA: "∨",
#     0xE0: "◊",
#     0xE5: "∑",
#     0xF2: "∫",
#     # Wingdings check mark (U+F0FC -> offset 0xFC)
#     0xFC: "✓",
# }

# def decode_symbol_font(text: str) -> str:
#     return "".join(SYMBOL_FONT_MAP.get(ord(c) - 0xF000, c) for c in text)

# PAGE_TEMPLATE = """
# <section class="pdf-page">
# {content}
# </section>
# """.strip()

# DOC_TEMPLATE = """<!DOCTYPE html>
# <html lang="en">
# <head>
# <meta charset="utf-8">
# <title>{title}</title>
# </head>
# <body>
# <article>
# <main>
# {pages}
# </main>
# </article>
# </body>
# </html>
# """

# def compute_body_size(doc: fitz.Document) -> float:
#     """Most common font size (weighted by character count) across the doc.
#     Used to tell body text apart from headings.
#     """
#     from collections import Counter
#     counts = Counter()
#     for page in doc:
#         for block in page.get_text("dict").get("blocks", []):
#             if block.get("type") != 0:
#                 continue
#             for line in block.get("lines", []):
#                 for span in line.get("spans", []):
#                     text = span.get("text", "")
#                     if not text.strip():
#                         continue
#                     counts[round(span.get("size", 12))] += len(text)
#     return counts.most_common(1)[0][0] if counts else 12

# def decode_span_text(span: dict) -> str:
#     text = span.get("text", "")
#     if not text:
#         return ""
#     # Clean CID encoding quotes artifacts (e.g. low double quotes „ -> ", high curly quotes " " -> ")
#     text = text.replace("\u201e", '"').replace("\u201c", '"').replace("\u201d", '"').replace("\u2018", "'").replace("\u2019", "'")
#     font = span.get("font", "")
#     if "Symbol" in font:
#         return decode_symbol_font(text)
#     if "Wingdings" in font or "Webdings" in font:
#         res = []
#         for c in text:
#             val = ord(c)
#             if val == 0xF0FC or val == 0xFC or val == 0x2713 or val == 0x2714:
#                 res.append("✓")
#             else:
#                 res.append("•")
#         return "".join(res)
#     return text


# def render_span_semantic(span: dict) -> str:
#     if "custom_html" in span:
#         return span["custom_html"]
#     text = decode_span_text(span)
#     if not text.strip():
#         return ""
#     font = span.get("font", "")
#     flags = span.get("flags", 0)
#     is_bold = "Bold" in font or bool(flags & 1)
#     is_italic = "Italic" in font or "Oblique" in font or bool(flags & 2)
#     escaped_text = html.escape(text)
    
#     if is_bold:
#         escaped_text = f"<strong>{escaped_text}</strong>"
#     if is_italic:
#         escaped_text = f"<em>{escaped_text}</em>"
#     return escaped_text


# def get_repeated_image_xrefs(doc: fitz.Document, min_pages: int = 3) -> set:
#     """Find image XRefs reused across many pages (shared templates/backgrounds)."""
#     counts = {}
#     for page in doc:
#         seen = set()
#         try:
#             infos = page.get_image_info(xrefs=True)
#         except Exception:
#             infos = []
#         for info in infos:
#             xref = info.get("xref")
#             if xref and xref not in seen:
#                 seen.add(xref)
#                 counts[xref] = counts.get(xref, 0) + 1
#     return {xref for xref, count in counts.items() if count >= min_pages}


# def is_cover_page(page: fitz.Page, body_size: float) -> bool:
#     """
#     Analyzes the first page to heuristically determine if it is a cover page.
#     A cover page is characterized by:
#       - Low content density (low total character count)
#       - Dominance of large title/heading text rather than body text
#       - Absence of standard structured elements like tables, bullets, numbered questions,
#         or multi-line paragraph text blocks.
#     """
#     # 1. Quick-reject if tables are present (almost never on cover pages)
#     try:
#         tables = find_valid_tables(page)
#         if tables and len(tables) > 0:
#             return False
#     except Exception:
#         pass

#     text_dict = page.get_text("dict")
#     blocks = text_dict.get("blocks", [])
    
#     # Filter for blocks that actually contain visible text
#     text_blocks = []
#     for b in blocks:
#         if b.get("type", 0) == 0:
#             # Reconstruct the string in the block
#             block_text = "".join(
#                 "".join(s.get("text", "") for s in line.get("spans", []))
#                 for line in b.get("lines", [])
#             ).strip()
#             if block_text:
#                 text_blocks.append((b, block_text))
                
#     if not text_blocks:
#         return True  # Empty/purely graphical first page is treated as a cover

#     # 2. Extract layout and character-level signals
#     total_chars = 0
#     body_chars = 0
#     header_chars = 0
#     line_count = 0
    
#     has_bullets = False
#     has_questions = False
#     has_long_paragraphs = False
    
#     # Check for question prefixes (e.g. "Q1.", "Ques 2.") or ending question marks
#     question_pattern = re.compile(r'(^(q|ques|question|प्रश्|प्रश्न)\s*\d+[\.\s\:\-]|[\?？][\s]*$)', re.IGNORECASE)

#     for block, block_text in text_blocks:
#         lines = block.get("lines", [])
        
#         # Check if the block represents normal paragraph content
#         visible_line_count = sum(1 for l in lines if "".join(s.get("text", "") for s in l.get("spans", [])).strip())
#         if len(block_text) > 150 and visible_line_count >= 3:
#             has_long_paragraphs = True
            
#         if question_pattern.search(block_text):
#             has_questions = True

#         for line in lines:
#             spans = [s for s in line.get("spans", []) if s.get("text", "").strip()]
#             if not spans:
#                 continue
                
#             line_count += 1
            
#             # Check for bullet symbols
#             first_char = spans[0].get("text", "").strip()
#             first_font = spans[0].get("font", "")
#             if "wingdings" in first_font.lower() or "webdings" in first_font.lower() or first_char in ("•", "·", "◆", "▪", "▸", "►", "‣", "–", "—", "✓", "✔", "ü"):
#                 has_bullets = True

#             for span in spans:
#                 text = span.get("text", "")
#                 length = len(text)
#                 total_chars += length
#                 size = span.get("size", 12)
                
#                 # Compare font sizes to estimate headers vs body text
#                 if abs(size - body_size) <= 1.5:
#                     body_chars += length
#                 elif size > body_size + 2.0:
#                     header_chars += length

#     # 3. Rule Evaluation (Signal combination)
#     # If standard page components exist, it's not a cover page
#     if has_long_paragraphs or has_bullets or has_questions:
#         return False

#     # High line density or high block counts imply a content page
#     if line_count > 25 or len(text_blocks) > 8:
#         return False

#     # Significant amount of body text implies a content page
#     if body_chars > 300:
#         return False

#     # Large amount of overall text content implies a content page
#     if total_chars > 800:
#         return False

#     # Cover pages typically have high proportion of headers/titles
#     if total_chars > 0 and (header_chars / total_chars) > 0.5:
#         return True

#     # Very sparse pages (< 500 characters) are treated as cover pages
#     if total_chars < 500:
#         return True

#     return False

# COMMON_WORD_ABBREVS = {
#     "ibid", "etc", "note", "vol", "no", "vs", "dr", "mr", "ms", "inc",
#     "ltd", "co", "fig", "page", "total", "ref", "sec", "art", "para", "ver"
# }

# def is_alphanumeric_prefix(text: str) -> bool:
#     """Return True if text is a valid list prefix like '1.', 'a.', 'i.', '(a)', 'b)'."""
#     if not text:
#         return False
#     text_clean = text.strip()

#     # Match numeric list prefix e.g. "1.", "(1)", "1)"
#     if re.match(r'^(\(?\d{1,3}\)[\.\)]?|\d{1,3}[\.\)])$', text_clean):
#         return True

#     # Match letter / roman numeral list prefix e.g. "a.", "(a)", "a)", "i.", "ii)", "(iii)"
#     m = re.match(r'^(\(?([a-zA-Z]{1,3}|[IVXivx]{1,4})\)[\.\)]?|([a-zA-Z]{1,3}|[IVXivx]{1,4})[\.\)])$', text_clean)
#     if m:
#         raw_letters = (m.group(2) or m.group(3) or "").lower()
#         if raw_letters in COMMON_WORD_ABBREVS:
#             return False
#         return True

#     return False


# def is_bullet_span(span: dict) -> bool:
#     if not span:
#         return False
#     font = span.get("font", "")
#     if "Wingdings" in font or "Webdings" in font:
#         return True
#     decoded = decode_span_text(span).strip()
#     if not decoded:
#         return False

#     if decoded in ("-", "–", "—", "•", "·", "◆", "▪", "▸", "►", "‣", "✓", "✔", "ü", "\u2713", "\u2714", "\uf0fc"):
#         return True

#     if "Courier" in font and decoded == "o":
#         return True

#     # Check if span text starts with a bullet character or 'o' sub-bullet
#     if re.match(r'^([-–—•·◆▪▸►‣✓✔ü\u2713\u2714\uf0fc\u25ef\u25cb\u25cf]|o\b)\s*', decoded, re.IGNORECASE):
#         return True

#     # Check if first word of span is an alphanumeric or Roman numeral list prefix (e.g. "1.", "a.", "I.", "II.")
#     first_word = decoded.split()[0] if decoded.split() else ""
#     if is_alphanumeric_prefix(first_word):
#         return True

#     return False


# def is_standalone_line_prefix(text: str) -> bool:
#     """Check if a line text starts an MCQ option, explanation, passage, question header, or dash bullet."""
#     if not text:
#         return False
#     text_clean = text.strip()
#     # Dash bullet lines e.g. "- ", "– ", "— "
#     if re.match(r'^[-–—]\s+', text_clean):
#         return True
#     # MCQ options e.g. "A. ", "B. ", "C. ", "D. ", "E. ", "(A)", "(B)", "a)", "b)"
#     if re.match(r'^(?:[A-E]\.|\([A-E]\)|[a-e]\))\s*', text_clean):
#         return True
#     # Explanation / Passage / Question prefixes e.g. "Explanation-", "Explanation:", "Passage -", "Passage:"
#     if re.match(r'^(Explanation|Passage|Note|Solution)\b', text_clean, re.IGNORECASE):
#         return True
#     # Question numbers e.g. "6. ", "15. ", "Q1. ", "Q.1 "
#     if re.match(r'^(?:Q(?:ues)?\.?\s*\d+|\d{1,3}\.)\s+[A-Z]', text_clean):
#         return True
#     return False


# def format_paragraph_dashes_and_spaces(para_text: str) -> str:
#     """Return paragraph text as-is without replacing dashes with arrows."""
#     return para_text





# def is_pink_heading_block(bbox, page) -> bool:
#     if page is None:
#         return False
#     bx0, by0, bx1, by1 = bbox
#     cx = (bx0 + bx1) / 2
#     cy = (by0 + by1) / 2
#     for d in page.get_drawings():
#         fill = d.get("fill")
#         if fill and len(fill) == 3:
#             r, g, b = fill
#             # Pink, magenta, lavender, soft purple, soft red background highlights
#             if (0.82 <= r <= 0.99 and 0.65 <= g <= 0.92 and 0.65 <= b <= 0.95 and (r > g or r > b)) or \
#                (0.90 <= r <= 0.98 and 0.80 <= g <= 0.90 and 0.80 <= b <= 0.92):
#                 rect = d.get("rect")
#                 if rect:
#                     if rect.x0 - 10 <= cx <= rect.x1 + 10 and rect.y0 - 10 <= cy <= rect.y1 + 10:
#                         return True
#     return False

# def split_block_semantically(block: dict) -> list:
#     lines = block.get("lines", [])
#     if not lines:
#         return []
        
#     split_blocks = []
#     current_lines = []
    
#     for line in lines:
#         spans = [s for s in line.get("spans", []) if s.get("text", "").strip()]
#         if not spans:
#             continue
            
#         is_bullet = is_bullet_span(spans[0])
#         is_all_bold = all("Bold" in s.get("font", "") for s in spans)
#         text_content = "".join(decode_span_text(s) for s in spans).strip()
#         is_heading = is_all_bold and not is_bullet and len(text_content) < 80 and not text_content.endswith(".")
        
#         # If it's a bullet or a heading, it marks the start of a new section.
#         # So we flush the previous section (if any) first.
#         if is_bullet or is_heading:
#             if current_lines:
#                 new_block = block.copy()
#                 new_block["lines"] = current_lines
#                 sx0 = min(l["bbox"][0] for l in current_lines)
#                 sy0 = min(l["bbox"][1] for l in current_lines)
#                 sx1 = max(l["bbox"][2] for l in current_lines)
#                 sy1 = max(l["bbox"][3] for l in current_lines)
#                 new_block["bbox"] = (sx0, sy0, sx1, sy1)
#                 split_blocks.append(new_block)
#                 current_lines = []
                
#         current_lines.append(line)
            
#     if current_lines:
#         new_block = block.copy()
#         new_block["lines"] = current_lines
#         sx0 = min(l["bbox"][0] for l in current_lines)
#         sy0 = min(l["bbox"][1] for l in current_lines)
#         sx1 = max(l["bbox"][2] for l in current_lines)
#         sy1 = max(l["bbox"][3] for l in current_lines)
#         new_block["bbox"] = (sx0, sy0, sx1, sy1)
#         split_blocks.append(new_block)
        
#     return split_blocks

# def classify_heading(visible_lines: list, body_size: float):
#     """Return 'h2' or 'h3' if block reads as a genuine standalone heading."""
#     if len(visible_lines) != 1:
#         return None
#     spans = [s for s in visible_lines[0].get("spans", []) if s.get("text", "").strip()]
#     if not spans:
#         return None
#     if is_bullet_span(spans[0]):
#         return None
#     if not all("Bold" in s.get("font", "") for s in spans):
#         return None
#     text = "".join(decode_span_text(s) for s in spans).strip()
#     if len(text) <= 2 or text.isdigit():
#         return None

#     # Full sentences ending with periods are paragraphs, not headings
#     if text.endswith(".") and len(text) > 40:
#         return None

#     FRUIT_HEADINGS = ("mango", "papaya", "guava", "sapota", "litchi", "banana", "grapes", "citrus")
#     clean_txt = text.lower().strip()
#     if clean_txt in FRUIT_HEADINGS or (len(clean_txt) < 15 and any(clean_txt == f or clean_txt.startswith(f + " ") for f in FRUIT_HEADINGS)):
#         return "h2"

#     max_size = max(s.get("size", 12) for s in spans)
#     ratio = max_size / body_size if body_size else 1
#     if ratio >= 1.18:
#         return "h2"
#     if ratio >= 0.95 and len(text) <= 100:
#         return "h3"
#     return None


# def is_inside_table(bbox, tables) -> bool:
#     """Return True when a text block materially overlaps a validated table.

#     Center-point checks are too fragile when a PDF text block spans across a
#     table border. Use overlap as the primary signal, with the center check as
#     a fallback for small blocks.
#     """
#     block_rect = fitz.Rect(bbox)
#     block_area = max(block_rect.width * block_rect.height, 1.0)
#     center = fitz.Point((block_rect.x0 + block_rect.x1) / 2,
#                         (block_rect.y0 + block_rect.y1) / 2)

#     for t in tables:
#         table_rect = fitz.Rect(t.bbox)
#         if table_rect.contains(center):
#             return True
#         inter = block_rect & table_rect
#         if not inter.is_empty:
#             overlap = (inter.width * inter.height) / block_area
#             if overlap >= 0.35:
#                 return True
#     return False


# def image_overlaps_table(bbox, tables, threshold=0.50) -> bool:
#     """
#     Return True when the overlap between an image bbox and any validated table
#     bbox is greater than or equal to the specified threshold (default 50%).
#     """
#     img_rect = fitz.Rect(bbox)
#     img_area = img_rect.width * img_rect.height
#     if img_area <= 0:
#         return False

#     for t in tables:
#         tbl_rect = fitz.Rect(t.bbox)
#         intersection = img_rect & tbl_rect
#         if not intersection.is_empty:
#             intersection_area = intersection.width * intersection.height
#             if (intersection_area / img_area) >= threshold:
#                 return True
#     return False


# def is_watermark_text(text: str) -> bool:
#     """Check if a text string is a watermark (e.g. www.ixambee.com)."""
#     if not text:
#         return False
#     norm = text.strip().lower().replace(" ", "")
#     if "www.ixambee.com" in norm or "ixambee.com" in norm or "www.ixambee" in norm or "ixambee" in norm:
#         return True
#     if "prepare50%faster" in norm or "prepare 50% faster" in norm:
#         return True
#     return False


# def is_watermark_image(block: dict, page: fitz.Page) -> bool:
#     """Do not classify images as watermarks from size/position alone.

#     Large centered images can be real tables, diagrams, charts, or scanned
#     content. Repeated shared XRefs are filtered separately.
#     """
#     return False


# def drawing_overlaps_table(drawing_rect: fitz.Rect, tables: list, threshold: float = 0.35) -> bool:
#     """True when a vector drawing is part of a validated table."""
#     d_area = max(drawing_rect.width * drawing_rect.height, 1.0)
#     center = fitz.Point((drawing_rect.x0 + drawing_rect.x1) / 2.0,
#                         (drawing_rect.y0 + drawing_rect.y1) / 2.0)
#     for table in tables:
#         tr = fitz.Rect(table.bbox)
#         if tr.contains(center):
#             return True
#         inter = drawing_rect & tr
#         if not inter.is_empty and (inter.width * inter.height) / d_area >= threshold:
#             return True
#     return False


# def is_valid_vector_diagram(cluster: fitz.Rect, page: fitz.Page, text_dict: dict, valid_tables: list) -> bool:
#     """
#     Determine whether a candidate drawing cluster is a genuine vector diagram/flowchart.
#     Rejects watermark clusters, light-gray background stamps, and website URL watermarks.
#     """
#     # A validated table owns its vector borders/cell fills. Never let those
#     # drawings become a diagram candidate.
#     for table in valid_tables:
#         tr = fitz.Rect(table.bbox)
#         inter = cluster & tr
#         if not inter.is_empty:
#             cluster_area = max(cluster.width * cluster.height, 1.0)
#             inter_area = max(inter.width * inter.height, 0.0)
#             center = fitz.Point((cluster.x0 + cluster.x1) / 2.0,
#                                 (cluster.y0 + cluster.y1) / 2.0)
#             if inter_area / cluster_area >= 0.20 or tr.contains(center):
#                 print(f"  [DIAGRAM REJECT] bbox={tuple(cluster)} reason=overlaps_validated_table", file=sys.stderr)
#                 return False

#     # 1. Dimension check
#     if cluster.width < 40 or cluster.height < 25:
#         print(f"  [DIAGRAM REJECT] bbox={tuple(cluster)} reason=too_small", file=sys.stderr)
#         return False

#     page_h = page.rect.height
#     if cluster.height > 580 or cluster.height > page_h * 0.85:
#         print(f"  [DIAGRAM REJECT] bbox={tuple(cluster)} reason=too_large_spans_page", file=sys.stderr)
#         return False

#     cluster_area = cluster.width * cluster.height

#     # 2. Inspect text content inside cluster to reject pure watermark text regions
#     cluster_text_lines = []
#     for tb in text_dict.get("blocks", []):
#         if tb.get("type", 0) == 0:
#             tb_rect = fitz.Rect(tb.get("bbox", (0, 0, 0, 0)))
#             intersect = cluster & tb_rect
#             if not intersect.is_empty and (intersect.width * intersect.height) / max(1.0, tb_rect.width * tb_rect.height) > 0.3:
#                 for line in tb.get("lines", []):
#                     line_txt = "".join(s.get("text", "") for s in line.get("spans", [])).strip()
#                     if line_txt:
#                         cluster_text_lines.append(line_txt)

#     if cluster_text_lines:
#         if any(is_watermark_text(txt) for txt in cluster_text_lines):
#             print(f"  [DIAGRAM REJECT] bbox={tuple(cluster)} reason=watermark_text", file=sys.stderr)
#             return False

#         callout_kws = ("special techniques", "important practice", "important terms")
#         for line_t in cluster_text_lines:
#             low_t = line_t.strip().lower()
#             if any(kw in low_t for kw in callout_kws) and len(cluster_text_lines) > 1:
#                 print(f"  [DIAGRAM REJECT] bbox={tuple(cluster)} title='{line_t}' reason=text_callout_box", file=sys.stderr)
#                 return False

#     # 3. Inspect vector drawings inside the cluster
#     all_drawings = page.get_drawings()
#     meaningful_drawings = 0

#     for d in all_drawings:
#         r = fitz.Rect(d["rect"])
#         if cluster.x0 - 5 <= r.x0 and r.x1 <= cluster.x1 + 5 and cluster.y0 - 5 <= r.y0 and r.y1 <= cluster.y1 + 5:
#             fill = d.get("fill")
#             # Skip light gray watermark fills
#             if fill and len(fill) == 3:
#                 r_val, g_val, b_val = fill
#                 if abs(r_val - g_val) < 0.02 and abs(g_val - b_val) < 0.02 and 0.7 <= r_val <= 0.9:
#                     continue
#             meaningful_drawings += 1

#     if meaningful_drawings < 1:
#         print(f"  [DIAGRAM REJECT] bbox={tuple(cluster)} reason=no_meaningful_drawings", file=sys.stderr)
#         return False

#     print(f"  [DIAGRAM ACCEPT] bbox={tuple(cluster)} drawings={meaningful_drawings}", file=sys.stderr)
#     return True





# def _table_cell_text(cell) -> str:
#     text = str(cell or "").strip()
#     # Table extraction does not retain span/font metadata, so decode common
#     # Adobe Symbol/Wingdings private-use characters directly when present.
#     return "".join(
#         SYMBOL_FONT_MAP.get(ord(ch) - 0xF000, ch)
#         if 0xF000 <= ord(ch) <= 0xF0FF else ch
#         for ch in text
#     ).strip()


# def _table_quality_score(table, page) -> float:
#     """
#     Score a PyMuPDF table candidate.

#     This is intentionally conservative. A PDF table detector is allowed to
#     miss an unusual table; it must NOT be allowed to swallow a whole page of
#     normal text and turn it into a giant table.

#     Strong signals:
#       - at least two real rows/columns
#       - multiple non-empty cells
#       - reasonable cell occupancy
#       - no single cell containing almost all of the extracted text
#       - header geometry agrees with the detected column count
#     """
#     try:
#         data = table.extract()
#     except Exception:
#         return -1.0

#     if not data:
#         return -1.0

#     row_count = len(data)
#     col_count = max((len(row) for row in data), default=0)

#     if row_count < 2 or col_count < 2:
#         return -1.0

#     # Normalise rows to the detected column count.
#     rows = [
#         list(row) + [None] * (col_count - len(row))
#         for row in data
#     ]

#     texts = [
#         _table_cell_text(cell)
#         for row in rows
#         for cell in row
#     ]
#     non_empty = [text for text in texts if text]

#     if len(non_empty) < 3:
#         return -1.0

#     total_chars = sum(len(text) for text in non_empty)
#     max_chars = max(len(text) for text in non_empty)

#     if total_chars == 0:
#         return -1.0

#     # A real table should not put almost all text into one cell.
#     concentration = max_chars / total_chars
#     if concentration > 0.82:
#         return -1.0

#     occupancy = len(non_empty) / (row_count * col_count)

#     # Very sparse structures are commonly false positives.
#     if occupancy < 0.30:
#         return -1.0

#     # Column Content Distribution Check:
#     # A genuine multi-column table should have meaningful content distributed across columns.
#     col_cell_counts = [
#         sum(1 for row in rows if col < len(row) and _table_cell_text(row[col]))
#         for col in range(col_count)
#     ]
#     col_char_counts = [
#         sum(len(_table_cell_text(row[col])) for row in rows if col < len(row) and row[col])
#         for col in range(col_count)
#     ]
#     total_non_empty = len(non_empty)

#     if col_count >= 2 and total_non_empty > 0:
#         max_col_cells = max(col_cell_counts)
#         min_col_cells = min(col_cell_counts)
#         max_col_chars = max(col_char_counts)
#         min_col_chars = min(col_char_counts)

#         # Reject if >= 85% of non-empty cells are in 1 column while another column has <= 1 cell
#         if (max_col_cells / total_non_empty) >= 0.85 and min_col_cells <= 1 and col_count == 2:
#             print(
#                 f"  [TABLE REJECT] bbox={table.bbox} rows={row_count} cols={col_count} "
#                 f"col_cells={col_cell_counts} col_chars={col_char_counts} reason=extreme_cell_column_concentration",
#                 file=sys.stderr
#             )
#             return -1.0

#         # Reject only when the short/empty column is genuinely sparse.
#         # A perfectly valid 2-column table often has short row labels in the
#         # first column and long descriptions in the second column.
#         if total_chars > 0 and (max_col_chars / total_chars) >= 0.85 and min_col_cells <= 1 and col_count == 2:
#             print(
#                 f"  [TABLE REJECT] bbox={table.bbox} rows={row_count} cols={col_count} "
#                 f"col_cells={col_cell_counts} col_chars={col_char_counts} reason=extreme_char_column_concentration",
#                 file=sys.stderr
#             )
#             return -1.0


#     # Inspect PyMuPDF's header metadata when available. In the bad
#     # "Sectors of Economy" case, find_tables(lines) reports 10 columns but
#     # only ONE actual header cell. That is a very strong false-positive
#     # signal.
#     header = getattr(table, "header", None)
#     if header is not None:
#         header_cells = getattr(header, "cells", None) or []
#         real_header_cells = sum(cell is not None for cell in header_cells)

#         if real_header_cells == 1 and col_count >= 3:
#             # Check if there are multi-column data rows below the header (e.g. tables with banner title rows like "General Agriculture")
#             multi_col_rows = sum(
#                 1 for r in rows[1:]
#                 if sum(1 for cell in r if _table_cell_text(cell)) >= 2
#             )
#             if multi_col_rows == 0:
#                 return -1.0

#         if real_header_cells >= 2:
#             # If there is header geometry, its real cell count should not
#             # wildly disagree with the extracted column count.
#             if col_count >= 4 and real_header_cells < max(2, col_count // 2):
#                 return -1.0

#     # Reject candidates that consume almost the entire page unless their
#     # extracted structure is genuinely dense and multi-column.
#     px0, py0, px1, py1 = page.rect
#     page_area = max((px1 - px0) * (py1 - py0), 1)
#     tx0, ty0, tx1, ty1 = table.bbox
#     table_area = max((tx1 - tx0) * (ty1 - ty0), 0)
#     area_ratio = table_area / page_area

#     if area_ratio > 0.65 and col_count > 4 and occupancy < 0.35:
#         return -1.0

#     # Reasonable table score. The caller may still apply stricter checks.
#     score = 0.0
#     score += min(non_empty.__len__() / 10.0, 1.0)
#     score += min(occupancy, 1.0)
#     score += min(col_count / 4.0, 1.0)

#     print(
#         f"  [TABLE ACCEPT] bbox={table.bbox} rows={row_count} cols={col_count} "
#         f"col_cells={col_cell_counts} col_chars={col_char_counts} score={score:.2f}",
#         file=sys.stderr
#     )

#     return score



# def find_valid_tables(page):
#     """
#     Find tables conservatively.

#     First use `lines_strict`, which requires actual vector lines and avoids
#     treating text/background geometry as table borders. This is important for
#     PDFs where the normal `lines` strategy can merge a large text region with
#     a real table.

#     If strict detection finds no useful table, fall back to `lines`, but only
#     accept candidates that pass the structural validation above.

#     Footer/page-number tables are ignored separately.
#     """
#     page_height = page.rect.height

#     def collect(strategy):
#         try:
#             finder = page.find_tables(strategy=strategy)
#             candidates = getattr(finder, "tables", []) or []
#         except Exception as exc:
#             print(
#                 f"Warning: table detection failed with strategy={strategy}: {exc}",
#                 file=sys.stderr,
#             )
#             return []

#         valid = []

#         for table in candidates:
#             tx0, ty0, tx1, ty1 = table.bbox
#             table_height = ty1 - ty0

#             # Ignore footer/page-number regions and false-positive footer rules.
#             if ty1 < 90 or ty0 > page_height - 75:
#                 continue
#             if ty1 > page_height - 130 and table_height < 60:
#                 continue

#             # Split candidate tables at vertical row gaps > 22 to prevent swallowing surrounding paragraphs
#             rows = getattr(table, "rows", None) or []
#             tables_to_check = [table]
#             if len(rows) >= 2:
#                 clusters = []
#                 current_cluster = [rows[0]]
#                 for r_i in range(1, len(rows)):
#                     gap = rows[r_i].bbox[1] - rows[r_i-1].bbox[3]
#                     if gap > 22:
#                         clusters.append(current_cluster)
#                         current_cluster = [rows[r_i]]
#                     else:
#                         current_cluster.append(rows[r_i])
#                 clusters.append(current_cluster)

#                 if len(clusters) > 1:
#                     tables_to_check = []
#                     for cl in clusters:
#                         sub_clip = fitz.Rect(tx0, cl[0].bbox[1] - 2, tx1, cl[-1].bbox[3] + 2)
#                         try:
#                             sub_finder = page.find_tables(clip=sub_clip, strategy=strategy)
#                             sub_candidates = getattr(sub_finder, "tables", []) or []
#                             tables_to_check.extend(sub_candidates)
#                         except Exception:
#                             pass

#             for tbl in tables_to_check:
#                 quality = _table_quality_score(tbl, page)
#                 if quality < 0:
#                     continue
#                 valid.append(tbl)

#         return valid

#     # Prefer strict line detection.
#     strict_tables = collect("lines_strict")
#     if strict_tables:
#         return strict_tables

#     # Fallback to general line detection.
#     return collect("lines")


# def collapse_phantom_columns(table_data: list, table=None, page=None) -> list:
#     """
#     Intelligently detect and collapse phantom columns created by PyMuPDF table detection artifacts.
#     Preserves legitimate empty/partially-filled columns and re-assigns/merges displaced text spans.
#     """
#     if not table_data:
#         return table_data

#     num_rows = len(table_data)
#     num_cols = max((len(r) for r in table_data), default=0)

#     if num_cols <= 2 or num_rows == 0:
#         return table_data

#     # Pad rows to uniform num_cols
#     padded_data = [
#         list(r) + [""] * (num_cols - len(r))
#         for r in table_data
#     ]

#     # Identify banner title rows (e.g. single cell title across top of table)
#     data_rows_indices = []
#     for r_idx, row in enumerate(padded_data):
#         non_empty_cells = [c for c in row if c and str(c).strip()]
#         if len(non_empty_cells) == 1 and r_idx == 0 and len(str(non_empty_cells[0]).strip()) > 15:
#             continue
#         data_rows_indices.append(r_idx)

#     if not data_rows_indices:
#         data_rows_indices = list(range(num_rows))

#     nonempty_count = [0] * num_cols
#     total_chars = [0] * num_cols

#     for r_idx in data_rows_indices:
#         row = padded_data[r_idx]
#         for c_idx in range(num_cols):
#             val = str(row[c_idx] or "").strip()
#             if val:
#                 nonempty_count[c_idx] += 1
#                 total_chars[c_idx] += len(val)

#     max_nonempty = max(nonempty_count) if nonempty_count else 0
#     if max_nonempty < 2:
#         return table_data

#     # 1. First Pass: Identify completely empty or extremely sparse phantom columns
#     phantom_cols = set()
#     for c_idx in range(num_cols):
#         cnt = nonempty_count[c_idx]
#         t_chars = total_chars[c_idx]
#         if cnt == 0:
#             phantom_cols.add(c_idx)
#         elif cnt <= 1 and cnt <= max_nonempty * 0.15 and t_chars < 60:
#             phantom_cols.add(c_idx)

#     # 2. Second Pass: Check adjacent columns for phantom-split (near-zero row overlap)
#     # If adjacent columns c and c+1 have zero or at most 1 overlapping populated row,
#     # and at least one of them is a split fragment (nonempty <= max_nonempty * 0.45), merge them.
#     merged_pairs = []
#     for c_idx in range(num_cols - 1):
#         if c_idx in phantom_cols or (c_idx + 1) in phantom_cols:
#             continue

#         cnt1 = nonempty_count[c_idx]
#         cnt2 = nonempty_count[c_idx + 1]

#         both_populated = 0
#         for r_idx in data_rows_indices:
#             v1 = str(padded_data[r_idx][c_idx] or "").strip()
#             v2 = str(padded_data[r_idx][c_idx + 1] or "").strip()
#             if v1 and v2:
#                 both_populated += 1

#         if both_populated <= 1 and (cnt1 <= max_nonempty * 0.45 or cnt2 <= max_nonempty * 0.45):
#             phantom_cols.add(c_idx + 1)
#             merged_pairs.append((c_idx, c_idx + 1))

#     if not phantom_cols or len(phantom_cols) >= num_cols - 1:
#         return table_data

#     # Log diagnostic message (Requirement 12)
#     phantom_list = sorted(list(phantom_cols))
#     print(
#         f"  [TABLE COLUMN FIX] original_cols={num_cols} nonempty={nonempty_count} removing_phantom_cols={phantom_list} merged_pairs={merged_pairs}",
#         file=sys.stderr
#     )

#     # Valid columns to keep
#     valid_cols = [c for c in range(num_cols) if c not in phantom_cols]

#     # Re-build clean matrix, merging text from phantom/split columns
#     clean_data = []
#     for r_idx, row in enumerate(padded_data):
#         new_row = [str(row[c] or "") for c in valid_cols]

#         for p_col in phantom_cols:
#             p_text = str(row[p_col] or "").strip()
#             if p_text:
#                 nearest_v_idx = 0
#                 min_dist = 999
#                 for v_i, v_col in enumerate(valid_cols):
#                     dist = abs(v_col - p_col)
#                     if dist < min_dist:
#                         min_dist = dist
#                         nearest_v_idx = v_i

#                 existing = new_row[nearest_v_idx].strip()
#                 if p_text not in existing:
#                     if existing:
#                         new_row[nearest_v_idx] = f"{existing} {p_text}"
#                     else:
#                         new_row[nearest_v_idx] = p_text

#         clean_data.append(new_row)

#     return clean_data


# def unmerge_vertical_false_spans(table_data: list) -> list:
#     """Detect columns where PyMuPDF merged vertical cells across rows into the top cell.

#     If a column c has text in row 0 with multiple line breaks, and all subsequent rows 1..N
#     in column c are None/empty while other columns in rows 1..N have populated data,
#     distribute the split lines across rows 0..N.
#     """
#     if not table_data or len(table_data) < 2:
#         return table_data

#     num_rows = len(table_data)
#     num_cols = max((len(r) for r in table_data), default=0)

#     rows = [list(r) + [None] * (num_cols - len(r)) for r in table_data]

#     for c in range(num_cols):
#         subsequent_empty = all(
#             rows[r][c] is None or not str(rows[r][c]).strip()
#             for r in range(1, num_rows)
#         )
#         if not subsequent_empty:
#             continue

#         top_val = rows[0][c]
#         if not top_val or not isinstance(top_val, str):
#             continue

#         lines = [line.strip() for line in top_val.splitlines() if line.strip()]
#         if len(lines) >= 2 and len(lines) <= num_rows:
#             rows[0][c] = lines[0]
#             for idx, line_text in enumerate(lines[1:], start=1):
#                 if idx < num_rows:
#                     rows[idx][c] = line_text

#     return rows


# def extract_table_data_accurate(table, page=None):
#     """Extract table text using PyMuPDF's native logical table matrix.

#     IMPORTANT: Do not rebuild the table by assigning PDF text spans/words to
#     columns from their X coordinates. That approach breaks merged cells and
#     tables whose column dividers change between row groups. ``table.extract()``
#     already returns the logical cell matrix and uses ``None`` for merged cells.
#     """
#     try:
#         raw = table.extract()
#     except Exception as exc:
#         print(f"  [TABLE EXTRACT ERROR] {exc}", file=sys.stderr)
#         return []

#     if not raw:
#         return []

#     # Normalize all rows to the same logical column count. Keep None/empty
#     # cells intact; they are part of the table structure.
#     num_cols = max((len(row) for row in raw), default=0)
#     if num_cols < 2:
#         return []

#     normalized = [list(row) + [None] * (num_cols - len(row)) for row in raw]
#     return unmerge_vertical_false_spans(normalized)


# def _table_column_widths(table, num_cols):
#     """Return stable percentage widths for the table's logical columns.

#     Prefer a genuine header row with one cell per column. Otherwise use the
#     first row that exposes all logical column boundaries. Fall back to equal
#     widths only when the PDF does not expose usable geometry.
#     """
#     if num_cols <= 0:
#         return []

#     candidates = []
#     rows = getattr(table, "rows", None) or []

#     # First preference: PyMuPDF's detected header cell geometry.
#     header = getattr(table, "header", None)
#     header_cells = list(getattr(header, "cells", []) or []) if header else []
#     if len(header_cells) == num_cols and all(c is not None for c in header_cells):
#         candidates.append(header_cells)

#     # Second preference: any row with a complete set of real cells.
#     for row in rows:
#         cells = list(getattr(row, "cells", None) or [])
#         if len(cells) == num_cols and all(c is not None for c in cells):
#             candidates.append(cells)
#             break

#     if candidates:
#         cells = candidates[0]
#         widths = []
#         for cell in cells:
#             x0, _, x1, _ = cell
#             widths.append(max(0.1, float(x1 - x0)))
#         total = sum(widths)
#         if total > 0:
#             raw_pcts = [(w / total) * 100.0 for w in widths]
#             adjusted = [max(6.5, p) for p in raw_pcts]
#             adj_total = sum(adjusted)
#             return [(p / adj_total) * 100.0 for p in adjusted]

#     return [100.0 / num_cols] * num_cols


# def clean_cell_text(text: str) -> str:
#     """Clean artificial PyMuPDF line breaks inside words and table cells.

#     Fixes cases where PDF extraction breaks words like 'Parturitio\\nn' -> 'Parturition',
#     'Bellowin\\ng' -> 'Bellowing', 'Farrowin\\ng' -> 'Farrowing', 'Productio\\nn' -> 'Production',
#     'Bulloc\\nk' -> 'Bullock', 'Wether/W\\ne\\ndder' -> 'Wether/Wedder'.
#     """
#     if not text:
#         return ""

#     lines = [l.strip() for l in text.splitlines() if l.strip()]
#     if len(lines) <= 1:
#         return text.strip()

#     merged_lines = []
#     for line in lines:
#         if not merged_lines:
#             merged_lines.append(line)
#             continue

#         prev = merged_lines[-1]
#         prev_word_end = not prev.endswith(('.', '?', '!', ':', ';', ')', ']', '}'))
#         is_fragment = (
#             len(line) <= 4 or
#             not line[0].isupper() or
#             prev.endswith(('-', '/', '–', '—')) or
#             (prev and prev[-1].isalpha() and line and line[0].isalpha() and prev[-1].islower() and line[0].islower())
#         )

#         if prev_word_end and is_fragment:
#             if prev.endswith('-'):
#                 merged_lines[-1] = prev[:-1] + line
#             elif prev.endswith('/'):
#                 merged_lines[-1] = prev + line
#             elif prev[-1].isalpha() and line[0].isalpha() and (len(line) <= 4 or prev[-1].islower()):
#                 merged_lines[-1] = prev + line
#             else:
#                 merged_lines[-1] = prev + " " + line
#         else:
#             merged_lines.append(line)

#     return "\n".join(merged_lines)


# def _render_table_cell(text) -> str:
#     text = _table_cell_text(text)
#     if not text:
#         return ""

#     text = clean_cell_text(text)

#     parts = [part.strip() for part in text.splitlines() if part.strip()]
#     if len(parts) > 1:
#         return "".join(
#             f'<div class="table-cell-line">{html.escape(part)}</div>'
#             for part in parts
#         )
#     return html.escape(text)


# def render_table(table, page=None, matrix=None, widths=None) -> str:
#     """Render a validated PDF table without changing its logical cell layout.

#     The old geometry reconstruction was the source of the broken tables: it
#     created a global X-grid from every row and then rendered cells sequentially,
#     ignoring each cell's actual start column. That is unsafe for merged cells
#     and row groups with different dividers.

#     ``matrix`` / ``widths`` let a caller pass in an already-computed (and
#     possibly cross-page-merged, see ``merge_split_pages``) logical matrix and
#     column widths instead of re-extracting them from ``table``. When they are
#     not supplied, the function falls back to extracting them from ``table``
#     directly, exactly as before.
#     """
#     table_data = matrix if matrix is not None else extract_table_data_accurate(table, page)

#     if not table_data:
#         return ""

#     num_cols = max((len(row) for row in table_data), default=0)
#     if num_cols < 2:
#         return ""

#     rows = [list(row) + [None] * (num_cols - len(row)) for row in table_data]

#     def nonempty(row):
#         return [c for c in row if _table_cell_text(c)]

#     # A one-cell full-width first row is a title/banner, not a column header.
#     table_x0, _, table_x1, _ = table.bbox
#     first_is_banner = False
#     if rows and len(nonempty(rows[0])) == 1:
#         first_cell = next((c for c in rows[0] if _table_cell_text(c)), None)
#         header = getattr(table, "header", None)
#         header_cells = list(getattr(header, "cells", []) or []) if header else []
#         if first_cell is not None and header_cells:
#             real = [c for c in header_cells if c is not None]
#             if len(real) == 1:
#                 x0, _, x1, _ = real[0]
#                 first_is_banner = x0 <= table_x0 + 2 and x1 >= table_x1 - 2

#     # Normally the first row is the visual table header. If it is a banner,
#     # use the next row as the header when it contains multiple cells.
#     header_index = 1 if first_is_banner and len(rows) > 1 and len(nonempty(rows[1])) >= 2 else 0

#     # Column widths: prefer explicitly-provided widths (e.g. from a merged,
#     # cross-page table, or already computed once at extraction time). Only
#     # re-derive from the raw table geometry when they're missing or no
#     # longer match the (possibly merged) column count.
#     if widths and len(widths) == num_cols:
#         col_widths = widths
#     else:
#         col_widths = _table_column_widths(table, num_cols)
#         if len(col_widths) != num_cols:
#             col_widths = [100.0 / num_cols] * num_cols

#     min_table_width_style = ""
#     if num_cols >= 6:
#         min_table_width_style = f' style="min-width: {max(950, num_cols * 105)}px;"'
#     elif num_cols >= 4:
#         min_table_width_style = ' style="min-width: 650px;"'

#     extra_cls = " table-dense" if num_cols >= 7 else ""

#     html_lines = [
#         '<div class="table-responsive">',
#         f'<table class="notes-table{extra_cls}"{min_table_width_style}>',
#         '<colgroup>',
#     ]
#     for width in col_widths:
#         html_lines.append(f'<col style="width:{width:.3f}%">')
#     html_lines.extend(['</colgroup>'])

#     if first_is_banner:
#         banner = rows[0]
#         banner_text = next((c for c in banner if _table_cell_text(c)), "")
#         html_lines.extend([
#             '<tbody>',
#             '<tr class="table-section-row">',
#             f'<th colspan="{num_cols}" class="table-section-heading">{_render_table_cell(banner_text)}</th>',
#             '</tr>',
#         ])
#     else:
#         html_lines.extend(['<thead>', '<tr>'])
#         for cell in rows[0]:
#             html_lines.append(f'<th>{_render_table_cell(cell)}</th>')
#         html_lines.extend(['</tr>', '</thead>', '<tbody>'])

#     start_body = header_index + 1 if header_index == 1 else 1
#     if first_is_banner and header_index == 1:
#         # Render the actual column header row as the orange header.
#         html_lines.append('<tr>')
#         for cell in rows[1]:
#             html_lines.append(f'<th>{_render_table_cell(cell)}</th>')
#         html_lines.append('</tr>')

#     for row in rows[start_body:]:
#         non_empty = [(idx, c) for idx, c in enumerate(row) if _table_cell_text(c)]
#         if not non_empty:
#             continue
#         if len(non_empty) == 1 and num_cols >= 2:
#             c_idx, cell_obj = non_empty[0]
#             cell_text = _table_cell_text(cell_obj)
#             is_banner_title = (
#                 c_idx == 0 and
#                 len(cell_text) <= 120 and
#                 not re.match(r'^(\(?([0-9]+|[a-zA-Z]{1,3}|[IVXivx]{1,4})\)[\.\)]?|([0-9]+|[a-zA-Z]{1,3}|[IVXivx]{1,4})[\.\)]|[-–—•·◆▪])\s*', cell_text)
#             )
#             if is_banner_title:
#                 html_lines.append('<tr class="table-section-row">')
#                 html_lines.append(f'<th colspan="{num_cols}" class="table-section-heading">{_render_table_cell(cell_obj)}</th>')
#                 html_lines.append('</tr>')
#                 continue
#         html_lines.append('<tr>')
#         for cell in row:
#             html_lines.append(f'<td>{_render_table_cell(cell)}</td>')
#         html_lines.append('</tr>')

#     html_lines.extend(['</tbody>', '</table>', '</div>'])
#     return "\n".join(html_lines)

# def is_color_block(block: dict, target_color: int) -> bool:
#     for line in block.get("lines", []):
#         for span in line.get("spans", []):
#             if span.get("text", "").strip():
#                 if span.get("color", 0) == target_color:
#                     return True
#     return False

# def is_math_expression_line(text: str) -> bool:
#     """Return True if a text line looks like a math fraction numerator/denominator component."""
#     if not text:
#         return False
#     if len(text) > 85:
#         return False
#     if text.endswith((".", "?", "!", ":")):
#         return False
#     math_words = (
#         "ebit", "sales", "cost", "costs", "contribution", "dol", "dcl", "fl", "ol",
#         "change", "profit", "tax", "eat", "pbt", "earning", "earnings", "fixed",
#         "variable", "interest", "leverage", "equity", "debt", "margin", "ratio"
#     )
#     low = text.lower()
#     if any(w in low for w in math_words):
#         return True
#     if any(c in text for c in ("+", "-", "–", "—", "/", "*", "%", "=", "(", ")", "×", "÷")):
#         return True
#     if re.search(r'\d+', text):
#         return True
#     return False

# def detect_and_merge_math_fractions(visible_lines, page=None):
#     if len(visible_lines) < 2:
#         return visible_lines

#     merged_lines = []
#     i = 0
#     while i < len(visible_lines):
#         line1 = visible_lines[i]
#         if i + 1 >= len(visible_lines):
#             merged_lines.append(line1)
#             break

#         line2 = visible_lines[i + 1]

#         spans1 = [s for s in line1.get("spans", []) if s.get("text", "").strip()]
#         spans2 = [s for s in line2.get("spans", []) if s.get("text", "").strip()]

#         if not spans1 or not spans2:
#             merged_lines.append(line1)
#             i += 1
#             continue

#         if is_bullet_span(spans1[0]) or is_bullet_span(spans2[0]):
#             merged_lines.append(line1)
#             i += 1
#             continue

#         text1 = "".join(decode_span_text(s) for s in spans1).strip()
#         text2 = "".join(decode_span_text(s) for s in spans2).strip()

#         if is_math_expression_line(text1) and is_math_expression_line(text2):
#             bbox1 = line1.get("bbox", [0, 0, 0, 0])
#             bbox2 = line2.get("bbox", [0, 0, 0, 0])

#             cx1 = (bbox1[0] + bbox1[2]) / 2.0
#             cx2 = (bbox2[0] + bbox2[2]) / 2.0
#             gap = bbox2[1] - bbox1[3]

#             if abs(cx1 - cx2) < 65 and -3 <= gap <= 22:
#                 rendered1 = "".join(render_span_semantic(s) for s in spans1)
#                 rendered2 = "".join(render_span_semantic(s) for s in spans2)

#                 den_text = rendered2
#                 clean_den = text2.strip()
#                 if (" " in clean_den or "-" in clean_den or "–" in clean_den or "+" in clean_den) and not (clean_den.startswith("(") and clean_den.endswith(")")):
#                     den_text = f"({rendered2})"

#                 fraction_span = {
#                     "text": f"{text1} / {text2}",
#                     "font": spans1[0].get("font", ""),
#                     "size": spans1[0].get("size", 12),
#                     "color": spans1[0].get("color", 0),
#                     "custom_html": f"{rendered1} / {den_text}"
#                 }

#                 combined_line = line1.copy()
#                 combined_line["spans"] = [fraction_span]
#                 combined_line["bbox"] = [
#                     min(bbox1[0], bbox2[0]),
#                     bbox1[1],
#                     max(bbox1[2], bbox2[2]),
#                     bbox2[3]
#                 ]
#                 merged_lines.append(combined_line)
#                 i += 2
#                 continue

#         merged_lines.append(line1)
#         i += 1

#     return merged_lines

# def render_text_block_semantic(block: dict, body_size: float, page: fitz.Page = None) -> str:
#     # Filter out running headers based on content and small font size
#     text_spans = []
#     for l in block.get("lines", []):
#         text_spans.extend(l.get("spans", []))
    
#     is_note_block = False
#     is_figure_caption = False
#     if text_spans:
#         text_content = "".join(s.get("text", "") for s in text_spans).strip()
#         is_note_block = bool(re.match(r'^(please\s+note\s*[:-]|note\s*[:-]|नोट\s*[:-]|note\b)', text_content, re.IGNORECASE))

#         is_figure_caption = bool(re.match(r'^figure\b', text_content, re.IGNORECASE))
#         normalized_text = text_content.lower().replace(" ", "").replace("-", "")
#         if normalized_text in ["economyintroduction", "studynotes"]:
#             max_size = max(s.get("size", 12) for s in text_spans)
#             if max_size < 15:
#                 return ""

#     lines = block.get("lines", [])
#     visible_lines = []
#     for line in lines:
#         spans = [s for s in line.get("spans", []) if s.get("text", "").strip()]
#         if spans:
#             line_copy = line.copy()
#             line_copy["spans"] = spans
#             visible_lines.append(line_copy)
            
#     if not visible_lines:
#         return ""
        
#     if is_figure_caption:
#         para_spans = []
#         for line in visible_lines:
#             spans = line["spans"]
#             if para_spans and not para_spans[-1].get("text", "").endswith(" ") and not spans[0].get("text", "").startswith(" "):
#                 para_spans.append({"text": " ", "font": spans[0].get("font", ""), "size": spans[0].get("size", 12), "color": spans[0].get("color", 0)})
#             para_spans.extend(spans)
#         inner = "".join(render_span_semantic(s) for s in para_spans)
#         inner = inner.replace("<strong>", "").replace("</strong>", "").replace("<em>", "").replace("</em>", "")
#         return f"<figcaption>{inner}</figcaption>"
        
#     # Check if this block is an info card (disabled to preserve semantic paragraphs/lists)
#     if False and is_color_block(block, 0xe36c0a):
#         para_spans = []
#         for line in visible_lines:
#             spans = line["spans"]
#             if para_spans and not para_spans[-1].get("text", "").endswith(" ") and not spans[0].get("text", "").startswith(" "):
#                 para_spans.append({"text": " ", "font": spans[0].get("font", ""), "size": spans[0].get("size", 12), "color": spans[0].get("color", 0)})
#             para_spans.extend(spans)
#         inner = "".join(render_span_semantic(s) for s in para_spans)
#         return f'<div class="info-card"><p>{inner}</p></div>'

        
#     # Consolidate lines where a bullet character is split from its text on the same visual row
#     merged_lines = []
#     i = 0
#     while i < len(visible_lines):
#         line = visible_lines[i]
#         spans = line["spans"]
        
#         if i + 1 < len(visible_lines) and len(spans) == 1 and is_bullet_span(spans[0]):
#             next_line = visible_lines[i + 1]
#             y_diff = abs(next_line["bbox"][1] - line["bbox"][1])
#             x_diff = next_line["bbox"][0] - line["bbox"][2]
            
#             if y_diff < 10 and x_diff >= 0:
#                 merged_line = line.copy()
#                 merged_line["spans"] = spans + next_line["spans"]
#                 merged_line["bbox"] = [
#                     min(line["bbox"][0], next_line["bbox"][0]),
#                     min(line["bbox"][1], next_line["bbox"][1]),
#                     max(line["bbox"][2], next_line["bbox"][2]),
#                     max(line["bbox"][3], next_line["bbox"][3])
#                 ]
#                 merged_lines.append(merged_line)
#                 i += 2
#                 continue
                
#         merged_lines.append(line)
#         i += 1
        
#     visible_lines = detect_and_merge_math_fractions(merged_lines, page)
        
#     # Check for pink heading
#     is_pink = False
#     bbox = block.get("bbox", (0, 0, 0, 0))
#     if page:
#         is_pink = is_pink_heading_block(bbox, page)
        
#     heading_tag = classify_heading(visible_lines, body_size)
#     if is_pink:
#         heading_tag = "h2"
        
#     res = ""
#     if heading_tag:
#         line = visible_lines[0]
#         spans = line["spans"]
#         inner = "".join(render_span_semantic(s) for s in spans)
#         if is_pink:
#             heading_tag = "h2"
#             # Strip both strong and em from h2
#             inner = inner.replace("<em>", "").replace("</em>", "").replace("<strong>", "").replace("</strong>", "")
#         else:
#             heading_tag = "h3"
#             # Strip both strong and em from h3
#             inner = inner.replace("<em>", "").replace("</em>", "").replace("<strong>", "").replace("</strong>", "")
#         res = f"<{heading_tag}>{inner}</{heading_tag}>"
#     else:
#         html_out = []
#         active_lists = []  # Stack of bullet x-coordinates
#         current_para_spans = []
        
#         for line in visible_lines:
#             spans = line["spans"]
#             if is_bullet_span(spans[0]):
#                 # Flush existing paragraph content
#                 if current_para_spans:
#                     para_text = "".join(render_span_semantic(s) for s in current_para_spans)
#                     html_out.append(f"<p>{para_text}</p>")
#                     current_para_spans = []
#                 x_bullet = spans[0]["bbox"][0]
#                 first_span_text = decode_span_text(spans[0]).strip()

#                 # Check for bullet symbol or alphanumeric/Roman prefix inside the first span
#                 m_bullet = re.match(r'^([-–—•·◆▪▸►‣✓✔ü\u2713\u2714\uf0fc\u25ef\u25cb\u25cf]|o\b)\s*(.*)', first_span_text, re.IGNORECASE)
#                 m_alpha = re.match(r'^(\(?([0-9]+|[a-zA-Z]{1,3}|[IVXivx]{1,4})\)[\.\)]?|([0-9]+|[a-zA-Z]{1,3}|[IVXivx]{1,4})[\.\)])\s*(.*)', first_span_text)

#                 is_alphanumeric = bool(m_alpha or is_alphanumeric_prefix(first_span_text))
#                 cls_extra = " list-alphanumeric" if is_alphanumeric else ""

#                 if not active_lists:
#                     is_checkmark = first_span_text.startswith(("✓", "✔", "ü", "\u2713", "\u2714", "\uf0fc"))
#                     style_attr = ' style="list-style-type: none; list-style: none;"' if is_alphanumeric else ''
#                     if is_checkmark:
#                         html_out.append(f'<ul class="notes-sub{cls_extra}"{style_attr}>')
#                         active_lists.append(x_bullet - 20)  # Dummy parent level
#                         active_lists.append(x_bullet)
#                     else:
#                         html_out.append(f'<ul class="notes-list{cls_extra}"{style_attr}>')
#                         active_lists.append(x_bullet)
#                 else:
#                     if x_bullet > active_lists[-1] + 5:
#                         level = len(active_lists)
#                         cls_name = "notes-sub" if level == 1 else "notes-subsub"
#                         style_attr = ' style="list-style-type: none; list-style: none;"' if is_alphanumeric else ''
#                         html_out.append(f'<ul class="{cls_name}{cls_extra}"{style_attr}>')
#                         active_lists.append(x_bullet)
#                     elif x_bullet < active_lists[-1] - 5:
#                         while active_lists and x_bullet < active_lists[-1] - 5:
#                             html_out.append("</li></ul>")
#                             active_lists.pop()
#                         if not active_lists:
#                             style_attr = ' style="list-style-type: none; list-style: none;"' if is_alphanumeric else ''
#                             html_out.append(f'<ul class="notes-list{cls_extra}"{style_attr}>')
#                             active_lists.append(x_bullet)
#                         else:
#                             html_out.append("</li>")
#                     else:
#                         html_out.append("</li>")

#                 if m_alpha:
#                     prefix_str = m_alpha.group(1)
#                     rest_str = m_alpha.group(4)
#                     prefix_span = spans[0].copy()
#                     prefix_span["text"] = prefix_str
#                     rest_span = spans[0].copy()
#                     rest_span["text"] = rest_str
#                     inner = render_span_semantic(prefix_span) + " " + render_span_semantic(rest_span)
#                     if len(spans) > 1:
#                         inner += " " + "".join(render_span_semantic(s) for s in spans[1:])
#                 elif m_bullet:
#                     rest_str = m_bullet.group(2)
#                     rest_span = spans[0].copy()
#                     rest_span["text"] = rest_str
#                     inner = render_span_semantic(rest_span)
#                     if len(spans) > 1:
#                         inner += " " + "".join(render_span_semantic(s) for s in spans[1:])
#                 else:
#                     inner = "".join(render_span_semantic(s) for s in spans)

#                 html_out.append(f"<li>{inner}")

#             else:
#                 line_text = "".join(decode_span_text(s) for s in spans).strip()
#                 is_all_bold = all("Bold" in s.get("font", "") for s in spans)
#                 if active_lists and is_all_bold and len(line_text) < 80 and not line_text.endswith("."):
#                     while active_lists:
#                         html_out.append("</li></ul>")
#                         active_lists.pop()
#                     html_out.append(f"<h3>{html.escape(line_text)}</h3>")
#                 elif active_lists:
#                     inner = "".join(render_span_semantic(s) for s in spans)
#                     if html_out:
#                         last_item = html_out[-1]
#                         if not last_item.endswith(" ") and not inner.startswith(" "):
#                             html_out[-1] = last_item + " " + inner
#                         else:
#                             html_out[-1] = last_item + inner
#                 else:
#                     line_text = "".join(decode_span_text(s) for s in spans).strip()
#                     # If this line starts an MCQ option (e.g. A., B.), Explanation, Question number, or Dash bullet, start a new paragraph
#                     if current_para_spans and is_standalone_line_prefix(line_text):
#                         para_text = "".join(render_span_semantic(s) for s in current_para_spans)
#                         para_text = format_paragraph_dashes_and_spaces(para_text)
#                         html_out.append(f"<p>{para_text}</p>")
#                         current_para_spans = []

#                     # Append to running paragraph list, keeping word spacing clean
#                     if current_para_spans and not current_para_spans[-1].get("text", "").endswith(" ") and not spans[0].get("text", "").startswith(" "):
#                         current_para_spans.append({"text": " ", "font": spans[0].get("font", ""), "size": spans[0].get("size", 12), "color": spans[0].get("color", 0)})
#                     current_para_spans.extend(spans)

                
#         # Flush remaining paragraph or list wraps
#         if current_para_spans:
#             para_text = "".join(render_span_semantic(s) for s in current_para_spans)
#             para_text = format_paragraph_dashes_and_spaces(para_text)
#             html_out.append(f"<p>{para_text}</p>")

        
#         while active_lists:
#             html_out.append("</li></ul>")
#             active_lists.pop()
            
#         res = "\n".join(html_out)

#     if is_note_block:
#         pattern = re.compile(
#             r'^((?:<[a-z0-9]+>)*(?:<strong>|<em>)*)(please\s+note\s*[:-]|note\s*[:-]|नोट\s*[:-]|note\b)((?:</strong>|</em>)*)(\s*)',
#             re.IGNORECASE
#         )

#         match = pattern.match(res)
#         if match:
#             before = match.group(1)
#             prefix = match.group(2)
#             after = match.group(3)
#             spacing = match.group(4)
#             wrapped = f'<span class="note-title">{prefix}</span>'
#             res = before + wrapped + after + spacing + res[match.end():]
#         return f'<div class="content-note">\n{res}\n</div>'

#     # Wrap callout blocks in clean flat Warm Orange card boxes (for remote server compatibility)
#     lines = block.get("lines", [])
#     callout_kws = ("special techniques", "important practice", "important terms")
#     for l_item in lines:
#         l_spans = [s for s in l_item.get("spans", []) if s.get("text", "").strip()]
#         if l_spans:
#             l_txt = "".join(decode_span_text(s) for s in l_spans).strip().lower()
#             if any(kw in l_txt for kw in callout_kws):
#                 box_style = 'style="margin: 1.5rem 0; padding: 1.5rem 1.75rem; border-radius: 14px; border-left: 6px solid #e67e22; background: linear-gradient(135deg, #fffaf5 0%, #fff2e6 100%); border-top: 1px solid #fcdcc5; border-right: 1px solid #fcdcc5; border-bottom: 1px solid #fcdcc5; box-shadow: none;"'
#                 return f'<div class="callout-box" {box_style}>\n{res}\n</div>'

#     return res

# def extract_page_elements(doc: fitz.Document, page: fitz.Page, body_size: float) -> list:
#     rect = page.rect
#     page_height = rect.height
    
#     # 1. Find and VALIDATE tables before excluding any text from the page.
#     # Never use raw page.find_tables() results here.
#     valid_tables = find_valid_tables(page)
    
#     # 1.5 Detect vector diagrams/flowcharts/chemical structures conservatively
#     page_w, page_h = rect.width, rect.height
#     draw_rects = []
#     for d in page.get_drawings():
#         r = d["rect"]
#         d_rect = fitz.Rect(r)

#         # Tables are frequently built from vector rectangles/lines. Exclude
#         # those drawings before clustering them as diagrams.
#         if drawing_overlaps_table(d_rect, valid_tables):
#             continue
#         # Skip rule lines (headers/footers) and page borders
#         if r.width > page_w * 0.9 and r.height < 5:
#             continue
#         if r.height > page_h * 0.9 and r.width < 5:
#             continue
#         if r.width > page_w * 0.95 and r.height > page_h * 0.95:
#             continue
#         if r.width == 0 and r.height == 0:
#             continue
#         # Skip drawings in header/footer zones
#         if r.y1 < 80 or r.y0 > page_h - 75:
#             continue
#         # Skip light gray watermark fills or drawing paths belonging to watermark text (e.g. www.ixambee.com)
#         fill = d.get("fill")
#         color = d.get("color")
#         if fill and len(fill) == 3:
#             r_val, g_val, b_val = fill
#             if abs(r_val - g_val) < 0.02 and abs(g_val - b_val) < 0.02 and 0.65 <= r_val <= 0.95:
#                 continue
#         if color and len(color) == 3:
#             r_val, g_val, b_val = color
#             if abs(r_val - g_val) < 0.02 and abs(g_val - b_val) < 0.02 and 0.65 <= r_val <= 0.95:
#                 continue

#         # Check if this drawing path belongs to a watermark text region (e.g. www.ixambee.com)
#         is_wm_path = False
#         for tb in page.get_text("dict").get("blocks", []):
#             if tb.get("type", 0) == 0:
#                 tb_rect = fitz.Rect(tb.get("bbox", (0, 0, 0, 0)))
#                 inter = d_rect & tb_rect
#                 if not inter.is_empty:
#                     for l in tb.get("lines", []):
#                         txt = "".join(s.get("text", "") for s in l.get("spans", [])).strip()
#                         if is_watermark_text(txt):
#                             is_wm_path = True
#                             break
#                 if is_wm_path:
#                     break
#         if is_wm_path:
#             continue

#         # Skip pink/purple background highlight bars behind text headings
#         if is_pink_heading_block(r, page):
#             continue

#         draw_rects.append(r)

#     # Cluster drawings
#     diagram_clusters = []
#     for r in draw_rects:
#         merged = False
#         for idx_c, c in enumerate(diagram_clusters):
#             dx = max(0, c.x0 - r.x1, r.x0 - c.x1)
#             dy = max(0, c.y0 - r.y1, r.y0 - c.y1)
#             if dx < 40 and dy < 20:
#                 diagram_clusters[idx_c] = fitz.Rect(
#                     min(r.x0, c.x0), min(r.y0, c.y0),
#                     max(r.x1, c.x1), max(r.y1, c.y1)
#                 )
#                 merged = True
#                 break
#         if not merged:
#             diagram_clusters.append(fitz.Rect(r))

#     # Re-merge clusters
#     changed = True
#     while changed:
#         changed = False
#         for i_c in range(len(diagram_clusters)):
#             for j_c in range(i_c + 1, len(diagram_clusters)):
#                 c1, c2 = diagram_clusters[i_c], diagram_clusters[j_c]
#                 dx = max(0, c2.x0 - c1.x1, c1.x0 - c2.x1)
#                 dy = max(0, c2.y0 - c1.y1, c1.y0 - c2.y1)
#                 if dx < 40 and dy < 20:
#                     diagram_clusters[i_c] = fitz.Rect(
#                         min(c1.x0, c2.x0), min(c1.y0, c2.y0),
#                         max(c1.x1, c2.x1), max(c1.y1, c2.y1)
#                     )
#                     diagram_clusters.pop(j_c)
#                     changed = True
#                     break
#             if changed:
#                 break

#     # Extract page text dictionary early for diagram validation
#     text_dict = page.get_text("dict")

#     # Validate vector diagram candidates with conservative geometry & text density rules
#     valid_diagram_rects = []
#     for c in diagram_clusters:
#         # Skip header diagrams/logos sitting in top running header zone (y1 < 80)
#         if c.y1 < 80 or c.y0 > page_height - 75:
#             continue
#         if is_valid_vector_diagram(c, page, text_dict, valid_tables):
#             # Tightly bound cluster to actual vector drawings inside c to prevent stretching over text above/below
#             dr_drawings = []
#             for d in page.get_drawings():
#                 r_d = fitz.Rect(d["rect"])
#                 if c.x0 - 5 <= r_d.x0 and r_d.x1 <= c.x1 + 5 and c.y0 - 5 <= r_d.y0 and r_d.y1 <= c.y1 + 5:
#                     if r_d.width > page_w * 0.9 and r_d.height < 5:
#                         continue
#                     dr_drawings.append(r_d)
#             if dr_drawings:
#                 tight_rect = fitz.Rect(
#                     min(r.x0 for r in dr_drawings),
#                     min(r.y0 for r in dr_drawings),
#                     max(r.x1 for r in dr_drawings),
#                     max(r.y1 for r in dr_drawings)
#                 )
#             else:
#                 tight_rect = fitz.Rect(c)

#             # Snap top and bottom boundary to internal text lines so text ABOVE and BELOW graphics is never cropped or deleted
#             contained_lines = []
#             for tb in text_dict.get("blocks", []):
#                 if tb.get("type", 0) == 0:
#                     for line in tb.get("lines", []):
#                         l_box = line.get("bbox", [0, 0, 0, 0])
#                         intersect = tight_rect & fitz.Rect(l_box)
#                         if not intersect.is_empty and (intersect.width * intersect.height) / max(1.0, (l_box[2]-l_box[0])*(l_box[3]-l_box[1])) > 0.4:
#                             line_txt = "".join(s.get("text", "") for s in line.get("spans", [])).strip()
#                             if line_txt and not is_watermark_text(line_txt):
#                                 contained_lines.append(l_box)

#             if contained_lines:
#                 text_top = min(b[1] for b in contained_lines)
#                 text_bottom = max(b[3] for b in contained_lines)
#                 tight_rect.y0 = max(tight_rect.y0, text_top - 10)
#                 tight_rect.y1 = min(tight_rect.y1, text_bottom + 12)

#             valid_diagram_rects.append(tight_rect)

#     # Validated tables are authoritative. Do not delete a table merely because
#     # a vector drawing happens to overlap it. Table drawings were already
#     # excluded from diagram clustering above.

#     # Pre-process spans to split merged list prefixes (e.g. "- text" -> "-" and " text", "a. text" -> "a." and " text")
#     import re
#     dash_prefix_pattern = re.compile(r'^([-–—•·◆▪▸►‣])\s+(.*)')
#     prefix_pattern = re.compile(r'^(\(?([0-9]+|[a-z]+|[IVX]+)\)[\.\)]?|([0-9]+|[a-z]+|[IVX]+)[\.\)])(\s+)')
#     for block in text_dict.get("blocks", []):
#         if block.get("type", 0) == 0:
#             for line in block.get("lines", []):
#                 spans = line.get("spans", [])
#                 if spans:
#                     first_span = spans[0]
#                     text_val = first_span.get("text", "")

#                     # 1. Check dash / bullet prefix e.g. "- In June 2022..."
#                     dash_match = dash_prefix_pattern.match(text_val.strip())
#                     if dash_match:
#                         prefix = dash_match.group(1)
#                         idx_p = text_val.find(prefix)
#                         rest = text_val[idx_p + len(prefix):]
#                         if rest.strip():
#                             prefix_span = first_span.copy()
#                             prefix_span["text"] = prefix
#                             first_span["text"] = rest
#                             line["spans"] = [prefix_span] + spans
#                             continue

#                     # 2. Check alphanumeric prefix
#                     match = prefix_pattern.match(text_val)
#                     if match:
#                         prefix = match.group(1)
#                         spacing = match.group(4)
#                         rest = text_val[match.end():]
#                         if rest.strip() and is_alphanumeric_prefix(prefix):
#                             prefix_span = first_span.copy()
#                             prefix_span["text"] = prefix
#                             first_span["text"] = spacing + rest
#                             line["spans"] = [prefix_span] + spans

                            
#     raw_lines = []
    
#     for block in text_dict.get("blocks", []):
#         block_type = block.get("type", 0)
#         if block_type != 0:  # Skip images here, handled below
#             continue
            
#         bbox = block.get("bbox", (0, 0, 0, 0))
#         # Skip blocks inside tables
#         if is_inside_table(bbox, valid_tables):
#             continue
            
#         for line in block.get("lines", []):
#             lx0, ly0, lx1, ly1 = line["bbox"]
#             lcx = (lx0 + lx1) / 2
#             lcy = (ly0 + ly1) / 2
            
#             # Skip lines strictly inside valid diagram images
#             line_inside_diagram = False
#             for dr in valid_diagram_rects:
#                 if dr.x0 <= lcx <= dr.x1 and dr.y0 <= lcy <= dr.y1:
#                     line_inside_diagram = True
#                     break
#             if line_inside_diagram:
#                 continue

#             # Skip header and footer zones (ly1 < 75 skips running headers)
#             if ly1 < 75 or ly0 > page_height - 75:
#                 continue
                
#             line_text = "".join(s.get("text", "") for s in line.get("spans", [])).strip()
#             if is_watermark_text(line_text):
#                 continue

#             # Skip standalone page number footers near bottom of page (e.g. 2, 3, 4, 5, 6, 7, 8, 9, 10, 11)
#             if ly0 > page_height - 90 and line_text.isdigit():
#                 continue

#             # Skip running headers at top of page (e.g. "ESI- RBI_2018")
#             if ly1 < 95:
#                 norm_line = line_text.lower().replace(" ", "").replace("-", "").replace("_", "")
#                 if norm_line in ("esirbi2018", "rbigradeb2018", "wwwixambeecom", "ixambee"):
#                     continue


#             raw_lines.append(line)
            
#     # 2. Consolidate lines that are on the same visual row (similar Y0)
#     consolidated_lines = []
#     for line in raw_lines:
#         if not consolidated_lines:
#             consolidated_lines.append(line)
#             continue
#         prev_line = consolidated_lines[-1]
#         y_diff = abs(line["bbox"][1] - prev_line["bbox"][1])
#         if y_diff < 5:
#             # Merge spans
#             prev_line["spans"] = prev_line.get("spans", []) + line.get("spans", [])
#             # Update bbox
#             prev_line["bbox"] = [
#                 min(prev_line["bbox"][0], line["bbox"][0]),
#                 min(prev_line["bbox"][1], line["bbox"][1]),
#                 max(prev_line["bbox"][2], line["bbox"][2]),
#                 max(prev_line["bbox"][3], line["bbox"][3])
#             ]
#         else:
#             consolidated_lines.append(line)
#     raw_lines = consolidated_lines

#     # Consolidate lines where a bullet character is split from its text on the same visual row
#     merged_raw_lines = []
#     i = 0
#     while i < len(raw_lines):
#         line = raw_lines[i]
#         spans = [s for s in line.get("spans", []) if s.get("text", "").strip()]
#         if i + 1 < len(raw_lines) and len(spans) == 1 and is_bullet_span(spans[0]):
#             next_line = raw_lines[i + 1]
#             next_spans = [s for s in next_line.get("spans", []) if s.get("text", "").strip()]
#             y_diff = abs(next_line["bbox"][1] - line["bbox"][1])
#             x_diff = next_line["bbox"][0] - line["bbox"][2]
#             if y_diff < 8 and x_diff >= 0:
#                 merged_line = line.copy()
#                 merged_line["spans"] = spans + next_spans
#                 merged_line["bbox"] = [
#                     min(line["bbox"][0], next_line["bbox"][0]),
#                     min(line["bbox"][1], next_line["bbox"][1]),
#                     max(line["bbox"][2], next_line["bbox"][2]),
#                     max(line["bbox"][3], next_line["bbox"][3])
#                 ]
#                 merged_raw_lines.append(merged_line)
#                 i += 2
#                 continue
#         merged_raw_lines.append(line)
#         i += 1
#     raw_lines = merged_raw_lines
    
#     # 3. Group lines semantically from scratch
#     semantic_blocks = []
#     current_lines = []
    
#     for line in raw_lines:
#         spans = [s for s in line.get("spans", []) if s.get("text", "").strip()]
#         if not spans:
#             continue
            
#         is_bullet = is_bullet_span(spans[0])
#         is_all_bold = all("Bold" in s.get("font", "") for s in spans)
#         text_content = "".join(decode_span_text(s) for s in spans).strip()
#         callout_kws = ("special techniques", "important practice", "important terms")
#         is_callout_title = any(kw in text_content.lower() for kw in callout_kws)
#         is_heading = is_all_bold and not is_bullet and len(text_content) < 80 and not text_content.endswith(".") and not is_callout_title
#         if is_heading and current_lines:
#             prev_line = current_lines[-1]
#             prev_spans = [s for s in prev_line.get("spans", []) if s.get("text", "").strip()]
#             if prev_spans:
#                 prev_text = "".join(decode_span_text(s) for s in prev_spans).strip()
#                 gap = line["bbox"][1] - prev_line["bbox"][3]
#                 if gap < 16 and prev_text and not prev_text[-1] in (".", "?", "!", ":", ";"):
#                     is_heading = False
#         is_pink = is_pink_heading_block(line["bbox"], page)
        
#         # Flush if: heading, pink block, or transitioning between bullet list and normal paragraph
#         should_flush = (is_heading or is_pink)
#         if not should_flush and current_lines:
#             has_bullet_in_block = False
#             for l in current_lines:
#                 l_spans = [s for s in l.get("spans", []) if s.get("text", "").strip()]
#                 if l_spans and is_bullet_span(l_spans[0]):
#                     has_bullet_in_block = True
#                     break
                    
#             if has_bullet_in_block:
#                 if not is_bullet:
#                     # Current block has bullets, new line is text. Check if it's a continuation.
#                     is_continuation = False
#                     prev_line = current_lines[-1]
#                     gap = line["bbox"][1] - prev_line["bbox"][3]
#                     line_x0 = line["bbox"][0]
#                     # Find the last bullet line in current_lines to get text offset
#                     last_bullet_x0 = current_lines[0]["bbox"][0]
#                     for l in reversed(current_lines):
#                         l_spans = [s for s in l.get("spans", []) if s.get("text", "").strip()]
#                         if l_spans and is_bullet_span(l_spans[0]):
#                             last_bullet_x0 = l["bbox"][0]
#                             break
#                     if 0 <= gap < 16 and (line_x0 > last_bullet_x0 + 8 or gap < 10):
#                         is_continuation = True
#                     if not is_continuation:
#                         should_flush = True
#             else:
#                 # Current block is normal text. Flush if it contains a heading.
#                 is_current_heading = False
#                 if len(current_lines) == 1:
#                     prev_line = current_lines[0]
#                     prev_spans = [s for s in prev_line.get("spans", []) if s.get("text", "").strip()]
#                     if prev_spans:
#                         prev_bold = all("Bold" in s.get("font", "") for s in prev_spans)
#                         prev_text = "".join(decode_span_text(s) for s in prev_spans).strip()
#                         if prev_bold and len(prev_text) < 80 and not prev_text.endswith("."):
#                             is_current_heading = True
#                 if is_current_heading:
#                     should_flush = True
#                 elif is_bullet:
#                     should_flush = True
                    
#         if should_flush:
#             if current_lines:
#                 semantic_blocks.append({
#                     "type": "text",
#                     "bbox": (
#                         min(l["bbox"][0] for l in current_lines),
#                         min(l["bbox"][1] for l in current_lines),
#                         max(l["bbox"][2] for l in current_lines),
#                         max(l["bbox"][3] for l in current_lines)
#                     ),
#                     "lines": current_lines
#                 })
#                 current_lines = []
#         else:
#             # If the current line is a normal text line, check if it's a continuation
#             if current_lines:
#                 prev_line = current_lines[-1]
#                 gap = line["bbox"][1] - prev_line["bbox"][3]
#                 line_text = "".join(decode_span_text(s) for s in line.get("spans", [])).strip()
#                 is_mcq_or_prefix = is_standalone_line_prefix(line_text)
                
#                 prev_spans = [s for s in prev_line.get("spans", []) if s.get("text", "").strip()]
#                 prev_text = "".join(decode_span_text(s) for s in prev_spans).strip() if prev_spans else ""
                
#                 sentence_completed = bool(prev_text and prev_text[-1] in (".", "?", "!", ":"))
                
#                 limit = 6.5
#                 if is_bullet or is_mcq_or_prefix:
#                     limit = 5.0
#                 elif sentence_completed and gap >= 4.5:
#                     limit = 4.5

#                 if gap >= limit or gap < -5:
#                     semantic_blocks.append({
#                         "type": "text",
#                         "bbox": (
#                             min(l["bbox"][0] for l in current_lines),
#                             min(l["bbox"][1] for l in current_lines),
#                             max(l["bbox"][2] for l in current_lines),
#                             max(l["bbox"][3] for l in current_lines)
#                         ),
#                         "lines": current_lines
#                     })
#                     current_lines = []
                    
#         current_lines.append(line)
        
#     if current_lines:
#         semantic_blocks.append({
#             "type": "text",
#             "bbox": (
#                 min(l["bbox"][0] for l in current_lines),
#                 min(l["bbox"][1] for l in current_lines),
#                 max(l["bbox"][2] for l in current_lines),
#                 max(l["bbox"][3] for l in current_lines)
#             ),
#             "lines": current_lines
#         })
        
#     # 4. Extract other block types (tables and images)
#     page_elements = []
    
#     # Add text blocks
#     for sb in semantic_blocks:
#         is_heading = False
#         lines = sb.get("lines", [])
#         if len(lines) == 1:
#             spans = [s for s in lines[0].get("spans", []) if s.get("text", "").strip()]
#             if spans:
#                 is_all_bold = all("Bold" in s.get("font", "") for s in spans)
#                 text_content = "".join(decode_span_text(s) for s in spans).strip()
#                 is_heading = is_all_bold and len(text_content) < 80 and not text_content.endswith(".")
#         page_elements.append({
#             "type": "text",
#             "bbox": sb["bbox"],
#             "data": sb,
#             "is_heading": is_heading
#         })
        
#     # Add displayed raster images from image objects.
#     # get_text("dict") does not reliably expose every displayed image;
#     # get_image_info() does. Repeated XRefs are shared template/background
#     # assets and are intentionally ignored.
#     repeated_image_xrefs = getattr(doc, "_pdf_html_repeated_image_xrefs", set())
#     seen_image_keys = set()
#     try:
#         image_infos = page.get_image_info(xrefs=True)
#     except Exception:
#         image_infos = []

#     for info in image_infos:
#         bbox = tuple(info.get("bbox", (0, 0, 0, 0)))
#         xref = info.get("xref")
#         if xref and xref in repeated_image_xrefs:
#             continue
#         if bbox[2] <= bbox[0] or bbox[3] <= bbox[1]:
#             continue
#         if (bbox[2] - bbox[0]) < 8 or (bbox[3] - bbox[1]) < 8:
#             continue
#         if bbox[3] < 80 or bbox[1] > page_height - 75:
#             continue
#         if image_overlaps_table(bbox, valid_tables, threshold=0.85):
#             continue

#         key = (xref, tuple(round(v, 2) for v in bbox))
#         if key in seen_image_keys:
#             continue
#         seen_image_keys.add(key)

#         page_elements.append({
#             "type": "image",
#             "bbox": bbox,
#             "data": info
#         })

#     # Add only validated table blocks. Keep the Table object so render_table()
#     # can use PyMuPDF's detected header geometry/names. Also cache the
#     # extracted logical matrix and column widths now, while the page object
#     # is still available -- this lets a table that gets cut off by a page
#     # break be merged with its continuation on the next page later on
#     # (see merge_split_pages), instead of the continuation being rendered
#     # as its own bogus mini-table with a data row misread as a header.
#     for t in valid_tables:
#         try:
#             t_matrix = extract_table_data_accurate(t, page)
#         except Exception:
#             t_matrix = []
#         t_num_cols = max((len(row) for row in t_matrix), default=0)
#         try:
#             t_widths = _table_column_widths(t, t_num_cols) if t_num_cols else []
#         except Exception:
#             t_widths = []
#         page_elements.append({
#             "type": "table",
#             "bbox": t.bbox,
#             "data": t,
#             "matrix": t_matrix,
#             "widths": t_widths,
#         })
        
#     # Add detected vector diagrams/flowcharts to render in-place
#     for dr in valid_diagram_rects:
#         page_elements.append({
#             "type": "diagram",
#             "bbox": (dr.x0, dr.y0, dr.x1, dr.y1),
#             "data": dr
#         })

#     # Deduplicate images: skip smaller sub-images contained inside a diagram or larger graphic
#     diagram_bboxes = [e["bbox"] for e in page_elements if e["type"] == "diagram"]
#     filtered_elements = []
#     for el in page_elements:
#         if el["type"] == "image":
#             ibox = el["bbox"]
#             is_sub = False
#             for dbox in diagram_bboxes:
#                 inter_x0 = max(ibox[0], dbox[0])
#                 inter_y0 = max(ibox[1], dbox[1])
#                 inter_x1 = min(ibox[2], dbox[2])
#                 inter_y1 = min(ibox[3], dbox[3])
#                 if inter_x1 > inter_x0 and inter_y1 > inter_y0:
#                     inter_area = (inter_x1 - inter_x0) * (inter_y1 - inter_y0)
#                     iarea = max(1, (ibox[2] - ibox[0]) * (ibox[3] - ibox[1]))
#                     darea = max(1, (dbox[2] - dbox[0]) * (dbox[3] - dbox[1]))
#                     if iarea < darea * 0.95 and (inter_area / iarea) > 0.4:
#                         is_sub = True
#                         break
#             if is_sub:
#                 continue
#         filtered_elements.append(el)
#     page_elements = filtered_elements
        
#     # Sort all elements on page top-to-bottom
#     page_elements.sort(key=lambda e: e["bbox"][1])

    
#     # 5. Merge info cards (consecutive blocks with color 0xe36c0a)
#     merged_elements = []
#     i = 0
#     while i < len(page_elements):
#         el = page_elements[i]
#         if el["type"] == "text" and is_color_block(el["data"], 0xe36c0a):
#             merged_lines = list(el["data"]["lines"])
#             j = i + 1
#             while j < len(page_elements):
#                 next_el = page_elements[j]
#                 if next_el["type"] == "text" and is_color_block(next_el["data"], 0xe36c0a):
#                     gap = next_el["bbox"][1] - el["bbox"][3]
#                     if gap < 20:
#                         merged_lines.extend(next_el["data"]["lines"])
#                         el["bbox"] = [
#                             min(el["bbox"][0], next_el["bbox"][0]),
#                             min(el["bbox"][1], next_el["bbox"][1]),
#                             max(el["bbox"][2], next_el["bbox"][2]),
#                             max(el["bbox"][3], next_el["bbox"][3])
#                         ]
#                         j += 1
#                         continue
#                 break
#             el["data"]["lines"] = merged_lines
#             merged_elements.append(el)
#             i = j
#         else:
#             merged_elements.append(el)
#             i += 1
            
#     page_elements = merged_elements
    
#     # 5.2 Merge Callout Box Blocks (group callout title header + consecutive bullet list items)
#     merged_elements = []
#     i = 0
#     callout_kws = ("special techniques", "important practice", "important terms")
#     while i < len(page_elements):
#         el = page_elements[i]
#         if el["type"] == "text":
#             lines = el["data"].get("lines", [])
#             txt = "".join(decode_span_text(s) for line in lines for s in line.get("spans", []) if s.get("text", "").strip()).strip().lower()
#             if any(kw in txt for kw in callout_kws):
#                 merged_lines = list(lines)
#                 j = i + 1
#                 while j < len(page_elements):
#                     next_el = page_elements[j]
#                     if next_el["type"] == "text":
#                         next_lines = next_el["data"].get("lines", [])
#                         next_spans = [s for line in next_lines for s in line.get("spans", []) if s.get("text", "").strip()]
#                         next_txt = "".join(decode_span_text(s) for s in next_spans).strip().lower()
                        
#                         # Stop merging if next block is a new major section (e.g. CITRUS, PAPAYA, BANANA, GRAPES, Diseases, etc.)
#                         section_kws = ("diseases", "papaya", "citrus", "grapes", "mango", "banana", "sapota", "litchi", "guava", "disorders", "insect- pests")
#                         if any(next_txt.startswith(kw) or next_txt == kw for kw in section_kws):
#                             break

#                         gap = next_el["bbox"][1] - el["bbox"][3]
#                         if gap < 40:
#                             merged_lines.extend(next_lines)
#                             el["bbox"] = [
#                                 min(el["bbox"][0], next_el["bbox"][0]),
#                                 min(el["bbox"][1], next_el["bbox"][1]),
#                                 max(el["bbox"][2], next_el["bbox"][2]),
#                                 max(el["bbox"][3], next_el["bbox"][3])
#                             ]
#                             j += 1
#                             continue
#                     break
#                 el["data"]["lines"] = merged_lines
#                 merged_elements.append(el)
#                 i = j
#                 continue
#         merged_elements.append(el)
#         i += 1
#     page_elements = merged_elements
    
#     # 5.5 Detect and merge captions for images/diagrams
#     merged_elements = []
#     i = 0
#     while i < len(page_elements):
#         el = page_elements[i]
#         if el["type"] in ("image", "diagram"):
#             if i + 1 < len(page_elements):
#                 next_el = page_elements[i + 1]
#                 if next_el["type"] == "text":
#                     lines = next_el["data"].get("lines", [])
#                     if len(lines) == 1:
#                         txt_spans = lines[0].get("spans", [])
#                         txt_content = "".join(decode_span_text(s) for s in txt_spans).strip()
#                         gap = next_el["bbox"][1] - el["bbox"][3]
#                         is_next_heading = False
#                         if all("Bold" in s.get("font", "") for s in txt_spans):
#                             is_next_heading = True
#                         elif re.match(r"^\d+[\.\s]", txt_content):
#                             is_next_heading = True

#                         if 0 <= gap < 45 and len(txt_content) < 120 and not is_next_heading:
#                             el["caption"] = txt_content
#                             merged_elements.append(el)
#                             i += 2
#                             continue
#         merged_elements.append(el)
#         i += 1
#     page_elements = merged_elements
#     return page_elements

# def render_page_elements(page: fitz.Page, page_elements: list, body_size: float, html_path: Path = None) -> str:
#     # 6. Render elements to HTML
#     images_dir = None
#     if html_path:
#         images_dir = html_path.parent / "images"
#         images_dir.mkdir(parents=True, exist_ok=True)

#     elements_html = []
#     image_counter = 0
#     for element in page_elements:
#         el_type = element["type"]
#         if el_type == "table":
#             table_matrix = element.get("matrix")
#             table_widths = element.get("widths")
#             table_html = render_table(element["data"], page, matrix=table_matrix, widths=table_widths)
#             if table_html and table_html.strip():
#                 elements_html.append(table_html)
#             else:
#                 # Fallback: preserve visual table region as an image so structure is never destroyed
#                 bbox = element["bbox"]
#                 clip_rect = fitz.Rect(bbox)
#                 if clip_rect.width > 0 and clip_rect.height > 0:
#                     try:
#                         pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), clip=clip_rect)
#                         img_bytes = pix.tobytes("png")
#                         if images_dir:
#                             img_filename = f"page_{page.number + 1}_tbl_{image_counter}.png"
#                             (images_dir / img_filename).write_bytes(img_bytes)
#                             image_counter += 1
#                             img_tag = f'<img src="images/{img_filename}" alt="Table" />'
#                         else:
#                             b64 = base64.b64encode(img_bytes).decode("ascii")
#                             img_tag = f'<img src="data:image/png;base64,{b64}" alt="Table" />'
#                         elements_html.append(f'<figure>{img_tag}</figure>')
#                     except Exception as e:
#                         print(f"Error rendering table image fallback: {e}", file=sys.stderr)
#         elif el_type == "image":
#             bbox = element["bbox"]
#             clip_rect = fitz.Rect(bbox)
#             if clip_rect.width > 0 and clip_rect.height > 0:
#                 try:
#                     pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), clip=clip_rect)
#                     img_bytes = pix.tobytes("png")
#                     if images_dir:
#                         img_filename = f"page_{page.number + 1}_img_{image_counter}.png"
#                         (images_dir / img_filename).write_bytes(img_bytes)
#                         image_counter += 1
#                         img_tag = f'<img src="images/{img_filename}" alt="Extracted Graphic" />'
#                     else:
#                         b64 = base64.b64encode(img_bytes).decode("ascii")
#                         img_tag = f'<img src="data:image/png;base64,{b64}" alt="Extracted Graphic" />'
#                     if "caption" in element:
#                         caption_tag = f'<figcaption>{html.escape(element["caption"])}</figcaption>'
#                         elements_html.append(f'<figure>{img_tag}\n{caption_tag}</figure>')
#                     else:
#                         elements_html.append(f'<figure>{img_tag}</figure>')
#                 except Exception as e:
#                     print(f"Error extracting image block: {e}", file=sys.stderr)
#         elif el_type == "diagram":
#             bbox = element["bbox"]
#             clip_rect = fitz.Rect(bbox)
#             if clip_rect.width > 0 and clip_rect.height > 0:
#                 try:
#                     pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), clip=clip_rect)
#                     img_bytes = pix.tobytes("png")
#                     if images_dir:
#                         img_filename = f"page_{page.number + 1}_diag_{image_counter}.png"
#                         (images_dir / img_filename).write_bytes(img_bytes)
#                         image_counter += 1
#                         img_tag = f'<img src="images/{img_filename}" alt="Diagram/Flowchart" />'
#                     else:
#                         b64 = base64.b64encode(img_bytes).decode("ascii")
#                         img_tag = f'<img src="data:image/png;base64,{b64}" alt="Diagram/Flowchart" />'
#                     if "caption" in element:
#                         caption_tag = f'<figcaption>{html.escape(element["caption"])}</figcaption>'
#                         elements_html.append(f'<figure>{img_tag}\n{caption_tag}</figure>')
#                     else:
#                         elements_html.append(f'<figure>{img_tag}</figure>')
#                 except Exception as e:
#                     print(f"Error extracting diagram block: {e}", file=sys.stderr)
#         elif el_type == "text":
#             text_html = render_text_block_semantic(element["data"], body_size, page)
#             if text_html:
#                 elements_html.append(text_html)
                
#     content = "\n".join(elements_html)
#     return PAGE_TEMPLATE.format(content=content)

# def render_page(doc: fitz.Document, page: fitz.Page, body_size: float, html_path: Path = None) -> str:
#     elements = extract_page_elements(doc, page, body_size)
#     return render_page_elements(page, elements, body_size, html_path)

# def extract_pdf_title(doc: fitz.Document) -> str:
#     if len(doc) == 0:
#         return "Document"

#     # Check if page 1 is a cover page vs content page
#     body_size = compute_body_size(doc)
#     has_cover = is_cover_page(doc[0], body_size)

#     # If no cover page exists, extract running header title from top of page 1 or page 2
#     if not has_cover:
#         for p_idx in [0, 1]:
#             if p_idx < len(doc):
#                 p = doc[p_idx]
#                 text_dict = p.get_text("dict")
#                 for b in text_dict.get("blocks", []):
#                     if b.get("type") == 0:
#                         for l in b.get("lines", []):
#                             y1 = l.get("bbox", [0, 0, 0, 0])[3]
#                             if y1 < 120:  # Top running header region
#                                 line_text = "".join(decode_span_text(s) for s in l.get("spans", [])).strip()
#                                 norm = line_text.lower().replace(" ", "")
#                                 if norm and norm not in ("www.ixambee.com", "ixambee", "prepare50%faster", "studynotes"):
#                                     cleaned_title = re.sub(r'\s+\d+$', '', line_text).strip()
#                                     if len(cleaned_title) > 3:
#                                         return cleaned_title

#     page = doc[0]
#     blocks = page.get_text("dict")["blocks"]
    
#     spans = []
#     for b in blocks:
#         if b["type"] == 0:
#             for l in b["lines"]:
#                 spans.extend(l["spans"])
                
#     if not spans:
#         return Path(doc.name).stem
        
#     # Find non-generic spans
#     non_generic_spans = []
#     for s in spans:
#         text = decode_span_text(s).strip()
#         if text and text.lower() not in ["study notes", "studynotes"]:
#             non_generic_spans.append(s)
            
#     if not non_generic_spans:
#         return decode_span_text(spans[0]).strip() if spans else "Document"
        
#     # Find maximum font size among non-generic spans
#     max_size = max(s.get("size", 0) for s in non_generic_spans)
    
#     # Collect all non-generic spans with size close to max_size (within 1.0px)
#     title_spans = []
#     for s in non_generic_spans:
#         if abs(s.get("size", 0) - max_size) <= 1.0:
#             title_spans.append(s)
            
#     # Sort top-to-bottom, then left-to-right
#     title_spans.sort(key=lambda s: (s["bbox"][1], s["bbox"][0]))
    
#     # Join distinct parts
#     title_parts = []
#     for s in title_spans:
#         t = decode_span_text(s).strip()
#         if t and t not in title_parts:
#             title_parts.append(t)
            
#     if title_parts:
#         return " ".join(title_parts)

#     return Path(doc.name).stem

        
#     return "Document"


# def _is_minor_page_start_element(el: dict) -> bool:
#     """True for small leading elements (running title, logo, page banner)
#     that can sit between a page break and a table continuation without
#     breaking the continuation. Deliberately conservative: real body
#     paragraphs or large graphics return False so we never accidentally
#     merge two genuinely different tables.
#     """
#     if el["type"] == "image":
#         bbox = el["bbox"]
#         w = bbox[2] - bbox[0]
#         h = bbox[3] - bbox[1]
#         return w < 220 and h < 120
#     if el["type"] == "text":
#         lines = el["data"].get("lines", [])
#         text = "".join(
#             decode_span_text(s)
#             for l in lines
#             for s in l.get("spans", [])
#             if s.get("text", "").strip()
#         ).strip()
#         return len(text) < 90
#     return False


# def _table_col_count(matrix: list) -> int:
#     return max((len(row) for row in matrix), default=0)


# def _row_signature(row) -> set:
#     return {
#         _table_cell_text(c).strip().lower()
#         for c in row
#         if _table_cell_text(c).strip()
#     }


# def _merge_table_matrices(prev_matrix: list, next_matrix: list) -> list:
#     """Pad both matrices to a common column count and stack them.

#     If the continuation's first row duplicates the original header row text
#     (some PDFs repeat the header on every page), that row is dropped instead
#     of being appended as a bogus data row.
#     """
#     if not next_matrix:
#         return prev_matrix

#     next_matrix = list(next_matrix)
#     if prev_matrix and next_matrix:
#         prev_header_sig = _row_signature(prev_matrix[0])
#         next_first_sig = _row_signature(next_matrix[0])
#         if prev_header_sig and next_first_sig:
#             overlap = len(prev_header_sig & next_first_sig)
#             if overlap >= max(1, len(next_first_sig) * 0.5):
#                 next_matrix = next_matrix[1:]

#     if not next_matrix:
#         return prev_matrix

#     ncols = max(_table_col_count(prev_matrix), _table_col_count(next_matrix))

#     def pad(matrix):
#         return [list(row) + [None] * (ncols - len(row)) for row in matrix]

#     return pad(prev_matrix) + pad(next_matrix)


# def merge_split_pages(all_pages_elements: list) -> None:
#     for idx in range(len(all_pages_elements) - 1):
#         prev_elements = all_pages_elements[idx]
#         next_elements = all_pages_elements[idx + 1]
#         if not prev_elements or not next_elements:
#             continue

#         # 1. Multi-page table continuation.
#         # When a table is cut off by a page break, its continuation on the
#         # next page usually has no repeated header row of its own (or, at
#         # most, a small running title / logo banner sits above it). If that
#         # continuation is treated as its own independent table, PyMuPDF's
#         # extraction reads its first *data* row as a bogus header (e.g. row
#         # 6 of an 11-row table becoming the header of a second, wrong,
#         # 5-row table). Detect that pattern here and fold the continuation's
#         # rows into the original table instead, so the whole thing renders
#         # as one table with the correct header.
#         if prev_elements[-1]["type"] == "table":
#             insert_idx = None
#             for j, el in enumerate(next_elements):
#                 if el["type"] == "table":
#                     insert_idx = j
#                     break
#                 if not _is_minor_page_start_element(el):
#                     break

#             if insert_idx is not None:
#                 prev_table_el = prev_elements[-1]
#                 next_table_el = next_elements[insert_idx]
#                 prev_matrix = prev_table_el.get("matrix") or []
#                 next_matrix = next_table_el.get("matrix") or []
#                 prev_cols = _table_col_count(prev_matrix)
#                 next_cols = _table_col_count(next_matrix)

#                 # Only merge tables whose column counts are compatible
#                 # (allow off-by-one for a stray phantom/merged column) and
#                 # where the first table is a genuine multi-row table, to
#                 # avoid ever merging two unrelated tables that happen to
#                 # share a column count.
#                 if (
#                     prev_cols >= 2
#                     and next_cols >= 2
#                     and abs(prev_cols - next_cols) <= 1
#                     and len(prev_matrix) >= 1
#                 ):
#                     merged_matrix = _merge_table_matrices(prev_matrix, next_matrix)
#                     prev_table_el["matrix"] = merged_matrix

#                     merged_num_cols = _table_col_count(merged_matrix)
#                     prev_widths = prev_table_el.get("widths") or []
#                     if len(prev_widths) != merged_num_cols and merged_num_cols:
#                         prev_widths = [100.0 / merged_num_cols] * merged_num_cols
#                     prev_table_el["widths"] = prev_widths

#                     prev_table_el["bbox"] = [
#                         min(prev_table_el["bbox"][0], next_table_el["bbox"][0]),
#                         prev_table_el["bbox"][1],
#                         max(prev_table_el["bbox"][2], next_table_el["bbox"][2]),
#                         next_table_el["bbox"][3],
#                     ]

#                     # Drop the banner/logo (if any) and the continuation
#                     # table itself from the next page's element list -- it
#                     # has now been folded into the previous page's table.
#                     del next_elements[: insert_idx + 1]

#         # 2. Multi-page text paragraph continuation check across page break
#         if prev_elements and next_elements:
#             el_prev = prev_elements[-1]
#             el_next = next_elements[0]

#             if el_prev["type"] == "text" and el_next["type"] == "text":
#                 if not el_prev.get("is_heading") and not el_next.get("is_heading"):
#                     lines_prev = el_prev["data"].get("lines", [])
#                     lines_next = el_next["data"].get("lines", [])

#                     if lines_prev and lines_next:
#                         last_line = lines_prev[-1]
#                         last_spans = [s for s in last_line.get("spans", []) if s.get("text", "").strip()]
#                         first_line = lines_next[0]
#                         first_spans = [s for s in first_line.get("spans", []) if s.get("text", "").strip()]

#                         if last_spans and first_spans and not is_bullet_span(first_spans[0]):
#                             last_text = "".join(decode_span_text(s) for s in last_spans).strip()
#                             if last_text and not last_text[-1] in (".", "?", "!", ":", ";", "\u201d", '"'):
#                                 if last_text.endswith("-") and len(last_text) > 2:
#                                     for s in reversed(last_spans):
#                                         if s.get("text", "").endswith("-"):
#                                             s["text"] = s["text"][:-1]
#                                             break

#                                 lines_prev.extend(lines_next)
#                                 el_prev["data"]["lines"] = lines_prev
#                                 el_prev["bbox"] = [
#                                     min(el_prev["bbox"][0], el_next["bbox"][0]),
#                                     min(el_prev["bbox"][1], el_next["bbox"][1]),
#                                     max(el_prev["bbox"][2], el_next["bbox"][2]),
#                                     max(el_prev["bbox"][3], el_next["bbox"][3])
#                                 ]
#                                 next_elements.pop(0)

# def post_process_worksheet_html(raw_html: str) -> str:
#     lines = raw_html.split("\n")
#     out_lines = []
#     in_mcq = False
#     in_q_section = False
#     in_exp_card = False
#     in_box_card = False      # NEW: tracks open .pdf-box-card divs
#     opt_index = 0

#     labels = ["A.", "B.", "C.", "D.", "E.", "F.", "G."]

#     # Regex: matches "Box 1 – ..." / "Box 2: ..." / "Box-3 — ..." inside any tags
#     _RE_BOX = re.compile(
#         r'Box\s*[-–—]?\s*\d+\s*[-–—:]\s*(.+)',
#         re.IGNORECASE
#     )

#     num_lines = len(lines)
#     for idx in range(num_lines):
#         line = lines[idx]
#         stripped = line.strip()

#         # ── Step 0: Detect "Box N – Title" heading ──────────────────────────
#         # Matches e.g.  <p><strong>Box 1 – NBFC-P2P in India – as of June 30, 2019 </strong></p>
#         clean_for_box = re.sub(r'<[^>]+>', '', stripped).strip()
#         m_box = _RE_BOX.match(clean_for_box)
#         if m_box:
#             # Close any open card/section first
#             if in_mcq:
#                 out_lines.append('</ul></div>')
#                 in_mcq = False
#                 in_q_section = False
#             elif in_q_section:
#                 out_lines.append('</div>')
#                 in_q_section = False
#             elif in_exp_card:
#                 out_lines.append('</div>')
#                 in_exp_card = False
#             if in_box_card:
#                 out_lines.append('</div>')
#                 in_box_card = False

#             # Full text of the box title (everything after "Box N –")
#             box_title = re.sub(r'<[^>]+>', '', stripped).strip()
#             out_lines.append(f'<div class="pdf-box-card"><h4 class="box-title">{box_title}</h4>')
#             in_box_card = True
#             opt_index = 0
#             continue

#         # Close box card on section boundary
#         if in_box_card and (stripped == '</section>' or stripped.startswith('<section')):
#             out_lines.append('</div>')
#             in_box_card = False

#         # 1. Fix Leaked Option E + Question Prompt (e.g. "<li>1.4 9. Which...", "Coimbattore 15. __ was...")
#         m_leak = re.match(r'^(?:<li>|<p>)?\s*([A-Za-z0-9\.\,\s\-\%\/\(\)]+?)\s+(\d{1,3}\.\s+[A-Z_].*)', stripped)
#         if m_leak and not re.match(r'^(?:Q(?:ues)?\.?\s*\d+|\d{1,3}\.)\s+', stripped):
#             e_val = m_leak.group(1).strip()
#             q_prompt = m_leak.group(2).strip()
#             if in_mcq:
#                 lbl = labels[opt_index % len(labels)] if opt_index < len(labels) else "E."
#                 is_bold_opt = bool(re.search(r'<strong>|<b>', e_val, re.IGNORECASE))
#                 li_cls = ' class="correct-option"' if is_bold_opt else ''
#                 out_lines.append(f'<li{li_cls}><span class="opt-label">{lbl}</span> <span class="opt-text">{e_val}</span></li>')
#                 out_lines.append('</ul></div>')
#                 in_mcq = False
#                 in_q_section = False
#                 opt_index = 0
            
#             m_num = re.match(r'^((?:Q(?:ues)?\.?\s*\d+|\d{1,3}\.))\s*(.*)', q_prompt)
#             if m_num:
#                 qn = m_num.group(1).strip()
#                 qt = m_num.group(2).strip()
#                 out_lines.append(f'<div class="question-section"><p class="q-header"><span class="q-num">{qn}</span> <span class="q-text">{qt}</span></p>')
#             else:
#                 out_lines.append(f'<div class="question-section"><p class="q-header"><span class="q-text">{q_prompt}</span></p>')
#             in_q_section = True
#             opt_index = 0
#             continue


#         clean_text = re.sub(r'<[^>]+>', '', stripped).strip()

#         clean_text = re.sub(r'<[^>]+>', '', stripped).strip()

#         # 2. Check if Question Prompt e.g. "Q.1", "Question 5:", "Q12."
#         m_q = re.match(r'^(?:Q(?:ues)?\.?\s*\d+|\d{1,3}\.)\s+[A-Z]', clean_text)
#         is_actual_q = False
#         if m_q:
#             # Must explicitly start with Q / Question / प्रश् / प्रश्न
#             if re.match(r'^(?:Q(?:ues)?\.?\s*\d+|Question\b|प्रश्|प्रश्न)\b', clean_text, re.IGNORECASE):
#                 is_actual_q = True
#             else:
#                 # If it's a plain number (e.g. "1."), look ahead up to 6 lines for explicit MCQ options e.g. (A) or A.
#                 for lookahead_idx in range(idx + 1, min(idx + 7, num_lines)):
#                     lookahead_line = lines[lookahead_idx].strip()
#                     lookahead_clean = re.sub(r'<[^>]+>', '', lookahead_line).strip()
#                     if re.match(r'^(?:<li>|<p>)?\s*(?:<strong>|<b>)?\s*\(?([A-Ea-e])\)?\s*[\.\)]\s+[A-Za-z0-9]', lookahead_line, re.IGNORECASE):
#                         is_actual_q = True
#                         break
#                     # Stop if we hit a section boundary or another heading
#                     if re.match(r'^<h[1-4]\b', lookahead_line, re.IGNORECASE) or re.match(r'^(?:Q(?:ues)?\.?\s*\d+|\d{1,3}\.)\s+[A-Z]', lookahead_clean):
#                         break

#         if is_actual_q:
#             if in_mcq:
#                 out_lines.append('</ul></div>')
#                 in_mcq = False
#                 in_q_section = False
#             elif in_q_section:
#                 out_lines.append('</div>')
#                 in_q_section = False
#             elif in_exp_card:
#                 out_lines.append('</div>')
#                 in_exp_card = False

#             m_num = re.match(r'^((?:Q(?:ues)?\.?\s*\d+|\d{1,3}\.))\s*(.*)', clean_text)
#             if m_num:
#                 qn = m_num.group(1).strip()
#                 qt = m_num.group(2).strip()
#                 out_lines.append(f'<div class="question-section"><p class="q-header"><span class="q-num">{qn}</span> <span class="q-text">{qt}</span></p>')
#             else:
#                 out_lines.append(f'<div class="question-section"><p class="q-header"><span class="q-text">{clean_text}</span></p>')
#             in_q_section = True
#             opt_index = 0
#             continue

#         # 3. Check if Explanation heading
#         if re.match(r'^(Explanation|Solution)\b', clean_text, re.IGNORECASE):
#             if in_mcq:
#                 out_lines.append('</ul></div>')
#                 in_mcq = False
#                 in_q_section = False
#             elif in_q_section:
#                 out_lines.append('</div>')
#                 in_q_section = False
#             elif in_exp_card:
#                 out_lines.append('</div>')
#                 in_exp_card = False

#             out_lines.append(f'<div class="explanation-card"><p class="explanation-title">{clean_text}</p>')
#             in_exp_card = True
#             opt_index = 0
#             continue

#         # 4. Handle List opening in Question Section
#         if in_q_section and (stripped.startswith('<ul') or stripped == '<ul>'):
#             if not in_mcq:
#                 out_lines.append('<ul class="mcq-options-list">')
#                 in_mcq = True
#                 opt_index = 0
#             continue

#         # 5. Handle List closing in Question Section
#         if in_q_section and stripped == '</ul>' and in_mcq:
#             out_lines.append('</ul>')
#             in_mcq = False
#             continue

#         # 6. Check if explicit MCQ Option inside Question Section
#         m_lbl = re.match(r'^(?:<li>|<p>)?\s*(?:<strong>|<b>)?\s*([A-Ea-e][\.\)]|\([A-Ea-e]\))\s*(.*)', stripped)
#         if not m_lbl:
#             m_lbl = re.match(r'^([A-Ea-e][\.\)]|\([A-Ea-e]\))\s*(.*)', clean_text)

#         is_explicit_opt = bool(m_lbl and len(m_lbl.group(1)) <= 4)
#         is_list_item = stripped.startswith('<li>')

#         # If in question section but before option list started, and text does NOT start with explicit A. B. C. D. E.:
#         # Join it as continuation of the question text!
#         if in_q_section and not in_mcq and not is_explicit_opt and not is_list_item and not stripped.startswith('<ul'):
#             if out_lines and 'class="q-text"' in out_lines[-1]:
#                 out_lines[-1] = re.sub(r'</span>\s*</p>$', f' {clean_text}</span></p>', out_lines[-1])
#                 continue

#         # Only transform into MCQ option li if it is an explicit option (A., B., C., D.) or inside an active MCQ list
#         if in_q_section and is_explicit_opt:
#             is_bold_opt = bool(re.search(r'<strong>|<b>', stripped, re.IGNORECASE))
#             lbl = m_lbl.group(1).strip()
#             txt = m_lbl.group(2).strip()

#             txt_clean = re.sub(r'</?(?:p|li|span)[^>]*>', '', txt, flags=re.IGNORECASE).strip()
#             txt_clean = re.sub(r'^\s*<strong>\s*', '<strong>', txt_clean)
#             txt_clean = re.sub(r'\s*</strong>\s*$', '</strong>', txt_clean)

#             if is_bold_opt and not txt_clean.startswith('<strong>'):
#                 txt_clean = f'<strong>{txt_clean}</strong>'

#             if not in_mcq:
#                 out_lines.append('<ul class="mcq-options-list">')
#                 in_mcq = True

#             li_cls = ' class="correct-option"' if is_bold_opt else ''
#             out_lines.append(f'<li{li_cls}><span class="opt-label">{lbl}</span> <span class="opt-text">{txt_clean}</span></li>')
#             opt_index += 1
#             continue



#         # 7. Boundary reset
#         if stripped == '</section>' or stripped.startswith('<section'):
#             if in_mcq:
#                 out_lines.append('</ul>')
#                 in_mcq = False
#             elif in_exp_card:
#                 out_lines.append('</div>')
#                 in_exp_card = False
#             out_lines.append(line)
#             continue

#         out_lines.append(line)

#     if in_mcq:
#         out_lines.append('</ul></div>')
#     elif in_q_section or in_exp_card:
#         out_lines.append('</div>')
#     if in_box_card:
#         out_lines.append('</div>')

#     return "\n".join(out_lines)


# def convert(pdf_path: Path, html_path: Path, start: int = None, end: int = None) -> None:
#     doc = fitz.open(pdf_path)
#     try:
#         page_count = doc.page_count
        
#         # Auto-extract title from the first page of the PDF
#         pdf_title = extract_pdf_title(doc)
        
#         body_size = compute_body_size(doc)

#         # Cache shared/repeated image XRefs once per document.
#         doc._pdf_html_repeated_image_xrefs = get_repeated_image_xrefs(doc)
        
#         # Auto-detect cover page if start page is not explicitly passed
#         if start is None:
#             if is_cover_page(doc[0], body_size):
#                 start_idx = 1  # Skip cover page
#             else:
#                 start_idx = 0  # Start from Page 1
#         else:
#             start_idx = max(0, start - 1)

#         end_idx = min(page_count, end or page_count)

#         all_pages_elements = []
#         for page_index in range(start_idx, end_idx):
#             page = doc[page_index]
#             all_pages_elements.append(extract_page_elements(doc, page, body_size))
            
#         merge_split_pages(all_pages_elements)
        
#         pages_html = []
#         if start_idx == 0:
#             pages_html.append("<!-- NO_COVER_PAGE -->")

#         for i, page_index in enumerate(range(start_idx, end_idx)):
#             page = doc[page_index]
#             pages_html.append(render_page_elements(page, all_pages_elements[i], body_size, html_path))

#         full_html = DOC_TEMPLATE.format(
#             title=html.escape(pdf_title),
#             pages="\n".join(pages_html),
#         )
#         full_html = post_process_worksheet_html(full_html)

#         html_path.write_text(full_html, encoding="utf-8")
#     finally:
#         doc.close()



# def main() -> None:
#     parser = argparse.ArgumentParser(description="Convert a PDF to a semantic HTML file.")
#     parser.add_argument("pdf", type=Path, nargs="?", default=Path(PDF_PATH), help="Path to the input PDF file")
#     parser.add_argument("html", type=Path, nargs="?", default=None, help="Path to write the output HTML file")
#     parser.add_argument("--start", type=int, default=2, help="First page to convert (1-based, default 2 to skip cover)")
#     parser.add_argument("--end", type=int, default=None, help="Last page to convert (default: last page)")
#     args = parser.parse_args()
 
#     pdf_path = args.pdf
    
#     # If the input looks like a numeric MySQL ID, try to resolve it from queue or archive
#     if str(pdf_path).isdigit():
#         mysql_id = int(str(pdf_path))
#         queue_pdf = Path(__file__).parent.parent / "storage" / "queue" / str(mysql_id) / "document.pdf"
#         archive_pdf = Path(__file__).parent.parent / "storage" / "archive" / str(mysql_id) / "document.pdf"
#         if queue_pdf.exists():
#             pdf_path = queue_pdf
#             if args.html is None:
#                 args.html = Path(__file__).parent.parent / "storage" / "queue" / str(mysql_id) / "document.html"
#         elif archive_pdf.exists():
#             pdf_path = archive_pdf
#             if args.html is None:
#                 args.html = Path(__file__).parent.parent / "storage" / "archive" / str(mysql_id) / "document.html"

#     if not pdf_path.exists():
#         print(f"Input PDF not found: {pdf_path}", file=sys.stderr)
#         sys.exit(1)
 
#     output_dir = Path(OUTPUT_DIR)
#     output_dir.mkdir(parents=True, exist_ok=True)
#     html_path = args.html if args.html is not None else output_dir / f"{pdf_path.stem}.html"
 
#     convert(pdf_path, html_path, args.start, args.end)
#     print(f"Wrote {html_path}")

# if __name__ == "__main__":
#     main()

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
<style>
ul.list-alphanumeric, ul.list-alphanumeric li {{
    list-style-type: none !important;
    list-style: none !important;
}}
ul.list-alphanumeric li::before {{
    content: none !important;
}}
/* Warm Orange Callout Box Style (Clean Flat Card) */
.callout-box {{
    margin: 1.5rem 0;
    padding: 1.5rem 1.75rem;
    border-radius: 14px;
    border-left: 6px solid #e67e22;
    background: linear-gradient(135deg, #fffaf5 0%, #fff2e6 100%);
    border-top: 1px solid #fcdcc5;
    border-right: 1px solid #fcdcc5;
    border-bottom: 1px solid #fcdcc5;
    box-shadow: none;
    transition: transform 0.2s ease;
}}
.callout-box:hover {{
    transform: translateY(-2px);
    box-shadow: none;
}}
.callout-title, .callout-box p strong, .callout-box h3 {{
    color: #d35400 !important;
    font-weight: 700;
}}
.callout-box ul.notes-list li {{
    margin-bottom: 0.6rem;
    line-height: 1.65;
    color: #2c3e50;
}}
.callout-box ul.notes-list li strong {{
    color: #d35400 !important;
}}
.callout-title {{
    font-family: 'Outfit', sans-serif;
    font-weight: 700;
    font-size: 1.15rem;
    margin-bottom: 0.75rem;
    color: #2c3e50;
    letter-spacing: -0.01em;
}}
.callout-box ul.notes-list {{
    margin: 0;
    padding-left: 1.2rem;
}}
.callout-box ul.notes-list li {{
    margin-bottom: 0.5rem;
    line-height: 1.6;
    color: #34495e;
}}
.callout-box p {{
    margin: 0 0 0.5rem 0;
    line-height: 1.6;
    color: #34495e;
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
    if "custom_html" in span:
        return span["custom_html"]
    text = decode_span_text(span)
    if not text.strip():
        return ""
    font = span.get("font", "")
    flags = span.get("flags", 0)
    is_bold = "Bold" in font or bool(flags & 1)
    is_italic = "Italic" in font or "Oblique" in font or bool(flags & 2)
    escaped_text = html.escape(text)
    
    if is_bold:
        escaped_text = f"<strong>{escaped_text}</strong>"
    if is_italic:
        escaped_text = f"<em>{escaped_text}</em>"
    return escaped_text


def get_repeated_image_xrefs(doc: fitz.Document, min_pages: int = 3) -> set:
    """Find image XRefs reused across many pages (shared templates/backgrounds)."""
    counts = {}
    for page in doc:
        seen = set()
        try:
            infos = page.get_image_info(xrefs=True)
        except Exception:
            infos = []
        for info in infos:
            xref = info.get("xref")
            if xref and xref not in seen:
                seen.add(xref)
                counts[xref] = counts.get(xref, 0) + 1
    return {xref for xref, count in counts.items() if count >= min_pages}


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
        tables = find_valid_tables(page)
        if tables and len(tables) > 0:
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
            # Pink, magenta, lavender, soft purple, soft red background highlights
            if (0.82 <= r <= 0.99 and 0.65 <= g <= 0.92 and 0.65 <= b <= 0.95 and (r > g or r > b)) or \
               (0.90 <= r <= 0.98 and 0.80 <= g <= 0.90 and 0.80 <= b <= 0.92):
                rect = d.get("rect")
                if rect:
                    if rect.x0 - 10 <= cx <= rect.x1 + 10 and rect.y0 - 10 <= cy <= rect.y1 + 10:
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

    FRUIT_HEADINGS = ("mango", "papaya", "guava", "sapota", "litchi", "banana", "grapes", "citrus")
    clean_txt = text.lower().strip()
    if clean_txt in FRUIT_HEADINGS or (len(clean_txt) < 15 and any(clean_txt == f or clean_txt.startswith(f + " ") for f in FRUIT_HEADINGS)):
        return "h2"

    max_size = max(s.get("size", 12) for s in spans)
    ratio = max_size / body_size if body_size else 1
    if ratio >= 1.18:
        return "h2"
    if ratio >= 0.95 and len(text) <= 100:
        return "h3"
    return None


def is_inside_table(bbox, tables) -> bool:
    """Return True when a text block materially overlaps a validated table.

    Center-point checks are too fragile when a PDF text block spans across a
    table border. Use overlap as the primary signal, with the center check as
    a fallback for small blocks.
    """
    block_rect = fitz.Rect(bbox)
    block_area = max(block_rect.width * block_rect.height, 1.0)
    center = fitz.Point((block_rect.x0 + block_rect.x1) / 2,
                        (block_rect.y0 + block_rect.y1) / 2)

    for t in tables:
        table_rect = fitz.Rect(t.bbox)
        if table_rect.contains(center):
            return True
        inter = block_rect & table_rect
        if not inter.is_empty:
            overlap = (inter.width * inter.height) / block_area
            if overlap >= 0.35:
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
    if "www.ixambee.com" in norm or "ixambee.com" in norm or "www.ixambee" in norm or "ixambee" in norm:
        return True
    if "prepare50%faster" in norm or "prepare 50% faster" in norm:
        return True
    return False


def is_watermark_image(block: dict, page: fitz.Page) -> bool:
    """Do not classify images as watermarks from size/position alone.

    Large centered images can be real tables, diagrams, charts, or scanned
    content. Repeated shared XRefs are filtered separately.
    """
    return False


def drawing_overlaps_table(drawing_rect: fitz.Rect, tables: list, threshold: float = 0.35) -> bool:
    """True when a vector drawing is part of a validated table."""
    d_area = max(drawing_rect.width * drawing_rect.height, 1.0)
    center = fitz.Point((drawing_rect.x0 + drawing_rect.x1) / 2.0,
                        (drawing_rect.y0 + drawing_rect.y1) / 2.0)
    for table in tables:
        tr = fitz.Rect(table.bbox)
        if tr.contains(center):
            return True
        inter = drawing_rect & tr
        if not inter.is_empty and (inter.width * inter.height) / d_area >= threshold:
            return True
    return False


def is_valid_vector_diagram(cluster: fitz.Rect, page: fitz.Page, text_dict: dict, valid_tables: list) -> bool:
    """
    Determine whether a candidate drawing cluster is a genuine vector diagram/flowchart.
    Rejects watermark clusters, light-gray background stamps, and website URL watermarks.
    """
    # A validated table owns its vector borders/cell fills. Never let those
    # drawings become a diagram candidate.
    for table in valid_tables:
        tr = fitz.Rect(table.bbox)
        inter = cluster & tr
        if not inter.is_empty:
            cluster_area = max(cluster.width * cluster.height, 1.0)
            inter_area = max(inter.width * inter.height, 0.0)
            center = fitz.Point((cluster.x0 + cluster.x1) / 2.0,
                                (cluster.y0 + cluster.y1) / 2.0)
            if inter_area / cluster_area >= 0.20 or tr.contains(center):
                print(f"  [DIAGRAM REJECT] bbox={tuple(cluster)} reason=overlaps_validated_table", file=sys.stderr)
                return False

    # 1. Dimension check
    if cluster.width < 40 or cluster.height < 25:
        print(f"  [DIAGRAM REJECT] bbox={tuple(cluster)} reason=too_small", file=sys.stderr)
        return False

    page_h = page.rect.height
    if cluster.height > 580 or cluster.height > page_h * 0.85:
        print(f"  [DIAGRAM REJECT] bbox={tuple(cluster)} reason=too_large_spans_page", file=sys.stderr)
        return False

    cluster_area = cluster.width * cluster.height

    # 2. Inspect text content inside cluster to reject pure watermark text regions
    cluster_text_lines = []
    for tb in text_dict.get("blocks", []):
        if tb.get("type", 0) == 0:
            tb_rect = fitz.Rect(tb.get("bbox", (0, 0, 0, 0)))
            intersect = cluster & tb_rect
            if not intersect.is_empty and (intersect.width * intersect.height) / max(1.0, tb_rect.width * tb_rect.height) > 0.3:
                for line in tb.get("lines", []):
                    line_txt = "".join(s.get("text", "") for s in line.get("spans", [])).strip()
                    if line_txt:
                        cluster_text_lines.append(line_txt)

    if cluster_text_lines:
        if any(is_watermark_text(txt) for txt in cluster_text_lines):
            print(f"  [DIAGRAM REJECT] bbox={tuple(cluster)} reason=watermark_text", file=sys.stderr)
            return False

        callout_kws = ("special techniques", "important practice", "important terms")
        for line_t in cluster_text_lines:
            low_t = line_t.strip().lower()
            if any(kw in low_t for kw in callout_kws) and len(cluster_text_lines) > 1:
                print(f"  [DIAGRAM REJECT] bbox={tuple(cluster)} title='{line_t}' reason=text_callout_box", file=sys.stderr)
                return False

    # 3. Inspect vector drawings inside the cluster
    all_drawings = page.get_drawings()
    meaningful_drawings = 0

    for d in all_drawings:
        r = fitz.Rect(d["rect"])
        if cluster.x0 - 5 <= r.x0 and r.x1 <= cluster.x1 + 5 and cluster.y0 - 5 <= r.y0 and r.y1 <= cluster.y1 + 5:
            fill = d.get("fill")
            # Skip light gray watermark fills
            if fill and len(fill) == 3:
                r_val, g_val, b_val = fill
                if abs(r_val - g_val) < 0.02 and abs(g_val - b_val) < 0.02 and 0.7 <= r_val <= 0.9:
                    continue
            meaningful_drawings += 1

    if meaningful_drawings < 1:
        print(f"  [DIAGRAM REJECT] bbox={tuple(cluster)} reason=no_meaningful_drawings", file=sys.stderr)
        return False

    print(f"  [DIAGRAM ACCEPT] bbox={tuple(cluster)} drawings={meaningful_drawings}", file=sys.stderr)
    return True





def _table_cell_text(cell) -> str:
    # Geometry-aware table cells are dictionaries carrying the actual text
    # plus colspan/start_col/bbox metadata. Never stringify the dictionary:
    # doing so leaks the internal cell structure into the generated HTML.
    if isinstance(cell, dict):
        cell = cell.get("text", "")
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

        # Reject only when the short/empty column is genuinely sparse.
        # A perfectly valid 2-column table often has short row labels in the
        # first column and long descriptions in the second column.
        if total_chars > 0 and (max_col_chars / total_chars) >= 0.85 and min_col_cells <= 1 and col_count == 2:
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

            # Split candidate tables at vertical row gaps > 22 to prevent swallowing surrounding paragraphs
            rows = getattr(table, "rows", None) or []
            tables_to_check = [table]
            if len(rows) >= 2:
                clusters = []
                current_cluster = [rows[0]]
                for r_i in range(1, len(rows)):
                    gap = rows[r_i].bbox[1] - rows[r_i-1].bbox[3]
                    if gap > 22:
                        clusters.append(current_cluster)
                        current_cluster = [rows[r_i]]
                    else:
                        current_cluster.append(rows[r_i])
                clusters.append(current_cluster)

                if len(clusters) > 1:
                    tables_to_check = []
                    for cl in clusters:
                        sub_clip = fitz.Rect(tx0, cl[0].bbox[1] - 2, tx1, cl[-1].bbox[3] + 2)
                        try:
                            sub_finder = page.find_tables(clip=sub_clip, strategy=strategy)
                            sub_candidates = getattr(sub_finder, "tables", []) or []
                            tables_to_check.extend(sub_candidates)
                        except Exception:
                            pass

            for tbl in tables_to_check:
                quality = _table_quality_score(tbl, page)
                if quality < 0:
                    continue
                valid.append(tbl)

        return valid

    # Prefer strict line detection.
    strict_tables = collect("lines_strict")
    if strict_tables:
        return strict_tables

    # Fallback to general line detection.
    return collect("lines")


def collapse_phantom_columns(table_data: list, table=None, page=None) -> list:
    """
    Intelligently detect and collapse phantom columns created by PyMuPDF table detection artifacts.
    Preserves legitimate empty/partially-filled columns and re-assigns/merges displaced text spans.
    """
    if not table_data:
        return table_data

    num_rows = len(table_data)
    num_cols = max((len(r) for r in table_data), default=0)

    if num_cols <= 2 or num_rows == 0:
        return table_data

    # Pad rows to uniform num_cols
    padded_data = [
        list(r) + [""] * (num_cols - len(r))
        for r in table_data
    ]

    # Identify banner title rows (e.g. single cell title across top of table)
    data_rows_indices = []
    for r_idx, row in enumerate(padded_data):
        non_empty_cells = [c for c in row if c and str(c).strip()]
        if len(non_empty_cells) == 1 and r_idx == 0 and len(str(non_empty_cells[0]).strip()) > 15:
            continue
        data_rows_indices.append(r_idx)

    if not data_rows_indices:
        data_rows_indices = list(range(num_rows))

    nonempty_count = [0] * num_cols
    total_chars = [0] * num_cols

    for r_idx in data_rows_indices:
        row = padded_data[r_idx]
        for c_idx in range(num_cols):
            val = str(row[c_idx] or "").strip()
            if val:
                nonempty_count[c_idx] += 1
                total_chars[c_idx] += len(val)

    max_nonempty = max(nonempty_count) if nonempty_count else 0
    if max_nonempty < 2:
        return table_data

    # 1. First Pass: Identify completely empty or extremely sparse phantom columns
    phantom_cols = set()
    for c_idx in range(num_cols):
        cnt = nonempty_count[c_idx]
        t_chars = total_chars[c_idx]
        if cnt == 0:
            phantom_cols.add(c_idx)
        elif cnt <= 1 and cnt <= max_nonempty * 0.15 and t_chars < 60:
            phantom_cols.add(c_idx)

    # 2. Second Pass: Check adjacent columns for phantom-split (near-zero row overlap)
    # If adjacent columns c and c+1 have zero or at most 1 overlapping populated row,
    # and at least one of them is a split fragment (nonempty <= max_nonempty * 0.45), merge them.
    merged_pairs = []
    for c_idx in range(num_cols - 1):
        if c_idx in phantom_cols or (c_idx + 1) in phantom_cols:
            continue

        cnt1 = nonempty_count[c_idx]
        cnt2 = nonempty_count[c_idx + 1]

        both_populated = 0
        for r_idx in data_rows_indices:
            v1 = str(padded_data[r_idx][c_idx] or "").strip()
            v2 = str(padded_data[r_idx][c_idx + 1] or "").strip()
            if v1 and v2:
                both_populated += 1

        if both_populated <= 1 and (cnt1 <= max_nonempty * 0.45 or cnt2 <= max_nonempty * 0.45):
            phantom_cols.add(c_idx + 1)
            merged_pairs.append((c_idx, c_idx + 1))

    if not phantom_cols or len(phantom_cols) >= num_cols - 1:
        return table_data

    # Log diagnostic message (Requirement 12)
    phantom_list = sorted(list(phantom_cols))
    print(
        f"  [TABLE COLUMN FIX] original_cols={num_cols} nonempty={nonempty_count} removing_phantom_cols={phantom_list} merged_pairs={merged_pairs}",
        file=sys.stderr
    )

    # Valid columns to keep
    valid_cols = [c for c in range(num_cols) if c not in phantom_cols]

    # Re-build clean matrix, merging text from phantom/split columns
    clean_data = []
    for r_idx, row in enumerate(padded_data):
        new_row = [str(row[c] or "") for c in valid_cols]

        for p_col in phantom_cols:
            p_text = str(row[p_col] or "").strip()
            if p_text:
                nearest_v_idx = 0
                min_dist = 999
                for v_i, v_col in enumerate(valid_cols):
                    dist = abs(v_col - p_col)
                    if dist < min_dist:
                        min_dist = dist
                        nearest_v_idx = v_i

                existing = new_row[nearest_v_idx].strip()
                if p_text not in existing:
                    if existing:
                        new_row[nearest_v_idx] = f"{existing} {p_text}"
                    else:
                        new_row[nearest_v_idx] = p_text

        clean_data.append(new_row)

    return clean_data


def _table_row_cells_geometry(table, page):
    """Return the table's real cells and reconstruct their text from PDF words.

    Important: PDF ``span`` text is not guaranteed to contain whitespace at
    formatting boundaries. In this document, for example, ``LIC``, ``of``,
    ``India`` and other words can be separate spans whose bounding boxes touch,
    so joining spans with ``""`` produces ``LICofIndia``. PyMuPDF's ``words``
    extraction uses glyph spacing and correctly reconstructs those words.

    We therefore keep the REAL cell geometry from ``table.rows`` (so the
    existing column/row logic is unchanged), but populate each cell from
    ``page.get_text("words")``.
    """
    if page is None:
        return []

    rows = getattr(table, "rows", None) or []
    if not rows:
        return []

    # Words preserve the PDF's actual word boundaries and whitespace.
    page_words = page.get_text("words")

    # Build a lookup of text spans so we can retain bold/italic information
    # later if needed. The current table renderer only needs plain text, but
    # keeping this list here makes the extraction boundary-aware.
    result = []

    for row in rows:
        r_bbox = getattr(row, "bbox", None)
        if not r_bbox:
            result.append([])
            continue

        real_cells = []
        for cell_bbox in (getattr(row, "cells", None) or []):
            if cell_bbox is None:
                continue
            x0, y0, x1, y1 = cell_bbox
            if x1 <= x0 or y1 <= y0:
                continue
            real_cells.append((x0, y0, x1, y1))

        real_cells.sort(key=lambda b: (b[0], b[1]))
        row_cells = []

        for cx0, cy0, cx1, cy1 in real_cells:
            # Keep a small tolerance because PDF glyph boxes can touch table
            # borders. Use word CENTER for x and y membership so a word cannot
            # accidentally leak into an adjacent cell.
            pad_x = 2.5
            pad_y = 1.5

            cell_words = []
            for w in page_words:
                if len(w) < 5:
                    continue
                wx0, wy0, wx1, wy1, word_text = w[:5]
                if not str(word_text).strip():
                    continue

                wcx = (wx0 + wx1) / 2.0
                wcy = (wy0 + wy1) / 2.0

                if (cx0 - pad_x <= wcx <= cx1 + pad_x and
                        cy0 - pad_y <= wcy <= cy1 + pad_y):
                    cell_words.append(w)

            # Reading order: top-to-bottom, then left-to-right.
            cell_words.sort(key=lambda w: (round(w[1], 1), w[0]))

            # Group words into visual lines. Word extraction already knows
            # where spaces are; we only need to restore line breaks.
            lines = []
            for w in cell_words:
                if not lines:
                    lines.append([w])
                    continue

                prev = lines[-1][0]
                # Same PDF line normally has a very small y difference.
                if abs(w[1] - prev[1]) <= 2.0:
                    lines[-1].append(w)
                else:
                    lines.append([w])

            line_texts = []
            for line_words in lines:
                line_words.sort(key=lambda w: w[0])

                # ``get_text("words")`` has already separated words correctly.
                # Joining with one space therefore fixes both:
                #   LICofIndia -> LIC of India
                #   CompaniesAct -> Companies Act
                # while preserving punctuation inside individual words.
                decoded_words = []
                for w in line_words:
                    wt = decode_span_text({"text": str(w[4])})
                    if wt:
                        decoded_words.append(wt)

                if decoded_words:
                    line_texts.append(" ".join(decoded_words))

            text = "\n".join(line_texts).strip()
            row_cells.append({"bbox": (cx0, cy0, cx1, cy1), "text": text})

        result.append(row_cells)

    return result


def _table_geometry_matrix(table, page):
    """Build a logical HTML table from real PDF cell rectangles.

    The base x-grid is the union of actual cell boundaries. Each row then uses
    colspan to represent its own divider positions. This handles tables such as
    page 9 where the upper rows use a 36/64 split while the lower rows use a
    20/80 split, without inventing a phantom column.
    """
    rows = _table_row_cells_geometry(table, page)
    if not rows:
        return []

    x_points = []
    for row in rows:
        for cell in row:
            x0, _, x1, _ = cell["bbox"]
            x_points.extend([round(x0, 3), round(x1, 3)])
    x_points = sorted(set(x_points))

    # Remove numerical noise while retaining genuinely different dividers.
    clean_x = []
    for x in x_points:
        if not clean_x or abs(x - clean_x[-1]) > 1.5:
            clean_x.append(x)
    x_points = clean_x

    if len(x_points) < 2:
        return []

    matrix = []
    for row in rows:
        logical_row = []
        for cell in row:
            x0, y0, x1, y1 = cell["bbox"]
            start = min(range(len(x_points)), key=lambda i: abs(x_points[i] - x0))
            end = min(range(len(x_points)), key=lambda i: abs(x_points[i] - x1))
            logical_row.append({
                "text": cell["text"],
                "colspan": max(1, end - start),
                "start_col": start,
                "bbox": cell["bbox"],
            })
        matrix.append(logical_row)

    return matrix


def unmerge_vertical_false_spans(table_data: list) -> list:
    """Detect columns where PyMuPDF merged vertical cells across rows into the top cell.

    If a column c has text in row 0 with multiple line breaks, and all subsequent rows 1..N
    in column c are None/empty while other columns in rows 1..N have populated data,
    distribute the split lines across rows 0..N.
    """
    if not table_data or len(table_data) < 2:
        return table_data

    num_rows = len(table_data)
    num_cols = max((len(r) for r in table_data), default=0)

    rows = [list(r) + [None] * (num_cols - len(r)) for r in table_data]

    for c in range(num_cols):
        subsequent_empty = all(
            rows[r][c] is None or not str(rows[r][c]).strip()
            for r in range(1, num_rows)
        )
        if not subsequent_empty:
            continue

        top_val = rows[0][c]
        if not top_val or not isinstance(top_val, str):
            continue

        lines = [line.strip() for line in top_val.splitlines() if line.strip()]
        if len(lines) >= 2 and len(lines) <= num_rows:
            rows[0][c] = lines[0]
            for idx, line_text in enumerate(lines[1:], start=1):
                if idx < num_rows:
                    rows[idx][c] = line_text

    return rows


def extract_table_data_accurate(table, page=None):
    """Extract table text using PyMuPDF's native logical table matrix.

    IMPORTANT: Do not rebuild the table by assigning PDF text spans/words to
    columns from their X coordinates. That approach breaks merged cells and
    tables whose column dividers change between row groups. ``table.extract()``
    already returns the logical cell matrix and uses ``None`` for merged cells.
    """
    try:
        raw = table.extract()
    except Exception as exc:
        print(f"  [TABLE EXTRACT ERROR] {exc}", file=sys.stderr)
        return []

    if not raw:
        return []

    # Normalize all rows to the same logical column count. Keep None/empty
    # cells intact; they are part of the table structure.
    num_cols = max((len(row) for row in raw), default=0)
    if num_cols < 2:
        return []

    normalized = [list(row) + [None] * (num_cols - len(row)) for row in raw]
    return unmerge_vertical_false_spans(normalized)


def _table_column_widths(table, num_cols):
    """Return stable percentage widths for the table's logical columns.

    Prefer a genuine header row with one cell per column. Otherwise use the
    first row that exposes all logical column boundaries. Fall back to equal
    widths only when the PDF does not expose usable geometry.
    """
    if num_cols <= 0:
        return []

    candidates = []
    rows = getattr(table, "rows", None) or []

    # First preference: PyMuPDF's detected header cell geometry.
    header = getattr(table, "header", None)
    header_cells = list(getattr(header, "cells", []) or []) if header else []
    if len(header_cells) == num_cols and all(c is not None for c in header_cells):
        candidates.append(header_cells)

    # Second preference: any row with a complete set of real cells.
    for row in rows:
        cells = list(getattr(row, "cells", None) or [])
        if len(cells) == num_cols and all(c is not None for c in cells):
            candidates.append(cells)
            break

    if candidates:
        cells = candidates[0]
        widths = []
        for cell in cells:
            x0, _, x1, _ = cell
            widths.append(max(0.1, float(x1 - x0)))
        total = sum(widths)
        if total > 0:
            raw_pcts = [(w / total) * 100.0 for w in widths]
            adjusted = [max(6.5, p) for p in raw_pcts]
            adj_total = sum(adjusted)
            return [(p / adj_total) * 100.0 for p in adjusted]

    return [100.0 / num_cols] * num_cols


def clean_cell_text(text: str) -> str:
    """Clean artificial PyMuPDF line breaks inside words and table cells.

    Fixes cases where PDF extraction breaks words across lines inside cells.
    """
    if not text:
        return ""

    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if len(lines) <= 1:
        return text.strip()

    merged_lines = []
    for line in lines:
        if not merged_lines:
            merged_lines.append(line)
            continue

        prev = merged_lines[-1]
        prev_word_end = not prev.endswith(('.', '?', '!', ':', ';', ')', ']', '}'))
        is_fragment = (
            len(line) <= 4 or
            not line[0].isupper() or
            prev.endswith(('-', '/', '–', '—')) or
            (prev and prev[-1].isalpha() and line and line[0].isalpha()
             and prev[-1].islower() and line[0].islower())
        )

        if prev_word_end and is_fragment:
            if prev.endswith('-'):
                merged_lines[-1] = prev[:-1] + line
            elif prev.endswith('/'):
                merged_lines[-1] = prev + line
            elif prev[-1].isalpha() and line[0].isalpha() and (len(line) <= 4 or prev[-1].islower()):
                merged_lines[-1] = prev + line
            else:
                merged_lines[-1] = prev + " " + line
        else:
            merged_lines.append(line)

    return "\n".join(merged_lines)


def _render_table_cell(text) -> str:
    text = _table_cell_text(text)
    if not text:
        return ""

    text = clean_cell_text(text)

    parts = [part.strip() for part in text.splitlines() if part.strip()]
    if len(parts) > 1:
        return "".join(
            f'<div class="table-cell-line">{html.escape(part)}</div>'
            for part in parts
        )
    return html.escape(text)


def render_table(table, page=None, matrix=None, widths=None, custom_matrix=None) -> str:
    """Render a validated PDF table without changing its logical cell layout.

    The old geometry reconstruction was the source of the broken tables: it
    created a global X-grid from every row and then rendered cells sequentially,
    ignoring each cell's actual start column. That is unsafe for merged cells
    and row groups with different dividers.

    ``matrix`` / ``widths`` let a caller pass in an already-computed (and
    possibly cross-page-merged, see ``merge_split_pages``) logical matrix and
    column widths instead of re-extracting them from ``table``. When they are
    not supplied, the function falls back to extracting them from ``table``
    directly, exactly as before.
    """
    if matrix is not None:
        table_data = matrix
    elif custom_matrix is not None:
        table_data = custom_matrix
    else:
        table_data = extract_table_data_accurate(table, page)

    if not table_data:
        return ""

    num_cols = max((len(row) for row in table_data), default=0)
    if num_cols < 2:
        return ""

    rows = [list(row) + [None] * (num_cols - len(row)) for row in table_data]

    # Targeted geometry fallback for two known PDF-extraction artefacts.
    # Do not change the general native-matrix logic: only tables that clearly
    # exhibit one of these exact signatures are re-read from their real cell
    # rectangles.
    if page is not None:
        all_text = " ".join(
            _table_cell_text(c).strip().lower()
            for row in rows
            for c in row
            if _table_cell_text(c).strip()
        )
        docs_marker = "documents, required to be filed with the registrar of companies at the time of registration"

        # The Documents table is visually a 2-column table, although the
        # native matrix can expose a phantom third column.
        docs_table = docs_marker in all_text

        # The page-break continuation can similarly appear as a 3-column
        # matrix with all actual text stranded in the last column. Its real
        # row geometry is 2-column. This condition is deliberately narrow so
        # legitimate 3-column tables are untouched.
        last_col_only = False
        if num_cols >= 3 and rows:
            populated = [(r_i, c_i) for r_i, row in enumerate(rows)
                         for c_i, c in enumerate(row) if _table_cell_text(c).strip()]
            if populated:
                last_col_only = all(c_i == num_cols - 1 for _, c_i in populated)

        if docs_table or (table.bbox[1] <= 150 and last_col_only):
            try:
                geometry_rows = _table_geometry_matrix(table, page)
                if geometry_rows:
                    rows = geometry_rows
                    num_cols = max((len(r) for r in rows), default=0)
            except Exception as exc:
                print(f"  [TABLE TARGETED GEOMETRY FALLBACK] {exc}", file=sys.stderr)

    # Targeted fix for the "Documents, required to be filed..." table.
    # In this PDF PyMuPDF can expose a spurious third trailing column for this
    # specific table even though the source table has only two visible columns.
    # Do NOT apply this to other tables: some other tables legitimately contain
    # a blank third column.
    if num_cols >= 3 and rows:
        first_row_text = " ".join(
            _table_cell_text(c) for c in rows[0] if _table_cell_text(c)
        ).strip().lower()
        if first_row_text.startswith(
            "documents, required to be filed with the registrar of companies at the time of registration"
        ):
            while len(rows[0]) > 2 and all(
                not _table_cell_text(row[-1]) for row in rows
            ):
                for row in rows:
                    row.pop()
            num_cols = max((len(row) for row in rows), default=0)

    def nonempty(row):
        return [c for c in row if _table_cell_text(c)]

    # A one-cell full-width first row is a title/banner, not a column header.
    table_x0, _, table_x1, _ = table.bbox
    first_is_banner = False
    if rows and len(nonempty(rows[0])) == 1:
        first_cell = next((c for c in rows[0] if _table_cell_text(c)), None)
        header = getattr(table, "header", None)
        header_cells = list(getattr(header, "cells", []) or []) if header else []
        if first_cell is not None and header_cells:
            real = [c for c in header_cells if c is not None]
            if len(real) == 1:
                x0, _, x1, _ = real[0]
                first_is_banner = x0 <= table_x0 + 2 and x1 >= table_x1 - 2

    # Normally the first row is the visual table header. If it is a banner,
    # use the next row as the header when it contains multiple cells.
    header_index = 1 if first_is_banner and len(rows) > 1 and len(nonempty(rows[1])) >= 2 else 0

    # Column widths: prefer explicitly-provided widths (e.g. from a merged,
    # cross-page table, or already computed once at extraction time). Only
    # re-derive from the raw table geometry when they're missing or no
    # longer match the (possibly merged) column count.
    if widths and len(widths) == num_cols:
        col_widths = widths
    else:
        col_widths = _table_column_widths(table, num_cols)
        if len(col_widths) != num_cols:
            col_widths = [100.0 / num_cols] * num_cols

    min_table_width_style = ""
    if num_cols >= 6:
        min_table_width_style = f' style="min-width: {max(950, num_cols * 105)}px;"'
    elif num_cols >= 4:
        min_table_width_style = ' style="min-width: 650px;"'

    extra_cls = " table-dense" if num_cols >= 7 else ""

    html_lines = [
        '<div class="table-responsive">',
        f'<table class="notes-table{extra_cls}"{min_table_width_style}>',
        '<colgroup>',
    ]
    for width in col_widths:
        html_lines.append(f'<col style="width:{width:.3f}%">')
    html_lines.extend(['</colgroup>'])

    if first_is_banner:
        banner = rows[0]
        banner_text = next((c for c in banner if _table_cell_text(c)), "")
        html_lines.extend([
            '<tbody>',
            '<tr class="table-section-row">',
            f'<th colspan="{num_cols}" class="table-section-heading">{_render_table_cell(banner_text)}</th>',
            '</tr>',
        ])
    else:
        html_lines.extend(['<thead>', '<tr>'])
        for cell in rows[0]:
            html_lines.append(f'<th>{_render_table_cell(cell)}</th>')
        html_lines.extend(['</tr>', '</thead>', '<tbody>'])

    start_body = header_index + 1 if header_index == 1 else 1
    if first_is_banner and header_index == 1:
        # Render the actual column header row as the orange header.
        html_lines.append('<tr>')
        for cell in rows[1]:
            html_lines.append(f'<th>{_render_table_cell(cell)}</th>')
        html_lines.append('</tr>')

    for row in rows[start_body:]:
        non_empty = [(idx, c) for idx, c in enumerate(row) if _table_cell_text(c)]
        if not non_empty:
            continue
        html_lines.append('<tr>')
        for cell in row:
            html_lines.append(f'<td>{_render_table_cell(cell)}</td>')
        html_lines.append('</tr>')

    html_lines.extend(['</tbody>', '</table>', '</div>'])
    return "\n".join(html_lines)

def is_color_block(block: dict, target_color: int) -> bool:
    for line in block.get("lines", []):
        for span in line.get("spans", []):
            if span.get("text", "").strip():
                if span.get("color", 0) == target_color:
                    return True
    return False

def is_math_expression_line(text: str) -> bool:
    """Return True if a text line looks like a math fraction numerator/denominator component."""
    if not text:
        return False
    if len(text) > 85:
        return False
    if text.endswith((".", "?", "!", ":")):
        return False
    math_words = (
        "ebit", "sales", "cost", "costs", "contribution", "dol", "dcl", "fl", "ol",
        "change", "profit", "tax", "eat", "pbt", "earning", "earnings", "fixed",
        "variable", "interest", "leverage", "equity", "debt", "margin", "ratio"
    )
    low = text.lower()
    if any(w in low for w in math_words):
        return True
    if any(c in text for c in ("+", "-", "–", "—", "/", "*", "%", "=", "(", ")", "×", "÷")):
        return True
    if re.search(r'\d+', text):
        return True
    return False

def detect_and_merge_math_fractions(visible_lines, page=None):
    if len(visible_lines) < 2:
        return visible_lines

    merged_lines = []
    i = 0
    while i < len(visible_lines):
        line1 = visible_lines[i]
        if i + 1 >= len(visible_lines):
            merged_lines.append(line1)
            break

        line2 = visible_lines[i + 1]

        spans1 = [s for s in line1.get("spans", []) if s.get("text", "").strip()]
        spans2 = [s for s in line2.get("spans", []) if s.get("text", "").strip()]

        if not spans1 or not spans2:
            merged_lines.append(line1)
            i += 1
            continue

        if is_bullet_span(spans1[0]) or is_bullet_span(spans2[0]):
            merged_lines.append(line1)
            i += 1
            continue

        text1 = "".join(decode_span_text(s) for s in spans1).strip()
        text2 = "".join(decode_span_text(s) for s in spans2).strip()

        if is_math_expression_line(text1) and is_math_expression_line(text2):
            bbox1 = line1.get("bbox", [0, 0, 0, 0])
            bbox2 = line2.get("bbox", [0, 0, 0, 0])

            cx1 = (bbox1[0] + bbox1[2]) / 2.0
            cx2 = (bbox2[0] + bbox2[2]) / 2.0
            gap = bbox2[1] - bbox1[3]

            if abs(cx1 - cx2) < 65 and -3 <= gap <= 22:
                rendered1 = "".join(render_span_semantic(s) for s in spans1)
                rendered2 = "".join(render_span_semantic(s) for s in spans2)

                den_text = rendered2
                clean_den = text2.strip()
                if (" " in clean_den or "-" in clean_den or "–" in clean_den or "+" in clean_den) and not (clean_den.startswith("(") and clean_den.endswith(")")):
                    den_text = f"({rendered2})"

                fraction_span = {
                    "text": f"{text1} / {text2}",
                    "font": spans1[0].get("font", ""),
                    "size": spans1[0].get("size", 12),
                    "color": spans1[0].get("color", 0),
                    "custom_html": f"{rendered1} / {den_text}"
                }

                combined_line = line1.copy()
                combined_line["spans"] = [fraction_span]
                combined_line["bbox"] = [
                    min(bbox1[0], bbox2[0]),
                    bbox1[1],
                    max(bbox1[2], bbox2[2]),
                    bbox2[3]
                ]
                merged_lines.append(combined_line)
                i += 2
                continue

        merged_lines.append(line1)
        i += 1

    return merged_lines

def render_text_block_semantic(block: dict, body_size: float, page: fitz.Page = None) -> str:
    # Filter out running headers based on content and small font size
    text_spans = []
    for l in block.get("lines", []):
        text_spans.extend(l.get("spans", []))
    
    is_note_block = False
    is_figure_caption = False
    if text_spans:
        text_content = "".join(s.get("text", "") for s in text_spans).strip()
        is_note_block = bool(re.match(r'^(please\s+note\s*[:-]|note\s*[:-]|नोट\s*[:-]|note\b)', text_content, re.IGNORECASE))

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
        
    visible_lines = detect_and_merge_math_fractions(merged_lines, page)
        
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
                is_alphanumeric = bool(re.match(r'^(\(?([0-9]+|[a-z]{1,3}|[IVX]{1,4})\)[\.\)]?|([0-9]+|[a-z]{1,3}|[IVX]{1,4})[\.\)])$', bullet_char))
                cls_extra = " list-alphanumeric" if is_alphanumeric else ""
                
                if not active_lists:
                    is_checkmark = bullet_char in ("✓", "✔", "ü", "\u2713", "\u2714", "\uf0fc")
                    style_attr = ' style="list-style-type: none; list-style: none;"' if is_alphanumeric else ''
                    if is_checkmark:
                        html_out.append(f'<ul class="notes-sub{cls_extra}"{style_attr}>')
                        active_lists.append(x_bullet - 20)  # Dummy parent level
                        active_lists.append(x_bullet)
                    else:
                        html_out.append(f'<ul class="notes-list{cls_extra}"{style_attr}>')
                        active_lists.append(x_bullet)
                else:
                    if x_bullet > active_lists[-1] + 5:
                        level = len(active_lists)
                        cls_name = "notes-sub" if level == 1 else "notes-subsub"
                        style_attr = ' style="list-style-type: none; list-style: none;"' if is_alphanumeric else ''
                        html_out.append(f'<ul class="{cls_name}{cls_extra}"{style_attr}>')
                        active_lists.append(x_bullet)
                    elif x_bullet < active_lists[-1] - 5:
                        while active_lists and x_bullet < active_lists[-1] - 5:
                            html_out.append("</li></ul>")
                            active_lists.pop()
                        if not active_lists:
                            style_attr = ' style="list-style-type: none; list-style: none;"' if is_alphanumeric else ''
                            html_out.append(f'<ul class="notes-list{cls_extra}"{style_attr}>')
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

    # Wrap Exam Tip blocks in simple dashed Exam Tip boxes (evaluated before note/callout wrappers)
    lines = block.get("lines", [])
    full_block_text = "".join(
        decode_span_text(s)
        for l_item in lines
        for s in l_item.get("spans", [])
        if s.get("text", "").strip()
    ).strip()
    if re.search(r'\bexam\s+tip\b', full_block_text, re.IGNORECASE):
        clean_text = re.sub(r'^<p>(.*?)</p>$', r'\1', res, flags=re.DOTALL).strip()
        clean_text = re.sub(r'^(?:<[a-z0-9]+>)*(?:<strong>)*\s*exam\s+tip\s*[:-]*\s*(?:</strong>)*(?:</[a-z0-9]+>)*', '', clean_text, flags=re.IGNORECASE).strip()
        box_style = 'style="background: #fffdf8; border: 1px dashed #f5b94c; border-radius: 6px; padding: 14px 24px; margin: 12px 0; color: #222; font-size: 16px; line-height: 1.55;"'
        strong_style = 'style="color: #f07800; font-weight: 700; margin-right: 6px;"'
        return f'<div class="exam-tip" {box_style}>\n  <strong {strong_style}>Exam Tip:</strong> {clean_text}\n</div>'

    if is_note_block:
        pattern = re.compile(
            r'^((?:<[a-z0-9]+>)*(?:<strong>|<em>)*)(please\s+note\s*[:-]|note\s*[:-]|नोट\s*[:-]|note\b)((?:</strong>|</em>)*)(\s*)',
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

    # Wrap callout blocks in clean flat Warm Orange card boxes (for remote server compatibility)
    callout_kws = ("special techniques", "important practice", "important terms")
    for l_item in lines:
        l_spans = [s for s in l_item.get("spans", []) if s.get("text", "").strip()]
        if l_spans:
            l_txt = "".join(decode_span_text(s) for s in l_spans).strip().lower()
            if any(kw in l_txt for kw in callout_kws):
                box_style = 'style="margin: 1.5rem 0; padding: 1.5rem 1.75rem; border-radius: 14px; border-left: 6px solid #e67e22; background: linear-gradient(135deg, #fffaf5 0%, #fff2e6 100%); border-top: 1px solid #fcdcc5; border-right: 1px solid #fcdcc5; border-bottom: 1px solid #fcdcc5; box-shadow: none;"'
                return f'<div class="callout-box" {box_style}>\n{res}\n</div>'

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
        d_rect = fitz.Rect(r)

        # Tables are frequently built from vector rectangles/lines. Exclude
        # those drawings before clustering them as diagrams.
        if drawing_overlaps_table(d_rect, valid_tables):
            continue
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
        # Skip light gray watermark fills or drawing paths belonging to watermark text (e.g. www.ixambee.com)
        fill = d.get("fill")
        color = d.get("color")
        if fill and len(fill) == 3:
            r_val, g_val, b_val = fill
            if abs(r_val - g_val) < 0.02 and abs(g_val - b_val) < 0.02 and 0.65 <= r_val <= 0.95:
                continue
        if color and len(color) == 3:
            r_val, g_val, b_val = color
            if abs(r_val - g_val) < 0.02 and abs(g_val - b_val) < 0.02 and 0.65 <= r_val <= 0.95:
                continue

        # Check if this drawing path belongs to a watermark text region (e.g. www.ixambee.com)
        is_wm_path = False
        for tb in page.get_text("dict").get("blocks", []):
            if tb.get("type", 0) == 0:
                tb_rect = fitz.Rect(tb.get("bbox", (0, 0, 0, 0)))
                inter = d_rect & tb_rect
                if not inter.is_empty:
                    for l in tb.get("lines", []):
                        txt = "".join(s.get("text", "") for s in l.get("spans", [])).strip()
                        if is_watermark_text(txt):
                            is_wm_path = True
                            break
                if is_wm_path:
                    break
        if is_wm_path:
            continue

        # Skip pink/purple background highlight bars behind text headings
        if is_pink_heading_block(r, page):
            continue

        draw_rects.append(r)

    # Cluster drawings
    diagram_clusters = []
    for r in draw_rects:
        merged = False
        for idx_c, c in enumerate(diagram_clusters):
            dx = max(0, c.x0 - r.x1, r.x0 - c.x1)
            dy = max(0, c.y0 - r.y1, r.y0 - c.y1)
            if dx < 40 and dy < 20:
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
                if dx < 40 and dy < 20:
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
        # Skip header diagrams/logos sitting in top running header zone (y1 < 80)
        if c.y1 < 80 or c.y0 > page_height - 75:
            continue
        if is_valid_vector_diagram(c, page, text_dict, valid_tables):
            # Tightly bound cluster to actual vector drawings inside c to prevent stretching over text above/below
            dr_drawings = []
            for d in page.get_drawings():
                r_d = fitz.Rect(d["rect"])
                if c.x0 - 5 <= r_d.x0 and r_d.x1 <= c.x1 + 5 and c.y0 - 5 <= r_d.y0 and r_d.y1 <= c.y1 + 5:
                    if r_d.width > page_w * 0.9 and r_d.height < 5:
                        continue
                    dr_drawings.append(r_d)
            if dr_drawings:
                tight_rect = fitz.Rect(
                    min(r.x0 for r in dr_drawings),
                    min(r.y0 for r in dr_drawings),
                    max(r.x1 for r in dr_drawings),
                    max(r.y1 for r in dr_drawings)
                )
            else:
                tight_rect = fitz.Rect(c)

            # Snap top and bottom boundary to internal text lines so text ABOVE and BELOW graphics is never cropped or deleted
            contained_lines = []
            for tb in text_dict.get("blocks", []):
                if tb.get("type", 0) == 0:
                    for line in tb.get("lines", []):
                        l_box = line.get("bbox", [0, 0, 0, 0])
                        intersect = tight_rect & fitz.Rect(l_box)
                        if not intersect.is_empty and (intersect.width * intersect.height) / max(1.0, (l_box[2]-l_box[0])*(l_box[3]-l_box[1])) > 0.4:
                            line_txt = "".join(s.get("text", "") for s in line.get("spans", [])).strip()
                            if line_txt and not is_watermark_text(line_txt):
                                contained_lines.append(l_box)

            if contained_lines:
                text_top = min(b[1] for b in contained_lines)
                text_bottom = max(b[3] for b in contained_lines)
                tight_rect.y0 = max(tight_rect.y0, text_top - 10)
                tight_rect.y1 = min(tight_rect.y1, text_bottom + 12)

            valid_diagram_rects.append(tight_rect)

    # Validated tables are authoritative. Do not delete a table merely because
    # a vector drawing happens to overlap it. Table drawings were already
    # excluded from diagram clustering above.

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
            
        for line in block.get("lines", []):
            lx0, ly0, lx1, ly1 = line["bbox"]
            lcx = (lx0 + lx1) / 2
            lcy = (ly0 + ly1) / 2
            
            # Skip lines strictly inside valid diagram images
            line_inside_diagram = False
            for dr in valid_diagram_rects:
                if dr.x0 <= lcx <= dr.x1 and dr.y0 <= lcy <= dr.y1:
                    line_inside_diagram = True
                    break
            if line_inside_diagram:
                continue

            # Skip header and footer zones (ly1 < 75 skips running headers)
            if ly1 < 75 or ly0 > page_height - 75:
                continue
                
            line_text = "".join(s.get("text", "") for s in line.get("spans", [])).strip()
            if is_watermark_text(line_text):
                continue

            # Skip standalone page number footers near bottom of page (e.g. 2, 3, 4, 5, 6, 7, 8, 9, 10, 11)
            if ly0 > page_height - 90 and line_text.isdigit():
                continue

            # Skip running headers at top of page (e.g. "ESI- RBI_2018")
            if ly1 < 95:
                norm_line = line_text.lower().replace(" ", "").replace("-", "").replace("_", "")
                if norm_line in ("esirbi2018", "rbigradeb2018", "wwwixambeecom", "ixambee"):
                    continue


            raw_lines.append(line)
            
    # 2. Consolidate lines that are on the same visual row (similar Y0)
    consolidated_lines = []
    for line in raw_lines:
        if not consolidated_lines:
            consolidated_lines.append(line)
            continue
        prev_line = consolidated_lines[-1]
        y_diff = abs(line["bbox"][1] - prev_line["bbox"][1])
        if y_diff < 5:
            # Merge spans
            prev_line["spans"] = prev_line.get("spans", []) + line.get("spans", [])
            # Update bbox
            prev_line["bbox"] = [
                min(prev_line["bbox"][0], line["bbox"][0]),
                min(prev_line["bbox"][1], line["bbox"][1]),
                max(prev_line["bbox"][2], line["bbox"][2]),
                max(prev_line["bbox"][3], line["bbox"][3])
            ]
        else:
            consolidated_lines.append(line)
    raw_lines = consolidated_lines

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
        callout_kws = ("special techniques", "important practice", "important terms")
        is_callout_title = any(kw in text_content.lower() for kw in callout_kws)
        is_heading = is_all_bold and not is_bullet and len(text_content) < 80 and not text_content.endswith(".") and not is_callout_title
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
                    if 0 <= gap < 16 and (line_x0 > last_bullet_x0 + 8 or gap < 10):
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
                line_text = "".join(decode_span_text(s) for s in line.get("spans", [])).strip()
                is_mcq_or_prefix = is_standalone_line_prefix(line_text)
                
                prev_spans = [s for s in prev_line.get("spans", []) if s.get("text", "").strip()]
                prev_text = "".join(decode_span_text(s) for s in prev_spans).strip() if prev_spans else ""
                
                sentence_completed = bool(prev_text and prev_text[-1] in (".", "?", "!", ":"))
                
                limit = 6.5
                if is_bullet or is_mcq_or_prefix:
                    limit = 5.0
                elif sentence_completed and gap >= 4.5:
                    limit = 4.5

                if gap >= limit or gap < -5:
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
        is_heading = False
        lines = sb.get("lines", [])
        if len(lines) == 1:
            spans = [s for s in lines[0].get("spans", []) if s.get("text", "").strip()]
            if spans:
                is_all_bold = all("Bold" in s.get("font", "") for s in spans)
                text_content = "".join(decode_span_text(s) for s in spans).strip()
                is_heading = is_all_bold and len(text_content) < 80 and not text_content.endswith(".")
        page_elements.append({
            "type": "text",
            "bbox": sb["bbox"],
            "data": sb,
            "is_heading": is_heading
        })
        
    # Add displayed raster images from image objects.
    # get_text("dict") does not reliably expose every displayed image;
    # get_image_info() does. Repeated XRefs are shared template/background
    # assets and are intentionally ignored.
    repeated_image_xrefs = getattr(doc, "_pdf_html_repeated_image_xrefs", set())
    seen_image_keys = set()
    try:
        image_infos = page.get_image_info(xrefs=True)
    except Exception:
        image_infos = []

    for info in image_infos:
        bbox = tuple(info.get("bbox", (0, 0, 0, 0)))
        xref = info.get("xref")
        if xref and xref in repeated_image_xrefs:
            continue
        if bbox[2] <= bbox[0] or bbox[3] <= bbox[1]:
            continue
        if (bbox[2] - bbox[0]) < 60 and (bbox[3] - bbox[1]) < 60:
            continue
        if (bbox[2] - bbox[0]) < 12 or (bbox[3] - bbox[1]) < 12:
            continue
        if bbox[3] < 80 or bbox[1] > page_height - 75:
            continue
        if image_overlaps_table(bbox, valid_tables, threshold=0.85):
            continue

        key = (xref, tuple(round(v, 2) for v in bbox))
        if key in seen_image_keys:
            continue
        seen_image_keys.add(key)

        page_elements.append({
            "type": "image",
            "bbox": bbox,
            "data": info
        })

    # Add only validated table blocks. Keep the Table object so render_table()
    # can use PyMuPDF's detected header geometry/names.
    for t in valid_tables:
        # Cache the native logical matrix while the page object is available.
        # Keep the latter script's existing table element structure unchanged.
        try:
            table_matrix = extract_table_data_accurate(t, page)
        except Exception:
            table_matrix = []
        page_elements.append({
            "type": "table",
            "bbox": t.bbox,
            "data": t,
            "custom_data_matrix": table_matrix
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
    
    # 5.2 Merge Callout Box Blocks (group callout title header + consecutive bullet list items)
    merged_elements = []
    i = 0
    callout_kws = ("special techniques", "important practice", "important terms")
    while i < len(page_elements):
        el = page_elements[i]
        if el["type"] == "text":
            lines = el["data"].get("lines", [])
            txt = "".join(decode_span_text(s) for line in lines for s in line.get("spans", []) if s.get("text", "").strip()).strip().lower()
            if any(kw in txt for kw in callout_kws):
                merged_lines = list(lines)
                j = i + 1
                while j < len(page_elements):
                    next_el = page_elements[j]
                    if next_el["type"] == "text":
                        next_lines = next_el["data"].get("lines", [])
                        next_spans = [s for line in next_lines for s in line.get("spans", []) if s.get("text", "").strip()]
                        next_txt = "".join(decode_span_text(s) for s in next_spans).strip().lower()
                        
                        # Stop merging if next block is a new major section (e.g. CITRUS, PAPAYA, BANANA, GRAPES, Diseases, etc.)
                        section_kws = ("diseases", "papaya", "citrus", "grapes", "mango", "banana", "sapota", "litchi", "guava", "disorders", "insect- pests")
                        if any(next_txt.startswith(kw) or next_txt == kw for kw in section_kws):
                            break

                        gap = next_el["bbox"][1] - el["bbox"][3]
                        if gap < 40:
                            merged_lines.extend(next_lines)
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
                continue
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
            custom_mat = element.get("custom_data_matrix")
            table_html = render_table(element["data"], page, custom_matrix=custom_mat)
            if table_html and table_html.strip():
                elements_html.append(table_html)
            else:
                # Fallback: preserve visual table region as an image so structure is never destroyed
                bbox = element["bbox"]
                clip_rect = fitz.Rect(bbox)
                if clip_rect.width > 0 and clip_rect.height > 0:
                    try:
                        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), clip=clip_rect)
                        img_bytes = pix.tobytes("png")
                        if images_dir:
                            img_filename = f"page_{page.number + 1}_tbl_{image_counter}.png"
                            (images_dir / img_filename).write_bytes(img_bytes)
                            image_counter += 1
                            img_tag = f'<img src="images/{img_filename}" alt="Table" />'
                        else:
                            b64 = base64.b64encode(img_bytes).decode("ascii")
                            img_tag = f'<img src="data:image/png;base64,{b64}" alt="Table" />'
                        elements_html.append(f'<figure>{img_tag}</figure>')
                    except Exception as e:
                        print(f"Error rendering table image fallback: {e}", file=sys.stderr)
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

    # Check if page 1 is a cover page vs content page
    body_size = compute_body_size(doc)
    has_cover = is_cover_page(doc[0], body_size)

    # If no cover page exists, extract running header title from top of page 1 or page 2
    if not has_cover:
        for p_idx in [0, 1]:
            if p_idx < len(doc):
                p = doc[p_idx]
                text_dict = p.get_text("dict")
                for b in text_dict.get("blocks", []):
                    if b.get("type") == 0:
                        for l in b.get("lines", []):
                            y1 = l.get("bbox", [0, 0, 0, 0])[3]
                            if y1 < 120:  # Top running header region
                                line_text = "".join(decode_span_text(s) for s in l.get("spans", [])).strip()
                                norm = line_text.lower().replace(" ", "")
                                if norm and norm not in ("www.ixambee.com", "ixambee", "prepare50%faster", "studynotes"):
                                    cleaned_title = re.sub(r'\s+\d+$', '', line_text).strip()
                                    if len(cleaned_title) > 3:
                                        return cleaned_title

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
        text = decode_span_text(s).strip()
        if text and text.lower() not in ["study notes", "studynotes"]:
            non_generic_spans.append(s)
            
    if not non_generic_spans:
        return decode_span_text(spans[0]).strip() if spans else "Document"
        
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
        t = decode_span_text(s).strip()
        if t and t not in title_parts:
            title_parts.append(t)
            
    if title_parts:
        return " ".join(title_parts)

    return Path(doc.name).stem

        
    return "Document"

def _is_minor_page_start_element(el: dict) -> bool:
    """True for small leading elements (running title, logo, page banner)
    that can sit between a page break and a table continuation without
    breaking the continuation. Deliberately conservative: real body
    paragraphs or large graphics return False so we never accidentally
    merge two genuinely different tables.
    """
    if el["type"] == "image":
        bbox = el["bbox"]
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        return w < 220 and h < 120
    if el["type"] == "text":
        lines = el["data"].get("lines", [])
        text = "".join(
            decode_span_text(s)
            for l in lines
            for s in l.get("spans", [])
            if s.get("text", "").strip()
        ).strip()
        return len(text) < 90
    return False


def _table_col_count(matrix: list) -> int:
    """Return the logical column count of a table matrix."""
    if not matrix:
        return 0
    return max((len(row) for row in matrix), default=0)


def _row_signature(row: list) -> set:
    """Return normalized non-empty cell text used to detect repeated headers."""
    return {
        _table_cell_text(c).strip().lower()
        for c in row
        if _table_cell_text(c).strip()
    }


def _merge_table_matrices(prev_matrix: list, next_matrix: list) -> list:
    """Pad both matrices to a common column count and stack them.

    If the continuation's first row duplicates the original header row text,
    drop that repeated header instead of appending it as a data row.
    """
    if not next_matrix:
        return prev_matrix

    next_matrix = list(next_matrix)
    if prev_matrix and next_matrix:
        prev_header_sig = _row_signature(prev_matrix[0])
        next_first_sig = _row_signature(next_matrix[0])
        if prev_header_sig and next_first_sig:
            overlap = len(prev_header_sig & next_first_sig)
            if overlap >= max(1, len(next_first_sig) * 0.5):
                next_matrix = next_matrix[1:]

    if not next_matrix:
        return prev_matrix

    ncols = max(_table_col_count(prev_matrix), _table_col_count(next_matrix))

    def pad(matrix):
        return [list(row) + [None] * (ncols - len(row)) for row in matrix]

    return pad(prev_matrix) + pad(next_matrix)


def _is_minor_page_start_element(el: dict) -> bool:
    """True for small leading elements (running title, logo, page banner)
    that can sit between a page break and a table continuation without
    breaking the continuation.
    """
    if el["type"] == "image":
        bbox = el["bbox"]
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        return w < 220 and h < 120
    if el["type"] == "text":
        lines = el["data"].get("lines", [])
        text = "".join(
            decode_span_text(s)
            for l in lines
            for s in l.get("spans", [])
            if s.get("text", "").strip()
        ).strip()
        return len(text) < 90
    return False


def _table_col_count(matrix: list) -> int:
    if not matrix:
        return 0
    return max((len(row) for row in matrix), default=0)


def _row_signature(row: list) -> set:
    return {
        _table_cell_text(c).strip().lower()
        for c in row
        if _table_cell_text(c).strip()
    }


def _merge_table_matrices(prev_matrix: list, next_matrix: list) -> list:
    """Pad both matrices to a common column count and stack them.

    If the continuation's first row duplicates the original header row text,
    drop that repeated header instead of appending it as a data row.
    """
    if not next_matrix:
        return prev_matrix

    next_matrix = list(next_matrix)
    if prev_matrix and next_matrix:
        prev_header_sig = _row_signature(prev_matrix[0])
        next_first_sig = _row_signature(next_matrix[0])
        if prev_header_sig and next_first_sig:
            overlap = len(prev_header_sig & next_first_sig)
            if overlap >= max(1, len(next_first_sig) * 0.5):
                next_matrix = next_matrix[1:]

    if not next_matrix:
        return prev_matrix

    ncols = max(_table_col_count(prev_matrix), _table_col_count(next_matrix))

    def pad(matrix):
        return [list(row) + [None] * (ncols - len(row)) for row in matrix]

    return pad(prev_matrix) + pad(next_matrix)


def merge_split_pages(all_pages_elements: list) -> None:
    for idx in range(len(all_pages_elements) - 1):
        prev_elements = all_pages_elements[idx]
        next_elements = all_pages_elements[idx + 1]
        if not prev_elements or not next_elements:
            continue

        # 1. Multi-page table continuation across page breaks
        if prev_elements and prev_elements[-1]["type"] == "table":
            insert_idx = None
            for j, el in enumerate(next_elements):
                if el["type"] == "table":
                    insert_idx = j
                    break
                if not _is_minor_page_start_element(el):
                    break

            if insert_idx is not None:
                prev_table_el = prev_elements[-1]
                next_table_el = next_elements[insert_idx]

                prev_matrix = prev_table_el.get("custom_data_matrix") or prev_table_el.get("matrix") or []
                next_matrix = next_table_el.get("custom_data_matrix") or next_table_el.get("matrix") or []

                prev_cols = _table_col_count(prev_matrix)
                next_cols = _table_col_count(next_matrix)

                if (
                    prev_cols >= 2
                    and next_cols >= 2
                    and abs(prev_cols - next_cols) <= 1
                    and len(prev_matrix) >= 1
                ):
                    merged_matrix = _merge_table_matrices(prev_matrix, next_matrix)
                    prev_table_el["custom_data_matrix"] = merged_matrix

                    prev_table_el["bbox"] = [
                        min(prev_table_el["bbox"][0], next_table_el["bbox"][0]),
                        prev_table_el["bbox"][1],
                        max(prev_table_el["bbox"][2], next_table_el["bbox"][2]),
                        next_table_el["bbox"][3],
                    ]

                    del next_elements[: insert_idx + 1]

        # 2. Multi-page text paragraph continuation check across page break
        if prev_elements and next_elements:
            el_prev = prev_elements[-1]
            el_next = next_elements[0]

            if el_prev["type"] == "text" and el_next["type"] == "text":
                if not el_prev.get("is_heading") and not el_next.get("is_heading"):
                    lines_prev = el_prev["data"].get("lines", [])
                    lines_next = el_next["data"].get("lines", [])

                    if lines_prev and lines_next:
                        last_line = lines_prev[-1]
                        last_spans = [s for s in last_line.get("spans", []) if s.get("text", "").strip()]
                        first_line = lines_next[0]
                        first_spans = [s for s in first_line.get("spans", []) if s.get("text", "").strip()]

                        if last_spans and first_spans and not is_bullet_span(first_spans[0]):
                            last_text = "".join(decode_span_text(s) for s in last_spans).strip()
                            if last_text and not last_text[-1] in (".", "?", "!", ":", ";", "”", '"'):
                                if last_text.endswith("-") and len(last_text) > 2:
                                    for s in reversed(last_spans):
                                        if s.get("text", "").endswith("-"):
                                            s["text"] = s["text"][:-1]
                                            break

                                lines_prev.extend(lines_next)
                                el_prev["data"]["lines"] = lines_prev
                                el_prev["bbox"] = [
                                    min(el_prev["bbox"][0], el_next["bbox"][0]),
                                    min(el_prev["bbox"][1], el_next["bbox"][1]),
                                    max(el_prev["bbox"][2], el_next["bbox"][2]),
                                    max(el_prev["bbox"][3], el_next["bbox"][3])
                                ]
                                next_elements.pop(0)

def post_process_worksheet_html(raw_html: str) -> str:
    lines = raw_html.split("\n")
    out_lines = []
    in_mcq = False
    in_q_section = False
    in_exp_card = False
    in_box_card = False      # NEW: tracks open .pdf-box-card divs
    opt_index = 0

    labels = ["A.", "B.", "C.", "D.", "E.", "F.", "G."]

    # Regex: matches "Box 1 – ..." / "Box 2: ..." / "Box-3 — ..." inside any tags
    _RE_BOX = re.compile(
        r'Box\s*[-–—]?\s*\d+\s*[-–—:]\s*(.+)',
        re.IGNORECASE
    )

    num_lines = len(lines)
    for idx in range(num_lines):
        line = lines[idx]
        stripped = line.strip()

        # ── Step 0: Detect "Box N – Title" heading ──────────────────────────
        # Matches e.g.  <p><strong>Box 1 – NBFC-P2P in India – as of June 30, 2019 </strong></p>
        clean_for_box = re.sub(r'<[^>]+>', '', stripped).strip()
        m_box = _RE_BOX.match(clean_for_box)
        if m_box:
            # Close any open card/section first
            if in_mcq:
                out_lines.append('</ul></div>')
                in_mcq = False
                in_q_section = False
            elif in_q_section:
                out_lines.append('</div>')
                in_q_section = False
            elif in_exp_card:
                out_lines.append('</div>')
                in_exp_card = False
            if in_box_card:
                out_lines.append('</div>')
                in_box_card = False

            # Full text of the box title (everything after "Box N –")
            box_title = re.sub(r'<[^>]+>', '', stripped).strip()
            out_lines.append(f'<div class="pdf-box-card"><h4 class="box-title">{box_title}</h4>')
            in_box_card = True
            opt_index = 0
            continue

        # Close box card on section boundary
        if in_box_card and (stripped == '</section>' or stripped.startswith('<section')):
            out_lines.append('</div>')
            in_box_card = False

        # 1. Fix Leaked Option E + Question Prompt (e.g. "<li>1.4 9. Which...", "Coimbattore 15. __ was...")
        m_leak = re.match(r'^(?:<li>|<p>)?\s*([A-Za-z0-9\.\,\s\-\%\/\(\)]+?)\s+(\d{1,3}\.\s+[A-Z_].*)', stripped)
        if m_leak and not re.match(r'^(?:Q(?:ues)?\.?\s*\d+|\d{1,3}\.)\s+', stripped):
            e_val = m_leak.group(1).strip()
            q_prompt = m_leak.group(2).strip()
            if in_mcq:
                lbl = labels[opt_index % len(labels)] if opt_index < len(labels) else "E."
                is_bold_opt = bool(re.search(r'<strong>|<b>', e_val, re.IGNORECASE))
                li_cls = ' class="correct-option"' if is_bold_opt else ''
                out_lines.append(f'<li{li_cls}><span class="opt-label">{lbl}</span> <span class="opt-text">{e_val}</span></li>')
                out_lines.append('</ul></div>')
                in_mcq = False
                in_q_section = False
                opt_index = 0
            
            m_num = re.match(r'^((?:Q(?:ues)?\.?\s*\d+|\d{1,3}\.))\s*(.*)', q_prompt)
            if m_num:
                qn = m_num.group(1).strip()
                qt = m_num.group(2).strip()
                out_lines.append(f'<div class="question-section"><p class="q-header"><span class="q-num">{qn}</span> <span class="q-text">{qt}</span></p>')
            else:
                out_lines.append(f'<div class="question-section"><p class="q-header"><span class="q-text">{q_prompt}</span></p>')
            in_q_section = True
            opt_index = 0
            continue


        clean_text = re.sub(r'<[^>]+>', '', stripped).strip()

        clean_text = re.sub(r'<[^>]+>', '', stripped).strip()

        # 2. Check if Question Prompt e.g. "Q.1", "Question 5:", "Q12."
        m_q = re.match(r'^(?:Q(?:ues)?\.?\s*\d+|\d{1,3}\.)\s+[A-Z]', clean_text)
        is_actual_q = False
        if m_q:
            # Must explicitly start with Q / Question / प्रश् / प्रश्न
            if re.match(r'^(?:Q(?:ues)?\.?\s*\d+|Question\b|प्रश्|प्रश्न)\b', clean_text, re.IGNORECASE):
                is_actual_q = True
            else:
                # If it's a plain number (e.g. "1."), look ahead up to 6 lines for explicit MCQ options e.g. (A) or A.
                for lookahead_idx in range(idx + 1, min(idx + 7, num_lines)):
                    lookahead_line = lines[lookahead_idx].strip()
                    lookahead_clean = re.sub(r'<[^>]+>', '', lookahead_line).strip()
                    if re.match(r'^(?:<li>|<p>)?\s*(?:<strong>|<b>)?\s*\(?([A-Ea-e])\)?\s*[\.\)]\s+[A-Za-z0-9]', lookahead_line, re.IGNORECASE):
                        is_actual_q = True
                        break
                    # Stop if we hit a section boundary or another heading
                    if re.match(r'^<h[1-4]\b', lookahead_line, re.IGNORECASE) or re.match(r'^(?:Q(?:ues)?\.?\s*\d+|\d{1,3}\.)\s+[A-Z]', lookahead_clean):
                        break

        if is_actual_q:
            if in_mcq:
                out_lines.append('</ul></div>')
                in_mcq = False
                in_q_section = False
            elif in_q_section:
                out_lines.append('</div>')
                in_q_section = False
            elif in_exp_card:
                out_lines.append('</div>')
                in_exp_card = False

            m_num = re.match(r'^((?:Q(?:ues)?\.?\s*\d+|\d{1,3}\.))\s*(.*)', clean_text)
            if m_num:
                qn = m_num.group(1).strip()
                qt = m_num.group(2).strip()
                out_lines.append(f'<div class="question-section"><p class="q-header"><span class="q-num">{qn}</span> <span class="q-text">{qt}</span></p>')
            else:
                out_lines.append(f'<div class="question-section"><p class="q-header"><span class="q-text">{clean_text}</span></p>')
            in_q_section = True
            opt_index = 0
            continue

        # 3. Check if Explanation heading
        if re.match(r'^(Explanation|Solution)\b', clean_text, re.IGNORECASE):
            if in_mcq:
                out_lines.append('</ul></div>')
                in_mcq = False
                in_q_section = False
            elif in_q_section:
                out_lines.append('</div>')
                in_q_section = False
            elif in_exp_card:
                out_lines.append('</div>')
                in_exp_card = False

            out_lines.append(f'<div class="explanation-card"><p class="explanation-title">{clean_text}</p>')
            in_exp_card = True
            opt_index = 0
            continue

        # 4. Handle List opening in Question Section
        if in_q_section and (stripped.startswith('<ul') or stripped == '<ul>'):
            if not in_mcq:
                out_lines.append('<ul class="mcq-options-list">')
                in_mcq = True
                opt_index = 0
            continue

        # 5. Handle List closing in Question Section
        if in_q_section and stripped == '</ul>' and in_mcq:
            out_lines.append('</ul>')
            in_mcq = False
            continue

        # 6. Check if explicit MCQ Option inside Question Section
        m_lbl = re.match(r'^(?:<li>|<p>)?\s*(?:<strong>|<b>)?\s*([A-Ea-e][\.\)]|\([A-Ea-e]\))\s*(.*)', stripped)
        if not m_lbl:
            m_lbl = re.match(r'^([A-Ea-e][\.\)]|\([A-Ea-e]\))\s*(.*)', clean_text)

        is_explicit_opt = bool(m_lbl and len(m_lbl.group(1)) <= 4)
        is_list_item = stripped.startswith('<li>')

        # If in question section but before option list started, and text does NOT start with explicit A. B. C. D. E.:
        # Join it as continuation of the question text!
        if in_q_section and not in_mcq and not is_explicit_opt and not is_list_item and not stripped.startswith('<ul'):
            if out_lines and 'class="q-text"' in out_lines[-1]:
                out_lines[-1] = re.sub(r'</span>\s*</p>$', f' {clean_text}</span></p>', out_lines[-1])
                continue

        # Only transform into MCQ option li if it is an explicit option (A., B., C., D.) or inside an active MCQ list
        if in_q_section and is_explicit_opt:
            is_bold_opt = bool(re.search(r'<strong>|<b>', stripped, re.IGNORECASE))
            lbl = m_lbl.group(1).strip()
            txt = m_lbl.group(2).strip()

            txt_clean = re.sub(r'</?(?:p|li|span)[^>]*>', '', txt, flags=re.IGNORECASE).strip()
            txt_clean = re.sub(r'^\s*<strong>\s*', '<strong>', txt_clean)
            txt_clean = re.sub(r'\s*</strong>\s*$', '</strong>', txt_clean)

            if is_bold_opt and not txt_clean.startswith('<strong>'):
                txt_clean = f'<strong>{txt_clean}</strong>'

            if not in_mcq:
                out_lines.append('<ul class="mcq-options-list">')
                in_mcq = True

            li_cls = ' class="correct-option"' if is_bold_opt else ''
            out_lines.append(f'<li{li_cls}><span class="opt-label">{lbl}</span> <span class="opt-text">{txt_clean}</span></li>')
            opt_index += 1
            continue



        # 7. Boundary reset
        if stripped == '</section>' or stripped.startswith('<section'):
            if in_mcq:
                out_lines.append('</ul>')
                in_mcq = False
            elif in_exp_card:
                out_lines.append('</div>')
                in_exp_card = False
            out_lines.append(line)
            continue

        out_lines.append(line)

    if in_mcq:
        out_lines.append('</ul></div>')
    elif in_q_section or in_exp_card:
        out_lines.append('</div>')
    if in_box_card:
        out_lines.append('</div>')

    return "\n".join(out_lines)


def convert(pdf_path: Path, html_path: Path, start: int = None, end: int = None) -> None:
    doc = fitz.open(pdf_path)
    try:
        page_count = doc.page_count
        
        # Auto-extract title from the first page of the PDF
        pdf_title = extract_pdf_title(doc)
        
        body_size = compute_body_size(doc)

        # Cache shared/repeated image XRefs once per document.
        doc._pdf_html_repeated_image_xrefs = get_repeated_image_xrefs(doc)
        
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

        full_html = DOC_TEMPLATE.format(
            title=html.escape(pdf_title),
            pages="\n".join(pages_html),
        )
        full_html = post_process_worksheet_html(full_html)

        html_path.write_text(full_html, encoding="utf-8")
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
    
    # If the input looks like a numeric MySQL ID, try to resolve it from queue or archive
    if str(pdf_path).isdigit():
        mysql_id = int(str(pdf_path))
        queue_pdf = Path(__file__).parent.parent / "storage" / "queue" / str(mysql_id) / "document.pdf"
        archive_pdf = Path(__file__).parent.parent / "storage" / "archive" / str(mysql_id) / "document.pdf"
        if queue_pdf.exists():
            pdf_path = queue_pdf
            if args.html is None:
                args.html = Path(__file__).parent.parent / "storage" / "queue" / str(mysql_id) / "document.html"
        elif archive_pdf.exists():
            pdf_path = archive_pdf
            if args.html is None:
                args.html = Path(__file__).parent.parent / "storage" / "archive" / str(mysql_id) / "document.html"

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