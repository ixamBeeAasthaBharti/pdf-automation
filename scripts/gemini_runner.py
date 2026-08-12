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
#     run_gemini()


from importlib.resources import contents
from pathlib import Path
import os
import time
import json
from dotenv import load_dotenv
from google import genai
from google.genai import types
from bs4 import BeautifulSoup

# =====================================================
# LOAD ENVIRONMENT
# =====================================================
load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")
print(f"Using API key: {API_KEY[:10]}...{API_KEY[-4:]}")

if not API_KEY:
    raise ValueError("❌ GEMINI_API_KEY not found in .env")

client = genai.Client(api_key=API_KEY)

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

Do not wrap the output inside markdown code fences.
"""

def get_figure(page_number):

    for item in FIGURE_METADATA:

        if item["page"] == page_number:

            return FIGURE_DIR / item["filename"]

    return None

def process_chunk(chunk_file: Path):

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

        page_image = ROOT / clean_src

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

    for attempt in range(5):  #for debugging change back to 5 afterwards#################
        try:

            print(f"\n{'=' * 60}")
            print(f"\nAttempt {attempt + 1}/5")
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

INSTRUCTIONS:

First, visually classify this image:

IF THE IMAGE CONTAINS A TABLE OR STRUCTURED TABULAR CONTENT:
This includes:
- A traditional grid with rows and columns.
- A two-column or multi-column COMPARISON layout (e.g. "Companies Act, 2013" vs "SEBI Regulations").
- Side-by-side coloured boxes presenting data under column headings.
- Key-value layouts (e.g. Particulars | Details).
- Any study note snippet where the MAIN content is organised in parallel columns.
NOTE: Decorative headers, logos, italic chapter titles, and page numbers at the top of the image are NOT the table — extract them as headings, then extract the table below them.
Action:
- Replace the <img src="images/{image['path'].name}"> tag with a semantic HTML table.
- Do NOT keep the <img> tag.
- Output format: <div class="extracted-table-block"> containing any headings above and the table itself.
- Extract every cell, heading, and note exactly as visible.
- See TABLE IMAGES (CRITICAL) in the system prompt for the full format.

IF THE IMAGE IS NOT A TABLE (pure diagram, chart, logo, photograph, flowchart, formula):
- Keep the <img src="images/{image['path'].name}"> tag exactly once.
- Do NOT change the src attribute.
- For charts/diagrams: wrap in <figure><img src="images/{image['path'].name}"><figcaption>...</figcaption></figure>.
- Do not convert to text or description.

END VISUAL
                """
                )

                contents.append(
                    types.Part.from_bytes(
                        data=image["bytes"],
                        mime_type="image/png",
                    )
                )
            

            print(f"Sending {len(image_parts)} images to Gemini")

            print(f"Sending {len(images)} visual references to Gemini")

            response = client.models.generate_content(
                model="gemini-3.6-flash",
                contents=contents,
                config=types.GenerateContentConfig(
                    temperature=0,
                ),
            )

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

            output = PROCESSED_DIR / chunk_file.name

            output.write_text(result, encoding="utf-8")

            print(f"[OK] Saved {output.name}")

            return

        except Exception as e:

            print(f"Attempt {attempt + 1}/5 failed")
            print(e)

            if "503" not in str(e):
                raise

            wait = min(30 * (attempt + 1), 120)

            print(f"Retrying in {wait} sec")

            time.sleep(wait)

    raise RuntimeError(f"Failed: {chunk_file.name}")



# =====================================================
# SEND TO GEMINI
# =====================================================
def run_gemini():

    if not CHUNK_DIR.exists():
        raise FileNotFoundError(
            f"Chunk directory not found:\n{CHUNK_DIR}"
        )

    PROCESSED_DIR.mkdir(exist_ok=True)

    chunks = sorted(CHUNK_DIR.glob("chunk_*.html"))

   

    print(f"\nFound {len(chunks)} chunks\n")

    for index, chunk in enumerate(chunks, start=1):
        print(f"\nChunk {index}/{len(chunks)}")

        processed = PROCESSED_DIR / chunk.name

        if processed.exists():

            print(f"Skipping {chunk.name}")

            continue

        process_chunk(chunk)

    print("\nAll chunks processed.")
    

if __name__ == "__main__":
    process_chunk(
        CHUNK_DIR / "chunk_002.html"
    )