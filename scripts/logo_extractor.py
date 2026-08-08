from pathlib import Path
import fitz

# =====================================================
# PATHS
# =====================================================

ROOT = Path(__file__).parent.parent

INPUT_DIR = ROOT / "input"
ASSETS_DIR = ROOT / "assets"

ASSETS_DIR.mkdir(exist_ok=True)

LOGO_COVER_FILE = ASSETS_DIR / "logo_cover.png"    # large, used on the cover page
LOGO_HEADER_FILE = ASSETS_DIR / "logo_header.png"  # small, used in running header


def extract_logo():
    """
    Extract the ixamBee logo from the input PDF.

    - Cover logo  : first (and only) image block on page 0 (the cover page).
    - Header logo : first image block on page 1 (the running header strip).

    Both files are saved only once; subsequent calls are no-ops so the
    assets directory can be shared across the whole 6000-PDF batch without
    re-extracting every time.
    """

    already_have_cover = LOGO_COVER_FILE.exists()
    already_have_header = LOGO_HEADER_FILE.exists()

    if already_have_cover and already_have_header:
        print("Logos already extracted - skipping.")
        return

    pdf_files = sorted(INPUT_DIR.glob("*.pdf"))

    if not pdf_files:
        print("No PDF found - logo extraction skipped.")
        return

    doc = fitz.open(pdf_files[0])

    # --------------------------------------------------
    # Cover logo  (page 0 - the decorative title page)
    # --------------------------------------------------

    if not already_have_cover:

        page0 = doc[0]

        blocks0 = page0.get_text("dict")["blocks"]

        img_blocks0 = [b for b in blocks0 if b["type"] == 1]

        if img_blocks0:

            x0, y0, x1, y1 = img_blocks0[0]["bbox"]

            pix = page0.get_pixmap(
                matrix=fitz.Matrix(3, 3),
                clip=fitz.Rect(x0, y0, x1, y1),
                alpha=False,
            )

            pix.save(LOGO_COVER_FILE)

            print(f"Cover logo saved -> {LOGO_COVER_FILE.name}  ({x1-x0:.0f}x{y1-y0:.0f} pt)")

        else:
            print("No image block found on page 0.")

    # --------------------------------------------------
    # Header logo (page 1 - top-right running logo)
    # --------------------------------------------------

    if not already_have_header and len(doc) > 1:

        page1 = doc[1]

        blocks1 = page1.get_text("dict")["blocks"]

        img_blocks1 = [b for b in blocks1 if b["type"] == 1]

        if img_blocks1:

            x0, y0, x1, y1 = img_blocks1[0]["bbox"]

            pix = page1.get_pixmap(
                matrix=fitz.Matrix(3, 3),
                clip=fitz.Rect(x0, y0, x1, y1),
                alpha=False,
            )

            pix.save(LOGO_HEADER_FILE)

            print(f"Header logo saved -> {LOGO_HEADER_FILE.name}  ({x1-x0:.0f}x{y1-y0:.0f} pt)")

        else:
            print("No image block found on page 1.")


if __name__ == "__main__":
    extract_logo()
