import streamlit as st
import pandas as pd
import requests

# --- Configuration ---
st.set_page_config(page_title="Syndicate Staking Calculator", layout="wide")

# --- Fetch Live Prices from CoinGecko ---
@st.cache_data(ttl=600) # Caches the data for 10 minutes to avoid rate limits
def get_live_prices():
    url = "https://api.coingecko.com/api/v3/simple/price?ids=bittensor,solana,hedera-hashgraph&vs_currencies=cad"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        return {
            "TAO": data.get("bittensor", {}).get("cad", 0.0),
            "SOL": data.get("solana", {}).get("cad", 0.0),
            "HBAR": data.get("hedera-hashgraph", {}).get("cad", 0.0)
        }
    except Exception as e:
        st.sidebar.error(f"Failed to fetch live prices: {e}")
        return {"TAO": 340.0, "SOL": 200.0, "HBAR": 0.15} # Fallback defaults

prices = get_live_prices()

# --- Sidebar Controls ---
st.sidebar.header("Asset Configuration")
asset = st.sidebar.selectbox("Select Asset", ["TAO", "SOL", "HBAR"])

# Auto-populate the price based on the selected asset, but allow manual override
live_price = prices[asset]
token_price = st.sidebar.number_input(f"{asset} Price (CAD)", value=float(live_price), step=1.0)

st.sidebar.header("Investment Parameters")
initial_stake = st.sidebar.number_input(f"Initial {asset} Stake", value=28.5, step=1.0)
apy = st.sidebar.slider("Staking APY (%)", min_value=0.0, max_value=100.0, value=35.0, step=0.5)
weekly_dca = st.sidebar.number_input("Weekly DCA Amount (CAD)", value=500.0, step=50.0)

# --- Core Logic ---
st.title("Syndicate Compounding & DCA Calculator")
st.markdown(f"Modeling 5-year growth for **{asset}** at **${token_price:,.2f} CAD**.")

weeks_in_year = 52
total_years = 5
total_weeks = total_years * weeks_in_year
weekly_rate = (apy / 100) / weeks_in_year

# Tracking variables
current_tokens = initial_stake
total_fiat_invested = initial_stake * token_price

data = []

# Calculate week by week
for week in range(1, total_weeks + 1):
    # 1. Add weekly DCA
    tokens_bought = weekly_dca / token_price
    current_tokens += tokens_bought
    total_fiat_invested += weekly_dca
    
    # 2. Add weekly compounding interest
    interest_earned = current_tokens * weekly_rate
    current_tokens += interest_earned
    
    # 3. Record data at the end of each year
    if week % weeks_in_year == 0:
        year = week // weeks_in_year
        portfolio_value = current_tokens * token_price
        data.append({
            "Year": f"Year {year}",
            "Total Tokens": round(current_tokens, 2),
            "Total Value (CAD)": round(portfolio_value, 2),
            "Out of Pocket (CAD)": round(total_fiat_invested, 2),
            "Interest Earned (Tokens)": round(current_tokens - initial_stake - (weekly_dca / token_price * week), 2)
        })

df = pd.DataFrame(data)

# --- Visualization ---
st.subheader("Portfolio Value Growth Over 5 Years")
# Create a chart mapping the Out of Pocket vs Total Value
chart_data = df.set_index("Year")[["Out of Pocket (CAD)", "Total Value (CAD)"]]
st.line_chart(chart_data)

# --- Breakdown Table ---
st.subheader("Year-over-Year Breakdown")
# Format the table for clean reading
formatted_df = df.copy()
formatted_df["Total Value (CAD)"] = formatted_df["Total Value (CAD)"].apply(lambda x: f"${x:,.2f}")
formatted_df["Out of Pocket (CAD)"] = formatted_df["Out of Pocket (CAD)"].apply(lambda x: f"${x:,.2f}")
st.dataframe(formatted_df, use_container_width=True, hide_index=True)
