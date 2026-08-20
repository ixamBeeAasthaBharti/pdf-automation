import sys
from pathlib import Path

# Add scripts directory to path
scripts_dir = Path(__file__).parent
if str(scripts_dir) not in sys.path:
    sys.path.append(str(scripts_dir))

from mysql_logger import log_completed

def main():
    mysql_id = 37556
    html_path = Path(__file__).parent.parent / "storage" / "document.html"
    
    if not html_path.exists():
        print(f"Error: {html_path} does not exist. Please run pdf_html.py first.")
        return
        
    print(f"Reading converted HTML from: {html_path}")
    html_content = html_path.read_text(encoding="utf-8")
    
    print(f"Uploading HTML content to database for MySQL ID {mysql_id}...")
    log_completed(mysql_id, str(html_path), html_content)
    print("✅ Database update successful! The document is now ready to view.")

if __name__ == "__main__":
    main()
