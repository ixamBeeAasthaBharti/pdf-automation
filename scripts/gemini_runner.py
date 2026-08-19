# from pathlib import Path
# import os
# import time

# from dotenv import load_dotenv
# from google import genai
# from google.genai import types

# # =====================================================
# # LOAD ENVIRONMENT
# # =====================================================

# load_dotenv()

# API_KEY = os.getenv("GEMINI_API_KEY")
# print(f"Using API key: {API_KEY[:10]}...{API_KEY[-4:]}")

# if not API_KEY:
#     raise ValueError("❌ GEMINI_API_KEY not found in .env")

# client = genai.Client(api_key=API_KEY)

# # =====================================================
# # PATHS
# # =====================================================

# ROOT = Path(__file__).parent.parent

# PROMPT_FILE = ROOT / "prompts" / "semantic_prompt.txt"
# INPUT_FILE = ROOT / "temp" / "preprocessed.html"
# OUTPUT_DIR = ROOT / "output"
# OUTPUT_FILE = OUTPUT_DIR / "output.html"

# # =====================================================
# # CHECK FILES
# # =====================================================

# if not PROMPT_FILE.exists():
#     raise FileNotFoundError(f"Prompt file not found:\n{PROMPT_FILE}")

# if not INPUT_FILE.exists():
#     raise FileNotFoundError(f"Input HTML not found:\n{INPUT_FILE}")

# OUTPUT_DIR.mkdir(exist_ok=True)

# # =====================================================
# # READ INPUT
# # =====================================================

# prompt = PROMPT_FILE.read_text(encoding="utf-8")
# html = INPUT_FILE.read_text(encoding="utf-8")

# full_prompt = f"""
# {prompt}

# =====================================================
# SOURCE HTML
# =====================================================

# {html}

# =====================================================
# IMPORTANT
# =====================================================

# Preserve every word.

# Do NOT summarize.

# Do NOT rewrite.

# Do NOT omit anything.

# Ignore PDF24 presentation markup.

# Reconstruct the document into clean semantic HTML5.

# Return ONLY valid HTML.

# Do not wrap the output inside markdown code fences.
# """

# # =====================================================
# # SEND TO GEMINI
# # =====================================================
# def run_gemini():   
#     print("🚀 Sending document to Gemini...")

#     start = time.time()

#     try:
        

#         response = client.models.generate_content(
#             model="gemini-3-flash-preview",
#             contents=full_prompt,
#             config=types.GenerateContentConfig(
#                 temperature=0,
#             ),
#         )

#     except Exception as e:
#         print("\n❌ Gemini request failed.\n")
#         raise e

#     elapsed = time.time() - start

# # =====================================================
# # CLEAN RESPONSE
# # =====================================================

#     result = response.text.strip()

#     if result.startswith("```html"):
#         result = result[7:].lstrip()

#     elif result.startswith("```"):
#         result = result[3:].lstrip()

#     if result.endswith("```"):
#         result = result[:-3].rstrip()

# # =====================================================
# # SAVE OUTPUT
# # =====================================================

#     OUTPUT_FILE.write_text(result, encoding="utf-8")

# # =====================================================
# # DONE
# # =====================================================

#     print(f"\n✅ Conversion completed in {elapsed:.2f} seconds")

#     print(f"📄 Output saved to:\n{OUTPUT_FILE}")
# if __name__ == "__main__":
from importlib.resources import contents
from pathlib import Path
import os
import sys
import time
import json
from dotenv import load_dotenv
from google import genai
from google.genai import types
from bs4 import BeautifulSoup

# Force UTF-8 output on Windows terminals
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# =====================================================
# LOAD ENVIRONMENT — multi-key rotation
# =====================================================
load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

def _load_api_keys() -> list[str]:
    """
    Read GEMINI_API_KEY_1, _2, _3 (and the legacy GEMINI_API_KEY) from .env.
    Returns a deduplicated list of all non-empty keys in priority order.
    """
    candidates = [
        os.getenv("GEMINI_API_KEY_1", ""),
        os.getenv("GEMINI_API_KEY_2", ""),
        os.getenv("GEMINI_API_KEY_3", ""),
        os.getenv("GEMINI_API_KEY", ""),   # legacy single-key fallback
    ]
    seen = set()
    keys = []
    for k in candidates:
        k = k.strip()
        if k and k not in seen:
            seen.add(k)
            keys.append(k)
    return keys

