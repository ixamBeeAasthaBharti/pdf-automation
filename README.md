# PDF Automation & Study Notes Conversion Engine

An automated, high-precision PDF-to-HTML conversion pipeline designed for Study Notes and educational documents. It extracts vector diagrams, preserves flowchart structures, maintains bullet hierarchies, handles complex tables, auto-detects cover pages, and formats MCQ question papers while outputting clean, responsive HTML compatible with the ixamBee Web Reader interface.

---

## 🌟 Key Features

- **High-Precision Layout Engine:** Built on PyMuPDF (`fitz`), analyzing block areas, line ratios, vector paths, and bounding boxes.
- **Cover Page Auto-Detection:** Intelligently checks page density, title fonts, and keywords on Page 1 to detect whether a cover page exists, suppressing duplicate headers in `master.php`.
- **Diagram & Flowchart Preservation:** Extracts multi-stage vector diagrams (chevrons, flowcharts, processes) as clear raster images while excluding background accent bars and watermarks.
- **MCQ & Question Paper Formatting:** Automatically recognizes question numbers, option prefixes (`A.`, `B.`, `C.`, `D.`, `E.`), and `Explanation-` blocks, preventing options from merging into single lines.
- **Watermark & Running Footer Filter:** Excludes background watermarks (`ixamBee.com`, etc.) and page number footers.
- **Typography & Font Preservation:** Preserves the original `Literata` serif font aesthetics alongside Bootstrap 5 layout grids.
- **Database & Reader Integration:** Syncs directly with MySQL (`tbl_html_to_pdf`) and serves documents dynamically via PHP (`reader/master.php`).

---

## 📋 Prerequisites

- **Python:** 3.9 or higher
- **PHP:** 7.4+ (or built-in PHP development server)
- **MySQL Database:** Remote or local MySQL instance

---

## ⚙️ Installation & Setup

1. **Clone or navigate to the repository directory:**
   ```bash
   cd "path/to/pdf automation"
   ```

2. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment Variables (`.env`):**
   Create or edit the `.env` file in the project root directory:

   ```ini
   # MySQL Connection Settings
   MYSQL_HOST=164.52.200.186
   MYSQL_PORT=2232
   MYSQL_USER=your_db_user
   MYSQL_PASSWORD=your_db_password
   MYSQL_DB=getmyresult

   # Optional API Keys
   ASPOSE_CLIENT_ID=your_aspose_client_id
   ASPOSE_CLIENT_SECRET=your_aspose_client_secret
   ```

4. **Verify Database Setup:**
   Run the database setup script to create or verify `tbl_html_to_pdf`:
   ```bash
   python scripts/mysql_setup.py
   ```

---

## 🚀 How to Run

### 1. Process Documents via Main Pipeline (`run.py`)

Running `python scripts/run.py` without arguments executes the **automated batch processing engine**.

#### 🔹 Run All Pending PDFs in Queue (Default Batch Mode)
```bash
python scripts/run.py
```
*What this does:*
1. Queries MySQL (`tbl_html_to_pdf`) for **all pending PDFs** where `status = 0`.
2. Downloads each PDF to `storage/queue/<id>/document.pdf`.
3. Runs `pdf_html.py` to extract text, flowcharts, tables, cover page auto-detection, and formatted HTML.
4. Uploads converted HTML to MySQL (`tbl_html_to_pdf`), sets `status = 1` (COMPLETED).
5. Moves queue files to `storage/archive/<id>/` and syncs `storage/outputs/<id>/`.

---

#### 🔹 Batch Options & Flags for `run.py`

- **Process Next N Pending PDFs:**
  ```bash
  python scripts/run.py --count 5
  ```
  *(Downloads and converts the next 5 pending PDFs in queue)*

- **Process a Specific Document ID:**
  ```bash
  python scripts/run.py --id 20124
  ```
  *(Fetches, converts, archives, and updates MySQL for a single document ID)*

- **Show Pipeline Status Summary:**
  ```bash
  python scripts/run.py --status
  ```
  *(Prints count of completed, pending, and failed documents in MySQL)*

---

### 2. Convert a Local PDF File (Offline Mode)

To convert a local PDF directly without database interaction:

```bash
python scripts/pdf_html.py "path/to/file.pdf" "path/to/output.html"
```

### 3. Upload Manual Edits Back to MySQL
If you manually edit `storage/archive/<MYSQL_ID>/document.html` or update images in the archive directory, upload those changes back to the database:

```bash
python scripts/upload_html.py <MYSQL_ID>
```
*Example:*
```bash
python scripts/upload_html.py 20124
```

---

## 🌐 Serving the Web Reader Interface

Start the local PHP development server from the project root:

```bash
php -S localhost:8000
```

Open your browser and navigate to:
```
http://localhost:8000/reader/master.php?id=<MYSQL_ID>
```
*Example:*
[http://localhost:8000/reader/master.php?id=20124](http://localhost:8000/reader/master.php?id=20124)

---

## 📁 Project Directory Structure

```
pdf automation/
├── .env                  # DB & API environment variables
├── requirements.txt      # Python dependencies
├── README.md             # Project documentation
│
├── scripts/
│   ├── run.py            # Primary production entry point
│   ├── pdf_html.py       # Core PDF extraction & HTML generator
│   ├── upload_html.py    # Manual HTML/Image upload to MySQL DB
│   ├── mysql_client.py   # Database connection pool manager
│   ├── mysql_fetcher.py  # PDF downloader from MySQL/URLs
│   ├── mysql_logger.py   # Status & pipeline logger
│   └── mysql_setup.py    # DB schema setup & migration script
│
├── reader/
│   ├── master.php        # Web Reader template & viewer interface
│   ├── reader.js         # Interactive font & reading controls
│   └── assets/           # Logos and branding assets
│
├── styles/
│   ├── reader.css        # Reader UI design system
│   └── pdf.css           # Document custom styles & font preservation
│
└── storage/
    ├── archive/          # HTML & extracted images per MySQL ID
    └── outputs/          # Synchronized outputs directory
```

---

## 🛠️ Editing & Customizing Documents

1. Open `storage/archive/<MYSQL_ID>/document.html`.
2. Add custom Bootstrap elements (`<div class="container">`, `<div class="row">`, `.table-responsive`, etc.) or custom CSS classes defined in `styles/pdf.css`.
3. Preview your changes instantly in the browser at `http://localhost:8000/reader/master.php?id=<MYSQL_ID>`.
4. Run `python scripts/upload_html.py <MYSQL_ID>` when ready to persist your manual edits to the remote MySQL database.
