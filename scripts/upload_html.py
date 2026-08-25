import sys
import argparse
from pathlib import Path
import shutil

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from mysql_client import get_connection

def upload_edited_html(mysql_id):
    path_archive = ROOT / "storage" / "archive" / str(mysql_id) / "document.html"
    path_outputs = ROOT / "storage" / "outputs" / str(mysql_id) / "output.html"

    if path_archive.exists():
        html_path = path_archive
    elif path_outputs.exists():
        html_path = path_outputs
    else:
        print(f"Error: HTML file not found for ID {mysql_id} in archive or outputs.")
        sys.exit(1)

    html_content = html_path.read_text(encoding="utf-8")

    # Sync manual edits to storage/outputs/<id>/ directory as well
    out_dir = ROOT / "storage" / "outputs" / str(mysql_id)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "output.html").write_text(html_content, encoding="utf-8")

    archive_images = ROOT / "storage" / "archive" / str(mysql_id) / "images"
    out_images = out_dir / "images"
    if archive_images.exists():
        if out_images.exists():
            shutil.rmtree(out_images)
        shutil.copytree(archive_images, out_images)
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE tbl_html_to_pdf
        SET    html_content            = %s,
               script_html             = %s,
               updated_on              = NOW(),
               updated_by              = 'manual_edit'
        WHERE  mysql_id = %s
    """, (html_content, html_content, mysql_id))

    conn.commit()
    cursor.close()
    conn.close()
    print(f"Successfully uploaded manual edits for ID {mysql_id} to MySQL database!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Upload manually edited archive HTML back to MySQL database.")
    parser.add_argument("id", type=int, help="MySQL ID of the document")
    args = parser.parse_args()
    upload_edited_html(args.id)
