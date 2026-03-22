import streamlit as st
import requests
import pandas as pd
import os
import subprocess

# --- 1. SYSTEM SETUP: FIXING THE CLOUD BROWSER ---
# This part makes sure Chromium is ready for Jumbo/Hoogvliet
@st.cache_resource
def setup_browser():
    try:
        from playwright.sync_api import sync_playwright
        # Force install chromium on the Streamlit server
        subprocess.run(["playwright", "install", "chromium"])
        return True
    except Exception as e:
        st.error(f"Browser Setup Error: {e}")
        return False

setup_browser()
from playwright.sync_api import sync_playwright

# --- 2. SUPERMARKET SCRAPERS ---

def get_ah_data(query):
    """Fetches AH prices using the 2026 Mobile API requirements."""
    try:
        # Step A: Get an anonymous token
        auth_url = "https://api.ah.nl/mobile-auth/v1/auth/token/anonymous"
        token_res = requests.post(auth_url, json={"clientId": "appie"}).json()
        token = token_res.get("access_token")
        
        # Step B: Search with proper headers
        search_url = f"https://api.ah.nl/mobile-services/product/search/v2?query={query}"
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Application": "nl.ah.mobile.consumer.app", # REQUIRED in 2026
            "User-Agent": "Appie/8.22.3",
            "Content-Type": "application/json"
        }
        
        res = requests.get(search_url, headers=headers, timeout=10).json()
        product = res['products'][0]
        
        price = product['currentPrice']
        is_promo = product.get('isBonus', False)
        
        return {
            "Price": f"€{price:.2f}",
            "Status": "🔥 SALE" if is_promo else "Regular"
        }
    except:
        return {"Price": "N/A", "Status": "Not Found"}

def get_jumbo_data(query):
    """Fetches Jumbo prices by mimicking a real user on a phone."""
    try:
        with sync_playwright() as p:
            # We use a real User Agent to avoid being blocked
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
            )
            page = context.new_page()
            page.goto(f"https://www.jumbo.com/zoeken?searchTerms={query}")
            
            # 1. Handle Cookie Wall
            try:
                page.click("button:has-text('Accepteren')", timeout=3000)
            except:
                pass
            
            # 2. Wait for price to load
            page.wait_for_selector(".whole-number", timeout=7000)
            euro = page.locator(".whole-number").first.inner_text()
            cents = page.locator(".fractional-number").first.inner_text()
            
            browser.close()
            return {"Price": f"€{euro}.{cents}", "Status": "Synced"}
    except:
        return {"Price": "N/A", "Status": "Not Found"}

# --- 3. THE APP INTERFACE ---

st.set_page_config(page_title="Supermarket Scout", layout="centered")
st.title("🛒 Supermarket Price Scout")

if 'watchlist' not in st.session_state:
    st.session_state.watchlist = []

# Top Section: Add Items
with st.container():
    col1, col2 = st.columns([3, 1])
    with col1:
        item_input = st.text_input("", placeholder="Enter item (e.g. 'Heineken 6-pack')")
    with col2:
        if st.button("Add to List") and item_input:
            if item_input not in st.session_state.watchlist:
                st.session_state.watchlist.append(item_input)
                st.rerun()

# Middle Section: The Comparison Table
if st.session_state.watchlist:
    st.write("---")
    results = []
    
    # Progress bar for the scraping wait time
    progress_bar = st.progress(0)
    for index, item in enumerate(st.session_state.watchlist):
        ah = get_ah_data(item)
        jumbo = get_jumbo_data(item)
        
        results.append({
            "Product": item,
            "Albert Heijn": ah['Price'],
            "AH Info": ah['Status'],
            "Jumbo": jumbo['Price'],
            "Jumbo Info": jumbo['Status']
        })
        progress_bar.progress((index + 1) / len(st.session_state.watchlist))

    df = pd.DataFrame(results)
    st.table(df)
    
    if st.button("🗑️ Clear Entire List"):
        st.session_state.watchlist = []
        st.rerun()
else:
    st.info("Your list is empty. Add your first item above!")
