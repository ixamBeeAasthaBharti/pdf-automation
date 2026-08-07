from pathlib import Path
import json
from bs4 import BeautifulSoup

# =====================================================
# PATHS
# =====================================================

ROOT = Path(__file__).parent.parent

PROCESSED_DIR = ROOT / "processed"

IMAGE_JSON = ROOT / "protected_images.json"


# =====================================================
# RESTORE IMAGES
# =====================================================

def restore_images():

    protected = json.loads(
        IMAGE_JSON.read_text(
            encoding="utf-8"
        )
    )

    chunk_files = sorted(
        PROCESSED_DIR.glob("chunk_*.html")
    )

    total = 0

    for chunk in chunk_files:

        html = chunk.read_text(
            encoding="utf-8"
        )

        for image_id, img_data in protected.items():

            token = f"[[{image_id}]]"

            if token in html:

                html = html.replace(
                    token,
                    img_data["html"],
                )

                total += 1

        chunk.write_text(
            html,
            encoding="utf-8",
        )

        print(f"Restored {chunk.name}")

    print("\n====================================")
    print("Image Restore Complete")
    print(f"Images restored : {total}")
    print("====================================")

if __name__ == "__main__":
    restore_images()