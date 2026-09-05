import os
import re
import csv
import io
import time
import random
import sqlite3
import argparse
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from curl_cffi import requests
import pdfplumber
from duckduckgo_search import DDGS

# ==========================================
# MODULE 1: The Memory Manager (SQLite)
# ==========================================
class CrawlMemory:
    def __init__(self, db_name="crawler_history.db"):
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS visited_sites 
                               (domain TEXT PRIMARY KEY, last_crawled TIMESTAMP)''')
        self.conn.commit()

    def extract_domain(self, url):
        return urlparse(url if url.startswith('http') else 'https://' + url).netloc

    def can_crawl(self, url, cooldown_days=15):
        domain = self.extract_domain(url)
        self.cursor.execute('SELECT last_crawled FROM visited_sites WHERE domain = ?', (domain,))
        result = self.cursor.fetchone()
        from datetime import datetime
        if result:
            days_passed = (datetime.now() - datetime.strptime(result[0], "%Y-%m-%d %H:%M:%S")).days
            if days_passed < cooldown_days:
                print(f"[SKIP] {domain} on {days_passed}-day cooldown.")
                return False
        return True

    def mark_as_crawled(self, url):
        domain = self.extract_domain(url)
        from datetime import datetime
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.cursor.execute('''INSERT INTO visited_sites (domain, last_crawled) 
                               VALUES (?, ?) ON CONFLICT(domain) DO UPDATE SET last_crawled = ?''', 
                            (domain, now, now))
        self.conn.commit()

# ==========================================
# MODULE 2: The Radar (Auto-Discovery)
# ==========================================
class AutoDiscoverer:
    def __init__(self):
        self.allowed_tlds = ['.gov.in', '.nic.in', '.ac.in']
    
    def find_target_websites(self, query, max_res=10):
        print(f"[RADAR] Hunting for: '{query}'...")
        targets = set()
        try:
            with DDGS() as ddgs:
                results = ddgs.text(query + " recruitment merit list result filetype:pdf", max_results=max_res)
                for r in results:
                    link = r.get('href', '')
                    if any(tld in link.lower() for tld in self.allowed_tlds):
                        targets.add(self._get_base_url(link))
        except Exception as e:
            print(f"[RADAR ERROR] {e}")
        return list(targets)

    def _get_base_url(self, url):
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}"

# ==========================================
# MODULE 3: Smart PDF Parser
# ==========================================
class SmartParser:
    def extract_data(self, pdf_bytes, source_url):
        records = []
        try:
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                for page in pdf.pages:
                    tables = page.extract_tables()
                    if not tables: continue
                    for table in tables:
                        # Auto-detect Columns
                        name_col, roll_col = -1, -1
                        if len(table) > 0 and table[0]:
                            header = [str(c).upper().strip() for c in table[0] if c]
                            for idx, col_name in enumerate(header):
                                if any(k in col_name for k in ['NAME', 'CANDIDATE', 'APPLICANT']): name_col = idx
                                if any(k in col_name for k in ['ROLL', 'REG', 'ID']): roll_col = idx

                        # Extract Data
                        for row in table[1:]:
                            clean_row = [str(c).strip() for c in row if c is not None]
                            row_text = ' '.join(clean_row).upper()
                            if re.search(r'\bST\b', row_text):
                                name = clean_row[name_col] if name_col != -1 and name_col < len(clean_row) else "Unknown"
                                roll = clean_row[roll_col] if roll_col != -1 and roll_col < len(clean_row) else "Unknown"
                                
                                # Fallback heuristic if headers fail
                                if name == "Unknown" or roll == "Unknown":
                                    for cell in clean_row:
                                        if re.match(r'^[A-Za-z\s\.]+$', cell) and len(cell) > 3 and cell.upper() not in ['ST','SC','UR','OBC']: name = cell
                                        elif re.search(r'\d', cell) and len(cell) >= 4: roll = cell

                                records.append(['Auto_Detected', source_url, roll, name, 'ST'])
        except Exception as e:
            print(f"[PARSER ERROR] {e}")
        return records

# ==========================================
# MODULE 4: Deep Crawler & Orchestrator
# ==========================================
def spider_find_pdfs(session, start_url, max_depth=5):
    base_domain = urlparse(start_url).netloc
    visited, valid_pdfs, queue = set(), [], [(start_url, 0)]
    
    while queue:
        url, depth = queue.pop(0)
        if url in visited or depth > max_depth: continue
        visited.add(url)
        
        if depth > 0:
            time.sleep(random.uniform(2.0, 4.5)) # Human-like delay
            
        try:
            res = session.get(url, timeout=30, verify=False)
            if res.status_code != 200: continue
            soup = BeautifulSoup(res.text, 'html.parser')
            
            for a in soup.find_all('a', href=True):
                href = a['href']
                full_url = urljoin(url, href)
                text = a.get_text().strip().upper()
                
                if '.pdf' in href.lower() and any(k in text for k in ['RESULT', 'MERIT', 'PANEL', 'PROVISIONAL']):
                    if full_url not in [p['URL'] for p in valid_pdfs]:
                        valid_pdfs.append({'URL': full_url, 'Title': text[:50]})
                elif depth < max_depth and urlparse(full_url).netloc == base_domain:
                    if any(kw in text for kw in ['RESULT', 'RECRUITMENT', 'NOTICE']):
                        if full_url not in visited: queue.append((full_url, depth + 1))
        except: pass
    return valid_pdfs

def send_to_telegram(csv_path, count):
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id: return
    req = requests.Session()
    req.post(f"https://api.telegram.org/bot{token}/sendMessage", data={"chat_id": chat_id, "text": f"🚨 *OSINT Radar*\nFound {count} ST candidates."})
    with open(csv_path, 'rb') as f:
        req.post(f"https://api.telegram.org/bot{token}/sendDocument", data={"chat_id": chat_id}, files={"document": f})

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", required=True, help="Search query (e.g., 'WB Govt Medical')")
    args = parser.parse_args()

    memory = CrawlMemory()
    radar = AutoDiscoverer()
    smart_parser = SmartParser()
    session = requests.Session(impersonate='chrome124')
    final_data = []

    print("=== STARTING OSINT ENGINE ===")
    targets = radar.find_target_websites(args.query)
    
    for target in targets:
        if memory.can_crawl(target):
            print(f"[CRAWLING] Deep scan initiated for: {target}")
            pdfs = spider_find_pdfs(session, target)
            for pdf in pdfs:
                try:
                    res = session.get(pdf['URL'], timeout=30, verify=False)
                    final_data.extend(smart_parser.extract_data(res.content, target))
                except: continue
            memory.mark_as_crawled(target)

    if final_data:
        out_file = "extracted_data.csv"
        with open(out_file, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerows([["Year", "Source", "Roll_Number", "Name", "Category"]] + final_data)
        send_to_telegram(out_file, len(final_data))
        print(f"=== DONE. {len(final_data)} Records Sent to Telegram ===")
            
