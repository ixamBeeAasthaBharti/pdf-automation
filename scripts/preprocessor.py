from bs4 import BeautifulSoup, Comment
import re
from pathlib import Path


def clean_html(input_file, output_file):
    html = Path(input_file).read_text(encoding="utf-8")

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

    Path(output_file).write_text(
        preprocessed,
        encoding="utf-8",
)

    print(f"Preprocessed HTML saved to: {output_file}")

