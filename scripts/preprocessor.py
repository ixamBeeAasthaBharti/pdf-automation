from bs4 import BeautifulSoup, Comment
import re
from pathlib import Path


def clean_html(input_file, output_file):
    with open(input_file, "r", encoding="utf-8") as f:
        
        html = f.read()

    soup = BeautifulSoup(html, "lxml")

    #Remove script and style tags
    for tag in soup(["script", "style"]):
        tag.decompose()

    # Unwrap spans that have no useful attributes
    for span in soup.find_all("span"):
        attrs = span.attrs

    # Keep spans that carry formatting/positioning information for now
        if "style" in attrs or "class" in attrs or "id" in attrs:
            continue

        span.unwrap()

    # Remove empty spans
    for span in soup.find_all("span"):
        if not span.get_text(strip=True) and not span.find():
            span.decompose()

    # Remove empty divs
    for div in soup.find_all("div"):
        if not div.get_text(strip=True) and not div.find():
            div.decompose()

    # Remove comments
    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()

   # Remove multiple blank lines



    preprocessed = str(soup)
    preprocessed = re.sub(r'\n\s*\n', '\n', preprocessed)

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(preprocessed)

    print(f"Preprocessed HTML saved to: {output_file}")

   

ROOT = Path(__file__).parent.parent

if __name__ == "__main__":
    input_path = ROOT / "input" / "input.html"
    output_path = ROOT / "temp" / "preprocessed.html"

    output_path.parent.mkdir(exist_ok=True)

    clean_html(input_path, output_path)