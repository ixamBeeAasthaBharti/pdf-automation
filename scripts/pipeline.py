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


from pymupdf_image_extractor import extract_images
from html_reconstructor      import reconstruct_html
from preprocessor            import clean_html
from chunker                 import chunk_html, MAX_CHARS
from gemini_runner           import run_gemini
from merger                  import merge_chunks
from aspose_converter        import convert_pdf_to_html
from aspose_html_normalizer   import normalize_aspose_html

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
        print(f"\n[Pipeline] {len(fetched_ids)} PDF(s) downloaded.")
        print(f"[Pipeline] Run: python scripts/pipeline.py --process (or --auto)")


# ─────────────────────────────────────────────────────────────────────────────
# --process
# ─────────────────────────────────────────────────────────────────────────────

def do_process():
    """Process all queue folders that have document.pdf using Aspose + Gemini pipeline."""
    print("\n" + "=" * 65)
    print(" PIPELINE - PROCESS MODE")
    print("=" * 65)

    init_db()
    init_pdf_jobs_db()

    if not QUEUE_DIR.exists():
        print("[Pipeline] Queue directory is empty. Run --fetch first.")
        return

    processed_any = False

    for subfolder in sorted(QUEUE_DIR.iterdir()):
        if not subfolder.is_dir():
            continue

        doc_id    = subfolder.name
        pdf_path  = subfolder / "document.pdf"

        if not pdf_path.exists():
            continue                          # not a valid queue entry

        print(f"\n{'=' * 65}")
        print(f" Processing: {doc_id}")
        print(f"{'=' * 65}")

        mysql_id = int(doc_id) if doc_id.isdigit() else None

        # Update status: pipeline starting
        if mysql_id:
            log_processing(mysql_id)
            update_pdf_job_status(mysql_id, "PROCESSING")

        try:
            output_file = _run_pipeline(doc_id, pdf_path)

            # Read the full output HTML content
            html_content = output_file.read_text(encoding="utf-8")

            if mysql_id:
                log_completed(mysql_id, str(output_file), html_content)
                update_pdf_job_status(mysql_id, "COMPLETED")

            # Move processed queue folder to archive
            _archive(subfolder, doc_id)

            processed_any = True
            print(f"[Pipeline] SUCCESS {doc_id} -> COMPLETED")

        except Exception:
            tb = traceback.format_exc()
            print(f"[Pipeline] FAILED  {doc_id} -> FAILED\n{tb}")
            if mysql_id:
                log_failed(mysql_id, tb)
                update_pdf_job_status(mysql_id, "FAILED")

        pass

    if not processed_any:

        print("\n[Pipeline] No documents ready to process.")


def _run_pipeline(doc_id: str, pdf_path: Path) -> Path:
    """Run the complete 7-step conversion pipeline for one isolated document using Aspose."""
    doc_out_dir   = OUTPUTS_DIR / doc_id
    image_dir     = doc_out_dir / "images"
    temp_dir      = doc_out_dir / "temp"
    aspose_dir    = temp_dir / "aspose"
    chunk_dir     = doc_out_dir / "chunks"
    processed_dir = doc_out_dir / "processed"

    for d in [image_dir, temp_dir, aspose_dir, chunk_dir, processed_dir]:
        d.mkdir(parents=True, exist_ok=True)

    image_map_file        = temp_dir / "image_map.json"
    normalized_html       = temp_dir / "normalized.html"
    cleaned_html          = temp_dir / "cleaned.html"
    final_output_file     = doc_out_dir / "output.html"

    # Step 1: Aspose PDF -> HTML
    print(f"\n--- Step 1/7 : Convert PDF with Aspose Cloud ---")
    raw_aspose_html = convert_pdf_to_html(pdf_path, aspose_dir)

    # Step 2: Extract Images from PDF via PyMuPDF
    print(f"\n--- Step 2/7 : Extract Images from PDF ---")
    extract_images(
        pdf_file=pdf_path,
        image_dir=image_dir,
        image_map_path=image_map_file,
    )

    # Step 3: Normalize Aspose HTML
    print(f"\n--- Step 3/7 : Normalize Aspose HTML ---")
    normalize_aspose_html(
        input_html_path=raw_aspose_html,
        output_html_path=normalized_html,
        image_map_path=image_map_file,
    )

    # Step 4: Clean HTML Markup
    print(f"\n--- Step 4/7 : Clean HTML Markup ---")
    clean_html(
        input_file=normalized_html,
        output_file=cleaned_html,
    )

    # Step 5: Chunk HTML
    print(f"\n--- Step 5/7 : Chunk HTML ---")
    chunk_html(
        input_file=cleaned_html,
        output_dir=chunk_dir,
        max_chars=MAX_CHARS,
    )

    # Step 6: Process Chunks with Gemini
    print(f"\n--- Step 6/7 : Process Chunks with Gemini ---")
    run_gemini(
        chunk_dir=chunk_dir,
        processed_dir=processed_dir,
        image_dir=image_dir,
        figure_dir=None,
    )

    # Step 7: Merge & Finalise
    print(f"\n--- Step 7/7 : Merge & Finalise ---")
    merge_chunks(
        processed_dir=processed_dir,
        output_file=final_output_file,
        image_map_file=image_map_file,
        assets_dir=ROOT / "assets",
    )

    return final_output_file


