from pathlib import Path
from bs4 import BeautifulSoup

# =====================================================
# PATHS
# =====================================================

ROOT = Path(__file__).parent.parent

PROCESSED_DIR = ROOT / "processed"
OUTPUT_DIR = ROOT / "output"
OUTPUT_FILE = OUTPUT_DIR / "output.html"

OUTPUT_DIR.mkdir(exist_ok=True)


# =====================================================
# MERGE
# =====================================================

def merge_chunks():

    chunk_files = sorted(PROCESSED_DIR.glob("chunk_*.html"))

    if not chunk_files:
        raise FileNotFoundError("No processed chunks found.")

    merged_body = []

    for chunk in chunk_files:

        print(f"Reading {chunk.name}")

        html = chunk.read_text(encoding="utf-8")

        soup = BeautifulSoup(html, "lxml")

        body = soup.body

        if body:

            for child in body.contents:

                merged_body.append(str(child))

        else:
            merged_body.append(str(soup))

    final_html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
</head>
<body>

{''.join(merged_body)}

</body>
</html>
"""
    final_html = final_html.replace(
        'src="images/',
        'src="../images/'
    )
    OUTPUT_FILE.write_text(
        final_html,
        encoding="utf-8",
    )

    print("\n========================================")
    print("✅ Merge Complete")
    print(f"Chunks merged : {len(chunk_files)}")
    print(f"Output file   : {OUTPUT_FILE}")
    print(f"Characters    : {len(final_html):,}")
    print("========================================")


if __name__ == "__main__":
    merge_chunks()