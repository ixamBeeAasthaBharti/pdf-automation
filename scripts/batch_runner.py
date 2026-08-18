"""
batch_runner.py
Main coordinator for multi-document batch conversion pipeline.
Scans storage/queue/ for subfolders containing document.pdf + document.html,
registers them, processes them in isolation, updates metadata.db,
and regenerates the dashboard.

Run from workspace root:
    python scripts/batch_runner.py
"""

import sys
import traceback
from pathlib import Path

# Add current scripts directory to python path for easy relative imports
scripts_dir = Path(__file__).parent
if str(scripts_dir) not in sys.path:
    sys.path.append(str(scripts_dir))

from db_manager import init_db, register_document, update_status, get_pending, reset_stuck
from dashboard import generate_dashboard
from pymupdf_image_extractor import extract_images
from html_reconstructor import reconstruct_html
from preprocessor import clean_html
from chunker import chunk_html, MAX_CHARS
from gemini_runner import run_gemini
from merger import merge_chunks

ROOT = Path(__file__).parent.parent
QUEUE_DIR = ROOT / "storage" / "queue"
OUTPUTS_DIR = ROOT / "storage" / "outputs"


def scan_and_register():
    """Scan queue directory and register valid document folders."""
    print(f"\n[Batch] Scanning {QUEUE_DIR} for new documents...")
    if not QUEUE_DIR.exists():
        QUEUE_DIR.mkdir(parents=True, exist_ok=True)
        print(f"[Batch] Created queue directory: {QUEUE_DIR}")
        return

    registered_count = 0
    skipped_count = 0

    # Look at direct subdirectories in queue/
    for subfolder in QUEUE_DIR.iterdir():
        if not subfolder.is_dir():
            continue

        doc_id = subfolder.name
        pdf_path = subfolder / "document.pdf"
        html_path = subfolder / "document.html"

        # Check if both required files are present
        if pdf_path.exists() and html_path.exists():
            register_document(doc_id, pdf_path, html_path)
            registered_count += 1
        else:
            missing = []
            if not pdf_path.exists():
                missing.append("document.pdf")
            if not html_path.exists():
                missing.append("document.html")
            print(f"   [WARN] Skipping '{doc_id}': missing {', '.join(missing)}")
            skipped_count += 1

    print(f"[Batch] Scan complete. Registered/Existing: {registered_count}, Skipped: {skipped_count}")


def process_document(doc_id: str, pdf_path: Path, html_path: Path):
    """Process a single document through the complete conversion pipeline in isolation."""
    print(f"\n{'=' * 70}")
    print(f"PROCESSING DOCUMENT: {doc_id}")
    print(f"PDF  : {pdf_path}")
    print(f"HTML : {html_path}")
    print(f"{'=' * 70}")

    # Set up isolated directories
    doc_out_dir = OUTPUTS_DIR / doc_id
    image_dir = doc_out_dir / "images"
    temp_dir = doc_out_dir / "temp"
    chunk_dir = doc_out_dir / "chunks"
    processed_dir = doc_out_dir / "processed"

    for d in [image_dir, temp_dir, chunk_dir, processed_dir]:
        d.mkdir(parents=True, exist_ok=True)

    image_map_file = temp_dir / "image_map.json"
    reconstructed_html_file = temp_dir / "preprocessed.html"
    cleaned_html_file = temp_dir / "cleaned.html"
    final_output_file = doc_out_dir / "output.html"

    # Step 1: Extract Images
    print("\n--- Step 1: Extracting Images from PDF ---")
    extract_images(
        pdf_file=pdf_path,
        image_dir=image_dir,
        image_map_path=image_map_file
    )

    # Step 2: Reconstruct HTML structure
    print("\n--- Step 2: Reconstructing HTML Structure ---")
    reconstruct_html(
        input_html=html_path,
        image_map_path=image_map_file,
        output_html=reconstructed_html_file
    )

    # Step 3: Clean/Preprocess HTML
    print("\n--- Step 3: Cleaning HTML Markup ---")
    clean_html(
        input_file=reconstructed_html_file,
        output_file=cleaned_html_file
    )

    # Step 4: Chunk HTML for LLM window limits
    print("\n--- Step 4: Chunking HTML ---")
    chunk_html(
        input_file=cleaned_html_file,
        output_dir=chunk_dir,
        max_chars=MAX_CHARS
    )

    # Step 5: Process through Gemini
    print("\n--- Step 5: Processing Chunks with Gemini ---")
    run_gemini(
        chunk_dir=chunk_dir,
        processed_dir=processed_dir,
        image_dir=image_dir,
        figure_dir=None # Let it fallback to ROOT/figures if figures metadata exists
    )

    # Step 6: Merge chunks back to final page
    print("\n--- Step 6: Merging and Finalizing Output ---")
    merge_chunks(
        processed_dir=processed_dir,
        output_file=final_output_file,
        image_map_file=image_map_file,
        assets_dir=ROOT / "assets"
    )

    print(f"\n[OK] Successfully completed: {doc_id}")
    return final_output_file


def run_batch():
    """Main batch processing execution loop."""
    init_db()
    reset_stuck()
    scan_and_register()

    pending = get_pending()
    if not pending:
        print("\n[Batch] No pending documents to process.")
        generate_dashboard()
        return

    print(f"\n[Batch] Found {len(pending)} pending document(s) to process.")

    success_count = 0
    failure_count = 0

    for doc_id, pdf_str, html_str in pending:
        pdf_path = Path(pdf_str)
        html_path = Path(html_str)

        update_status(doc_id, "PROCESSING")

        try:
            output_file = process_document(doc_id, pdf_path, html_path)
            update_status(doc_id, "COMPLETED", output_path=output_file)
            success_count += 1
        except Exception as e:
            tb = traceback.format_exc()
            print(f"\n[ERROR] Failed to process document '{doc_id}':")
            print(tb)
            update_status(doc_id, "FAILED", error_log=tb)
            failure_count += 1

        # Regenerate dashboard after each document so progress is visible immediately
        try:
            generate_dashboard()
        except Exception as db_err:
            print(f"[WARN] Failed to generate dashboard: {db_err}")

    print("\n" + "=" * 50)
    print("BATCH PROCESSING COMPLETE SUMMARY")
    print(f"   Processed: {success_count + failure_count}")
    print(f"   Success  : {success_count}")
    print(f"   Failure  : {failure_count}")
    print("=" * 50)


if __name__ == "__main__":
    run_batch()
