from pathlib import Path
from bs4 import BeautifulSoup
import json

# =====================================================
# PATHS
# =====================================================

ROOT = Path(__file__).parent.parent

PROCESSED_DIR  = ROOT / "processed"
OUTPUT_DIR     = ROOT / "output"
OUTPUT_FILE    = OUTPUT_DIR / "output.html"
ASSETS_DIR     = ROOT / "assets"
LOGO_FILE      = ASSETS_DIR / "logo.png"          
IMAGE_MAP_FILE = ROOT / "image_map.json"

OUTPUT_DIR.mkdir(exist_ok=True)


# =====================================================
# COVER PAGE BUILDER
# =====================================================

def build_cover(soup: BeautifulSoup, output_file: Path = None) -> None:
    """
    Replaces the <article><header> Gemini generates with a proper
    cover page that mirrors the branded PDF title page.

    Strategy:
      - Collect ALL children of <header> in DOM order.
      - The first <h1> becomes the main document title (navy, large).
      - The first <h2>, if present, becomes the subtitle (exam code / year).
      - Remaining <p> / <h3> / <h4> tags become body lines (green label style).
      - The LAST <p> that contains a URL or phone number is treated as the
        contact line and pinned to the bottom of the cover.
      - Everything else ("Study Notes", "Professional Knowledge", etc.) is
        stacked in the cover body above the title.

    The logo is read from  assets/logo.png  — drop any PNG/JPG there
    once and every PDF run will pick it up automatically.
    """

    article = soup.find("article")
    if not article:
        return

    header = article.find("header")
    if not header:
        return

    # Compute relative path prefix based on output_file depth
    up = "../"
    if output_file is not None:
        try:
            depth = len(output_file.relative_to(ROOT).parts) - 1
            up = "../" * depth
        except ValueError:
            up = "../"

    logo_src = f"{up}assets/logo.png"

    # --- Collect every direct child element of <header> ---
    children = [c for c in header.children if hasattr(c, 'name') and c.name]

    h1_tag = header.find("h1")
    h2_tag = header.find("h2")

    main_title    = h1_tag.get_text(" ", strip=True) if h1_tag else "Document"
    sub_title     = h2_tag.get_text(" ", strip=True) if h2_tag else ""

    # --- Identify contact paragraph (last <p> with a URL or phone digits) ---
    import re
    all_p = header.find_all("p")
    contact_tag = None
    for p in reversed(all_p):
        txt = p.get_text()
        if re.search(r'(https?://|www\.|\d{7,})', txt):
            contact_tag = p
            break
    contact_html = str(contact_tag) if contact_tag else ""

    # --- Build extra body lines (everything except h1, h2, and contact p) ---
    body_lines_html = []                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      
    for child in children:
        if child is h1_tag:
            continue
        if child is h2_tag:
            continue
        if contact_tag and child is contact_tag:
            continue
        line_text = child.get_text(" ", strip=True)
        if line_text:
            body_lines_html.append(
                f'<p class="cover-meta-line">{line_text}</p>'
            )

    extra_body = "\n      ".join(body_lines_html)

    sub_title_html = (
        f'<p class="cover-subtitle">{sub_title}</p>'
        if sub_title else ""
    )

    # --- Logo img tag (dynamic relative path) ---
    if LOGO_FILE.exists():
        logo_html = (
            '<div class="cover-logo-wrap">'
            f'<img src="{logo_src}" alt="ixamBee" class="cover-logo-img"/>'
            '</div>'
        )
    else:
        logo_html = ""     # cover still looks fine without a logo

    # --- Update sticky reader header title & logo ---
    doc_header_title = soup.select_one(".doc-header .title")
    if doc_header_title and main_title:
        doc_header_title.string = main_title

    doc_header_logo = soup.select_one(".header-logo-img")
    if doc_header_logo:
        doc_header_logo["src"] = logo_src


    # --- Build cover HTML as a separate article ---
    cover_article_html = f"""
<article class="cover-article">
  <div class="cover-page">
    {logo_html}
    <div class="cover-body">
      {extra_body}
      <h1 class="cover-title">{main_title}</h1>
      {sub_title_html}
    </div>
    <div class="cover-contact">
      {contact_html}
    </div>
  </div>
</article>
"""

    # Insert the cover article before the main article
    cover_soup = BeautifulSoup(cover_article_html, "html.parser")
    article.insert_before(cover_soup)

    # Decompose the original header from the content article
    header.decompose()

    # Update the <title> tag to the actual document name
    title_tag = soup.find("title")
    if title_tag and main_title:
        title_tag.string = main_title


