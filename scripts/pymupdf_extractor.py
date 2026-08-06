from pathlib import Path
import fitz

ROOT = Path(__file__).parent.parent

PDF = ROOT / "input" / "input.pdf"

OUTPUT = ROOT / "temp" / "pymupdf"

OUTPUT.mkdir(parents=True, exist_ok=True)

doc = fitz.open(PDF)

print(f"Pages: {len(doc)}")

for i, page in enumerate(doc):

    html = page.get_text("html")

    (OUTPUT / f"page_{i+1:03}.html").write_text(
        html,
        encoding="utf-8",
    )

print("Done")