def _archive(queue_folder: Path, doc_id: str):
    """Move a processed queue folder to storage/archive/."""
    if not queue_folder.exists():
        print(f"[Pipeline] Queue folder {queue_folder} already moved/archived.")
        return
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    dest = ARCHIVE_DIR / doc_id
    if dest.exists():
        import shutil
        shutil.rmtree(dest)
    try:
        import shutil
        shutil.move(str(queue_folder), str(dest))
        print(f"[Pipeline] Archived input files -> {dest}")
    except Exception as e:
        print(f"[Pipeline] Archive warning (non-fatal): {e}")



# ─────────────────────────────────────────────────────────────────────────────
# --status
# ─────────────────────────────────────────────────────────────────────────────

def do_status():
    """Print a summary of all jobs from MySQL tbl_html_to_pdf."""
    from mysql_client import get_connection
    conn   = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT   pdf_id, mysql_id, status,
                 created_on, updated_on,
                 CHAR_LENGTH(html_content) AS content_chars
        FROM     tbl_html_to_pdf
        ORDER BY pdf_id DESC
        LIMIT    50
    """)
    rows = cursor.fetchall()

    # Also count pending in source table
    cursor.execute("""
        SELECT COUNT(*) AS cnt
        FROM   tbl_studymaterial_lang_map
        WHERE  type_order = 2 AND html_status = 0
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


def do_auto(count: int = 1, target_ids: list[int] = None):
    """Fetch next PDF(s) from MySQL, auto-convert PDF->HTML with Aspose Cloud, and process end-to-end."""
    do_fetch(count=count, target_ids=target_ids)
    do_process()


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="PDF Automation Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/pipeline.py --auto       # Fetch, auto-convert PDF->HTML via Aspose, and process
  python scripts/pipeline.py --fetch      # Download next PDF from MySQL
  python scripts/pipeline.py --process    # Auto-convert missing HTMLs & process queue items
  python scripts/pipeline.py --status     # Show job status table
        """,
    )
    parser.add_argument("--auto",    action="store_true", help="Fetch, auto-convert PDF->HTML via Aspose, and process end-to-end")
    parser.add_argument("--fetch",   action="store_true", help="Fetch next PDF(s) from MySQL")
    parser.add_argument("--count",   type=int, default=1,  help="Number of PDFs to fetch/process (default: 1)")
    parser.add_argument("--ids",     type=str, help="Comma-separated specific MySQL IDs to fetch (e.g. 1474,7908)")
    parser.add_argument("--process", action="store_true", help="Process queue items (auto-converts PDF to HTML if missing)")
    parser.add_argument("--status",  action="store_true", help="Show current job statuses")
    args = parser.parse_args()

    target_ids = None
    if args.ids:
        target_ids = [int(x.strip()) for x in args.ids.split(",") if x.strip().isdigit()]

    if args.auto:
        do_auto(count=args.count, target_ids=target_ids)
    elif args.fetch:
        do_fetch(count=args.count, target_ids=target_ids)
    elif args.process:
        do_process()
    elif args.status:
        do_status()
    else:
        parser.print_help()

