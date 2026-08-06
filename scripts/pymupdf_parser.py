from pathlib import Path
import fitz
import json
from bs4 import BeautifulSoup

# =====================================================
# PATHS
# =====================================================

ROOT = Path(__file__).parent.parent

INPUT_DIR = ROOT / "input"
TEMP_DIR = ROOT / "temp"
IMAGE_DIR = ROOT / "images"

TEMP_DIR.mkdir(exist_ok=True)
IMAGE_DIR.mkdir(exist_ok=True)

# Clear previous images
for f in IMAGE_DIR.glob("*"):
    f.unlink()

PDF = list(INPUT_DIR.glob("*.pdf"))[0]

# =====================================================
# PARSE PDF
# =====================================================

doc = fitz.open(PDF)

body = []
image_map = []

image_count = 0

for page_number, page in enumerate(doc):

    print(f"Processing page {page_number + 1}")

    blocks = page.get_text("dict")["blocks"]

    for block in blocks:

        # -------------------------------------------------
        # TEXT BLOCK
        # -------------------------------------------------

        if block["type"] == 0:

            text = ""

            for line in block.get("lines", []):

                for span in line.get("spans", []):

                    text += span["text"]

                text += " "

            text = text.strip()

            if text:
                body.append(f"<p>{text}</p>")

        # -------------------------------------------------
        # IMAGE BLOCK
        # -------------------------------------------------

        elif block["type"] == 1:

            # Ignore images on the cover page
            if page_number == 0:
                continue

            x0, y0, x1, y1 = block["bbox"]

            width = x1 - x0
            height = y1 - y0

            # Ignore small logo in header
            if (
                y0 < 80
                and width < 150
                and height < 80
            ):
                continue

            ext = block.get("ext", "png")

            filename = (
                f"page_{page_number+1:03d}_img_{image_count:03d}.{ext}"
            )

            (IMAGE_DIR / filename).write_bytes(
                block["image"]
            )

            image_id = f"IMAGE_{image_count:03d}"

            image_map.append({
                "id": image_id,
                "page": page_number + 1,
                "filename": filename,
                "bbox": [x0, y0, x1, y1],
            })

            body.append(
                f'<img src="images/{filename}" data-id="{image_id}">'
            )

            image_count += 1

# =====================================================
# SAVE IMAGE MAP
# =====================================================

(ROOT / "image_map.json").write_text(
    json.dumps(image_map, indent=4),
    encoding="utf-8",
)

# =====================================================
# BUILD HTML
# =====================================================

soup = BeautifulSoup(
    "<!DOCTYPE html><html><body></body></html>",
    "html.parser",
)

for item in body:

    soup.body.append(
        BeautifulSoup(item, "html.parser")
    )

(TEMP_DIR / "preprocessed.html").write_text(
    soup.prettify(),
    encoding="utf-8",
)

print("\n====================================")
print("Parsing Complete")
print(f"Pages  : {len(doc)}")
print(f"Images : {image_count}")
print(f"Output : {TEMP_DIR / 'preprocessed.html'}")
print("====================================")