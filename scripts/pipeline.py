"""
pipeline.py
Master orchestrator for the PDF automation pipeline.

Usage:
    python scripts/pipeline.py --fetch      Fetch the next PDF from MySQL
    python scripts/pipeline.py --process    Process all HTML-ready queue folders
    python scripts/pipeline.py --status     Show current job statuses from MySQL

Typical workflow (repeat for each document):
    Step 1:  python scripts/pipeline.py --fetch
    Step 2:  [Convert PDF to HTML with PDF24, save as storage/queue/<id>/document.html]
    Step 3:  python scripts/pipeline.py --process
    Step 4:  Open index.html to review results
"""

import sys
import argparse
import traceback
from pathlib import Path

# Force UTF-8 output on Windows terminals
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Ensure scripts/ is on the import path regardless of CWD
scripts_dir = Path(__file__).parent
if str(scripts_dir) not in sys.path:
    sys.path.append(str(scripts_dir))

from db_manager       import (init_db, init_pdf_jobs_db,
                              upsert_pdf_job, update_pdf_job_status)
from mysql_fetcher    import fetch_next
from mysql_logger     import log_html_ready, log_processing, log_completed, log_failed
from dashboard        import generate_dashboard

from pymupdf_image_extractor import extract_images
from html_reconstructor      import reconstruct_html
from preprocessor            import clean_html
from chunker                 import chunk_html, MAX_CHARS
from gemini_runner           import run_gemini
from merger                  import merge_chunks

ROOT        = Path(__file__).parent.parent
QUEUE_DIR   = ROOT / "storage" / "queue"
OUTPUTS_DIR = ROOT / "storage" / "outputs"
ARCHIVE_DIR = ROOT / "storage" / "archive"


# ─────────────────────────────────────────────────────────────────────────────
# --fetch
# ─────────────────────────────────────────────────────────────────────────────

def do_fetch(count: int = 1, target_ids: list[int] = None):
    """Fetch the next N unprocessed PDFs from MySQL."""
    print("\n" + "=" * 65)
    print(f" PIPELINE - FETCH MODE  (count={count}, ids={target_ids})")
    print("=" * 65)

    init_db()
    init_pdf_jobs_db()

    fetched_ids = fetch_next(count=count, target_ids=target_ids)

    if not fetched_ids:
        print("\n[Pipeline] Nothing to fetch. All eligible PDFs are processed.")
    else:
        print(f"\n[Pipeline] {len(fetched_ids)} PDF(s) ready for PDF24 conversion.")
        print(f"[Pipeline] After converting, run: python scripts/pipeline.py --process")


# ─────────────────────────────────────────────────────────────────────────────
# --process
# ─────────────────────────────────────────────────────────────────────────────

