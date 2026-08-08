from pathlib import Path
import fitz

ROOT = Path(__file__).parent.parent

pdf = list((ROOT / "input").glob("*.pdf"))[0]

doc = fitz.open(pdf)

for page_no, page in enumerate(doc, start=1):

    if page_no != 3:
        continue

    images = page.get_images(full=True)

    for img in images:

        print(img)