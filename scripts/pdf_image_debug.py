from pathlib import Path
import fitz

ROOT = Path(__file__).parent.parent

pdf = list((ROOT / "input").glob("*.pdf"))[0]

doc = fitz.open(pdf)

page = doc[3]      # page 4

images = page.get_images(full=True)

print(f"{len(images)} images")

for i, img in enumerate(images):

    xref = img[0]

    pix = fitz.Pixmap(doc, xref)

    outfile = ROOT / "temp" / f"embedded_{i}.png"

    if pix.alpha:
        pix = fitz.Pixmap(fitz.csRGB, pix)

    pix.save(outfile)

    print(outfile)