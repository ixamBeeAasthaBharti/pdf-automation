from pathlib import Path
import json
from bs4 import BeautifulSoup

ROOT = Path(__file__).parent.parent

INPUT_DIR = ROOT / "input"

html_files = list(INPUT_DIR.glob("*.html"))

if len(html_files) != 1:
    raise RuntimeError(
        f"Expected exactly one HTML in {INPUT_DIR}, found {len(html_files)}"
    )

INPUT_HTML = html_files[0]
OUTPUT_HTML = ROOT / "temp" / "preprocessed.html"
IMAGE_MAP = ROOT / "image_map.json"

# --------------------------------------------------

html = INPUT_HTML.read_text(encoding="utf-8")

soup = BeautifulSoup(html, "html.parser")

mapping = json.loads(IMAGE_MAP.read_text(encoding="utf-8"))

images = soup.find_all("img")

print(f"Found {len(images)} HTML images")
print(f"Found {len(mapping)} extracted images")

image_index = 0

for img in images:

    src = img.get("src", "")

    # Skip logos
    if "logo" in src.lower():
        continue

    # Replace only base64 images
    if src.startswith("data:image"):

        if image_index >= len(mapping):
            break

        current = mapping[image_index]

        img["src"] = f"images/{current['filename']}"
        img["data-id"] = current["id"]

        image_index += 1

OUTPUT_HTML.parent.mkdir(exist_ok=True)

OUTPUT_HTML.write_text(
    soup.prettify(),
    encoding="utf-8",
)

print(f"\nInserted {image_index} images")
print(f"Saved to\n{OUTPUT_HTML}")