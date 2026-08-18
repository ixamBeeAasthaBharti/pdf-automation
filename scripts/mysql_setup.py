"""
mysql_setup.py
One-time setup script — run this ONCE before using the pipeline.

What it does:
  1. Adds  htmltopdfstatus TINYINT DEFAULT 0  to tbl_studymaterial_lang_map
  2. Creates the  htmltopdfautomation  logging table

Run from workspace root:
    python scripts/mysql_setup.py
"""

import sys
from pathlib import Path

scripts_dir = Path(__file__).parent
if str(scripts_dir) not in sys.path:
    sys.path.append(str(scripts_dir))

from mysql_client import get_connection


def add_status_column():
    """Add htmltopdfstatus column to the source table (safe if already exists)."""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            ALTER TABLE tbl_studymaterial_lang_map
            ADD COLUMN htmltopdfstatus TINYINT NOT NULL DEFAULT 0
        """)
        conn.commit()
        print("[Setup] OK  Added column: tbl_studymaterial_lang_map.htmltopdfstatus")
    except Exception as e:
        if "Duplicate column" in str(e) or "already exists" in str(e).lower():
            print("[Setup] INFO Column htmltopdfstatus already exists -- skipping")
        else:
            cursor.close()
            conn.close()
            raise

    cursor.close()
    conn.close()


def create_automation_table():
    """Create the htmltopdfautomation logging table."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS htmltopdfautomation (
            pdf_id                  INT          AUTO_INCREMENT PRIMARY KEY,
            mysql_id                INT          NOT NULL UNIQUE,
            original_pdf            VARCHAR(1000)           COMMENT 'Download URL of the source PDF',
            pdf_html_format         VARCHAR(1000)           COMMENT 'Local path to the PDF24-converted HTML file',
            output_html             VARCHAR(1000)           COMMENT 'Local path to the final Gemini-processed output.html',
            html_content            LONGTEXT                COMMENT 'Full HTML content (with tags) of the final output',
            status                  VARCHAR(50)  DEFAULT 'DOWNLOADED'
                                                            COMMENT 'DOWNLOADED | HTML_READY | PROCESSING | COMPLETED | FAILED',
            processing_started_at   DATETIME     DEFAULT NULL COMMENT 'When pipeline.py --process started on this document',
            processing_completed_at DATETIME     DEFAULT NULL COMMENT 'When the output.html was successfully written',
            created_on              DATETIME     DEFAULT CURRENT_TIMESTAMP,
            created_by              VARCHAR(100) DEFAULT 'system',
            updated_on              DATETIME     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            updated_by              VARCHAR(100) DEFAULT 'system',
            INDEX idx_status   (status),
            INDEX idx_mysql_id (mysql_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """)
    conn.commit()
    print("[Setup] OK  Table ready: htmltopdfautomation")

    cursor.close()
    conn.close()


def add_processing_time_columns():
    """Safely add processing_started_at and processing_completed_at columns."""
    conn   = get_connection()
    cursor = conn.cursor()
    for col, definition in [
        ("processing_started_at",   "DATETIME DEFAULT NULL COMMENT 'When pipeline --process started'"),
        ("processing_completed_at", "DATETIME DEFAULT NULL COMMENT 'When output.html was written'"),
    ]:
        try:
            cursor.execute(
                f"ALTER TABLE htmltopdfautomation ADD COLUMN {col} {definition}"
            )
            conn.commit()
            print(f"[Setup] OK  Added column: htmltopdfautomation.{col}")
        except Exception as e:
            if "Duplicate column" in str(e) or "already exists" in str(e).lower():
                print(f"[Setup] INFO Column {col} already exists -- skipping")
            else:
                cursor.close()
                conn.close()
                raise
    cursor.close()
    conn.close()


def reset_stuck_processing():
    """
    Reset any rows stuck at PROCESSING back to DOWNLOADED.
    Safe to call anytime — only affects rows that crashed mid-run
    (e.g. power cut, Ctrl+C). Normal FAILED rows are unaffected.
    """
    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE htmltopdfautomation
        SET    status                = 'DOWNLOADED',
               processing_started_at = NULL,
               updated_on            = NOW()
        WHERE  status = 'PROCESSING'
    """)
    affected = cursor.rowcount
    conn.commit()
    cursor.close()
    conn.close()
    if affected:
        print(f"[Setup] WARN Reset {affected} stuck PROCESSING row(s) -> DOWNLOADED")
    else:
        print("[Setup] INFO No stuck PROCESSING rows found.")


def verify():
    """Quick verification — list columns of both tables."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("DESCRIBE tbl_studymaterial_lang_map")
    cols = [row[0] for row in cursor.fetchall()]
    print(f"\n[Verify] tbl_studymaterial_lang_map columns: {', '.join(cols)}")

    cursor.execute("DESCRIBE htmltopdfautomation")
    cols2 = [row[0] for row in cursor.fetchall()]
    print(f"[Verify] htmltopdfautomation columns: {', '.join(cols2)}")

    # Count eligible rows
    cursor.execute(
        "SELECT COUNT(*) FROM tbl_studymaterial_lang_map "
        "WHERE type_order = 2 AND htmltopdfstatus = 0"
    )
    count = cursor.fetchone()[0]
    print(f"[Verify] PDFs eligible for processing (type_order=2, htmltopdfstatus=0): {count}")

    cursor.close()
    conn.close()


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("MySQL One-Time Setup")
    print("=" * 60)
    add_status_column()
    create_automation_table()
    add_processing_time_columns()       # safe: skips if columns exist
    reset_stuck_processing()            # safe: clears crashed PROCESSING rows
    verify()
    print("\n[Setup] Done. You can now run: python scripts/pipeline.py --fetch")
