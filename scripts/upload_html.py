import sys
import argparse
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from mysql_client import get_connection

def upload_edited_html(mysql_id):
    html_path = ROOT / "storage" / "archive" / str(mysql_id) / "document.html"
    if not html_path.exists():
        print(f"Error: Archive HTML not found for ID {mysql_id} at {html_path}")
        sys.exit(1)
        
    html_content = html_path.read_text(encoding="utf-8")
    
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
