import os
import sys
import json
import requests
import re
from dotenv import load_dotenv
import time
from urllib.parse import unquote
from bs4 import BeautifulSoup  

load_dotenv()

def extract_metadata_with_gemini(title):
    try:
        import google.generativeai as genai
    except ImportError:
        print("[ERROR] google-generativeai SDK not installed. Run: pip install google-generativeai", file=sys.stderr)
        return None

    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        print('[ERROR] GEMINI_API_KEY not set in environment', file=sys.stderr)
        return None

    prompt = f"""
Extract the brand, model, and key attributes from this product title. Return as JSON with keys: brand, model, attributes.
Title: {title}
"""
    try:
        genai.configure(api_key=api_key)
        model_names = [
            'gemini-1.5-flash',
            'gemini-1.5-pro', 
            'gemini-1.0-pro',
            'models/gemini-1.5-flash',
            'models/gemini-1.5-pro',
            'models/gemini-1.0-pro'
        ]
        
        response = None
        last_error = None
        
        for model_name in model_names:
            try:
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(prompt)
                break  
            except Exception as e:
                last_error = e
                continue 
        
        if response is None:
            raise last_error or Exception("No working model found")
        
        response_text = response.text.strip()
        
        if response_text.startswith('```json'):
            response_text = response_text[7:]  
        elif response_text.startswith('```'):
            response_text = response_text[3:]   
            
        if response_text.endswith('```'):
            response_text = response_text[:-3] 
            
        response_text = response_text.strip()
        
        return json.loads(response_text)
    except json.JSONDecodeError as e:
        print(f"[ERROR] Failed to parse Gemini response as JSON: {e}", file=sys.stderr)
        print(f"[DEBUG] Raw response: {response.text}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"[ERROR] Gemini metadata extraction failed: {e}", file=sys.stderr)
        return None

def extract_price_from_text(text):
    """
    Extract price from text using multiple patterns
    """
    price_patterns = [
        r'₹\s*[\d,]+(?:\.\d+)?', 
        r'Rs\.?\s*[\d,]+(?:\.\d+)?', 
        r'INR\s*[\d,]+(?:\.\d+)?',  
        r'\b[\d,]+\s*₹',  
        r'Price:\s*₹?\s*[\d,]+(?:\.\d+)?',  
        r'MRP:?\s*₹?\s*[\d,]+(?:\.\d+)?', 
    ]
    
    for pattern in price_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            return matches[0].strip()
    
    return None

def search_platform_with_retry(search_func, query, platform_name, max_retries=2):
    """
    Wrapper function to retry platform searches with different queries
    """
    for attempt in range(max_retries):
        try:
            results = search_func(query)
            if results:
                return results
         
            if attempt < max_retries - 1:
                query = " ".join(query.split()[:3]) 
                time.sleep(1)  
        except Exception as e:
            print(f"[WARNING] {platform_name} search attempt {attempt + 1} failed: {e}", file=sys.stderr)
            if attempt < max_retries - 1:
                time.sleep(1)
    
    return []

def search_flipkart(query):
    """
    Use DuckDuckGo to search Flipkart for the product and return a list of (title, url, price) tuples.
    """
    search_url = "https://duckduckgo.com/html/"
    params = {"q": f"{query} site:flipkart.com"}  
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
    }
    
    try:
        resp = requests.get(search_url, params=params, headers=headers, timeout=15)
        resp.raise_for_status()
        with open("ddg_test.html", "w", encoding="utf-8") as f:
            f.write(resp.text)
       
        if ("no results" in resp.text.lower() or "captcha" in resp.text.lower() or "detected unusual traffic" in resp.text.lower()):
            print("[WARNING] DuckDuckGo may be blocking or returning no results.", file=sys.stderr)
            return []
        
        soup = BeautifulSoup(resp.text, "html.parser")
        results = []
        for a in soup.find_all("a", href=True):
            url = a["href"]
            if not url.startswith("https://www.flipkart.com/"):
                continue
            title = a.get_text(strip=True)
            if not title or len(title) < 5:
                continue
  
            price = None
            parent = a.find_parent()
            context = parent.get_text(" ", strip=True) if parent else title
            price = extract_price_from_text(context)
            if not price:
                price = extract_price_from_text(title)
            results.append({
                "title": title[:100],
                "url": url,
                "price": price
            })
            if len(results) >= 5:
                break
        results_with_prices = [r for r in results if r['price']]
        if results_with_prices:
            return results_with_prices[:5]
        return results[:5]
    except Exception as e:
        print(f"[ERROR] Flipkart search failed: {e}", file=sys.stderr)
        return []

