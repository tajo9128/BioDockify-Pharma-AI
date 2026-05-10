
import sys
import os
import logging
from pprint import pprint

# Add parent dir to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.literature.scraper import LiteratureAggregator, LiteratureConfig

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
# Force UTF-8 for Windows Console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

def test_system():
    print("[-] Initializing PhD-Grade Literature Aggregator...")
    
    # Enable all Tiers
    config = LiteratureConfig(
        sources=["pubmed", "europe_pmc", "openalex", "crossref"],
        include_preprints=False, # Tier 3 disabled for this test to match default
        max_results=3 # Small batch for speed
    )
    
    aggregator = LiteratureAggregator(config)
    
    query = "Alzheimer amyloid beta"
    print(f"[-] Running Search for: '{query}'")
    
    results = aggregator.search(query)
    
    print(f"\n[+] Search Complete. Found {len(results)} aggregated papers.\n")
    
    for i, paper in enumerate(results):
        print(f"--- PAPER {i+1} ---")
        print(f"Title: {paper['title']}")
        print(f"Source: {paper['source']}")
        print(f"OA Status: {'ACCESSIBLE' if paper['is_open_access'] else 'RESTRICTED'}")
        if paper['is_open_access']:
            print(f"License: {paper['license']}")
            print(f"Full Text: {paper.get('full_text_url', 'N/A')}")
        print("----------------\n")

if __name__ == "__main__":
    test_system()
