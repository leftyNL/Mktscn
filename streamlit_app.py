import streamlit as st
import requests
import pandas as pd

# YOUR SHARED SERVER URL
BASE_PROXY_URL = "https://carstens.de/proxy/proxy.php" 

def get_data_from_proxy(store, query):
    try:
        response = requests.get(f"{BASE_PROXY_URL}?store={store}&q={query}", timeout=10)
        data = response.json()
        
        if store == 'ah':
            product = data['products'][0]
            return {"Price": f"€{product['currentPrice']:.2f}", "Status": "Bonus" if product.get('isBonus') else "Regular"}
        elif store == 'jumbo':
            return {"Price": data.get('price', "N/A"), "Status": "Synced"}
            
    except Exception as e:
        return {"Price": "N/A", "Status": "Offline"}

st.title("🛒 Supermarket Price Scout")

if 'list' not in st.session_state: st.session_state.list = []

with st.sidebar:
    new_item = st.text_input("Add product:")
    if st.button("Add") and new_item:
        st.session_state.list.append(new_item)
        st.rerun()

if st.session_state.list:
    results = []
    for item in st.session_state.list:
        ah = get_data_from_proxy('ah', item)
        jumbo = get_data_from_proxy('jumbo', item)
        results.append({"Item": item, "AH": ah['Price'], "Jumbo": jumbo['Price']})
    
    st.table(pd.DataFrame(results))