def search_meesho(query):
    """
    Use DuckDuckGo to search Meesho for the product and return a list of (title, url, price) tuples.
    """
    search_url = "https://duckduckgo.com/html/"
    params = {"q": f"{query} site:meesho.com"} 
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }
    
    try:
        resp = requests.get(search_url, params=params, headers=headers, timeout=15)
        resp.raise_for_status()
        
        links = re.findall(r'<a[^>]+href="(https://www\\.meesho\\.com/[^\"]+)"[^>]*>(.*?)</a>', resp.text, re.DOTALL)
        results = []
        
        for url, title_html in links:
            url = unquote(url)
            if 'meesho.com' not in url:
                continue
                
            title = re.sub('<[^<]+?>', '', title_html).strip()
            if not title or len(title) < 5:
                continue
            
            price = None
            
            # Find price in surrounding context
            link_pos = resp.text.find(url)
            if link_pos != -1:
                context_start = max(0, link_pos - 500)
                context_end = min(len(resp.text), link_pos + 500)
                context = resp.text[context_start:context_end]
                price = extract_price_from_text(context)
            
            if not price:
                price = extract_price_from_text(title_html + " " + title)
            
            results.append({
                "title": title[:100],
                "url": url,
                "price": price
            })
            
            if len(results) >= 5:
                break
        
        # Prioritize results with prices
        results_with_prices = [r for r in results if r['price']]
        if results_with_prices:
            return results_with_prices[:5]
        
        # Fallback: Save HTML and try BeautifulSoup parsing if no results with prices
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            print("[WARNING] BeautifulSoup not installed, skipping fallback parsing for Meesho.", file=sys.stderr)
            return results[:5]
        # Save HTML for debugging
        with open("ddg_meesho.html", "w", encoding="utf-8") as f:
            f.write(resp.text)
        print("[INFO] Saved DuckDuckGo HTML for Meesho fallback parsing.", file=sys.stderr)
        soup = BeautifulSoup(resp.text, "html.parser")
        alt_results = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if href.startswith("https://www.meesho.com/"):
                title = a.get_text(strip=True)
                if not title or len(title) < 5:
                    continue
                price = extract_price_from_text(title)
                alt_results.append({
                    "title": title[:100],
                    "url": href,
                    "price": price
                })
                if len(alt_results) >= 5:
                    break
        alt_results_with_prices = [r for r in alt_results if r['price']]
        if alt_results_with_prices:
            return alt_results_with_prices[:5]
        return alt_results[:5] if alt_results else results[:5]
        
    except Exception as e:
        print(f"[ERROR] Meesho search failed: {e}", file=sys.stderr)
        return []

