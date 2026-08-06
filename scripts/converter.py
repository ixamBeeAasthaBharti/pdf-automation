from pathlib import Path

from preprocessor import clean_html
from chunker import chunk_html, MAX_CHARS
from gemini_runner import run_gemini
from merger import merge_chunks
import shutil
from image_extractor import extract_images
from figure_extractor import extract_figures

# =====================================================
# PATHS
# =====================================================

ROOT = Path(__file__).parent.parent

INPUT_FILE = ROOT / "input" / "input.html"
PREPROCESSED_FILE = ROOT / "temp" / "preprocessed.html"

CHUNK_DIR = ROOT / "chunks"
OUTPUT_FILE = ROOT / "output" / "output.html"


def clean_previous_run():

    folders = [
        ROOT / "chunks",
        ROOT / "processed",
        ROOT / "output",
    ]

    for folder in folders:

        if folder.exists():

            shutil.rmtree(folder)

        folder.mkdir(parents=True, exist_ok=True)


# =====================================================
# MAIN
# =====================================================

def main():

   print("=" * 60)
print("Step 1/5 : Cleanup & Preprocessing")
print("=" * 60)

clean_previous_run()

PREPROCESSED_FILE.parent.mkdir(exist_ok=True)

clean_html(
    INPUT_FILE,
    PREPROCESSED_FILE,
)

print("=" * 60)
print("Step 2/5 : Extract Images")
print("=" * 60)

extract_images()
extract_figures()

print("=" * 60)
print("Step 3/5 : Chunking")
print("=" * 60)

chunk_html(
    PREPROCESSED_FILE,
    CHUNK_DIR,
    max_chars=MAX_CHARS,
)

print("=" * 60)
print("Step 4/5 : Gemini Processing")
print("=" * 60)

run_gemini()

print("=" * 60)
print("Step 5/5 : Merge")
print("=" * 60)

merge_chunks()

print("\n✅ Pipeline completed successfully!")
print(f"\nOutput saved to:\n{OUTPUT_FILE}")


if __name__ == "__main__":
    main()