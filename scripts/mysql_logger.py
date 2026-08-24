"""
mysql_logger.py
Writes processing status and output back to MySQL.

Functions:
  log_html_ready(mysql_id, pdf_html_path)  — HTML file placed, ready to process
  log_processing(mysql_id)                 — pipeline started
  log_completed(mysql_id, output_path, html_content) — write full output + status=1
  log_failed(mysql_id, error)              — mark as FAILED

All functions are safe to call even if the row doesn't exist yet
(they silently skip if no rows are affected).
"""

import sys
from pathlib import Path

scripts_dir = Path(__file__).parent
if str(scripts_dir) not in sys.path:
    sys.path.append(str(scripts_dir))

from mysql_client import get_connection


def log_html_ready(mysql_id: int, pdf_html_path: str):
    """Update htmltopdfautomation: PDF24 HTML is ready, about to process."""
    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE htmltopdfautomation
        SET    pdf_html_format = %s,
               status          = 'HTML_READY',
               updated_on      = NOW(),
               updated_by      = 'system'
        WHERE  mysql_id = %s
    """, (pdf_html_path, mysql_id))
    conn.commit()
    cursor.close()
    conn.close()
    print(f"[Logger] MySQL ID {mysql_id} → HTML_READY")


def log_processing(mysql_id: int):
    """Update htmltopdfautomation: Gemini pipeline is running. Stamps processing_started_at."""
    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE htmltopdfautomation
        SET    status                = 'PROCESSING',
               processing_started_at = NOW(),
               updated_on            = NOW(),
               updated_by            = 'system'
        WHERE  mysql_id = %s
    """, (mysql_id,))
    conn.commit()
    cursor.close()
    conn.close()
    print(f"[Logger] MySQL ID {mysql_id} -> PROCESSING (timer started)")


def log_completed(mysql_id: int, output_html_path: str, html_content: str):
    """
    Mark job as COMPLETED:
      - Writes output_html path and full html_content (LONGTEXT) into htmltopdfautomation
      - Stamps processing_completed_at
      - Sets tbl_studymaterial_lang_map.htmltopdfstatus = 1
    """
    conn   = get_connection()
    cursor = conn.cursor()

    # 1. Upsert into automation log table to guarantee html_content is stored
    cursor.execute("""
        INSERT INTO htmltopdfautomation
            (mysql_id, output_html, html_content, status, processing_completed_at, created_by, updated_by)
        VALUES
            (%s, %s, %s, 'COMPLETED', NOW(), 'system', 'system')
        ON DUPLICATE KEY UPDATE
            output_html             = VALUES(output_html),
            html_content            = VALUES(html_content),
            status                  = 'COMPLETED',
            processing_completed_at = NOW(),
            updated_on              = NOW(),
            updated_by              = 'system'
    """, (mysql_id, output_html_path, html_content))

    # 2. Write back htmltopdfstatus = 1 to the source table
    cursor.execute("""
        UPDATE tbl_studymaterial_lang_map
        SET    htmltopdfstatus = 1
        WHERE  id = %s
    """, (mysql_id,))

    conn.commit()
    cursor.close()
    conn.close()
    print(f"[Logger] MySQL ID {mysql_id} -> COMPLETED | html_content saved in DB | htmltopdfstatus=1")



def log_failed(mysql_id: int, error: str):
    """Mark job as FAILED in htmltopdfautomation (source table status unchanged)."""
    conn   = get_connection()
    cursor = conn.cursor()

    # Truncate error to fit VARCHAR if needed (use first 500 chars as a note)
    short_error = error[:500] if error else "Unknown error"

    cursor.execute("""
        UPDATE htmltopdfautomation
        SET    status     = 'FAILED',
               updated_on = NOW(),
               updated_by = 'system'
        WHERE  mysql_id = %s
    """, (mysql_id,))
    conn.commit()
    cursor.close()
    conn.close()
    print(f"[Logger] MySQL ID {mysql_id} → FAILED  ({short_error[:80]}...)")


if __name__ == "__main__":
    print("[mysql_logger] Imported OK. Use individual functions from pipeline.py.")
