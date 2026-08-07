from pathlib import Path
import fitz

ROOT = Path(__file__).parent.parent

pdf = list((ROOT / "input").glob("*.pdf"))[0]

doc = fitz.open(pdf)

# Change this page number if needed
page = doc[44]   # Page 45

blocks = page.get_text("dict")["blocks"]

print(f"Total blocks: {len(blocks)}\n")

for i, block in enumerate(blocks):

    print("=" * 60)
    print(f"Block {i}")
    print("=" * 60)

    print("Type :", block["type"])
    print("BBox :", block["bbox"])

    if block["type"] == 0:
        text = ""

        for line in block.get("lines", []):
            for span in line.get("spans", []):
                text += span["text"]

        print("Text :", text[:100])

    elif block["type"] == 1:

        print("IMAGE BLOCK")

        print("Keys:", block.keys())

        print("Width :", block.get("width"))
        print("Height:", block.get("height"))

        print("Ext   :", block.get("ext"))

        print("Transform:", block.get("transform"))

        print("Image bytes present:", "image" in block)

        print("-" * 60)