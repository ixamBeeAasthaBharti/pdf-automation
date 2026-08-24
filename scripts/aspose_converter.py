import os
import sys
import zipfile
import requests
from pathlib import Path
from dotenv import load_dotenv

# Ensure UTF-8 output on Windows terminal
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).parent.parent
load_dotenv(ROOT / ".env")


def get_aspose_token(client_id: str, client_secret: str) -> str:
    """Request an OAuth2 access token from Aspose Cloud API."""
    token_url = "https://api.aspose.cloud/connect/token"
    payload = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
    }
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    
    response = requests.post(token_url, data=payload, headers=headers, timeout=60)
    if response.status_code != 200:
        raise RuntimeError(f"Aspose Authentication failed ({response.status_code}): {response.text}")
    
    token_data = response.json()
    access_token = token_data.get("access_token")
    if not access_token:
        raise RuntimeError(f"No access_token returned by Aspose: {token_data}")
        
    return access_token


def convert_pdf_to_html(pdf_path: Path, output_dir: Path) -> Path:
    """
    Converts a PDF file to HTML using Aspose Cloud API.
    
    Args:
        pdf_path: Path to the input .pdf file.
        output_dir: Path to directory where output HTML & resources will be saved.
        
    Returns:
        Path to the primary extracted HTML file.
    """
    client_id = os.getenv("ASPOSE_CLIENT_ID")
    client_secret = os.getenv("ASPOSE_CLIENT_SECRET")
    
    if not client_id or not client_secret:
        raise RuntimeError("ASPOSE_CLIENT_ID or ASPOSE_CLIENT_SECRET missing from .env file.")
        
    pdf_path = Path(pdf_path).resolve()
    if not pdf_path.exists():
        raise FileNotFoundError(f"Input PDF does not exist: {pdf_path}")
        
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("=" * 60)
    print(" ASPOSE PDF -> HTML CONVERTER")
    print("=" * 60)
    print(f"[Input PDF] : {pdf_path} ({pdf_path.stat().st_size:,} bytes)")
    print(f"[Output Dir]: {output_dir}")
    
    # 1. Authenticate
    print("\n[1/4] Authenticating with Aspose Cloud...")
    access_token = get_aspose_token(client_id, client_secret)
    print("      Authentication successful.")
    
    # 2. Upload & Convert to HTML ZIP
    print("\n[2/4] Uploading & converting PDF on Aspose Cloud...")
    out_name = f"{pdf_path.stem}_aspose.zip"
    convert_url = "https://api.aspose.cloud/v3.0/pdf/convert/html"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/pdf",
        "Accept": "application/json",
    }
    params = {"outPath": out_name}
    
    with open(pdf_path, "rb") as f:
        convert_res = requests.put(convert_url, headers=headers, params=params, data=f, timeout=300)
        
    if convert_res.status_code >= 400:
        raise RuntimeError(f"Aspose conversion failed ({convert_res.status_code}): {convert_res.text}")
    print("      Conversion successful on Aspose Cloud.")
    
    # 3. Download generated ZIP file from Aspose Storage
    print(f"\n[3/4] Downloading converted package ({out_name})...")
    download_url = f"https://api.aspose.cloud/v3.0/pdf/storage/file/{out_name}"
    download_headers = {"Authorization": f"Bearer {access_token}"}
    
    download_res = requests.get(download_url, headers=download_headers, timeout=120)
    if download_res.status_code >= 400:
        raise RuntimeError(f"Download failed ({download_res.status_code}): {download_res.text}")
        
    zip_output_path = output_dir / out_name
    with open(zip_output_path, "wb") as f:
        f.write(download_res.content)
    print(f"      Package downloaded: {zip_output_path.name} ({zip_output_path.stat().st_size:,} bytes)")
    
    # 4. Extract HTML & resources
    print("\n[4/4] Extracting package contents...")
    primary_html_file = None
    with zipfile.ZipFile(zip_output_path, "r") as zip_ref:
        zip_ref.extractall(output_dir)
        for member in zip_ref.namelist():
            if member.endswith(".html") or member.endswith(".htm"):
                primary_html_file = output_dir / member
                break
                
    if not primary_html_file or not primary_html_file.exists():
        html_files = list(output_dir.glob("*.html"))
        if html_files:
            primary_html_file = html_files[0]
            
    print(f"      Primary HTML extracted: {primary_html_file}")
    print("\n" + "=" * 60)
    print(" SUCCESS: PDF -> HTML conversion completed.")
    print("=" * 60)
    
    return primary_html_file


if __name__ == "__main__":
    if len(sys.argv) > 1:
        target_pdf = Path(sys.argv[1])
    else:
        # Default test: look inside test pdfs or input folder
        test_pdfs = list((ROOT / "test pdfs").glob("*.pdf"))
        if not test_pdfs:
            test_pdfs = list((ROOT / "input").glob("*.pdf"))
        if not test_pdfs:
            print("Error: No PDF file specified and no PDF files found in 'test pdfs' or 'input'.")
            sys.exit(1)
        target_pdf = test_pdfs[0]
        
    target_out_dir = ROOT / "output" / "aspose_test"
    try:
        html_file = convert_pdf_to_html(target_pdf, target_out_dir)
        print(f"\nTest conversion result saved to: {html_file}")
    except Exception as e:
        print(f"\nConversion failed with error: {e}")
        sys.exit(1)
