import streamlit as st
import requests
import pandas as pd
import os
import subprocess

# --- 1. CLOUD BROWSER SETUP ---
# This ensures Playwright and Chromium are installed on the Streamlit server
@st.cache_resource
def install_playwright():
    try:
        from playwright.sync_api import sync_playwright
        subprocess.run(["playwright", "install", "chromium"])
        return True
    except ImportError:
        return False

install_playwright()
from playwright.sync_api import sync_playwright

# --- 2. SCRAPER LOGIC ---

def get_ah_data(query):
    """Fetches data from AH using their mobile API with an anonymous token."""
    try:
        # Get Token
        auth_url = "https://api.ah.nl/mobile-auth/v1/auth/token/anonymous"
        token_res = requests.post(auth_url, json={"clientId": "appie"}).json()
        token = token_res.get("access_token")
        
        # Search Product
        search_url = f"https://api.ah.nl/mobile-services/product/search/v2?query={query}"
        headers = {"Authorization": f"Bearer {token}", "User-Agent": "Appie/8.22.3"}
        
        res = requests.get(search_url, headers=headers, timeout=10).json()
        product = res['products'][0]
        
        price = product['currentPrice']
        is_promo = product.get('isBonus', False)
        was_price = product.get('wasPrice', price)
        
        return {
            "Price": f"€{price:.2f}",
            "Status": f"🔥 Offer (was €{was_price})" if is_promo else "Regular"
        }
    except Exception:
        return {"Price": "N/A", "Status": "Not Found"}

def get_jumbo_data(query):
    """Fetches data from Jumbo using a headless browser."""
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            # We go directly to the search results
            page.goto(f"https://www.jumbo.com/zoeken?searchTerms={query}", wait_until="networkidle")
            
            # Wait for price elements
            page.wait_for_selector(".whole-number", timeout=5000)
            euro = page.locator(".whole-number").first.inner_text()
            cents = page.locator(".fractional-number").first.inner_text()
            
            # Check for discount labels
            promo_count = page.locator(".product-price__discount").count()
            
            browser.close()
            return {
                "Price": f"€{euro}.{cents}",
                "Status": "🔥 Offer" if promo_count > 0 else "Regular"
            }
    except Exception:
        return {"Price": "N/A", "Status": "Not Found"}

# --- 3. STREAMLIT UI ---

st.set_page_config(page_title="NL Price Tracker", page_icon="🛒")

st.title("🛒 Supermarket Price Compare")
st.info("Searching for items at AH and Jumbo... (Hoogvliet integration pending)")

# Initialize the watchlist in the session
if 'watchlist' not in st.session_state:
    st.session_state.watchlist = []

# Sidebar for adding/removing items
with st.sidebar:
    st.header("My Shopping List")
    new_item = st.text_input("Product Name (e.g. 'Heineken')")
    if st.button("Add Item"):
        if new_item and new_item not in st.session_state.watchlist:
            st.session_state.watchlist.append(new_item)
            st.rerun()
    
    if st.session_state.watchlist:
        item_to_remove = st.selectbox("Remove an item:", st.session_state.watchlist)
        if st.button("Remove"):
            st.session_state.watchlist.remove(item_to_remove)
            st.rerun()

# Display the comparison table
if st.session_state.watchlist:
    with st.spinner('Fetching live prices...'):
        final_data = []
        for item in st.session_state.watchlist:
            ah = get_ah_data(item)
            jumbo = get_jumbo_data(item)
            
            final_data.append({
                "Product": item.capitalize(),
                "AH Price": ah['Price'],
                "AH Detail": ah['Status'],
                "Jumbo Price": jumbo['Price'],
                "Jumbo Detail": jumbo['Status']
            })
        
        df = pd.DataFrame(final_data)
        st.table(df)
else:
    st.write("Your list is empty. Use the sidebar to add items!")

st.divider()
st.caption("Tip: Be specific with names (e.g., 'Halfvolle Melk 1L') for better results.")
