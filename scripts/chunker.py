from pathlib import Path
from bs4 import BeautifulSoup

ROOT = Path(__file__).parent.parent

MAX_CHARS = 180000


def chunk_html(input_file: Path, output_dir: Path, max_chars=MAX_CHARS):

    output_dir.mkdir(exist_ok=True)

    html = input_file.read_text(encoding="utf-8")

    soup = BeautifulSoup(html, "lxml")

    # Find pages (PDF24 div#page_... or div.page or PyMuPDF section.pdf-page)
    pages = soup.find_all(
        lambda tag: tag.name in ["div", "section"] and (
            (tag.get("id") and tag.get("id").startswith("page_")) or
            ("page" in tag.get("class", [])) or
            ("pdf-page" in tag.get("class", []))
        )
    )

    if not pages:
        raise RuntimeError("No pages found in HTML.")

    chunk_number = 1

    current_html = ""

    current_chars = 0

    for page in pages:

        page_html = str(page)

        page_chars = len(page_html)

        # If adding this page exceeds the limit,
        # save the current chunk first.
        if current_chars + page_chars > max_chars and current_html:

            output_file = output_dir / f"chunk_{chunk_number:03}.html"

            output_file.write_text(
                current_html,
                encoding="utf-8",
            )

            print(
                f"Chunk {chunk_number:03} | "
                f"{current_chars:,} chars"
            )

            chunk_number += 1

            current_html = ""

            current_chars = 0

        current_html += page_html + "\n"

        current_chars += page_chars

    # Save last chunk

    if current_html:

        output_file = output_dir / f"chunk_{chunk_number:03}.html"

        output_file.write_text(
            current_html,
            encoding="utf-8",
        )

        print(
            f"Chunk {chunk_number:03} | "
            f"{current_chars:,} chars"
        )

    print(f"\n[OK] Created {chunk_number} chunks")


if __name__ == "__main__":

    INPUT_FILE = ROOT / "temp" / "preprocessed.html"

    chunk_html(
        INPUT_FILE,
        ROOT / "chunks",
    )