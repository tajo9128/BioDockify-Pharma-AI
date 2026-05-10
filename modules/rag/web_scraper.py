
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
             
             # Upload asynchronously (fire and forget for now, or await if we want strict consistency)
             # Since this function is sync, we might need a sync wrapper or run_until_complete
             # For robustness, we check if there's an event loop, else new one.
             try:
                 loop = asyncio.get_event_loop()
             except RuntimeError:
                 loop = asyncio.new_event_loop()
                 asyncio.set_event_loop(loop)
                 
             if loop.is_running():
                 # We are likely in an async context (FastAPI), so we should ideally be async.
                 # But this function signature is sync `def scrape_url(...)`.
                 # To avoid breaking callers, we'll use a background task or just log warning.
                 # Ideally, we refactor this entire module to be async.
                 # For now, let's create a task if possible.
                 asyncio.create_task(surfsense.upload_file(text.encode('utf-8'), filename))
             else:
                 loop.run_until_complete(surfsense.upload_file(text.encode('utf-8'), filename))
                 
        except Exception as e:
             # Don't fail the scrape if SurfSense fails, just log
             print(f"Warning: Failed to upload scraped content to SurfSense: {e}")

        return text
    
    except Exception as e:
        raise Exception(f"Failed to scrape URL: {str(e)}")
