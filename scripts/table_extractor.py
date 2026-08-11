from pathlib import Path
import os
import time
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from google import genai
from google.genai import types

# =====================================================
# LOAD ENVIRONMENT
# =====================================================
load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise ValueError("❌ GEMINI_API_KEY not found in .env")

client = genai.Client(api_key=API_KEY)

# =====================================================
# PATHS
# =====================================================
ROOT = Path(__file__).parent.parent
PROCESSED_DIR = ROOT / "processed"
IMAGE_DIR = ROOT / "images"
FIGURE_DIR = ROOT / "figures"

# =====================================================
# PROMPT
# =====================================================
TABLE_PROMPT = """Look at this image. Does it contain a table?

If YES: 
Extract all text and structural data from it and output ONLY a valid HTML table wrapped in a div, like this:
<div class="table-responsive">
  <table>
    <thead><tr><th>...</th></tr></thead>
    <tbody><tr><td>...</td></tr></tbody>
  </table>
</div>
- Preserve all cell content exactly as it appears.
- Preserve header rows using <th> in a <thead>.
- Preserve merged cells using colspan or rowspan where applicable.
- Preserve bullet lists inside cells if they exist.
- Do not summarize or abbreviate anything.
- Do NOT output markdown code fences (like ```html).

If NO:
Output exactly the word SKIP and nothing else.
"""

def extract_tables_from_chunk(chunk_file: Path):
    print(f"\nProcessing {chunk_file.name} for tables...")
    html = chunk_file.read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "lxml")
    
    images = soup.find_all("img")
    if not images:
        print("  No images found.")
        return False
        
    modified = False
    for img in images:
        src = img.get("src", "")
        filename = Path(src).name
        
        # Determine which image file to use
        img_path = IMAGE_DIR / filename
        
        # If it's a figure, it might be in figures dir, but the src in processed chunk is usually pointing to images
        if not img_path.exists():
            print(f"  Warning: Image {filename} not found.")
            continue
            
        print(f"  Checking image: {filename}...")
        
        image_bytes = img_path.read_bytes()
        
        for attempt in range(3):
            try:
                response = client.models.generate_content(
                    model="gemini-3.5-flash",
                    contents=[
                        TABLE_PROMPT,
                        types.Part.from_bytes(data=image_bytes, mime_type="image/png")
                    ],
                    config=types.GenerateContentConfig(temperature=0),
                )
                
                result = response.text.strip()
                
                # Remove markdown fences if present
                if result.startswith("```html"):
                    result = result[7:].lstrip()
                elif result.startswith("```"):
                    result = result[3:].lstrip()
                if result.endswith("```"):
                    result = result[:-3].rstrip()
                    
                if result == "SKIP":
                    print("    -> Not a table. Skipping.")
                else:
                    print("    -> Table detected! Replacing image with HTML table.")
                    
                    # Parse the new table HTML
                    table_soup = BeautifulSoup(result, "html.parser")
                    
                    # Ensure it has the responsive wrapper
                    wrapper = table_soup.find("div", class_="table-responsive")
                    if wrapper:
                        replacement = wrapper
                    else:
                        table = table_soup.find("table")
                        if table:
                            wrapper = table_soup.new_tag("div", attrs={"class": "table-responsive"})
                            table.wrap(wrapper)
                            replacement = wrapper
                        else:
                            replacement = table_soup
                            
                    # Replace the img tag or its parent figure if it exists
                    parent = img.parent
                    if parent and parent.name == "figure":
                        parent.replace_with(replacement)
                    else:
                        img.replace_with(replacement)
                        
                    modified = True
                
                break # Success, break attempt loop
                
            except Exception as e:
                print(f"    -> Attempt {attempt+1} failed: {e}")
                if attempt < 2:
                    time.sleep(10 * (attempt + 1))
                else:
                    print(f"    -> Giving up on {filename}")
    
    if modified:
        print(f"  Saving modified chunk {chunk_file.name}")
        # Use HTML formatter, but keep it similar to original
        chunk_file.write_text(str(soup), encoding="utf-8")
        return True
    
    return False

def run_table_extraction():
    if not PROCESSED_DIR.exists():
        print("No processed directory found.")
        return
        
    chunks = sorted(PROCESSED_DIR.glob("chunk_*.html"))
    print(f"Found {len(chunks)} chunks to check for tables.")
    
    total_modified = 0
    for chunk in chunks:
        if extract_tables_from_chunk(chunk):
            total_modified += 1
            
    print(f"\nFinished table extraction. Modified {total_modified} chunks.")

if __name__ == "__main__":
    run_table_extraction()