# =====================================================
# IMAGE SIZE FIXER
# =====================================================

def fix_image_sizes(soup: BeautifulSoup, image_map_file: Path = None) -> None:
    """
    Reads image_map.json and stamps width/height (in CSS pixels) onto
    every <img> whose src matches a known extracted image.

    This is needed because the processed chunks Gemini returns do not
    carry width/height — without this step images render at their full
    4x-oversampled PNG resolution.

    Conversion: 1 PDF point * (96 px / 72 pt) = 1.333 px
    """
    if image_map_file is None:
        image_map_file = IMAGE_MAP_FILE

    if not image_map_file.exists():
        return

    image_map = json.loads(image_map_file.read_text(encoding="utf-8"))

    PT_TO_PX = 96 / 72

    # Build lookup: filename -> (width_px, height_px)
    size_map = {}
    for entry in image_map:
        x0, y0, x1, y1 = entry["bbox"]
        size_map[entry["filename"]] = (
            round((x1 - x0) * PT_TO_PX),
            round((y1 - y0) * PT_TO_PX),
        )

    fixed = 0
    for img_tag in soup.find_all("img"):
        src = img_tag.get("src", "")
        filename = Path(src).name
        if filename in size_map:
            w, h = size_map[filename]
            img_tag["width"]  = w
            img_tag["height"] = h
            fixed += 1

    print(f"Image sizes fixed : {fixed}")


def strip_body_logos(soup: BeautifulSoup) -> None:
    """
    Removes any stray header/footer logo images or logo figures inside the document body,
    ensuring only the cover page displays logo.png from the assets folder.
    """
    for img in soup.find_all("img"):
        if "cover-logo-img" in img.get("class", []):
            continue

        alt = img.get("alt", "").lower()
        src = img.get("src", "").lower()

        if "logo" in alt or "prepare 50% faster" in alt or "ixambee" in alt:
            parent = img.parent
            img.decompose()
            if parent and parent.name == "figure" and not parent.find_all():
                parent.decompose()


# =====================================================
# MERGE
# =====================================================


def merge_chunks(
    processed_dir: Path = None,
    output_file: Path = None,
    image_map_file: Path = None,
    assets_dir: Path = None,
):
    """
    Merge all processed chunk HTML files into a single output HTML.

    Optional path parameters allow per-document isolated runs from
    batch_runner / pipeline. When omitted, legacy global paths are used
    so converter.py continues to work unchanged.
    """
    # Fall back to legacy global paths when called from converter.py / standalone
    if processed_dir is None:
        processed_dir = PROCESSED_DIR
    if output_file is None:
        output_file = OUTPUT_FILE
    if image_map_file is None:
        image_map_file = IMAGE_MAP_FILE
    if assets_dir is None:
        assets_dir = ASSETS_DIR

    logo_file = assets_dir / "logo.png"
    output_file.parent.mkdir(parents=True, exist_ok=True)

    chunk_files = sorted(processed_dir.glob("chunk_*.html"))

    if not chunk_files:
        raise FileNotFoundError("No processed chunks found.")

    merged_body = []

    for chunk in chunk_files:

        print(f"Reading {chunk.name}")

        html = chunk.read_text(encoding="utf-8")

        soup = BeautifulSoup(html, "lxml")

        body = soup.body

        if body:
            for child in body.contents:
                merged_body.append(str(child))
        else:
            merged_body.append(str(soup))

    # --------------------------------------------------
    # Compute relative paths based on output_file depth
    # --------------------------------------------------
    # Example: storage/outputs/1474/output.html is 3 parts deep
    # → need "../../" to reach project root → "../../styles/reader.css"
    # Legacy: output/index.html is 1 part deep → "../styles/reader.css"
    try:
        depth = len(output_file.relative_to(ROOT).parts) - 1  # subtract filename
        up = "../" * depth
    except ValueError:
        up = "../"  # fallback if output_file is outside ROOT

    css_href   = f"{up}styles/reader.css"
    logo_src   = f"{up}assets/logo.png"

    # Images live in the SAME directory as output_file (sibling 'images/' folder)
    # → always just 'images/' relative to the HTML file, no '../' needed
    images_prefix = "images/"

    # --------------------------------------------------
    # Assemble the raw HTML shell
    # --------------------------------------------------

    raw_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Study Notes</title>
