import streamlit as st
import requests
import pandas as pd
import random
from playwright.sync_api import sync_playwright

# --- 1. CONFIG & HEADERS ---
USER_AGENTS = [
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
]

# --- 2. SCRAPERS WITH DEBUGGING ---

def get_ah_data(query):
    log = {"store": "AH", "status": "Initiating"}
    try:
        # Step A: Anonymous Auth
        auth_url = "https://api.ah.nl/mobile-auth/v1/auth/token/anonymous"
        token_res = requests.post(auth_url, json={"clientId": "appie"}, timeout=5)
        if token_res.status_code != 200:
            return {"Price": "N/A", "Status": f"Auth Fail ({token_res.status_code})"}, f"AH Auth Failed: {token_res.text}"
        
        token = token_res.json().get("access_token")
        
        # Step B: Search
        search_url = f"https://api.ah.nl/mobile-services/product/search/v2?query={query}"
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Application": "nl.ah.mobile.consumer.app",
            "User-Agent": random.choice(USER_AGENTS)
        }
        
        res = requests.get(search_url, headers=headers, timeout=10)
        if res.status_code != 200:
            return {"Price": "N/A", "Status": f"Block ({res.status_code})"}, f"AH Search Blocked: {res.status_code}"
            
        data = res.json()
        if not data.get('products'):
            return {"Price": "N/A", "Status": "Empty Results"}, "AH returned 0 products for this search."
            
        product = data['products'][0]
        return {"Price": f"€{product['currentPrice']:.2f}", "Status": "Success"}, "AH: OK"
    except Exception as e:
        return {"Price": "Err", "Status": "System Error"}, f"AH Exception: {str(e)}"

def get_jumbo_data(query):
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(user_agent=random.choice(USER_AGENTS))
            page = context.new_page()
            
            # Go to search
            response = page.goto(f"https://www.jumbo.com/zoeken?searchTerms={query}", wait_until="networkidle")
            
            if response.status != 200:
                browser.close()
                return {"Price": "N/A", "Status": "Blocked"}, f"Jumbo Blocked: {response.status}"

            # Accept Cookies
            try: page.click("button#onetrust-accept-btn-handler", timeout=3000)
            except: pass

            # Scrape
            page.wait_for_selector(".whole-number", timeout=7000)
            euro = page.locator(".whole-number").first.inner_text()
            cents = page.locator(".fractional-number").first.inner_text()
            
            browser.close()
            return {"Price": f"€{euro}.{cents}", "Status": "Success"}, "Jumbo: OK"
    except Exception as e:
        return {"Price": "N/A", "Status": "Timeout"}, f"Jumbo Error: {str(e)}"

# --- 3. UI ---
st.title("🛒 NL Price Tracker (v1.2 Debug)")

if 'watchlist' not in st.session_state:
    st.session_state.watchlist = []
if 'debug_logs' not in st.session_state:
    st.session_state.debug_logs = []

# Sidebar for management
with st.sidebar:
    item = st.text_input("Add product:")
    if st.button("Add"):
        st.session_state.watchlist.append(item)
        st.rerun()
    if st.button("Clear Logs"):
        st.session_state.debug_logs = []
        st.rerun()

# Comparison Table
if st.session_state.watchlist:
    display_list = []
    st.session_state.debug_logs = [] # Reset logs for this run
    
    for product in st.session_state.watchlist:
        ah_res, ah_log = get_ah_data(product)
        jumbo_res, jumbo_log = get_jumbo_data(product)
        
        st.session_state.debug_logs.append(ah_log)
        st.session_state.debug_logs.append(jumbo_log)
        
        display_list.append({
            "Product": product,
            "Albert Heijn": ah_res['Price'],
            "Jumbo": jumbo_res['Price']
        })
    
    st.table(pd.DataFrame(display_list))
    
    # DEBUG SECTION
    with st.expander("🛠️ Technical Debug Logs (Why it might be failing)"):
        for log in st.session_state.debug_logs:
            st.text(log)
