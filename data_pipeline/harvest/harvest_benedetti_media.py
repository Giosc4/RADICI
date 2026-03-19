import os
import requests
import pandas as pd
import time
import random
from bs4 import BeautifulSoup
from pdf2image import convert_from_path
from urllib.parse import urljoin
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Load your dataframe
df = pd.read_csv('db_archives_13_03_2025.csv') 

# Output folders
os.makedirs('pdf_images', exist_ok=True)
os.makedirs('audio_files', exist_ok=True)
os.makedirs('pdf_files', exist_ok=True)

# Path to store processed IDs
processed_log_path = 'processed_ids.txt'

# Load processed IDs if the file exists
if os.path.exists(processed_log_path):
    with open(processed_log_path, 'r') as f:
        processed_ids = set(line.strip() for line in f if line.strip())
else:
    processed_ids = set()

# Setup session with retry
session = requests.Session()
retry_strategy = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
adapter = HTTPAdapter(max_retries=retry_strategy)
session.mount("http://", adapter)
session.mount("https://", adapter)

def download_file(url, output_path):
    try:
        response = session.get(url, stream=True, timeout=10)
        response.raise_for_status()
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(1024):
                f.write(chunk)
        return True
    except Exception as e:
        print(f"Failed to download {url}: {e}")
        return False

start_id = 'V1456'
start_processing = False

for idx, row in df.iterrows():
    if row['archive'] == 'benedetti':
        item_id = row['id']

        # Skip until we reach the start ID
        if not start_processing:
            if item_id == start_id:
                start_processing = True
            else:
                continue

        # Skip already processed IDs
        if item_id in processed_ids:
            print(f"ID {item_id} already processed. Skipping.")
            continue

        page_url = f"http://www.ilcorago.org/benedetti/scheda.asp?id_disco='{item_id}'"
        pdf_path = f'pdf_files/{item_id}.pdf'
        jpg_path = f'pdf_images/{item_id}.jpg'

        try:
            print(f"Processing ID {item_id}...")

            res = session.get(page_url, timeout=10)
            res.raise_for_status()
            soup = BeautifulSoup(res.text, 'html.parser')

            # PDF
            pdf_link = next(
                (urljoin(page_url, link['href']) for link in soup.find_all('a', href=True) if '.pdf' in link['href'].lower()),
                None
            )

            if pdf_link and download_file(pdf_link, pdf_path):
                images = convert_from_path(pdf_path, dpi=200)
                images[0].save(jpg_path, 'JPEG')
                print(f"Saved image for ID {item_id}")
            else:
                print(f"No PDF found for ID {item_id}")

            # MP3
            audio_tag = soup.find('audio', src=True)
            mp3_link = urljoin(page_url, audio_tag['src']) if audio_tag and '.mp3' in audio_tag['src'].lower() else None

            if mp3_link and download_file(mp3_link, f'audio_files/{item_id}.mp3'):
                print(f"Saved MP3 for ID {item_id}")
            else:
                print(f"No MP3 found for ID {item_id}")

            # ✅ Log successful processing
            with open(processed_log_path, 'a') as f:
                f.write(item_id + '\n')
            processed_ids.add(item_id)

        except Exception as e:
            print(f"Error processing ID {item_id}: {e}")

        time.sleep(random.uniform(3, 6))
