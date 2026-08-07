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

        pdf24_view = page.find("div", class_="pdf24_view")

        if pdf24_view is None:
            continue

        x0, y0, x1, y1 = image["bbox"]

        left = x0 / 12
        top = y0 / 12

        width = (x1 - x0) / 12
        height = (y1 - y0) / 12

        img = soup.new_tag("img")

        img["src"] = f"../images/{image['filename']}"

        img["data-id"] = image["id"]

        img["class"] = "pdf24_figure"

        img["style"] = (
            f"position:absolute;"
            f"left:{left}em;"
            f"top:{top}em;"
            f"width:{width}em;"
            f"height:{height}em;"
        )

        pdf24_view.append(img)

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