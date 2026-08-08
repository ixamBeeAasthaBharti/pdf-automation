from pathlib import Path

from bs4 import BeautifulSoup
from pathlib import Path
from bs4 import BeautifulSoup
import base64
import json
import re

ROOT = Path(__file__).parent.parent

INPUT_FILE = ROOT / "temp" / "preprocessed.html"

IMAGE_DIR = ROOT / "images"

IMAGE_DIR.mkdir(exist_ok=True)


def extract_images():

    html = INPUT_FILE.read_text(encoding="utf-8")

    soup = BeautifulSoup(html, "lxml")

    images = soup.find_all("img")

    print(f"Found {len(images)} images\n")

    image_map = []
    count = 0

    for img in images:

        src = img.get("src", "")

        if not src.startswith("data:image"):
            continue

        match = re.match(
            r"data:image/(\w+);base64,(.*)",
            src,
            re.DOTALL,
        )

        if not match:
            continue

        extension = match.group(1)
        encoded = match.group(2)

        image_bytes = base64.b64decode(encoded)

        count += 1

        filename = f"image_{count:03}.{extension}"

        image_path = IMAGE_DIR / filename

        image_path.write_bytes(image_bytes)
        image_map.append({
            "image": filename,
            "src": f"images/{filename}",
            "parent_html": str(img.parent)
        })

        img["src"] = f"images/{filename}"

    INPUT_FILE.write_text(
        str(soup),
        encoding="utf-8",
    )

    (ROOT / "image_map.json").write_text(
        json.dumps(image_map, indent=4),
        encoding="utf-8",
    )

    print(f"\nSaved {count} images")
    print("Updated HTML successfully.")


if __name__ == "__main__":
    extract_images()