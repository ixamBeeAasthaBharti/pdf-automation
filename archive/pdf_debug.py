from pathlib import Path
import fitz

ROOT = Path(__file__).parent.parent

pdf = list((ROOT / "input").glob("*.pdf"))[0]

doc = fitz.open(pdf)

print(f"Pages: {len(doc)}")

for i, page in enumerate(doc):

    print(f"\nPage {i+1}")

    images = page.get_images(full=True)
    print("Embedded images:", len(images))

    drawings = page.get_drawings()
    print("Vector drawings:", len(drawings))

    blocks = page.get_text("dict")["blocks"]
    print("Text/Image blocks:", len(blocks))