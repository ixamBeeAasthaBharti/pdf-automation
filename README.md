# PDF to HTML Automation Pipeline

An automated, end-to-end Python pipeline that converts PDF study materials and mock tests into clean, structured, production-ready semantic HTML5 using **Aspose Cloud API** and **Google Gemini AI**.

---

## Architecture Overview

```text
PDF Document
   │
   ▼
[1] Aspose Cloud API (aspose_converter.py) ──► Raw Aspose HTML + Assets
   │
   ▼
[2] PyMuPDF (pymupdf_image_extractor.py)  ──► Extracted Figures & image_map.json
   │
   ▼
[3] Aspose HTML Normalizer (aspose_html_normalizer.py) ──► normalized.html
   │
   ▼
[4] Preprocessor (preprocessor.py)         ──► cleaned.html
   │
   ▼
[5] Chunker (chunker.py)                   ──► chunk_001.html, chunk_002.html...
   │
   ▼
[6] Gemini AI Engine (gemini_runner.py)    ──► Processed Chunks & Tables
   │
   ▼
[7] Merger (merger.py)                     ──► storage/outputs/<id>/output.html
                                              (DB: htmltopdfautomation)
```

---

## 🚀 Setup Instructions (After Cloning)

### 1. Install Dependencies
Ensure you have Python 3.10+ installed. Install required packages using:

```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables (`.env`)
Create or edit the `.env` file in the project root folder with your credentials:

```env
# Gemini API Keys (supports multi-key rotation on quota limits)
GEMINI_API_KEY_1=your_gemini_api_key_1
GEMINI_API_KEY_2=your_gemini_api_key_2
GEMINI_API_KEY_3=your_gemini_api_key_3

# Aspose Cloud API Credentials
ASPOSE_CLIENT_ID=your_aspose_client_id
ASPOSE_CLIENT_SECRET=your_aspose_client_secret

# MySQL Database Configuration
MYSQL_HOST=your_mysql_host
MYSQL_PORT=2232
MYSQL_USER=your_mysql_user
MYSQL_PASSWORD=your_mysql_password
MYSQL_DB=getmyresult
```

---

## 📖 How to Run the Pipeline (All Use Cases)

### Case 1: Full Automated End-to-End Run (MySQL → Aspose → Gemini)
Fetch the next unprocessed PDF from MySQL, automatically convert PDF → HTML via Aspose, normalize, process with Gemini, and update the database:

```bash
python scripts/pipeline.py --auto
```

---

### Case 2: Process a Specific MySQL Document ID
To fetch, convert, and process specific document ID(s) from MySQL (e.g., ID `1474`):

```bash
python scripts/pipeline.py --auto --ids 1474
```

To process multiple IDs in a batch:
```bash
python scripts/pipeline.py --auto --ids 1474,7908,1523
```

---

### Case 3: Two-Step Workflow (Fetch then Process)
If you prefer to download PDFs first, then process them in a separate step:

```bash
# Step A: Download N pending PDFs from MySQL into storage/queue/
python scripts/pipeline.py --fetch --count 5

# Step B: Process all queued documents automatically
python scripts/pipeline.py --process
```

---

### Case 4: Process a Manual PDF File (Without MySQL)
If you have a local PDF file that is not in MySQL:

1. Create a queue directory inside `storage/queue/<YOUR_ID>/` and copy your PDF as `document.pdf`:

   **Windows PowerShell:**
   ```powershell
   New-Item -ItemType Directory -Force -Path "storage/queue/9999"
   Copy-Item "C:\path\to\your_file.pdf" -Destination "storage/queue/9999/document.pdf"
   ```

2. Execute processing:
   ```bash
   python scripts/pipeline.py --process
   ```

---

### Case 5: Test Aspose PDF → HTML Conversion Only
To test raw Aspose PDF conversion standalone on any PDF file:

```bash
python scripts/aspose_converter.py "path/to/document.pdf"
```

Output will be saved in `output/aspose_test/`.

---

### Case 6: Check MySQL Job Statuses
View current status of all processed and pending documents from MySQL:

```bash
python scripts/pipeline.py --status
```

---

## 🖥️ Viewing the Output

1. **Local File Output**:
   Each processed document generates an isolated output directory:
   ```text
   storage/outputs/<ID>/output.html
   ```

2. **Reader UI Dashboard**:
   Open [`index.html`](file:///c:/Users/AASTHA/Desktop/pdf%20automation/index.html) in your web browser to access the interactive reader dashboard.

3. **PHP Reader URL**:
   Access the output via your PHP web server (e.g. `http://localhost:8000/reader/master.php?id=<ID>`). The full HTML with semantic tags is automatically saved to the `html_content` column in the `htmltopdfautomation` database table upon completion.
