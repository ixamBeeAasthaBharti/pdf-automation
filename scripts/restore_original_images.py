from pathlib import Path
from bs4 import BeautifulSoup

# =====================================================
# PATHS
# =====================================================

ROOT = Path(__file__).parent.parent

PREPROCESSED = ROOT / "temp" / "preprocessed.html"
PROCESSED_DIR = ROOT / "processed"


def build_image_map():

    soup = BeautifulSoup(
        PREPROCESSED.read_text(encoding="utf-8"),
        "lxml",
    )

    image_map = {}

    for img in soup.find_all("img"):

        src = img.get("src")

        if not src:
            continue

        image_map[src] = str(img)

    return image_map


def restore_images():

    image_map = build_image_map()

    chunk_files = sorted(
        PROCESSED_DIR.glob("chunk_*.html")
    )

    restored = 0

    for chunk in chunk_files:

        soup = BeautifulSoup(
            chunk.read_text(encoding="utf-8"),
            "lxml",
        )

        for img in soup.find_all("img"):

            src = img.get("src")

            if src not in image_map:
                continue

            original = BeautifulSoup(
                image_map[src],
                "lxml",
            ).img

            img.replace_with(original)

            restored += 1

        chunk.write_text(
            soup.prettify(),
            encoding="utf-8",
        )

    print(f"Restored {restored} images.")


if __name__ == "__main__":
    restore_images()