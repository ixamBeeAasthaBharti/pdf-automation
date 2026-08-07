from pathlib import Path

from preprocessor import clean_html
from chunker import chunk_html, MAX_CHARS
from gemini_runner import run_gemini
from merger import merge_chunks
import shutil
from pymupdf_image_extractor import extract_images
from html_reconstructor import reconstruct_html


# =====================================================
# PATHS
# =====================================================

ROOT = Path(__file__).parent.parent

INPUT_DIR = ROOT / "input"

html_files = sorted(INPUT_DIR.glob("*.html"))

if len(html_files) != 1:
    raise RuntimeError(
        f"Expected exactly one HTML file in {INPUT_DIR}, found {len(html_files)}"
    )

INPUT_FILE = html_files[0]
PREPROCESSED_FILE = ROOT / "temp" / "preprocessed.html"

CHUNK_DIR = ROOT / "chunks"
OUTPUT_FILE = ROOT / "output" / "output.html"


def clean_previous_run():

    folders = [
        ROOT / "chunks",
        ROOT / "processed",
        ROOT / "output",
        ROOT / "images",
        ROOT / "temp",
    ]

    for folder in folders:

        if folder.exists():
            shutil.rmtree(folder)

        folder.mkdir(parents=True, exist_ok=True)

# Remove previous image map
    image_map = ROOT / "image_map.json"

    if image_map.exists():
        image_map.unlink()


# =====================================================
# MAIN
# =====================================================

def main():

    print("=" * 60)
    print("Step 1/7 : Cleanup")
    print("=" * 60)

    clean_previous_run()

    print("=" * 60)
    print("Step 2/7 : Extract Images")
    print("=" * 60)

    extract_images()

    print("=" * 60)
    print("Step 3/7 : Reconstruct HTML")
    print("=" * 60)

    reconstruct_html()

    print("=" * 60)
    print("Step 4/7 : Preprocess HTML")
    print("=" * 60)

    clean_html(
        PREPROCESSED_FILE,
        PREPROCESSED_FILE,
    )

    print("=" * 60)
    print("Step 5/7 : Chunking")
    print("=" * 60)

    chunk_html(
        PREPROCESSED_FILE,
        CHUNK_DIR,
        max_chars=MAX_CHARS,
    )

    print("=" * 60)
    print("Step 6/7 : Gemini Processing")
    print("=" * 60)

    run_gemini()

    print("=" * 60)
    print("Step 7/7 : Merge")
    print("=" * 60)

    merge_chunks()

    print("\n✅ Pipeline completed successfully!")
    print(f"\nOutput saved to:\n{OUTPUT_FILE}")


if __name__ == "__main__":
    main()