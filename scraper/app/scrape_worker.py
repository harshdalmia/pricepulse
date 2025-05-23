import sys
import json
from amazon_scraper import scrape_amazon_product

if __name__ == "__main__":
    url = sys.argv[1]
    extract_metadata = "--extract-metadata" in sys.argv
    get_alternates = "--get-alternates" in sys.argv
    result = scrape_amazon_product(url, extract_metadata=extract_metadata, get_alternates=get_alternates)
    print(json.dumps(result))