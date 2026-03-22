import streamlit as st
import requests
import pandas as pd
import subprocess
from playwright.sync_api import sync_playwright

# --- 1. SYSTEM SETUP ---
@st.cache_resource
def install_browsers():
    try:
        # This installs the necessary browser engine on Streamlit's server
        subprocess.run(["playwright", "install", "chromium"])
        return True
    except:
        return False

install_browsers()

# --- 2. THE STEALTH SCRAPERS ---

def get_ah_data(query):
    """2026 Stealth Version for Albert Heijn"""
    try:
        # AH requires these exact headers to not return a 401/403 error
        auth_url = "https://api.ah.nl/mobile-auth/v1/auth/token/anonymous"
        token_res = requests.post(auth_url, json={"clientId": "appie"}).json()
        token = token_res.get("access_token")
        
        search_url = f"https://api.ah.nl/mobile-services/product/search/v2?query={query}"
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Application": "nl.ah.mobile.consumer.app",
            "User-Agent": "Appie/8.22.3",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        res = requests.get(search_url, headers=headers, timeout=10).json()
        if not res.get('products'): return {"Price": "N/A", "Status": "No Match"}
            
        product = res['products'][0]
        price = product['currentPrice']
        
        return {
            "Price": f"€{price:.2f}",
            "Status": "🔥 BONUS" if product.get('isBonus') else "Regular"
        }
    except Exception as e:
        return {"Price": "Blocked", "Status": "Check API"}

def get_jumbo_data(query):
    """2026 Stealth Version for Jumbo (Playwright)"""
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            # Mimic a modern iPhone to bypass bot detection
            context = browser.new_context(
                user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1"
            )
            page = context.new_page()
            page.goto(f"https://www.jumbo.com/zoeken?searchTerms={query}", wait_until="domcontentloaded")
            
            # 1. Click the Cookie Consent if it blocks the view
            try:
                page.click("button#onetrust-accept-btn-handler", timeout=3000)
            except:
                pass 

            # 2. Extract Price (Jumbo split prices into Euro and Cents)
            page.wait_for_selector(".whole-number", timeout=8000)
            euro = page.locator(".whole-number").first.inner_text()
            cents = page.locator(".fractional-number").first.inner_text()
            
            # 3. Check for discount labels
            is_promo = page.locator(".product-price__discount").count() > 0
            
            browser.close()
            return {"Price": f"€{euro}.{cents}", "Status": "🔥 SALE" if is_promo else "Regular"}
    except:
        return {"Price": "N/A", "Status": "Timeout"}

# --- 3. THE INTERFACE ---

st.set_page_config(page_title="Price Scout", page_icon="🛍️")
st.title("🛍️ Dutch Price Scout")

if 'list' not in st.session_state:
    st.session_state.list = []

# Input
with st.form("add_form", clear_on_submit=True):
    new_item = st.text_input("Product Name", placeholder="e.g. 'Heineken 6-pack' or 'Zaanse Hoeve Melk'")
    if st.form_submit_button("Add to Comparison"):
        if new_item:
            st.session_state.list.append(new_item)
            st.rerun()

# Table
if st.session_state.list:
    results = []
    with st.spinner("Scouting prices..."):
        for item in st.session_state.list:
            ah = get_ah_data(item)
            jumbo = get_jumbo_data(item)
            results.append({
                "Product": item,
                "Albert Heijn": ah['Price'],
                "AH Info": ah['Status'],
                "Jumbo": jumbo['Price'],
                "Jumbo Info": jumbo['Status']
            })
    
    st.table(pd.DataFrame(results))
    
    if st.button("Clear List"):
        st.session_state.list = []
        st.rerun()
else:
    st.info("Enter a product above to compare prices.")
