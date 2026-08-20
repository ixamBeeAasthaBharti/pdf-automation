import sys
from pathlib import Path

# Add scripts directory to path
scripts_dir = Path(__file__).parent
if str(scripts_dir) not in sys.path:
    sys.path.append(str(scripts_dir))

from mysql_logger import log_completed

import argparse
from mysql_logger import log_completed

def main():
    parser = argparse.ArgumentParser(description="Upload converted HTML to MySQL.")
    parser.add_argument("id", type=int, nargs="?", default=None, help="MySQL ID of the document (e.g. 1525)")
    parser.add_argument("html", type=Path, nargs="?", default=None, help="Path to the HTML file to upload")
    args = parser.parse_args()
    
    mysql_id = args.id
    html_path = args.html
    
    # Auto-detection if arguments are missing
    if mysql_id is None:
        queue_dir = Path(__file__).parent.parent / "storage" / "queue"
        eligible_folders = []
        if queue_dir.exists():
            for folder in queue_dir.iterdir():
                if folder.is_dir() and folder.name.isdigit():
                    html_file = folder / "document.html"
                    if html_file.exists():
                        eligible_folders.append((folder.name, html_file))
                        
        if len(eligible_folders) == 1:
            mysql_id = int(eligible_folders[0][0])
            html_path = eligible_folders[0][1]
            print(f"Auto-detected MySQL ID: {mysql_id} from {html_path}")
        elif len(eligible_folders) > 1:
            print("Multiple converted HTML files found in queue:")
            for idx, (f_name, f_path) in enumerate(eligible_folders):
                print(f"  [{idx}] MySQL ID {f_name}")
            print("\nPlease specify the ID, e.g.: python scripts/upload_to_db.py <mysql_id>")
            return
        else:
            # Fallback to legacy storage/document.html
            legacy_path = Path(__file__).parent.parent / "storage" / "document.html"
            if legacy_path.exists():
                mysql_id = 37556
                html_path = legacy_path
                print(f"No active queue found. Falling back to default ID {mysql_id} from {html_path}")
            else:
                print("Error: No converted HTML files found. Please run pdf_html.py first or specify the ID.")
                return
                
    if html_path is None:
        # Resolve HTML path based on ID
        html_path = Path(__file__).parent.parent / "storage" / "queue" / str(mysql_id) / "document.html"
        if not html_path.exists():
            html_path = Path(__file__).parent.parent / "storage" / "document.html"
            
    if not html_path.exists():
        print(f"Error: HTML file {html_path} does not exist.")
        return
        
    print(f"Reading converted HTML from: {html_path}")
    html_content = html_path.read_text(encoding="utf-8")
    
    print(f"Uploading HTML content to database for MySQL ID {mysql_id}...")
    log_completed(mysql_id, str(html_path), html_content)
    print("✅ Database update successful! The document is now ready to view.")

if __name__ == "__main__":
    main()
