from pathlib import Path
import fitz
import json

# =====================================================
# PATHS
# =====================================================

ROOT = Path(__file__).parent.parent

INPUT_DIR = ROOT / "input"
IMAGE_DIR = ROOT / "images"

IMAGE_DIR.mkdir(exist_ok=True)


def extract_images():

    # -------------------------------------------------
    # Cleanup previous images
    # -------------------------------------------------

    for f in IMAGE_DIR.glob("*"):
        f.unlink()

    pdf_files = sorted(INPUT_DIR.glob("*.pdf"))

    if len(pdf_files) != 1:
        raise RuntimeError(
            f"Expected exactly one PDF in {INPUT_DIR}, "
            f"found {len(pdf_files)}."
        )

    pdf = pdf_files[0]

    doc = fitz.open(pdf)

    image_map = []

    image_count = 0

    # -------------------------------------------------
    # Extract figures
    # -------------------------------------------------

    for page_number, page in enumerate(doc):

        print(f"Processing page {page_number + 1}")

        blocks = page.get_text("dict")["blocks"]

        # Get only image blocks from page
        image_blocks = [
            block
            for block in blocks
            if block["type"] == 1
        ]

        

        # Skip cover page completely
        if page_number == 0:
            continue

        # Remove logo
        image_blocks = image_blocks[1:]
        

        if not image_blocks:
            continue

       

        for block in image_blocks:

            x0, y0, x1, y1 = block["bbox"]

            filename = (
    f"page_{page_number+1:03d}_img_{image_count:03d}.png"
)

            rect = fitz.Rect(x0, y0, x1, y1)

            # Render only this figure region at high resolution
            pix = page.get_pixmap(
                matrix=fitz.Matrix(4, 4),
                clip=rect,
                alpha=True,
            )

            pix.save(IMAGE_DIR / filename)

           

            image_map.append(
                {
                    "id": f"IMAGE_{image_count:03d}",
                    "page": page_number + 1,
                    "filename": filename,
                    "bbox": [x0, y0, x1, y1],
                }
            )

            image_count += 1

    # -------------------------------------------------
    # Save mapping
    # -------------------------------------------------

    (ROOT / "image_map.json").write_text(
        json.dumps(image_map, indent=4),
        encoding="utf-8",
    )

    print("\n===================================")
    print("Image Extraction Complete")
    print(f"Pages  : {len(doc)}")
    print(f"Images : {image_count}")
    print("===================================")


if __name__ == "__main__":
    extract_images()