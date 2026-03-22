import streamlit as st
import requests
import pandas as pd
import os
import subprocess

# --- 1. SYSTEM FIX: PLAYWRIGHT PATHING ---
# We force Playwright to install in a location Streamlit can actually see
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "0" 

@st.cache_resource
def install_playwright():
    try:
        # We use 'install-deps' to ensure the Linux OS has the right libraries
        subprocess.run(["playwright", "install", "chromium"])
        return True
    except Exception as e:
        st.error(f"Installation Error: {e}")
        return False

if install_playwright():
    from playwright.sync_api import sync_playwright

# --- 2. THE SCRAPERS ---

def get_ah_data(query):
    """Refined 2026 AH Scraper with detailed error handling."""
    try:
        # Step A: Get Token
        auth_url = "https://api.ah.nl/mobile-auth/v1/auth/token/anonymous"
        token_res = requests.post(auth_url, json={"clientId": "appie"}, timeout=5).json()
        token = token_res.get("access_token")
        
        # Step B: The 'Secret' 2026 Headers
        search_url = f"https://api.ah.nl/mobile-services/product/search/v2?query={query}"
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Application": "nl.ah.mobile.consumer.app",
            "User-Agent": "Appie/8.22.3",
            "Accept": "application/json",
            "Host": "api.ah.nl"
        }
        
        res = requests.get(search_url, headers=headers, timeout=10)
        if res.status_code != 200:
            return {"Price": "N/A", "Status": f"AH Blocked ({res.status_code})"}
            
        data = res.json()
        product = data['products'][0]
        return {"Price": f"€{product['currentPrice']:.2f}", "Status": "🔥 Sale" if product.get('isBonus') else "Regular"}
    except:
        return {"Price": "N/A", "Status": "Check Query"}

def get_jumbo_data(query):
    """Jumbo Scraper using the correct Playwright pathing."""
    try:
        with sync_playwright() as p:
            # Headless shell is more 'stealthy' in 2026
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15")
            
            page.goto(f"https://www.jumbo.com/zoeken?searchTerms={query}", wait_until="networkidle")
            
            # Handle Cookie Wall
            try: page.click("button#onetrust-accept-btn-handler", timeout=3000)
            except: pass

            # Extract Price
            page.wait_for_selector(".whole-number", timeout=8000)
            euro = page.locator(".whole-number").first.inner_text()
            cents = page.locator(".fractional-number").first.inner_text()
            
            browser.close()
            return {"Price": f"€{euro}.{cents}", "Status": "Synced"}
    except Exception as e:
        return {"Price": "N/A", "Status": "Timeout/Bot-Block"}

# --- 3. UI ---
st.title("🛒 NL Supermarket Price Scout")

if 'list' not in st.session_state: st.session_state.list = []

with st.sidebar:
    item = st.text_input("Product Name:")
    if st.button("Add"):
        st.session_state.list.append(item)
        st.rerun()

if st.session_state.list:
    results = []
    for product in st.session_state.list:
        ah = get_ah_data(product)
        jumbo = get_jumbo_data(product)
        results.append({
            "Item": product, "AH": ah['Price'], "AH Status": ah['Status'],
            "Jumbo": jumbo['Price'], "Jumbo Status": jumbo['Status']
        })
    st.table(pd.DataFrame(results))
