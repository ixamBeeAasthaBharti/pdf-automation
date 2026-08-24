"""
run.py
Fully automatic PDF to HTML conversion pipeline.

Usage:
    python scripts/run.py                # Convert ALL pending PDFs from the query
    python scripts/run.py --count 5      # Convert next 5 pending PDFs
    python scripts/run.py --id 5024      # Convert a specific PDF by MySQL ID
    python scripts/run.py --status       # Show conversion status summary

Pipeline steps (per document):
    1. Fetch pending IDs from MySQL (htmltopdfstatus = 0)
    2. Download PDF  ->  storage/queue/<id>/document.pdf
    3. Convert PDF   ->  storage/queue/<id>/document.html  (via pdf_html.py)
    4. Upload HTML   ->  MySQL htmltopdfautomation  +  sets htmltopdfstatus = 1
    5. Archive       ->  storage/queue/<id>/  moved to  storage/archive/<id>/
    On failure: sets htmltopdfstatus = 2, logs FAILED in htmltopdfautomation
"""

import sys
import shutil
import argparse
import traceback
from pathlib import Path
from urllib.parse import quote

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

scripts_dir = Path(__file__).parent
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))

import requests
from mysql_client import get_connection
from mysql_logger import log_completed

ROOT        = Path(__file__).parent.parent
QUEUE_DIR   = ROOT / "storage" / "queue"
ARCHIVE_DIR = ROOT / "storage" / "archive"

BASE_PDF_URL = "https://static.ixambee.com/public/miscellaneous-pdf/"

# Hardcoded default queries to use if queries.sql is missing
DEFAULT_PENDING_QUERY = """
    SELECT id, content FROM tbl_studymaterial_lang_map
    WHERE content_id IN (
        SELECT content_id FROM tbl_studymaterial_mapping_with_esc
        WHERE esc_id IN (
            SELECT id FROM tbl_studymaterial_esc_s
            WHERE exam_id = 39 AND package_id = 841 AND chapter_id = 310 AND status = 1
        )
    )
    AND type_order = 2 AND status = 1 AND html_status = 0
    ORDER BY id ASC
"""

DEFAULT_STATUS_QUERY = """
    SELECT SUM(html_status=0) AS pending, SUM(html_status=1) AS done,
           SUM(html_status=2) AS failed, COUNT(*) AS total
    FROM tbl_studymaterial_lang_map
    WHERE content_id IN (
        SELECT content_id FROM tbl_studymaterial_mapping_with_esc
        WHERE esc_id IN (
            SELECT id FROM tbl_studymaterial_esc_s
            WHERE exam_id = 39 AND package_id = 841 AND chapter_id = 310 AND status = 1
        )
    ) AND type_order = 2 AND status = 1
"""


def load_queries_from_file():
    """
    Loads PENDING_QUERY and STATUS_QUERY from queries.sql in the root directory.
    Falls back to defaults if the file is missing or not parseable.
    """
    sql_path = Path(__file__).parent.parent / "queries.sql"
    if not sql_path.exists():
        return DEFAULT_PENDING_QUERY, DEFAULT_STATUS_QUERY

    try:
        content = sql_path.read_text(encoding="utf-8")
        queries = {}
        current_key = None
        current_lines = []
        
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("-- [") and stripped.endswith("]"):
                if current_key and current_lines:
                    queries[current_key] = "\n".join(current_lines).strip()
                current_key = stripped[4:-1].strip()
                current_lines = []
            elif current_key:
                current_lines.append(line)
                
        if current_key and current_lines:
            queries[current_key] = "\n".join(current_lines).strip()
            
        pending = queries.get("PENDING_QUERY", DEFAULT_PENDING_QUERY)
        status = queries.get("STATUS_QUERY", DEFAULT_STATUS_QUERY)
        return pending, status
    except Exception as e:
        print(f"Warning: Failed to parse queries.sql: {e}. Using defaults.", file=sys.stderr)
        return DEFAULT_PENDING_QUERY, DEFAULT_STATUS_QUERY

# Dynamically loaded queries
PENDING_QUERY, STATUS_QUERY = load_queries_from_file()


def fetch_pending_ids(count=None, target_id=None):
    conn   = get_connection()
    cursor = conn.cursor(dictionary=True)
    if target_id:
        cursor.execute("""
            SELECT id, content FROM tbl_studymaterial_lang_map
            WHERE id = %s AND type_order = 2 AND status = 1
        """, (target_id,))
    else:
        query = PENDING_QUERY
        if count:
            query += f" LIMIT {int(count)}"
        cursor.execute(query)
    rows = cursor.fetchall()
    cursor.close(); conn.close()
    return rows


