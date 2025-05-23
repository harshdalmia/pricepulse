from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import re
import sys

def clean_price(price_str):
    price_str = price_str.replace('₹', '').replace(',', '').strip()
    try:
        return float(re.findall(r"[\d.]+", price_str)[0])
    except Exception as e:
        print(f"[ERROR] Failed to clean price: {e} | Raw: {price_str}", file=sys.stderr)
        return None

def scrape_amazon_product(url, extract_metadata=False, get_alternates=False):
    with sync_playwright() as p:
        browser = None
        try:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                locale="en-US",
                extra_http_headers={
                    "accept-language": "en-US,en;q=0.9",
                    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                    "sec-fetch-site": "none",
                    "sec-fetch-mode": "navigate",
                    "sec-fetch-user": "?1",
                    "sec-fetch-dest": "document",
                }
            )
            page = context.new_page()
            try:
                response = page.goto(url, timeout=20000)
                final_url = page.url
                if final_url != url:
                    print(f"[REDIRECT] Navigated from {url} to {final_url}", file=sys.stderr)
                content = page.content()
                
                if ("Enter the characters you see below" in content or
                    "not a robot" in content or
                    "captcha" in content.lower() or
                    "Sorry, we just need to make sure you're not a robot" in content):
                    print(f"[BLOCKED] CAPTCHA or block detected on {final_url}", file=sys.stderr)
                    return {"error": "CAPTCHA or block detected"}
              
               
            except Exception as e:
                print(f"[ERROR] Failed to navigate to {url}: {e}", file=sys.stderr)
                return {"error": f"Failed to navigate: {e}"}
            try:
                page.wait_for_selector('#productTitle', timeout=10000)
            except PlaywrightTimeoutError:
                print(f"[ERROR] Timeout waiting for product title on {url}", file=sys.stderr)
                return {"error": "Timeout waiting for product title"}
            except Exception as e:
                print(f"[ERROR] Failed to find product title: {e}", file=sys.stderr)
                return {"error": f"Failed to find product title: {e}"}
            try:
                title = page.locator("#productTitle").nth(0).inner_text().strip()
            except Exception as e:
                print(f"[ERROR] Failed to extract title: {e}", file=sys.stderr)
                title = None
            
            metadata = None
            alternate_prices = None
            
            # Extract metadata if requested
            if extract_metadata and title:
                try:
                    from extract_metadata import extract_metadata_with_openai
                    metadata = extract_metadata_with_openai(title)
                    print(f"[DEBUG] Extracted metadata: {metadata}", file=sys.stderr)
                except Exception as e:
                    print(f"[ERROR] Failed to extract metadata: {e}", file=sys.stderr)
                    metadata = None
            
            # Get alternate prices if requested
            if get_alternates and title:
                try:
                    from extract_metadata import get_alternate_platform_prices
                    # Always call with just the title if metadata is None or empty
                    brand = None
                    model = None
                    if metadata and isinstance(metadata, dict):
                        brand = metadata.get('brand')
                        model = metadata.get('model')
                    alternate_prices = get_alternate_platform_prices(title, brand, model)
                    print(f"[DEBUG] Found {len(alternate_prices) if alternate_prices else 0} alternate prices", file=sys.stderr)
                except Exception as e:
                    print(f"[ERROR] Failed to get alternate prices: {e}", file=sys.stderr)
                    alternate_prices = []
            
            price = None
            price_selectors = [
                "span.a-price span.a-offscreen",
                "span#priceblock_ourprice",
                "span#priceblock_dealprice",
                "span#priceblock_saleprice",
                "span.apexPriceToPay span.a-offscreen",
                "span.a-price-whole"
            ]
            for selector in price_selectors:
                try:
                    locator = page.locator(selector)
                    if locator.count() > 0:
                        price_text = locator.first.inner_text().strip()
                        price = clean_price(price_text)
                        if price is not None:
                            break
                except Exception as e:
                    print(f"[ERROR] Failed to extract price with selector {selector}: {e}", file=sys.stderr)
            try:
                page.wait_for_selector('body', timeout=15000)
            except Exception as e:
                print(f"[ERROR] Timeout waiting for body: {e}", file=sys.stderr)
            if price is None:
                print(f"[ERROR] Could not find price on page. Saving HTML snippet for debugging.", file=sys.stderr)
                snippet = page.content()[:5000]
                print(f"[HTML SNIPPET] {snippet}", file=sys.stderr)
            try:
                image = page.locator("#landingImage").get_attribute("src")
            except Exception as e:
                print(f"[ERROR] Failed to extract image: {e}", file=sys.stderr)
                image = None
            if not title:
                return {"error": "Product title not found"}
            return {
                "title": title,
                "price": price,
                "image": image,
                "metadata": metadata,
                "alternate_prices": alternate_prices
            }
        except Exception as e:
            print(f"[ERROR] Unexpected error: {e}", file=sys.stderr)
            return {"error": str(e)}
        finally:
            if browser:
                browser.close()

def scrape_amazon(url, extract_metadata=True, get_alternates=True):
    """
    Main function to scrape Amazon product with metadata and alternative prices.
    Set extract_metadata=False or get_alternates=False to disable those features.
    """
    return scrape_amazon_product(url, extract_metadata=extract_metadata, get_alternates=get_alternates)