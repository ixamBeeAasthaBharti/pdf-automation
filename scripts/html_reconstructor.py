from pathlib import Path
import json
import re

from bs4 import BeautifulSoup

# =====================================================
# PATHS  (legacy defaults — used when called standalone)
# =====================================================

ROOT = Path(__file__).parent.parent

_DEFAULT_INPUT_DIR  = ROOT / "input"
_DEFAULT_IMAGE_MAP  = ROOT / "image_map.json"
_DEFAULT_OUTPUT_HTML = ROOT / "temp" / "preprocessed.html"


def reconstruct_html(
    input_html: Path = None,
    image_map_path: Path = None,
    output_html: Path = None,
    skip_cover: bool = False,
):
    """
    Reconstruct the PDF24 HTML by inserting extracted image tags at the
    correct positions, based on image_map.json.

    Parameters (all optional — falls back to legacy global paths):
        input_html     : Path to the PDF24-converted HTML file
        image_map_path : Path to image_map.json produced by pymupdf_image_extractor
        output_html    : Path where the reconstructed HTML will be written
        skip_cover     : If True, skips page 1 from image insertion and decomposes page 1.
    """
    # ------------------------------------------------------------------ #
    # Resolve paths                                                         #
    # ------------------------------------------------------------------ #
    if input_html is None:
        html_files = list(_DEFAULT_INPUT_DIR.glob("*.html"))
        if len(html_files) != 1:
            raise RuntimeError(
                f"Expected exactly one HTML file in {_DEFAULT_INPUT_DIR}, "
                f"found {len(html_files)}."
            )
        input_html = html_files[0]

    if image_map_path is None:
        image_map_path = _DEFAULT_IMAGE_MAP

    if output_html is None:
        output_html = _DEFAULT_OUTPUT_HTML

    input_html     = Path(input_html)
    image_map_path = Path(image_map_path)
    output_html    = Path(output_html)

    # ------------------------------------------------------------------ #
    # Read inputs                                                           #
    # ------------------------------------------------------------------ #
    html = input_html.read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "lxml")

    image_map = json.loads(image_map_path.read_text(encoding="utf-8")) if image_map_path.exists() else []

    pages = soup.find_all(
        "div",
        id=lambda x: x and x.startswith("page_")
    )

    for page in pages:
        screenshot = page.find("div", class_="pdf24_03")
        if screenshot:
            screenshot.decompose()

    # =====================================================
    # Insert extracted figures
    # =====================================================

    for image in image_map:

        page_number = image["page"] - 1

        if skip_cover and page_number == 0:
            continue

        if page_number >= len(pages):
            continue

        page = pages[page_number]

        first_text_div = page.find(lambda tag: tag.name == "div" and tag.get("style") and "top:" in tag.get("style"))
        if first_text_div:
            parent_container = first_text_div.parent
        else:
            parent_container = page.find("div", class_="pdf24_view")

        if parent_container is None:
            continue

        x0, y0, x1, y1 = image["bbox"]

        left_em   = x0 / 12
        top       = y0 / 12
        width_em  = (x1 - x0) / 12
        height_em = (y1 - y0) / 12

        PT_TO_PX  = 96 / 72
        width_px  = round((x1 - x0) * PT_TO_PX)
        height_px = round((y1 - y0) * PT_TO_PX)

        img = soup.new_tag("img")
        img["src"]     = f"../images/{image['filename']}"
        img["data-id"] = image["id"]
        img["class"]   = "pdf24_figure"
        img["width"]   = width_px
        img["height"]  = height_px
        img["style"]   = (
            f"position:absolute;"
            f"left:{left_em:.4f}em;"
            f"top:{top:.4f}em;"
            f"width:{width_em:.4f}em;"
            f"height:{height_em:.4f}em;"
        )

        parent_container.append(img)

    # Sort all absolute-positioned elements by row (top coordinate rounded) and column (left coordinate)
    def get_style_coord(elem, name):
        if elem.name is None:
            return 0.0
        style = elem.get("style", "")
        match = re.search(rf"{name}:\s*([\d.]+)\s*em", style)
        return float(match.group(1)) if match else 0.0

    for page in pages:
        first_text_div = page.find(lambda tag: tag.name == "div" and tag.get("style") and "top:" in tag.get("style"))
        if first_text_div:
            parent_container = first_text_div.parent
        else:
            parent_container = page.find("div", class_="pdf24_view")

        if parent_container:
            children = [c for c in parent_container.children if c.name is not None]
            children.sort(key=lambda c: (round(get_style_coord(c, "top"), 1), get_style_coord(c, "left")))
            parent_container.clear()
            for child in children:
                parent_container.append(child)

    # Extract cover title before decomposing
    cover_title = ""
    cover_subtitle = ""
    if skip_cover and len(pages) > 0:
        # Find all text divs on page 1
        text_divs = pages[0].find_all(lambda tag: tag.name == "div" and tag.get("style") and "font-size" in tag.get("style"))
        # Sort text divs by font size descending to find the largest text (title)
        def get_font_size(div):
            style = div.get("style", "")
            match = re.search(r"font-size:\s*([\d.]+)\s*(px|em|pt)", style)
            if match:
                val = float(match.group(1))
                if match.group(2) == "em":
                    val = val * 12
                return val
            return 0.0
            
        sorted_divs = sorted(text_divs, key=get_font_size, reverse=True)
        
        # Filter out empty text and generic labels
        title_candidates = []
        for div in sorted_divs:
            txt = div.get_text(" ", strip=True)
            if txt and txt not in title_candidates:
                if txt.lower() not in ("study notes", "quick recap", "exambee") and not re.match(r'^\d+$', txt):
                    title_candidates.append(txt)
        
        if title_candidates:
            cover_title = title_candidates[0]
            if len(title_candidates) > 1:
                cover_subtitle = title_candidates[1]
                
        # Save to temp directory
        temp_dir = output_html.parent
        temp_dir.mkdir(parents=True, exist_ok=True)
        cover_info_path = temp_dir / "cover_info.json"
        cover_info_path.write_text(json.dumps({
            "title": cover_title,
            "subtitle": cover_subtitle
        }, indent=4), encoding="utf-8")

        print(f"[html_reconstructor] Extracted cover page title: '{cover_title}'")
        print("[html_reconstructor] Decomposing cover page (Page 1) from the HTML DOM.")
        pages[0].decompose()

    print(f"Pages found : {len(soup.find_all(id=lambda x: x and x.startswith('page_')))}")
    print(f"Images found: {len(image_map)}")

    output_html.parent.mkdir(parents=True, exist_ok=True)
    output_html.write_text(soup.prettify(), encoding="utf-8")

    print(f"\nSaved to:\n{output_html}")


if __name__ == "__main__":
    reconstruct_html()