API_KEYS = _load_api_keys()

if not API_KEYS:
    raise ValueError(
        "No Gemini API keys found in .env.\n"
        "Set GEMINI_API_KEY_1 (and optionally _2, _3)."
    )

print(f"[Gemini] Loaded {len(API_KEYS)} API key(s). Primary: {API_KEYS[0][:10]}...{API_KEYS[0][-4:]}")

# Build a client for each key — rotated on quota exhaustion
_CLIENTS = [genai.Client(api_key=k) for k in API_KEYS]

# Keep a legacy reference so existing code that uses `client` still works
client = _CLIENTS[0]


# =====================================================
# PATHS
# =====================================================

ROOT = Path(__file__).parent.parent

PROMPT_FILE = ROOT / "prompts" / "semantic_prompt.txt"
CHUNK_DIR = ROOT / "chunks"
PROCESSED_DIR = ROOT / "processed"
FIGURE_DIR = ROOT / "figures"

FIGURE_DIR = ROOT / "figures"

METADATA_FILE = FIGURE_DIR / "metadata.json"

if METADATA_FILE.exists():
    with open(METADATA_FILE, "r", encoding="utf-8") as f:
        FIGURE_METADATA = json.load(f)
else:
    FIGURE_METADATA = []



# =====================================================
# CHECK FILES
# =====================================================

if not PROMPT_FILE.exists():
    raise FileNotFoundError(f"Prompt file not found:\n{PROMPT_FILE}")


def build_prompt(html: str) -> str:

    prompt = PROMPT_FILE.read_text(encoding="utf-8")

    return f"""
{prompt}



=====================================================
SOURCE HTML
=====================================================

{html}

=====================================================
IMPORTANT
=====================================================

Preserve every word.

Do NOT summarize.

Do NOT rewrite.

Do NOT omit anything.

Ignore PDF24 presentation markup.

Transform the EXISTING HTML into semantic HTML5 while preserving every existing element.

The output must contain every existing <img> tag exactly once.

The number of <img> tags in the output must equal the number in the input.

Return ONLY valid HTML.

CRITICAL: DO NOT output any reasoning, thinking, or explanations.
CRITICAL: Your entire response MUST be raw, valid HTML and nothing else.
CRITICAL: Do NOT output any text before the HTML starts or after it ends.

Do not wrap the output inside markdown code fences.
"""

def get_figure(page_number):

    for item in FIGURE_METADATA:

        if item["page"] == page_number:

            return FIGURE_DIR / item["filename"]

    return None

