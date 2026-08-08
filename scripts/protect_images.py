from pathlib import Path
import json
from bs4 import BeautifulSoup

ROOT = Path(__file__).parent.parent

INPUT_HTML = ROOT / "temp" / "preprocessed.html"
OUTPUT_HTML = ROOT / "temp" / "preprocessed.html"
OUTPUT_JSON = ROOT / "protected_images.json"


def protect_images():

    html = INPUT_HTML.read_text(encoding="utf-8")

    soup = BeautifulSoup(html, "lxml")

    protected = {}

    images = soup.find_all(
        "img",
        class_="pdf24_figure",
    )

    for img in images:

        image_id = img["data-id"]

        protected[image_id] = {
            "html": str(img)
        }

        placeholder = soup.new_string(f"[[{image_id}]]")

        img.replace_with(placeholder)

    OUTPUT_JSON.write_text(
        json.dumps(protected, indent=4),
        encoding="utf-8",
    )

    OUTPUT_HTML.write_text(
        soup.prettify(),
        encoding="utf-8",
    )

    print(f"Protected {len(protected)} images")


if __name__ == "__main__":
    protect_images()