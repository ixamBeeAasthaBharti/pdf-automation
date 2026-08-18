"""
dashboard.py
Generates index.html at the project root from the SQLite metadata database.
Run standalone:  python scripts/dashboard.py
Also called automatically by batch_runner.py after each batch completes.
"""

from pathlib import Path
from db_manager import get_all, get_all_pdf_jobs, init_db, init_pdf_jobs_db

ROOT = Path(__file__).parent.parent
INDEX_FILE = ROOT / "index.html"


STATUS_BADGE = {
    "COMPLETED":  ('<span class="badge completed">COMPLETED</span>', "#dcfce7", "#166534"),
    "FAILED":     ('<span class="badge failed">FAILED</span>',       "#fee2e2", "#991b1b"),
    "PROCESSING": ('<span class="badge processing">PROCESSING</span>', "#fefce8", "#854d0e"),
    "PENDING":    ('<span class="badge pending">PENDING</span>',     "#f1f5f9", "#475569"),
}


def generate_dashboard():
    init_db()
    init_pdf_jobs_db()
    rows = get_all()
    pdf_jobs = get_all_pdf_jobs()  # (pdf_id, mysql_id, doc_id, original_pdf, status, created_on, updated_on)

    # Build a quick lookup: doc_id -> mysql_id (for rows sourced from MySQL)
    mysql_id_map = {str(j[2]): j[1] for j in pdf_jobs if j[2]}

    table_rows_html = ""
    for doc_id, pdf_path, html_path, output_path, status, created_at, processed_at, error_log in rows:
        badge_html = STATUS_BADGE.get(status, STATUS_BADGE["PENDING"])[0]

        if output_path and Path(output_path).exists():
            # Make the link relative to the project root
            try:
                rel = Path(output_path).relative_to(ROOT)
                link_html = f'<a href="{rel.as_posix()}" target="_blank">Open Output</a>'
            except ValueError:
                link_html = f'<a href="{output_path}" target="_blank">Open Output</a>'
        elif status == "FAILED":
            tip = (error_log or "").replace('"', "'").replace("\n", " ")[:120]
            link_html = f'<span class="error-tip" title="{tip}">See error log</span>'
        else:
            link_html = "<span class='dim'>—</span>"

        mysql_id     = mysql_id_map.get(str(doc_id), "—")
        pdf_name     = Path(pdf_path).name if pdf_path else "—"
        created_short   = (created_at or "")[:16].replace("T", " ")
        processed_short = (processed_at or "")[:16].replace("T", " ") or "—"

        table_rows_html += f"""
        <tr>
          <td><strong>{doc_id}</strong></td>
          <td class="mono">{mysql_id}</td>
          <td class="mono">{pdf_name}</td>
          <td>{badge_html}</td>
          <td>{created_short}</td>
          <td>{processed_short}</td>
          <td>{link_html}</td>
        </tr>"""

    if not table_rows_html:
        table_rows_html = """
        <tr>
          <td colspan="7" style="text-align:center;color:#94a3b8;padding:2rem;">
            No documents registered yet.
            Run <code>python scripts/pipeline.py --fetch</code> to download the next PDF.
          </td>
        </tr>"""

    total     = len(rows)
    completed = sum(1 for r in rows if r[4] == "COMPLETED")
    failed    = sum(1 for r in rows if r[4] == "FAILED")
    pending   = sum(1 for r in rows if r[4] in ("PENDING", "PROCESSING"))

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>PDF Automation Dashboard</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif;
      background: #f1f5f9;
      color: #1e293b;
      min-height: 100vh;
      padding: 2rem 1.5rem;
    }}
    .header {{
      max-width: 1100px;
      margin: 0 auto 2rem;
    }}
    .header h1 {{
      font-size: 1.65rem;
      font-weight: 800;
      color: #1b3a6b;
      margin-bottom: 0.25rem;
    }}
    .header p {{ color: #64748b; font-size: 0.9rem; }}
    .stats {{
      display: flex;
      gap: 1rem;
      flex-wrap: wrap;
      max-width: 1100px;
      margin: 0 auto 1.5rem;
    }}
    .stat-card {{
      background: #fff;
      border-radius: 10px;
      padding: 1rem 1.5rem;
      flex: 1;
      min-width: 140px;
      box-shadow: 0 1px 4px rgba(0,0,0,0.06);
      border-top: 3px solid #1b3a6b;
    }}
    .stat-card.ok  {{ border-top-color: #16a34a; }}
    .stat-card.err {{ border-top-color: #dc2626; }}
    .stat-card.pnd {{ border-top-color: #d97706; }}
    .stat-card .num {{ font-size: 2rem; font-weight: 800; color: #1b3a6b; }}
    .stat-card.ok  .num {{ color: #16a34a; }}
    .stat-card.err .num {{ color: #dc2626; }}
    .stat-card.pnd .num {{ color: #d97706; }}
    .stat-card .lbl {{ font-size: 0.78rem; color: #64748b; text-transform: uppercase; letter-spacing: .05em; margin-top: 0.2rem; }}
    .card {{
      max-width: 1100px;
      margin: 0 auto;
      background: #fff;
      border-radius: 12px;
      box-shadow: 0 2px 10px rgba(0,0,0,0.06);
      overflow: hidden;
    }}
    table {{ width: 100%; border-collapse: collapse; }}
    thead tr {{ background: #1b3a6b; color: #fff; }}
    th {{ padding: 12px 16px; text-align: left; font-size: 0.82rem; font-weight: 700; text-transform: uppercase; letter-spacing: .05em; }}
    tbody tr {{ border-bottom: 1px solid #f1f5f9; }}
    tbody tr:hover {{ background: #f8fafc; }}
    td {{ padding: 13px 16px; font-size: 0.88rem; vertical-align: middle; }}
    .badge {{ padding: 3px 10px; border-radius: 20px; font-size: 0.75rem; font-weight: 700; display: inline-block; }}
    .completed {{ background: #dcfce7; color: #166534; }}
    .failed    {{ background: #fee2e2; color: #991b1b; }}
    .processing {{ background: #fefce8; color: #854d0e; }}
    .pending   {{ background: #f1f5f9; color: #475569; }}
    a {{ color: #1b3a6b; font-weight: 600; text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    .mono {{ font-family: monospace; font-size: 0.82rem; color: #475569; }}
    .dim {{ color: #cbd5e1; }}
    .error-tip {{ color: #dc2626; cursor: help; font-size: 0.82rem; border-bottom: 1px dashed #dc2626; }}
    .footer {{ text-align: center; margin-top: 2rem; color: #94a3b8; font-size: 0.8rem; }}
  </style>
</head>
<body>
  <div class="header">
    <h1>PDF Automation Dashboard</h1>
    <p>Auto-generated index of all processed documents. Refresh after running <code>batch_runner.py</code>.</p>
  </div>

  <div class="stats">
    <div class="stat-card">
      <div class="num">{total}</div>
      <div class="lbl">Total Documents</div>
    </div>
    <div class="stat-card ok">
      <div class="num">{completed}</div>
      <div class="lbl">Completed</div>
    </div>
    <div class="stat-card err">
      <div class="num">{failed}</div>
      <div class="lbl">Failed</div>
    </div>
    <div class="stat-card pnd">
      <div class="num">{pending}</div>
      <div class="lbl">Pending / Running</div>
    </div>
  </div>

  <div class="card">
    <table>
      <thead>
        <tr>
          <th>Document ID</th>
          <th>MySQL ID</th>
          <th>PDF Filename</th>
          <th>Status</th>
          <th>Registered</th>
          <th>Finished</th>
          <th>Output</th>
        </tr>
      </thead>
      <tbody>
        {table_rows_html}
      </tbody>
    </table>
  </div>

  <div class="footer">Generated by dashboard.py &mdash; PDF Automation Pipeline</div>
</body>
</html>"""

    INDEX_FILE.write_text(html, encoding="utf-8")
    print(f"[Dashboard] index.html updated  ({total} documents)")


if __name__ == "__main__":
    generate_dashboard()