<link rel="preconnect" href="https://fonts.googleapis.com"/>
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin/>
<link href="https://fonts.googleapis.com/css2?family=Lora:ital,wght@0,400;0,600;0,700;1,400;1,600&display=swap" rel="stylesheet"/>
<link rel="stylesheet" href="{css_href}"/>
</head>
<body>

<header class="doc-header">
  <div class="doc-header-inner">
    <div class="title">Study Notes</div>
    <div class="header-right">
      <div class="header-font-control">
        <button id="font-size-dec" class="font-btn-sep" aria-label="Decrease font size" title="Decrease font size">A−</button>
        <button id="font-size-inc" class="font-btn-sep" aria-label="Increase font size" title="Increase font size">A+</button>
      </div>
      <div class="header-logo-wrap"><img src="{logo_src}" alt="ixamBee Logo" class="header-logo-img"/></div>
    </div>


  </div>
  <div id="read-progress" class="read-progress"></div>
</header>



{''.join(merged_body)}

<script>
  const header = document.querySelector('.doc-header');
  const globalProgressBar = document.getElementById('read-progress');
  const tocProgressBar = document.getElementById('toc-progress-bar');
  
  // Smooth scrolling & progress calculation
  window.addEventListener('scroll', () => {{
    const scrollTop = window.scrollY;
    if (header) {{
      header.classList.toggle('scrolled', scrollTop > 10);
    }}
    const docHeight = document.documentElement.scrollHeight - window.innerHeight;
    const progressPercent = docHeight > 0 ? (scrollTop / docHeight) * 100 : 0;
    if (globalProgressBar) {{
      globalProgressBar.style.width = progressPercent + '%';
    }}
    if (tocProgressBar) {{
      tocProgressBar.style.width = progressPercent + '%';
    }}
  }}, {{ passive: true }});

  // Kindle-style Font Size Controls
  const FONT_LEVELS = [
    {{ label: '100%', scale: 1.0 }},
    {{ label: '110%', scale: 1.1 }},
    {{ label: '120%', scale: 1.2 }},
    {{ label: '130%', scale: 1.3 }},
    {{ label: '140%', scale: 1.4 }},
    {{ label: '155%', scale: 1.55 }},
    {{ label: '170%', scale: 1.7 }}
  ];

  let currentFontIndex = 0;
  const savedFontIndex = localStorage.getItem('readerFontScale');
  if (savedFontIndex !== null && !isNaN(savedFontIndex)) {{
    const parsedIndex = parseInt(savedFontIndex, 10);
    if (parsedIndex >= 0 && parsedIndex < FONT_LEVELS.length) {{
      currentFontIndex = parsedIndex;
    }}
  }}

  function applyFontScale(index) {{
    currentFontIndex = index;
    const level = FONT_LEVELS[index];
    document.documentElement.style.setProperty('--reader-font-scale', level.scale);
    localStorage.setItem('readerFontScale', index);

    const decBtn = document.getElementById('font-size-dec');
    const incBtn = document.getElementById('font-size-inc');

    if (decBtn) decBtn.disabled = (index === 0);
    if (incBtn) incBtn.disabled = (index === FONT_LEVELS.length - 1);
  }}


  // Apply saved/default scale immediately
  applyFontScale(currentFontIndex);

  document.addEventListener("DOMContentLoaded", () => {{
    const decBtn = document.getElementById('font-size-dec');
    const incBtn = document.getElementById('font-size-inc');

    if (decBtn) {{
      decBtn.addEventListener('click', (e) => {{
        e.stopPropagation();
        if (currentFontIndex > 0) {{
          applyFontScale(currentFontIndex - 1);
        }}
      }});
    }}

    if (incBtn) {{
      incBtn.addEventListener('click', (e) => {{
        e.stopPropagation();
        if (currentFontIndex < FONT_LEVELS.length - 1) {{
          applyFontScale(currentFontIndex + 1);
        }}
      }});
    }}

    // Dynamic Table of Contents & ScrollSpy

    const tocList = document.getElementById('toc-list');
    const sections = document.querySelectorAll('article:not(.cover-article) section, main section');
    
    if (tocList && sections.length > 0) {{
      sections.forEach(section => {{
        const heading = section.querySelector('h2.section-title, h2, h1, h3');
        const sectionId = section.getAttribute('aria-labelledby') || section.id || heading?.id;
        
        if (heading) {{
          if (!section.id) {{
            section.id = (sectionId || heading.textContent.trim().toLowerCase().replace(/[^a-z0-9]+/g, '-')).replace('-heading', '-section');
          }}
          const targetId = section.id;

          const li = document.createElement('li');
          const a = document.createElement('a');
          a.href = `#${{targetId}}`;
          a.textContent = heading.textContent.trim();
          
          a.addEventListener('click', (e) => {{
            e.preventDefault();
            const targetEl = document.getElementById(targetId);
            if (targetEl) {{
              targetEl.scrollIntoView({{ behavior: 'smooth' }});
              history.pushState(null, null, `#${{targetId}}`);
            }}
          }});
          
          li.appendChild(a);
          tocList.appendChild(li);
        }}
      }});

      const tocLinks = tocList.querySelectorAll('a');
      const observerOptions = {{
        root: null,
        rootMargin: '-15% 0px -60% 0px',
        threshold: 0
      }};

      const observer = new IntersectionObserver((entries) => {{
        entries.forEach(entry => {{
          if (entry.isIntersecting) {{
            const id = entry.target.id;
            tocLinks.forEach(link => {{
              link.classList.remove('active');
              link.removeAttribute('aria-current');
              if (link.getAttribute('href') === `#${{id}}`) {{
                link.classList.add('active');
                link.setAttribute('aria-current', 'true');
              }}
            }});
          }}
        }});
      }}, observerOptions);

      sections.forEach(section => observer.observe(section));
    }}
  }});
</script>



</body>
</html>
"""


    # Fix image src paths — normalize everything to 'images/<filename>'
    # Chunks from reconstructor use '../images/' (relative to chunk dir)
    # Gemini PATH-C output uses 'images/' — both must resolve to sibling images/
    raw_html = raw_html.replace('src="../images/', f'src="{images_prefix}')
    raw_html = raw_html.replace('src="images/',    f'src="{images_prefix}')

    # --------------------------------------------------
    # Post-process: inject cover page & clean body logos
    # --------------------------------------------------

    soup = BeautifulSoup(raw_html, "lxml")

    build_cover(soup)
    strip_body_logos(soup)
    fix_image_sizes(soup, image_map_file=image_map_file)

    final_html = str(soup)

    output_file.write_text(final_html, encoding="utf-8")

    logo_status = "yes" if logo_file.exists() else "no (drop assets/logo.png to add one)"

    print("\n========================================")

    print("Merge Complete")
    print(f"Chunks merged : {len(chunk_files)}")
    print(f"Logo included : {logo_status}")
    print(f"Output file   : {output_file}")
    print(f"Characters    : {len(final_html):,}")
    print("========================================")


if __name__ == "__main__":
    merge_chunks()