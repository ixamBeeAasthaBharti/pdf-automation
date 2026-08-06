from pathlib import Path
import fitz

ROOT = Path(__file__).parent.parent

pdf = list((ROOT / "input").glob("*.pdf"))[0]
doc = fitz.open(pdf)

page = doc[4]      # page 5

for img in page.get_image_info():
    print(img)