def init_job_record(mysql_id, pdf_url):
    try:
        conn = get_connection(); cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO tbl_html_to_pdf (mysql_id, original_pdf, status, created_by)
            VALUES (%s, %s, 'PROCESSING', 'system')
            ON DUPLICATE KEY UPDATE
                original_pdf=VALUES(original_pdf), status='PROCESSING',
                updated_on=NOW(), updated_by='system'
        """, (mysql_id, pdf_url))
        conn.commit(); cursor.close(); conn.close()
    except Exception as e:
        print(f"  [Init   ] Warning: {e}")


def download_pdf(mysql_id, content):
    queue_folder = QUEUE_DIR / str(mysql_id)
    queue_folder.mkdir(parents=True, exist_ok=True)
    pdf_dest = queue_folder / "document.pdf"
    if pdf_dest.exists():
        print(f"  [Download] Already exists ({pdf_dest.stat().st_size/1024:.1f} KB) -- skipping.")
        return pdf_dest
    pdf_url = BASE_PDF_URL + quote(content, safe="")
    print(f"  [Download] {pdf_url}")
    response = requests.get(pdf_url, stream=True, timeout=120, headers={"User-Agent": "Mozilla/5.0"})
    response.raise_for_status()
    with open(pdf_dest, "wb") as fh:
        for chunk in response.iter_content(chunk_size=8192):
            fh.write(chunk)
    print(f"  [Download] Saved ({pdf_dest.stat().st_size/1024:.1f} KB)")
    return pdf_dest


def convert_pdf(mysql_id, pdf_path):
    import pdf_html

    print("USING PDF HTML:", pdf_html.__file__)

    html_path = QUEUE_DIR / str(mysql_id) / "document.html"
    print(f"  [Convert ] {pdf_path.name} -> {html_path.name}")

    pdf_html.convert(pdf_path, html_path, start=2, end=None)

    print(f"  [Convert ] Done ({html_path.stat().st_size/1024:.1f} KB)")
    return html_path


def upload_html(mysql_id, html_path):
    html_content = html_path.read_text(encoding="utf-8")
    print(f"  [Upload  ] {len(html_content):,} chars -> MySQL...")
    log_completed(mysql_id, str(html_path), html_content)
    print(f"  [Upload  ] html_status = 1")


def archive_folder(mysql_id):
    src = QUEUE_DIR / str(mysql_id)
    if not src.exists():
        return
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    dest = ARCHIVE_DIR / str(mysql_id)
    if dest.exists():
        shutil.rmtree(dest)
    shutil.move(str(src), str(dest))
    print(f"  [Archive ] -> {dest}")


def mark_failed(mysql_id, error):
    short_err = (error or "Unknown error")[:500]
    try:
        conn = get_connection(); cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO tbl_html_to_pdf (mysql_id, status, created_by)
            VALUES (%s, 'FAILED', 'system')
            ON DUPLICATE KEY UPDATE status='FAILED', updated_on=NOW(), updated_by='system'
        """, (mysql_id,))
        cursor.execute("""
            UPDATE tbl_studymaterial_lang_map SET html_status=2 WHERE id=%s
        """, (mysql_id,))
        conn.commit(); cursor.close(); conn.close()
        print(f"  [Failed  ] ID {mysql_id} -> html_status=2")
    except Exception as e:
        print(f"  [Failed  ] Could not write to DB: {e}")


def process_one(mysql_id, content):
    print(f"\n{'='*65}")
    print(f"  ID {mysql_id}  |  {content}")
    print(f"{'='*65}")
    pdf_url = BASE_PDF_URL + quote(content, safe="")
    init_job_record(mysql_id, pdf_url)
    try:
        pdf_path  = download_pdf(mysql_id, content)
        html_path = convert_pdf(mysql_id, pdf_path)
        upload_html(mysql_id, html_path)
        archive_folder(mysql_id)
        print(f"\n  OK  ID {mysql_id} -- COMPLETE")
        return True
    except Exception:
        tb = traceback.format_exc()
        print(f"\n  FAIL  ID {mysql_id}\n{tb}")
        mark_failed(mysql_id, tb)
        archive_folder(mysql_id)
        return False


def show_status():
    conn = get_connection(); cursor = conn.cursor(dictionary=True)
    cursor.execute(STATUS_QUERY)
    counts = cursor.fetchone()
    cursor.execute("""
        SELECT mysql_id, status, created_on, updated_on,
               CHAR_LENGTH(html_content) AS content_chars
        FROM   tbl_html_to_pdf ORDER BY mysql_id DESC LIMIT 30
    """)
    rows = cursor.fetchall()
    cursor.close(); conn.close()


    icons = {"COMPLETED": "[OK]", "FAILED": "[!!]", "PROCESSING": "[..]"}
    sep = "=" * 70
    print(f"\n{sep}")
    print("  PDF Pipeline Status")
    print(f"  Total: {counts['total']}  |  Pending: {counts['pending']}  |  Done: {counts['done']}  |  Failed: {counts['failed']}")
    print(sep)
    if rows:
        print(f"  {'MySQL ID':>9}  {'Status':>14}  {'Created':>19}  {'HTML chars':>12}")
        print(f"  {'-'*60}")
        for r in rows:
            chars = r["content_chars"] or 0
            icon  = icons.get(r["status"], "    ")
            print(f"  {str(r['mysql_id']):>9}  {icon} {r['status']:>10}  {str(r['created_on'])[:19]:>19}  {chars:>12,}")
    print(f"{sep}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="PDF -> HTML Automation Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/run.py                 Convert all pending PDFs
  python scripts/run.py --count 5       Convert next 5 pending PDFs
  python scripts/run.py --id 5024       Convert one specific PDF by MySQL ID
  python scripts/run.py --status        Show status summary
        """
    )
    parser.add_argument("--count",   type=int,            help="Max PDFs to process in this run")
    parser.add_argument("--id",      type=int,            help="Process a specific MySQL ID")
    parser.add_argument("--status",  action="store_true", help="Show status summary and exit")
    args = parser.parse_args()

    if args.status:
        show_status()
        sys.exit(0)

    rows = fetch_pending_ids(count=args.count, target_id=args.id)
    if not rows:
        print("\n[Pipeline] No pending PDFs found. All done!")
        sys.exit(0)

    print(f"\n[Pipeline] {len(rows)} PDF(s) queued.")
    succeeded = failed = 0
    for row in rows:
        if process_one(row["id"], row["content"]):
            succeeded += 1
        else:
            failed += 1

    print(f"\n{'='*65}")
    print(f"  PIPELINE COMPLETE  --  {succeeded} OK  |  {failed} failed")
    print(f"{'='*65}\n")
