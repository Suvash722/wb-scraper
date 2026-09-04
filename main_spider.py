import io
import os
import re
import sys
import json
import requests as regular_requests
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from curl_cffi import requests
import pdfplumber

# --- INPUTS FROM GITHUB ACTIONS ---
target_urls_input = sys.argv[1] 
chat_id = sys.argv[2]
GAS_WEBHOOK_URL = os.environ.get('GAS_WEBHOOK_URL')

# Clean URLs
target_urls = [url.strip() for url in target_urls_input.split(',')]

# --- STEALTH SESSION ---
session = requests.Session(impersonate='chrome124')
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)',
    'Accept-Language': 'en-US,en;q=0.9',
})

final_extracted_data = []

def spider_find_pdfs(start_url):
    valid_pdfs = []
    try:
        if not start_url.startswith('http'):
            start_url = 'https://' + start_url
            
        res = session.get(start_url, timeout=30, verify=False)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            for a in soup.find_all('a', href=True):
                href = a['href']
                text = a.get_text().strip().upper()
                parent_text = a.find_parent('tr').get_text().strip().upper() if a.find_parent('tr') else ""
                combined_text = text + " " + parent_text
                
                if '.pdf' in href.lower() and any(k in combined_text for k in ['MERIT', 'RESULT', 'FINAL', 'PANEL', 'RECOMMENDED', 'PROVISIONAL']):
                    year_match = re.search(r'\b(202[0-6])\b', combined_text)
                    year = year_match.group(1) if year_match else 'Not_Mentioned'
                    full_url = urljoin(start_url, href)
                    
                    valid_pdfs.append({
                        'URL': full_url,
                        'Year': year,
                        'Title': combined_text[:50].replace('\n', ' ')
                    })
    except Exception as e:
        print(f"Error connecting to {start_url}: {e}")
    return valid_pdfs

def extract_st_from_pdf(pdf_bytes, year, source_url):
    records = []
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()
                if not tables: continue
                for table in tables:
                    for row in table:
                        clean_row = [str(c).strip() for c in row if c is not None]
                        row_text = ' '.join(clean_row).upper()
                        
                        if re.search(r'\bST\b', row_text):
                            name, roll_no = '', ''
                            for cell in clean_row:
                                if re.match(r'^[A-Za-z\s\.]+$', cell) and len(cell) > 3 and cell.upper() not in ['ST', 'SC', 'UR', 'OBC', 'MALE', 'FEMALE', 'YES', 'NO']:
                                    if not name: name = cell.strip()
                                elif re.search(r'\d', cell) and len(cell) >= 4:
                                    if not roll_no: roll_no = cell.strip()
                            
                            if name:
                                # Format matching the Google Sheet columns
                                # Year | Department | Source_Website | Roll_Number | Name | Category
                                records.append([year, 'Govt_Board', source_url, roll_no if roll_no else 'N/A', name, 'ST'])
    except Exception:
        pass
    return records

# --- MAIN EXECUTION ---
print(f"Starting crawl for: {target_urls}")

for url in target_urls:
    pdfs = spider_find_pdfs(url)
    print(f"Found {len(pdfs)} potential PDFs on {url}")
    
    for pdf in pdfs:
        print(f"Extracting: {pdf['Title']}")
        try:
            res = session.get(pdf['URL'], timeout=30, verify=False)
            if res.status_code == 200:
                data = extract_st_from_pdf(res.content, pdf['Year'], url)
                final_extracted_data.extend(data)
        except Exception as e:
            pass

# --- SEND DATA BACK TO GOOGLE APPS SCRIPT ---
print(f"Total ST Candidates extracted: {len(final_extracted_data)}")

payload = {
    "action": "save_data",
    "chat_id": chat_id,
    "data": final_extracted_data
}

if final_extracted_data:
    try:
        response = regular_requests.post(GAS_WEBHOOK_URL, json=payload)
        print("Data successfully sent to Google Sheet via GAS!")
    except Exception as e:
        print(f"Failed to send data to GAS: {e}")
else:
    # Send empty payload to notify completion without data
    regular_requests.post(GAS_WEBHOOK_URL, json={"action": "save_data", "chat_id": chat_id, "data": []})
                              
