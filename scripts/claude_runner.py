import anthropic
import os
import sys
import time
import json
import base64
from pathlib import Path
from dotenv import load_dotenv
from bs4 import BeautifulSoup

# Force UTF-8 output on Windows terminals
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Load environment variables
load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

def _load_api_keys() -> list[str]:
    """
    Read ANTHROPIC_API_KEY_1, _2, _3 (and the legacy ANTHROPIC_API_KEY) from .env.
    Returns a deduplicated list of all non-empty keys in priority order.
    """
    candidates = [
        os.getenv("ANTHROPIC_API_KEY_1", ""),
        os.getenv("ANTHROPIC_API_KEY_2", ""),
        os.getenv("ANTHROPIC_API_KEY_3", ""),
        os.getenv("ANTHROPIC_API_KEY", ""),   # legacy single-key fallback
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
    print("[Claude] Warning: No Anthropic API keys found in .env. Setup ANTHROPIC_API_KEY.")
    _CLIENTS = []
else:
    print(f"[Claude] Loaded {len(API_KEYS)} API key(s). Primary: {API_KEYS[0][:10]}...{API_KEYS[0][-4:]}")
    _CLIENTS = [anthropic.Anthropic(api_key=k) for k in API_KEYS]

ROOT = Path(__file__).parent.parent
PROMPT_FILE = ROOT / "prompts" / "semantic_prompt.txt"
CHUNK_DIR = ROOT / "chunks"
PROCESSED_DIR = ROOT / "processed"
FIGURE_DIR = ROOT / "figures"
METADATA_FILE = FIGURE_DIR / "metadata.json"

if METADATA_FILE.exists():
    with open(METADATA_FILE, "r", encoding="utf-8") as f:
        FIGURE_METADATA = json.load(f)
else:
    FIGURE_METADATA = []

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
        base64_image = base64.b64encode(image["bytes"]).decode("utf-8")
        
        # Add instruction text block for this image
        image_parts.append({
            "type": "text",
            "text": f"""
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

END VISUAL
            """
        })
        
        # Add actual base64 image block
        image_parts.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/png",
                "data": base64_image
            }
        })

    print(f"Image parts prepared: {len(image_parts)}")

    for image in images:
        figure = FIGURE_DIR / f"{image['path'].stem}_figure_01.png"
        if figure.exists():
            print(f"   {image['path'].name} -> using FIGURE")
        else:
            print(f"   {image['path'].name} -> using PAGE")

    if not _CLIENTS:
        raise RuntimeError("No Claude API clients initialized. Check ANTHROPIC_API_KEY in .env")

    RETRIES_PER_KEY = 5
    
    # Check if the error is rate limit or overload
    def _is_quota_error(exc: Exception) -> bool:
        msg = str(exc).lower()
        return isinstance(exc, anthropic.RateLimitError) or "429" in msg or "503" in msg

    for key_idx, active_client in enumerate(_CLIENTS):
        key_label = f"Key {key_idx + 1}/{len(_CLIENTS)} ({API_KEYS[key_idx][:10]}...)"
        print(f"\n[Claude] Using {key_label}")

        for attempt in range(RETRIES_PER_KEY):
            try:
                print(f"\n{'=' * 60}")
                print(f"Attempt {attempt + 1}/{RETRIES_PER_KEY}  |  {key_label}")
                print(f"Processing: {chunk_file.name}")
                print(f"Characters: {len(html):,}")
                print(f"{'=' * 60}")

                # Prepare the user content messages payload
                user_content = [
                    {
                        "type": "text",
                        "text": f"SOURCE HTML:\n\n{html}"
                    }
                ]
                user_content.extend(image_parts)

                # Set system instructions
                system_prompt = PROMPT_FILE.read_text(encoding="utf-8")

                print(f"Sending {len(images)} visual references to Claude")

                response = active_client.messages.create(
                    model="claude-3-5-sonnet-latest",
                    max_tokens=8192,
                    temperature=0,
                    system=system_prompt,
                    messages=[
                        {
                            "role": "user",
                            "content": user_content
                        }
                    ]
                )

                result = response.content[0].text.strip()

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
                print(f"[Claude] Attempt {attempt + 1}/{RETRIES_PER_KEY} failed: {e}")

                if _is_quota_error(e):
                    # Quota/rate error — wait briefly then retry on same key
                    wait = min(30 * (attempt + 1), 120)
                    if attempt < RETRIES_PER_KEY - 1:
                        print(f"[Claude] Rate limit/overload hit. Waiting {wait}s before retry...")
                        time.sleep(wait)
                    else:
                        # All retries on this key exhausted — break to next key
                        print(f"[Claude] All {RETRIES_PER_KEY} attempts on {key_label} failed.")
                        if key_idx < len(_CLIENTS) - 1:
                            print(f"[Claude] Rotating to Key {key_idx + 2}...")
                        break  # exit inner loop → try next key
                else:
                    # Non-retriable error (bad request, auth failure, etc.)
                    raise

    # All keys exhausted
    raise RuntimeError(
        f"[Claude] All {len(_CLIENTS)} API key(s) exhausted for {chunk_file.name}.\n"
        f"         Keys tried: {len(_CLIENTS)}  |  Attempts per key: {RETRIES_PER_KEY}\n"
        f"         Total attempts: {len(_CLIENTS) * RETRIES_PER_KEY}\n"
    )

def run_claude(
    chunk_dir: Path = None,
    processed_dir: Path = None,
    image_dir: Path = None,
    figure_dir: Path = None,
):
    """
    Process all chunks in chunk_dir through Claude.
    """
    # Fall back to legacy global paths when called from converter.py / standalone
    if chunk_dir is None:
        chunk_dir = CHUNK_DIR
    if processed_dir is None:
        processed_dir = PROCESSED_DIR
    if image_dir is None:
        image_dir = ROOT / "images"

    if not chunk_dir.exists():
        raise FileNotFoundError(f"Chunk directory not found:\n{chunk_dir}")

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
    # Test on a chunk if run as main script
    if (CHUNK_DIR / "chunk_002.html").exists():
        process_chunk(CHUNK_DIR / "chunk_002.html")
    else:
        print("No chunk_002.html found for standalone run.")
