import streamlit as st
import requests
import pandas as pd

# --- 1. SUPERMARKET SCRAPERS ---
def fetch_ah_price(query):
    """Fetches the best match from AH using their mobile API."""
    url = f"https://api.ah.nl/mobile-services/product/search/v2?query={query}"
    headers = {"User-Agent": "Appie/8.22.3"}
    try:
        res = requests.get(url, headers=headers, timeout=5).json()
        prod = res['products'][0]
        curr = prod['currentPrice']
        was = prod.get('wasPrice', curr)
        return {
            "Store": "AH",
            "Price": curr,
            "Offer": f"Sale: {curr} (was {was})" if prod.get('isBonus') else "Regular"
        }
    except:
        return {"Store": "AH", "Price": 0, "Offer": "Not Found"}

# Note: In the real app, Jumbo and Hoogvliet functions would follow 
# using BeautifulSoup or Playwright for web-parsing.

# --- 2. APP STATE ---
if 'watchlist' not in st.session_state:
    st.session_state.watchlist = ["Melk", "Pindakaas"]

# --- 3. UI LAYOUT ---
st.set_page_config(page_title="Dutch Price Tracker", layout="wide")
st.title("🛒 Supermarket Price Compare")

# Sidebar for Management
with st.sidebar:
    st.header("Manage List")
    new_item = st.text_input("Add product:")
    if st.button("Add"):
        if new_item:
            st.session_state.watchlist.append(new_item)
            st.rerun()
    
    to_remove = st.selectbox("Remove product:", [""] + st.session_state.watchlist)
    if st.button("Remove") and to_remove:
        st.session_state.watchlist.remove(to_remove)
        st.rerun()

# --- 4. THE DATA TABLE ---
if st.session_state.watchlist:
    results = []
    for item in st.session_state.watchlist:
        # Here we call our scrapers
        ah_data = fetch_ah_price(item)
        results.append({
            "Product": item,
            "AH Price": f"€{ah_data['Price']}",
            "AH Status": ah_data['Offer'],
            "Jumbo": "€--", # Placeholder for next scraper
            "Hoogvliet": "€--" 
        })
    
    df = pd.DataFrame(results)
    st.table(df)
else:
    st.info("Your list is empty. Add items in the sidebar!")