def search_reliance_digital(query):
    """
    Use DuckDuckGo to search Reliance Digital for the product and return a list of (title, url, price) tuples.
    """
    search_url = "https://duckduckgo.com/html/"
    params = {"q": f"{query} site:reliancedigital.in"}  # No quotes, as per requirement
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }
    
    try:
        resp = requests.get(search_url, params=params, headers=headers, timeout=15)
        resp.raise_for_status()
        
        links = re.findall(r'<a[^>]+href="(https://www\\.reliancedigital\\.in/[^\"]+)"[^>]*>(.*?)</a>', resp.text, re.DOTALL)
        results = []
        
        for url, title_html in links:
            url = unquote(url)
            if 'reliancedigital.in' not in url:
                continue
                
            title = re.sub('<[^<]+?>', '', title_html).strip()
            if not title or len(title) < 5:
                continue
            
            price = None
            
            # Find price in surrounding context
            link_pos = resp.text.find(url)
            if link_pos != -1:
                context_start = max(0, link_pos - 500)
                context_end = min(len(resp.text), link_pos + 500)
                context = resp.text[context_start:context_end]
                price = extract_price_from_text(context)
            
            if not price:
                price = extract_price_from_text(title_html + " " + title)
            
            results.append({
                "title": title[:100],
                "url": url,
                "price": price
            })
            
            if len(results) >= 5:
                break
        
        # Prioritize results with prices
        results_with_prices = [r for r in results if r['price']]
        if results_with_prices:
            return results_with_prices[:5]
        
        # Fallback: Save HTML and try BeautifulSoup parsing if no results with prices
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            print("[WARNING] BeautifulSoup not installed, skipping fallback parsing for Reliance Digital.", file=sys.stderr)
            return results[:5]
        # Save HTML for debugging
        with open("ddg_reliance.html", "w", encoding="utf-8") as f:
            f.write(resp.text)
        print("[INFO] Saved DuckDuckGo HTML for Reliance Digital fallback parsing.", file=sys.stderr)
        soup = BeautifulSoup(resp.text, "html.parser")
        alt_results = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if href.startswith("https://www.reliancedigital.in/"):
                title = a.get_text(strip=True)
                if not title or len(title) < 5:
                    continue
                price = extract_price_from_text(title)
                alt_results.append({
                    "title": title[:100],
                    "url": href,
                    "price": price
                })
                if len(alt_results) >= 5:
                    break
        alt_results_with_prices = [r for r in alt_results if r['price']]
        if alt_results_with_prices:
            return alt_results_with_prices[:5]
        return alt_results[:5] if alt_results else results[:5]
        
    except Exception as e:
        print(f"[ERROR] Reliance Digital search failed: {e}", file=sys.stderr)
        return []

def get_alternate_platform_prices(title, brand=None, model=None):
    """
    Use extracted metadata to form search queries and return alternate prices from Flipkart, Meesho, and Reliance Digital.
    """
    # Create multiple query variations
    queries = [title]
    
    if brand and model:
        queries.append(f"{brand} {model}")
        queries.append(f"{brand} {model} {title}")
    elif brand:
        queries.append(f"{brand} {title}")
    elif model:
        queries.append(f"{model} {title}")
    
    all_results = []
    
    for query in queries:
        # Clean up query
        query = re.sub(r'\s+', ' ', query).strip()
        
        print(f"[INFO] Searching with query: {query}", file=sys.stderr)
        
        # Search each platform with retry logic
        flipkart_results = search_platform_with_retry(search_flipkart, query, "Flipkart")
        meesho_results = search_platform_with_retry(search_meesho, query, "Meesho")
        reliance_results = search_platform_with_retry(search_reliance_digital, query, "Reliance Digital")
        
        # Add platform info and collect results
        for result in flipkart_results:
            result['platform'] = 'flipkart'
            all_results.append(result)
        
        for result in meesho_results:
            result['platform'] = 'meesho'
            all_results.append(result)
        
        for result in reliance_results:
            result['platform'] = 'reliance digital'
            all_results.append(result)
        
        # If we found results with prices, prioritize them
        results_with_prices = [r for r in all_results if r.get('price')]
        if len(results_with_prices) >= 5:
            break
        
        # Brief delay between query variations
        time.sleep(0.5)
    
    # Remove duplicates based on URL
    seen_urls = set()
    unique_results = []
    for result in all_results:
        if result['url'] not in seen_urls:
            seen_urls.add(result['url'])
            unique_results.append(result)
    
    # Sort by whether they have prices (with prices first)
    unique_results.sort(key=lambda x: (x.get('price') is None, x.get('platform', '')))
    
    return unique_results[:15]  # Return top 15 results

# For compatibility with the rest of the codebase
extract_metadata_with_openai = extract_metadata_with_gemini