def process_chunk(chunk_file: Path, processed_dir: Path = None, image_dir: Path = None):
    # Fall back to legacy global paths when called from converter.py / standalone
    if processed_dir is None:
        processed_dir = PROCESSED_DIR
    if image_dir is None:
        image_dir = ROOT / "images"

    html = chunk_file.read_text(encoding="utf-8")
    full_prompt = build_prompt(html)

    soup = BeautifulSoup(html, "lxml")

    images = []

    for img in soup.find_all("img"):

        src = img.get("src", "")

        # Accept both 'images/...' and '../images/...' (chunks use the latter)
        if "images/" not in src:
            continue

        # Normalise: strip any leading '../' so ROOT / 'images/...' resolves correctly
        clean_src = src.lstrip("./").lstrip("..").lstrip("/")
        if not clean_src.startswith("images/"):
            # fallback: just take the part from 'images/' onward
            clean_src = "images/" + src.split("images/", 1)[1]

        # Resolve image path: prefer the per-doc image_dir, then fall back to ROOT
        candidate = image_dir / Path(clean_src).name
        page_image = candidate if candidate.exists() else ROOT / clean_src

        page_number = int(page_image.stem.split("_")[1])

        figure_image = get_figure(page_number)

        if figure_image:
            images.append({
                "path": page_image,
                "bytes": figure_image.read_bytes(),
                "using_figure": True,
            })
        else:
            images.append({
                "path": page_image,
                "bytes": page_image.read_bytes(),
                "using_figure": False,
            })

    print(f"Images found : {len(images)}")

    image_parts = []

    for image in images:

        image_parts.append(

            types.Part.from_bytes(
            data=image["bytes"],
            mime_type="image/png",
            )

        )

    print(f"Image parts : {len(image_parts)}")

    for image in images:
       
        figure = (
            FIGURE_DIR /
            f"{image['path'].stem}_figure_01.png"
            )

        if figure.exists():
            print(f"   {image['path'].name} -> using FIGURE")
        else:
            print(f"   {image['path'].name} -> using PAGE")

    # ------------------------------------------------------------------
    # Two-level retry: 5 attempts per key, then rotate to next key.
    # Quota / rate-limit signals: 429, 503, RESOURCE_EXHAUSTED
    # ------------------------------------------------------------------
    RETRIES_PER_KEY = 5
    QUOTA_SIGNALS   = ("429", "503", "resource_exhausted", "quota", "rate")

    def _is_quota_error(exc: Exception) -> bool:
        msg = str(exc).lower()
        return any(sig in msg for sig in QUOTA_SIGNALS)

    for key_idx, active_client in enumerate(_CLIENTS):
        key_label = f"Key {key_idx + 1}/{len(_CLIENTS)} ({API_KEYS[key_idx][:10]}...)"
        print(f"\n[Gemini] Using {key_label}")

        for attempt in range(RETRIES_PER_KEY):
            try:
                print(f"\n{'=' * 60}")
                print(f"Attempt {attempt + 1}/{RETRIES_PER_KEY}  |  {key_label}")
                print(f"Processing: {chunk_file.name}")
                print(f"Characters: {len(html):,}")
                print(f"{'=' * 60}")

                contents = [full_prompt]

                for image in images:

                    contents.append(
                    f"""
VISUAL FOR HTML IMAGE

This binary corresponds to:

<img src="images/{image['path'].name}">

INSTRUCTIONS — classify this image into exactly ONE of these three paths:

PATH A — IF THE IMAGE CONTAINS A TABLE OR STRUCTURED TABULAR CONTENT:
This includes: traditional grid tables, two-column comparison layouts, side-by-side coloured boxes, key-value layouts, any parallel-column structured content.
NOTE: Decorative headers, logos, page numbers at the top are NOT the table — extract them as headings above the table.
Action:
- Replace <img src="images/{image['path'].name}"> with <div class="extracted-table-block"> containing headings + table.
- Do NOT keep the <img> tag.
- See TABLE IMAGES (CRITICAL) in the system prompt for full format.

PATH B — IF THE IMAGE IS TEXT-ONLY (headings, paragraphs, bullets — NO diagrams or drawings):
Text-only = only readable text content. No flowcharts, no arrows between boxes, no node diagrams, no charts.
Examples: bullet-point study notes, definition sections, legal provisions with paragraphs.
NOT text-only if the main content is a flowchart or diagram (even if it has text labels).
Action:
- Replace <img src="images/{image['path'].name}"> with <div class="extracted-text-block">.
- Do NOT keep the <img> tag.
- Extract all text in reading order using <h4 class="extracted-heading">, <p>, <ul><li>, <strong>, <em>.
- Skip watermarks, logos, page numbers, dividing lines.

PATH C — IF THE IMAGE IS A VISUAL (flowchart, diagram, chart, photograph, UI screenshot):
Action:
- Keep the <img src="images/{image['path'].name}"> tag exactly once.
- Do NOT change the src attribute.
- Wrap in <figure><img src="images/{image['path'].name}"><figcaption>...</figcaption></figure>.

CRITICAL: DO NOT EXPLAIN YOUR CLASSIFICATION. DO NOT THINK OUT LOUD. JUST APPLY THE ACTION DIRECTLY TO THE HTML.
END VISUAL
                """
                )

                    contents.append(
                        types.Part.from_bytes(
                            data=image["bytes"],
                            mime_type="image/png",
                        )
                    )

                print(f"Sending {len(images)} visual references to Gemini")

                response = active_client.models.generate_content(
                    model="gemini-3.6-flash",
                    contents=contents,
                    config=types.GenerateContentConfig(
                        temperature=0,
                    ),
                )

                if not response.text:
                    finish_reason = "UNKNOWN"
                    if response.candidates and len(response.candidates) > 0:
                        finish_reason = response.candidates[0].finish_reason
                    raise ValueError(f"'NoneType' object has no attribute 'strip'. Gemini API returned empty text. Finish reason: {finish_reason}")

                result = response.text.strip()

                print("=" * 60)
                print("IMG TAGS IN SOURCE :", html.count("<img"))
                print("IMG TAGS IN RESULT :", result.count("<img"), "(table images intentionally converted to HTML)")
                print("=" * 60)

                if result.startswith("```html"):
                    result = result[7:].lstrip()
                elif result.startswith("```"):
                    result = result[3:].lstrip()
                if result.endswith("```"):
                    result = result[:-3].rstrip()

                output = processed_dir / chunk_file.name
                output.write_text(result, encoding="utf-8")
                print(f"[OK] Saved {output.name}")
                return  # success — done

            except Exception as e:
                print(f"[Gemini] Attempt {attempt + 1}/{RETRIES_PER_KEY} failed: {e}")

                if _is_quota_error(e):
                    # Quota/rate error — wait briefly then retry on same key
                    wait = min(30 * (attempt + 1), 120)
                    if attempt < RETRIES_PER_KEY - 1:
                        print(f"[Gemini] Rate limit hit. Waiting {wait}s before retry...")
                        time.sleep(wait)
                    else:
                        # All retries on this key exhausted — break to next key
                        print(f"[Gemini] All {RETRIES_PER_KEY} attempts on {key_label} failed.")
                        if key_idx < len(_CLIENTS) - 1:
                            print(f"[Gemini] Rotating to Key {key_idx + 2}...")
                        break  # exit inner loop → try next key
                else:
                    # Non-retriable error (bad request, auth failure, etc.)
                    raise

    # All keys exhausted
    raise RuntimeError(
        f"[Gemini] All {len(_CLIENTS)} API key(s) exhausted for {chunk_file.name}.\n"
        f"         Keys tried: {len(_CLIENTS)}  |  Attempts per key: {RETRIES_PER_KEY}\n"
        f"         Total attempts: {len(_CLIENTS) * RETRIES_PER_KEY}\n"
        f"         Check your daily quota at https://aistudio.google.com"
    )



