from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import re

def clean_price(price_str):
    price_str = price_str.replace('₹', '').replace(',', '').strip()
    try:
        return float(re.findall(r"[\d.]+", price_str)[0])
    except Exception as e:
        print(f"[ERROR] Failed to clean price: {e} | Raw: {price_str}")
        return None

def scrape_amazon_product(url):
    with sync_playwright() as p:
        browser = None
        try:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            try:
                response = page.goto(url, timeout=20000)
                final_url = page.url
                if final_url != url:
                    print(f"[REDIRECT] Navigated from {url} to {final_url}")
                content = page.content()
               
                if ("Enter the characters you see below" in content or
                    "not a robot" in content or
                    "captcha" in content.lower() or
                    "Sorry, we just need to make sure you're not a robot" in content):
                    print(f"[BLOCKED] CAPTCHA or block detected on {final_url}")
                    return {"error": "CAPTCHA or block detected"}
               
                if ("unavailable" in content.lower() or
                    "404" in content or
                    "not found" in content.lower()):
                    print(f"[UNAVAILABLE] Product page unavailable or not found: {final_url}")
                    return {"error": "Product page unavailable or not found"}
            except PlaywrightTimeoutError:
                print(f"[ERROR] Timeout navigating to {url}")
                return {"error": f"Timeout navigating to {url}"}
            except Exception as e:
                print(f"[ERROR] Failed to navigate to {url}: {e}")
                return {"error": f"Failed to navigate: {e}"}
            try:
                page.wait_for_selector('#productTitle', timeout=10000)
            except PlaywrightTimeoutError:
                print(f"[ERROR] Timeout waiting for product title on {url}")
                return {"error": "Timeout waiting for product title"}
            except Exception as e:
                print(f"[ERROR] Failed to find product title: {e}")
                return {"error": f"Failed to find product title: {e}"}
            try:
                title = page.locator("#productTitle").nth(0).inner_text().strip()
            except Exception as e:
                print(f"[ERROR] Failed to extract title: {e}")
                title = None
            try:
                price = page.locator("span.a-price span.a-offscreen").first.inner_text().strip()
                price = clean_price(price)
            except Exception as e:
                print(f"[ERROR] Failed to extract price: {e}")
                price = None
            try:
                image = page.locator("#landingImage").get_attribute("src")
            except Exception as e:
                print(f"[ERROR] Failed to extract image: {e}")
                image = None
            if not title:
                return {"error": "Product title not found"}
            return {
                "title": title,
                "price": price,
                "image": image
            }
        except Exception as e:
            print(f"[ERROR] Unexpected error: {e}")
            return {"error": str(e)}
        finally:
            if browser:
                browser.close()

def scrape_amazon(url):
    return scrape_amazon_product(url)