def do_process(limit: int = None):
    """Process all PDF files in QUEUE_DIR that have a corresponding .html file."""
    print("\n" + "=" * 65)
    print(" PIPELINE - PROCESS MODE")
    print("=" * 65)

    init_db()
    init_pdf_jobs_db()

    if not QUEUE_DIR.exists():
        print("[Pipeline] Queue directory is empty. Run --fetch first.")
        return

    processed_any = False

    # Find all .pdf files in QUEUE_DIR
    pdf_files = sorted(QUEUE_DIR.glob("*.pdf"))
    if limit is not None and limit > 0:
        print(f"[Pipeline] Limiting processing to first {limit} item(s).")
        pdf_files = pdf_files[:limit]

    for pdf_path in pdf_files:
        html_path = pdf_path.with_suffix(".html")
        filename = pdf_path.name

        if not html_path.exists():
            print(f"\n[Pipeline] ⏳ {filename} — corresponding HTML missing.")
            print(f"           Convert this PDF with PDF24 and save to:")
            print(f"           {html_path}")
            continue

        # Look up mysql_id by querying the database for this filename
        mysql_id = None
        from mysql_client import get_connection
        try:
            conn = get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute(
                "SELECT id FROM tbl_studymaterial_lang_map WHERE content = %s LIMIT 1",
                (filename,)
            )
            row = cursor.fetchone()
            if row:
                mysql_id = row["id"]
            cursor.close()
            conn.close()
        except Exception as e:
            print(f"[Pipeline] Warning: Could not resolve MySQL ID for {filename}: {e}")

        if not mysql_id:
            print(f"[Pipeline] Skipping {filename}: Could not find MySQL ID in tbl_studymaterial_lang_map.")
            continue

        doc_id = str(mysql_id)

        # This pair has both files — process it
        print(f"\n{'=' * 65}")
        print(f" Processing: {filename} (ID: {doc_id})")
        print(f"{'=' * 65}")

        # Update status: HTML is ready
        log_html_ready(mysql_id, str(html_path))
        update_pdf_job_status(mysql_id, "HTML_READY")

        # Update status: pipeline starting
        log_processing(mysql_id)
        update_pdf_job_status(mysql_id, "PROCESSING")

        try:
            output_file = _run_pipeline(doc_id, pdf_path, html_path)

            # Read the full output HTML content
            html_content = output_file.read_text(encoding="utf-8")

            log_completed(mysql_id, str(output_file), html_content)
            update_pdf_job_status(mysql_id, "COMPLETED")

            # Move processed PDF and HTML from queue to archive
            _archive(pdf_path, html_path, doc_id)

            processed_any = True
            print(f"[Pipeline] SUCCESS {filename} -> COMPLETED")

        except Exception:
            tb = traceback.format_exc()
            print(f"[Pipeline] FAILED  {filename} -> FAILED\n{tb}")
            log_failed(mysql_id, tb)
            update_pdf_job_status(mysql_id, "FAILED")

        # Regenerate dashboard after each document so progress is visible
        try:
            generate_dashboard()
        except Exception as dash_err:
            print(f"[Pipeline] WARN: dashboard update failed: {dash_err}")

    if not processed_any:
        print("\n[Pipeline] No documents ready to process.")
        print("[Pipeline] Run --fetch first, then add HTML files.")


def _run_pipeline(doc_id: str, pdf_path: Path, html_path: Path) -> Path:
    """Run the complete 6-step conversion pipeline for one isolated document."""
    doc_out_dir   = OUTPUTS_DIR / doc_id
    image_dir     = doc_out_dir / "images"
    temp_dir      = doc_out_dir / "temp"
    chunk_dir     = doc_out_dir / "chunks"
    processed_dir = doc_out_dir / "processed"

    for d in [image_dir, temp_dir, chunk_dir, processed_dir]:
        d.mkdir(parents=True, exist_ok=True)

    image_map_file        = temp_dir / "image_map.json"
    reconstructed_html    = temp_dir / "preprocessed.html"
    cleaned_html          = temp_dir / "cleaned.html"
    final_output_file     = doc_out_dir / "output.html"

    print(f"\n--- Step 1/6 : Extract Images from PDF ---")
    skip_cover = extract_images(
        pdf_file=pdf_path,
        image_dir=image_dir,
        image_map_path=image_map_file,
    )

    print(f"\n--- Step 2/6 : Reconstruct HTML Structure ---")
    reconstruct_html(
        input_html=html_path,
        image_map_path=image_map_file,
        output_html=reconstructed_html,
        skip_cover=skip_cover,
    )

    print(f"\n--- Step 3/6 : Clean HTML Markup ---")
    clean_html(
        input_file=reconstructed_html,
        output_file=cleaned_html,
    )

    print(f"\n--- Step 4/6 : Chunk HTML ---")
    chunk_html(
        input_file=cleaned_html,
        output_dir=chunk_dir,
        max_chars=MAX_CHARS,
    )

    print(f"\n--- Step 5/6 : Process Chunks with Gemini ---")
    run_gemini(
        chunk_dir=chunk_dir,
        processed_dir=processed_dir,
        image_dir=image_dir,
        figure_dir=None,
    )

    print(f"\n--- Step 6/6 : Merge & Finalise ---")
    merge_chunks(
        processed_dir=processed_dir,
        output_file=final_output_file,
        image_map_file=image_map_file,
        assets_dir=ROOT / "assets",
    )

    return final_output_file