# =====================================================
# SEND TO GEMINI
# =====================================================
def run_gemini(
    chunk_dir: Path = None,
    processed_dir: Path = None,
    image_dir: Path = None,
    figure_dir: Path = None,
):
    """
    Process all chunks in chunk_dir through Gemini.
    Optional path parameters override the legacy global paths so this function
    can be called from batch_runner / pipeline with per-document isolated dirs.
    """
    # Fall back to legacy global paths when called from converter.py / standalone
    if chunk_dir is None:
        chunk_dir = CHUNK_DIR
    if processed_dir is None:
        processed_dir = PROCESSED_DIR
    if image_dir is None:
        image_dir = ROOT / "images"

    if not chunk_dir.exists():
        raise FileNotFoundError(
            f"Chunk directory not found:\n{chunk_dir}"
        )

    processed_dir.mkdir(parents=True, exist_ok=True)

    chunks = sorted(chunk_dir.glob("chunk_*.html"))

    print(f"\nFound {len(chunks)} chunks\n")

    for index, chunk in enumerate(chunks, start=1):
        print(f"\nChunk {index}/{len(chunks)}")

        processed = processed_dir / chunk.name

        if processed.exists():
            print(f"Skipping {chunk.name}")
            continue

        process_chunk(chunk, processed_dir=processed_dir, image_dir=image_dir)

    print("\nAll chunks processed.")
    

if __name__ == "__main__":
    process_chunk(
        CHUNK_DIR / "chunk_002.html"
    )