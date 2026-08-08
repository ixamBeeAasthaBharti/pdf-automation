from pathlib import Path
import json

from bs4 import BeautifulSoup

# =====================================================
# PATHS
# =====================================================

ROOT = Path(__file__).parent.parent

INPUT_DIR = ROOT / "input"

html_files = list(INPUT_DIR.glob("*.html"))

if len(html_files) != 1:
    raise RuntimeError(
        f"Expected exactly one HTML file in {INPUT_DIR}, "
        f"found {len(html_files)}."
    )

INPUT_HTML = html_files[0]

IMAGE_MAP = ROOT / "image_map.json"

OUTPUT_HTML = ROOT / "temp" / "preprocessed.html"


def reconstruct_html():

    html = INPUT_HTML.read_text(encoding="utf-8")

    soup = BeautifulSoup(html, "lxml")

    image_map = json.loads(
        IMAGE_MAP.read_text(encoding="utf-8")
    )

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

        if page_number >= len(pages):
            continue

        page = pages[page_number]

        # Find the container holding the absolute positioned elements (like pdf24_01 divs)
        first_text_div = page.find(lambda tag: tag.name == "div" and tag.get("style") and "top:" in tag.get("style"))
        if first_text_div:
            parent_container = first_text_div.parent
        else:
            parent_container = page.find("div", class_="pdf24_view")

        if parent_container is None:
            continue

        x0, y0, x1, y1 = image["bbox"]

        left_em = x0 / 12
        top = y0 / 12

        width_em = (x1 - x0) / 12
        height_em = (y1 - y0) / 12

        # Convert PDF points → CSS pixels (96 px/in ÷ 72 pt/in = 4/3)
        PT_TO_PX = 96 / 72
        width_px = round((x1 - x0) * PT_TO_PX)
        height_px = round((y1 - y0) * PT_TO_PX)

        img = soup.new_tag("img")

        img["src"] = f"../images/{image['filename']}"

        img["data-id"] = image["id"]

        img["class"] = "pdf24_figure"

        # width/height attributes ensure the image renders at its correct
        # PDF size even after Gemini converts the layout to semantic HTML
        img["width"] = width_px
        img["height"] = height_px

        img["style"] = (
            f"position:absolute;"
            f"left:{left_em:.4f}em;"
            f"top:{top:.4f}em;"
            f"width:{width_em:.4f}em;"
            f"height:{height_em:.4f}em;"
        )

        parent_container.append(img)

    # Sort all absolute-positioned elements (divs and imgs) on each page by 'top' coordinate
    import re

    def get_top_coord(elem):
        if elem.name is None:
            return 0.0
        style = elem.get("style", "")
        match = re.search(r"top:\s*([\d.]+)\s*em", style)
        if match:
            return float(match.group(1))
        return 0.0

    for page in pages:
        first_text_div = page.find(lambda tag: tag.name == "div" and tag.get("style") and "top:" in tag.get("style"))
        if first_text_div:
            parent_container = first_text_div.parent
        else:
            parent_container = page.find("div", class_="pdf24_view")

        if parent_container:
            # Extract all element children (ignoring whitespace text nodes)
            children = [c for c in parent_container.children if c.name is not None]
            # Sort them by their top coordinate
            children.sort(key=get_top_coord)
            # Clear container and re-append in sorted order
            parent_container.clear()
            for child in children:
                parent_container.append(child)

    print(f"Pages found : {len(soup.find_all(id=lambda x: x and x.startswith('page_')))}")
    print(f"Images found: {len(image_map)}")


    OUTPUT_HTML.parent.mkdir(exist_ok=True)

    OUTPUT_HTML.write_text(
        soup.prettify(),
        encoding="utf-8",
    )

    print(f"\nSaved to:\n{OUTPUT_HTML}")


if __name__ == "__main__":
    reconstruct_html()