def _archive(pdf_path: Path, html_path: Path, doc_id: str):
    """Move processed PDF and HTML files from queue to storage/archive/<doc_id>/."""
    dest_dir = ARCHIVE_DIR / doc_id
    dest_dir.mkdir(parents=True, exist_ok=True)

    import shutil
    # Move PDF
    try:
        shutil.move(str(pdf_path), str(dest_dir / "document.pdf"))
        print(f"[Pipeline] Archived PDF -> {dest_dir / 'document.pdf'}")
    except Exception as e:
        print(f"[Pipeline] Archive PDF warning (non-fatal): {e}")

    # Move HTML
    try:
        shutil.move(str(html_path), str(dest_dir / "document.html"))
        print(f"[Pipeline] Archived HTML -> {dest_dir / 'document.html'}")
    except Exception as e:
        print(f"[Pipeline] Archive HTML warning (non-fatal): {e}")



# ─────────────────────────────────────────────────────────────────────────────
# --status
# ─────────────────────────────────────────────────────────────────────────────

def do_status():
    """Print a summary of all jobs from MySQL htmltopdfautomation."""
    from mysql_client import get_connection
    conn   = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT   pdf_id, mysql_id, status,
                 created_on, updated_on,
                 CHAR_LENGTH(html_content) AS content_chars
        FROM     htmltopdfautomation
        ORDER BY pdf_id DESC
        LIMIT    50
    """)
    rows = cursor.fetchall()

    # Also count pending in source table
    cursor.execute("""
        SELECT COUNT(*) AS cnt
        FROM   tbl_studymaterial_lang_map
        WHERE  type_order = 2 AND htmltopdfstatus = 0
    """)
    pending_cnt = cursor.fetchone()["cnt"]

    cursor.close()
    conn.close()

    print(f"\n{'='*80}")
    print(f" PDF Automation — Job Status")
    print(f" Pending in MySQL (not yet fetched): {pending_cnt}")
    print(f"{'='*80}")
    print(f"{'#':>4}  {'MySQL ID':>9}  {'Status':>12}  {'Created':>19}  {'Updated':>19}  {'HTML chars':>12}")
    print(f"{'-'*80}")
    for r in rows:
        chars = r["content_chars"] or 0
        print(
            f"{r['pdf_id']:>4}  {str(r['mysql_id']):>9}  "
            f"{r['status']:>12}  {str(r['created_on'])[:19]:>19}  "
            f"{str(r['updated_on'])[:19]:>19}  {chars:>12,}"
        )
    print(f"{'='*80}\n")


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="PDF Automation Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/pipeline.py --fetch      # Download next PDF from MySQL
  python scripts/pipeline.py --process    # Convert all HTML-ready queue items
  python scripts/pipeline.py --status     # Show job status table
        """,
    )
    parser.add_argument("--fetch",   action="store_true", help="Fetch next PDF(s) from MySQL")
    parser.add_argument("--count",   type=int, default=1,  help="Number of PDFs to fetch (use with --fetch, default: 1)")
    parser.add_argument("--ids",     type=str, help="Comma-separated specific MySQL IDs to fetch (e.g. 1474,7908)")
    parser.add_argument("--process", action="store_true", help="Process HTML-ready queue items")
    parser.add_argument("--limit",   type=int, help="Limit the number of items to process (use with --process)")
    parser.add_argument("--status",  action="store_true", help="Show current job statuses")
    args = parser.parse_args()

    if args.fetch:
        target_ids = None
        if args.ids:
            target_ids = [int(x.strip()) for x in args.ids.split(",") if x.strip().isdigit()]
        do_fetch(count=args.count, target_ids=target_ids)
    elif args.process:
        do_process(limit=args.limit)
    elif args.status:
        do_status()
    else:
        parser.print_help()
