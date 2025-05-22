
import sys
import json
from amazon_scraper import scrape_amazon_product

if __name__ == "__main__":
    url = sys.argv[1]
    result = scrape_amazon_product(url)
    print(json.dumps(result))