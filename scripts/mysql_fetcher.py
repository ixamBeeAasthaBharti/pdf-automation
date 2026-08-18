"""
mysql_fetcher.py
Fetches the NEXT unprocessed PDF from MySQL (type_order=2, htmltopdfstatus=0)
and downloads it into storage/queue/<mysql_id>/document.pdf.

Processes ONE document at a time to keep the workflow controlled.

Run standalone:
    python scripts/mysql_fetcher.py

Or call fetch_next() from pipeline.py.
"""

import sys
import requests
from urllib.parse import quote
from pathlib import Path

# Force UTF-8 output on Windows terminals
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

scripts_dir = Path(__file__).parent
if str(scripts_dir) not in sys.path:
    sys.path.append(str(scripts_dir))

from mysql_client import get_connection
from db_manager import init_db, init_pdf_jobs_db, upsert_pdf_job

ROOT      = Path(__file__).parent.parent
QUEUE_DIR = ROOT / "storage" / "queue"
BASE_URL  = "https://www.ixambee.com/miscellaneous-pdf/"


def fetch_next(count: int = 1, target_ids: list[int] = None) -> list[int]:
    """
    Fetch the next N eligible rows from MySQL, download their PDFs, and
    register them in local SQLite + MySQL htmltopdfautomation.

    Filters applied:
      - type_order  = 2
      - status      = 1       (active/published content only)
      - expiry_date > NOW()   (not expired)
      - htmltopdfstatus = 0   (not yet processed by this pipeline)

    Returns a list of mysql_ids that were fetched (may be fewer than
    requested if not enough eligible rows exist).
    """
    conn   = get_connection()
    cursor = conn.cursor(dictionary=True)

    if target_ids:
        placeholders = ', '.join(['%s'] * len(target_ids))
        cursor.execute(f"""
            SELECT id, content
            FROM   tbl_studymaterial_lang_map
            WHERE  id IN ({placeholders})
        """, tuple(target_ids))
    else:
        # Pick next N unprocessed, active, non-expired PDFs (lowest id first)
        cursor.execute("""
            SELECT id, content
            FROM   tbl_studymaterial_lang_map
            WHERE  type_order      = 2
              AND  status          = 1
              AND  htmltopdfstatus = 0
              AND  (expiry_date IS NULL OR expiry_date > NOW())
            ORDER  BY id ASC
            LIMIT  %s
        """, (count,))
    rows = cursor.fetchall()

    if not rows:
        print("[Fetcher] No pending PDFs found matching all filters.")
        print("          Filters: type_order=2, status=1, htmltopdfstatus=0, expiry_date>NOW()")
        cursor.close()
        conn.close()
        return []

    print(f"\n[Fetcher] Found {len(rows)} eligible row(s) to fetch.\n")
    fetched_ids = []

    # Ensure local SQLite is ready before looping
    init_db()
    init_pdf_jobs_db()

    for i, row in enumerate(rows, start=1):
        mysql_id = row["id"]
        content  = row["content"]
        pdf_url  = BASE_URL + quote(content, safe="")

        print(f"[Fetcher] ({i}/{len(rows)}) MySQL ID {mysql_id} : {content}")

        # ------------------------------------------------------------------ #
        # Create isolated queue folder                                         #
        # ------------------------------------------------------------------ #
        doc_id       = str(mysql_id)
        queue_folder = QUEUE_DIR / doc_id
        queue_folder.mkdir(parents=True, exist_ok=True)

        pdf_dest = queue_folder / "document.pdf"

        if pdf_dest.exists():
            size_kb = pdf_dest.stat().st_size / 1024
            print(f"           Already downloaded ({size_kb:.1f} KB) -- skipping.")
            fetched_ids.append(mysql_id)
            continue

        # ------------------------------------------------------------------ #
        # Download PDF                                                         #
        # ------------------------------------------------------------------ #
        try:
            response = requests.get(pdf_url, stream=True, timeout=120,
                                    headers={"User-Agent": "Mozilla/5.0"})
            response.raise_for_status()
        except Exception as e:
            print(f"           ERROR downloading: {e}")
            continue    # skip this row, try the next one

        with open(pdf_dest, "wb") as fh:
            for chunk in response.iter_content(chunk_size=8192):
                fh.write(chunk)

        size_kb = pdf_dest.stat().st_size / 1024
        print(f"           Saved ({size_kb:.1f} KB) -> {pdf_dest}")

        # ------------------------------------------------------------------ #
        # Log to local SQLite                                                  #
        # ------------------------------------------------------------------ #
        upsert_pdf_job(
            mysql_id=mysql_id,
            doc_id=doc_id,
            original_pdf=str(pdf_dest),
            status="DOWNLOADED",
        )

        # ------------------------------------------------------------------ #
        # Log to MySQL htmltopdfautomation                                     #
        # ------------------------------------------------------------------ #
        cursor.execute("""
            INSERT INTO htmltopdfautomation
                (mysql_id, original_pdf, status, created_by)
            VALUES (%s, %s, 'DOWNLOADED', 'system')
            ON DUPLICATE KEY UPDATE
                original_pdf = VALUES(original_pdf),
                status       = 'DOWNLOADED',
                updated_on   = NOW(),
                updated_by   = 'system'
        """, (mysql_id, pdf_url))
        conn.commit()

        fetched_ids.append(mysql_id)

    cursor.close()
    conn.close()

    # ------------------------------------------------------------------ #
    # Print summary and instructions                                        #
    # ------------------------------------------------------------------ #
    sep = "=" * 65
    print(f"\n{sep}")
    print(f" DOWNLOAD COMPLETE  ({len(fetched_ids)} PDF(s) ready)")
    print(sep)
    for mid in fetched_ids:
        folder = QUEUE_DIR / str(mid)
        print(f"  ID {mid:>6} -> {folder}")
    print(sep)
    print(f"""
 NEXT STEPS for EACH folder above:
   1. Open https://tools.pdf24.org/en/pdf-to-html
   2. Upload the document.pdf from the folder
   3. Download the resulting HTML
   4. Save it as document.html in THE SAME folder
      (e.g. storage/queue/2598/document.html)

 Once ALL folders have document.html, run:
   python scripts/pipeline.py --process
{sep}
""")

    return fetched_ids


if __name__ == "__main__":
    fetch_next(count=1)
