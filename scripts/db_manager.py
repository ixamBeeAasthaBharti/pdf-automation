import sqlite3
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).parent.parent
DB_PATH = ROOT / "data" / "metadata.db"


def _connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(DB_PATH)


def init_db():
    """Create the documents table if it doesn't exist."""
    conn = _connect()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            doc_id       TEXT PRIMARY KEY,
            pdf_path     TEXT,
            html_path    TEXT,
            output_path  TEXT,
            status       TEXT DEFAULT 'PENDING',
            created_at   TEXT,
            processed_at TEXT,
            error_log    TEXT
        )
    """)
    conn.commit()
    conn.close()
    print(f"[DB] Initialised  ->  {DB_PATH}")


def register_document(doc_id: str, pdf_path: Path, html_path: Path):
    """Insert a new document record (ignored if doc_id already exists)."""
    conn = _connect()
    conn.execute(
        """
        INSERT OR IGNORE INTO documents (doc_id, pdf_path, html_path, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (doc_id, str(pdf_path), str(html_path), datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()


def update_status(
    doc_id: str,
    status: str,
    output_path: Path = None,
    error_log: str = None,
):
    """Update the status (and optionally output_path / error_log) for a document."""
    conn = _connect()
    conn.execute(
        """
        UPDATE documents
        SET status       = ?,
            output_path  = COALESCE(?, output_path),
            error_log    = COALESCE(?, error_log),
            processed_at = ?
        WHERE doc_id = ?
        """,
        (
            status,
            str(output_path) if output_path else None,
            error_log,
            datetime.now().isoformat(),
            doc_id,
        ),
    )
    conn.commit()
    conn.close()


def get_pending():
    """Return all documents with status PENDING."""
    conn = _connect()
    rows = conn.execute(
        "SELECT doc_id, pdf_path, html_path FROM documents WHERE status = 'PENDING'"
    ).fetchall()
    conn.close()
    return rows


def get_all():
    """Return all document rows for dashboard generation."""
    conn = _connect()
    rows = conn.execute(
        "SELECT doc_id, pdf_path, html_path, output_path, status, created_at, processed_at, error_log "
        "FROM documents ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    return rows


def reset_stuck():
    """Reset any PROCESSING records (left from a crashed run) back to PENDING."""
    conn = _connect()
    affected = conn.execute(
        "UPDATE documents SET status = 'PENDING' WHERE status = 'PROCESSING'"
    ).rowcount
    conn.commit()
    conn.close()
    if affected:
        print(f"[DB] Reset {affected} stuck PROCESSING record(s) -> PENDING")


# ─────────────────────────────────────────────────────────────────────────────
# pdf_jobs table  (local queue / processing state, keyed by MySQL row id)
# ─────────────────────────────────────────────────────────────────────────────

def init_pdf_jobs_db():
    """Create the pdf_jobs table if it doesn't exist."""
    conn = _connect()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS pdf_jobs (
            pdf_id       INTEGER PRIMARY KEY AUTOINCREMENT,
            mysql_id     INTEGER UNIQUE,
            doc_id       TEXT,
            original_pdf TEXT,
            status       TEXT DEFAULT 'DOWNLOADED',
            created_on   TEXT,
            updated_on   TEXT
        )
    """)
    conn.commit()
    conn.close()


def upsert_pdf_job(mysql_id: int, doc_id: str, original_pdf: str, status: str = "DOWNLOADED"):
    """Insert or update a pdf_jobs record by mysql_id."""
    conn = _connect()
    now = datetime.now().isoformat()
    conn.execute("""
        INSERT INTO pdf_jobs (mysql_id, doc_id, original_pdf, status, created_on, updated_on)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(mysql_id) DO UPDATE SET
            status     = excluded.status,
            updated_on = excluded.updated_on
    """, (mysql_id, doc_id, original_pdf, status, now, now))
    conn.commit()
    conn.close()


def update_pdf_job_status(mysql_id: int, status: str):
    """Update the status of a pdf_jobs record."""
    conn = _connect()
    conn.execute(
        "UPDATE pdf_jobs SET status = ?, updated_on = ? WHERE mysql_id = ?",
        (status, datetime.now().isoformat(), mysql_id),
    )
    conn.commit()
    conn.close()


def get_all_pdf_jobs():
    """Return all pdf_jobs rows ordered by creation time."""
    conn = _connect()
    rows = conn.execute(
        "SELECT pdf_id, mysql_id, doc_id, original_pdf, status, created_on, updated_on "
        "FROM pdf_jobs ORDER BY created_on DESC"
    ).fetchall()
    conn.close()
    return rows


if __name__ == "__main__":
    init_db()
    init_pdf_jobs_db()
    print("[DB] Schema ready (documents + pdf_jobs).")
