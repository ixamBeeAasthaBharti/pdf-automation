from pathlib import Path
import fitz
import json

# =====================================================
# PATHS  (legacy defaults — used when called standalone)
# =====================================================

ROOT = Path(__file__).parent.parent

_DEFAULT_INPUT_DIR = ROOT / "input"
_DEFAULT_IMAGE_DIR = ROOT / "images"
_DEFAULT_IMAGE_MAP = ROOT / "image_map.json"


def extract_images(
    pdf_file: Path = None,
    image_dir: Path = None,
    image_map_path: Path = None,
):
    """
    Extract image blocks from a PDF and save them as PNGs.

    Parameters (all optional — falls back to legacy global paths):
        pdf_file       : Path to the source PDF (default: first PDF in input/)
        image_dir      : Directory to save extracted PNG images (default: images/)
        image_map_path : Path to write image_map.json (default: image_map.json at root)
    """
    # ------------------------------------------------------------------ #
    # Resolve paths                                                         #
    # ------------------------------------------------------------------ #
    if pdf_file is None:
        pdf_files = sorted(_DEFAULT_INPUT_DIR.glob("*.pdf"))
        if len(pdf_files) != 1:
            raise RuntimeError(
                f"Expected exactly one PDF in {_DEFAULT_INPUT_DIR}, "
                f"found {len(pdf_files)}."
            )
        pdf_file = pdf_files[0]

    if image_dir is None:
        image_dir = _DEFAULT_IMAGE_DIR

    if image_map_path is None:
        image_map_path = _DEFAULT_IMAGE_MAP

    pdf_file       = Path(pdf_file)
    image_dir      = Path(image_dir)
    image_map_path = Path(image_map_path)

    image_dir.mkdir(parents=True, exist_ok=True)

    # -------------------------------------------------
    # Cleanup previous images in this dir
    # -------------------------------------------------
    for f in image_dir.glob("*.png"):
        f.unlink()

    doc = fitz.open(pdf_file)

    image_map   = []
    image_count = 0

    # -------------------------------------------------
    # Extract figures
    # -------------------------------------------------

    for page_number, page in enumerate(doc):

        print(f"Processing page {page_number + 1}")

        blocks = page.get_text("dict")["blocks"]

        # Get only image blocks from page
        image_blocks = [b for b in blocks if b["type"] == 1]

        # Skip cover page completely
        if page_number == 0:
            continue

        page_height = page.rect.height

        for block in image_blocks:

            x0, y0, x1, y1 = block["bbox"]

            # Skip header logos (top 90pt of page) and footer logos (bottom 50pt of page)
            if y0 < 90 or y1 > (page_height - 50):
                print(f"   Skipping header/footer logo on page {page_number + 1} at bbox ({x0:.1f}, {y0:.1f}, {x1:.1f}, {y1:.1f})")
                continue

            filename = f"page_{page_number+1:03d}_img_{image_count:03d}.png"


            rect = fitz.Rect(x0, y0, x1, y1)

            pix = page.get_pixmap(
                matrix=fitz.Matrix(4, 4),
                clip=rect,
                alpha=True,
            )

            pix.save(image_dir / filename)

            image_map.append(
                {
                    "id":       f"IMAGE_{image_count:03d}",
                    "page":     page_number + 1,
                    "filename": filename,
                    "bbox":     [x0, y0, x1, y1],
                }
            )

            image_count += 1

    # -------------------------------------------------
    # Save mapping
    # -------------------------------------------------

    image_map_path.parent.mkdir(parents=True, exist_ok=True)
    image_map_path.write_text(
        json.dumps(image_map, indent=4),
        encoding="utf-8",
    )

    print("\n===================================")
    print("Image Extraction Complete")
    print(f"Pages  : {len(doc)}")
    print(f"Images : {image_count}")
    print(f"Saved  : {image_dir}")
    print("===================================")


if __name__ == "__main__":
    extract_images()