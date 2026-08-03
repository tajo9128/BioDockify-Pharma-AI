
import requests
from bs4 import BeautifulSoup

def scrape_url(url: str) -> str:
    """
    Scrape text content from a URL.
    Handles basic HTML cleaning.
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style", "nav", "footer"]):
            script.decompose()
            
        text = soup.get_text()
        
        # Break into lines and remove leading/trailing space on each
        lines = (line.strip() for line in text.splitlines())
        # Break multi-headlines into a line each
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        # Drop blank lines
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        # --- SURFSENSE INTEGRATION ---
        # Automatically ingest scraped content into the Knowledge Engine
        try:
             # Lazy import to avoid circular dependencies
             from modules.knowledge.client import surfsense
             import asyncio
             
             # Create a filename from URL (simplified)
             import re
             safe_name = re.sub(r'[^a-zA-Z0-9]', '_', url)[:50]
             filename = f"scraped_{safe_name}.txt"
             
             try:
                 loop = asyncio.get_running_loop()
                 loop.create_task(surfsense.upload_file(text.encode('utf-8'), filename))
             except RuntimeError:
                 asyncio.run(surfsense.upload_file(text.encode('utf-8'), filename))
                 
        except Exception as e:
             # Don't fail the scrape if SurfSense fails, just log
             print(f"Warning: Failed to upload scraped content to SurfSense: {e}")

        return text
    
    except Exception as e:
        raise Exception(f"Failed to scrape URL: {str(e)}")
