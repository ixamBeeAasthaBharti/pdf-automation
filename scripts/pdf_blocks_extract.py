from pathlib import Path
import fitz
import json

ROOT = Path(__file__).parent.parent

TEMP = ROOT / "temp"
TEMP.mkdir(exist_ok=True)

# Delete previous extracted images
for f in TEMP.glob("page_*"):
    f.unlink()

pdf = list((ROOT / "input").glob("*.pdf"))[0]

image_map = []

doc = fitz.open(pdf)

image_count = 0

for page_number, page in enumerate(doc):

    print(f"\nPage {page_number + 1}")

    blocks = page.get_text("dict")["blocks"]

    for block in blocks:

        if block["type"] != 1:
            continue

        # Skip the cover page
        if page_number == 0:
            continue

        x0, y0, x1, y1 = block["bbox"]

        width = x1 - x0
        height = y1 - y0

        # Skip header logos
        if (
            y0 < 80          # near the top
            and width < 150  # small
            and height < 80
        ):
            print("Skipped logo")
            continue

        ext = block.get("ext", "png")

        output = (
            ROOT
            / "temp"
            / f"page_{page_number+1:03d}_img_{image_count:03d}.{ext}"
        )

        output.write_bytes(block["image"])
        image_map.append({
            "id": f"IMAGE_{image_count:03d}",
            "page": page_number + 1,
            "filename": output.name,
            "bbox": [x0, y0, x1, y1],
        })

        print(f"Saved {output.name}")

        image_count += 1

(ROOT / "image_map.json").write_text(
    json.dumps(image_map, indent=4),
    encoding="utf-8",
)

print(f"\nTotal images extracted: {image_count}")