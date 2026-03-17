

################



import streamlit as st
import requests
import pandas as pd
from openai import OpenAI

# -----------------------------
# 🔑 CONFIG
# -----------------------------
import os

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
CSRFTOKEN = st.secrets["CSRFTOKEN"]
SESSIONID = st.secrets["SESSIONID"]

client = OpenAI(api_key=OPENAI_API_KEY)

# -----------------------------
# FORMAT FUNCTION (NEW 🔥)
# -----------------------------
def format_volume(value):
    if value is None:
        return "N/A"

    tonnes = value / 1000

    if tonnes >= 1000:
        return f"{tonnes/1000:.2f}K tonnes"
    else:
        return f"{tonnes:.0f} tonnes"
# -----------------------------
# HEADER
# -----------------------------
col1, col2 = st.columns([1, 3])

with col1:
    st.image("logo.png", width=120)

with col2:
    st.markdown(
        "<h1 style='margin-top: -20px;'>Agronometrics AI Analyst</h1>",
        unsafe_allow_html=True
    )

st.markdown("### 📊 Real-time commodity insights powered by AI")
st.markdown("---")

# -----------------------------
# COMMODITIES
# -----------------------------
COMMODITIES = {
    "Tangerine": 34, "Strawberries": 16, "Raspberry": 26,
    "Plums": 23, "Pears": 27, "Peaches": 29, "Oranges": 31,
    "Nectarines": 24, "Mango": 28, "Limes": 18, "Lemons": 22,
    "Kiwifruit": 15, "Grapes": 21, "Grapefruit": 14,
    "Clementines": 12, "Cherries": 17, "Blueberries": 20,
    "Blackberries": 30, "Avocados": 19, "Asparagus": 11, "Apples": 25
}

# -----------------------------
# UI
# -----------------------------
col1, col2 = st.columns(2)

with col1:
    commodity_name = st.selectbox("Commodity", list(COMMODITIES.keys()))

with col2:
    data_type = st.selectbox("Data Type", ["Volume", "Price"])

period = st.selectbox("Period", ["weekly", "monthly"])

run = st.button("Run Analysis")

# -----------------------------
# FETCH DATA
# -----------------------------
def fetch_data(commodity_id, data_type, period):

    url = "https://www.agronometrics.com/system/get_trade_facts/"
    session = requests.Session()

    session.cookies.update({
        "csrftoken": CSRFTOKEN,
        "sessionid": SESSIONID
    })

    headers = {
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "Origin": "https://www.agronometrics.com",
        "Referer": "https://www.agronometrics.com/",
        "User-Agent": "Mozilla/5.0",
        "X-CSRFToken": CSRFTOKEN,
        "X-Requested-With": "XMLHttpRequest"
    }

    if data_type == "Volume":
        payload = {
            "params": {
                "top": "5",
                "units": "kg",
                "period": period,
                "measure": "volume_kg",
                "interval": "78",
                "compare_by": "history",
                "commodity": str(commodity_id),
                "datasource": "usda_mv",
                "season": "false",
                "history": False,
                "unit_factor": "1",
                "variety": "all",
                "location": "all",
                "origin": "all",
                "s_type": "all",
                "transportation_mode": "all",
                "movement_type": "all",
                "properties": "all"
            },
            "compare_by": "history",
            "datasource": "usda_mv"
        }

    else:
        payload = {
            "params": {
                "top": "5",
                "units": "kg",
                "period": period,
                "measure": "reported_price",
                "interval": "26",
                "compare_by": "history",
                "commodity": str(commodity_id),
                "datasource": "usda_sp",
                "season": "false",
                "history": True,
                "unit_factor": "1",
                "variety": "all",
                "location": "all",
                "grade": "all",
                "size": "all",
                "package": "all",
                "s_type": "all",
                "trade_flow": "all"
            },
            "compare_by": "history",
            "datasource": "usda_sp"
        }

    response = session.post(url, json=payload, headers=headers)

    if response.status_code != 200:
        st.error("❌ API failed")
        st.text(response.text[:300])
        return None

    try:
        return response.json()
    except:
        st.error("❌ Invalid response")
        return None

# -----------------------------
# PARSE DATA
# -----------------------------
def parse_data(data, period):

    tf = data["trade_facts"]
    dates = tf["categories"]
    series = tf["series"]

    df_list = []

    for s in series:
        df_list.append(pd.DataFrame({
            "date": dates,
            "value": s["data"],
            "series": s["name"]
        }))

    df = pd.concat(df_list, ignore_index=True)

    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df["date"] = pd.to_numeric(df["date"], errors="coerce")
    df["series"] = pd.to_numeric(df["series"], errors="coerce")

    if period == "weekly":
        df["real_date"] = pd.to_datetime(
            df["series"].astype(int).astype(str) +
            "-W" + df["date"].astype(int).astype(str) + "-1",
            format="%Y-W%W-%w",
            errors="coerce"
        )
    else:
        df["real_date"] = pd.to_datetime(
            df["series"].astype(int).astype(str) +
            "-" + df["date"].astype(int).astype(str),
            format="%Y-%m",
            errors="coerce"
        )

    return df

# -----------------------------
# GPT ANALYSIS
# -----------------------------
def analyze_with_gpt(df, period, data_type):

    df = df.dropna(subset=["value", "real_date"])

    latest_year = int(df["series"].max())
    prev_year = latest_year - 1

    df_latest = df[df["series"] == latest_year].sort_values("real_date")
    df_prev = df[df["series"] == prev_year]

    if df_latest.empty:
        return "No recent data available."

    latest_row = df_latest.iloc[-1]

    latest_value_raw = latest_row["value"]
    latest_date = latest_row["real_date"]

    # FORMAT VALUES 🔥
    if data_type == "Volume":
        latest_value = format_volume(latest_value_raw)
    else:
        latest_value = round(latest_value_raw, 2)

    # PERIOD LABEL
    if period == "weekly":
        period_label = f"Week {latest_date.isocalendar().week}"
        key = latest_date.isocalendar().week
        prev_match = df_prev[
            df_prev["real_date"].dt.isocalendar().week == key
        ]
    else:
        period_label = latest_date.strftime("%B")
        key = latest_date.month
        prev_match = df_prev[
            df_prev["real_date"].dt.month == key
        ]

    if len(prev_match) > 0:
        prev_value_raw = prev_match.iloc[-1]["value"]

        if data_type == "Volume":
            prev_value = format_volume(prev_value_raw)
        else:
            prev_value = round(prev_value_raw, 2)

        pct_change = ((latest_value_raw - prev_value_raw) / prev_value_raw) * 100
        pct_text = f"{pct_change:.2f}%"
    else:
        prev_value = "N/A"
        pct_text = "N/A"

    recent_trend = df_latest.tail(10)

    prompt = f"""
You are an agricultural market analyst writing in a neutral, data-driven style.

DATA CONTEXT:
Latest observation:
{period_label} {latest_year} → {latest_value}

YoY comparison:
{period_label} {latest_year}: {latest_value}
vs {period_label} {prev_year}: {prev_value}
Change: {pct_text}

Recent trend:
{recent_trend[["real_date", "value"]].to_string(index=False)}

INSTRUCTIONS:

1. First, write a short factual paragraph describing:
   - trend direction
   - YoY comparison
   - recent movement

2. Then add EXACTLY 2 short lines of interpretation:
   - what this likely reflects in the market
   - keep it grounded in the data

RULES:

- Keep tone neutral and professional
- No dramatic or speculative language
- No generic supply/demand explanations
- Keep interpretation subtle and data-linked

FORMAT:

Paragraph

Interpretation:
- Line 1
- Line 2
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a senior commodity analyst."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3
    )

    return response.choices[0].message.content

# -----------------------------
# RUN
# -----------------------------
if run:

    commodity_id = COMMODITIES[commodity_name]

    data = fetch_data(commodity_id, data_type, period)

    if not data:
        st.warning("⚠️ No data available")
    else:
        df = parse_data(data, period)

        df = df.dropna(subset=["value", "real_date"])

        latest_year = df["series"].max()
        df_latest = df[df["series"] == latest_year].sort_values("real_date")

        recent_df = df_latest.tail(20).sort_values("real_date", ascending=False)

        # FORMAT TABLE 🔥
        display_df = recent_df.copy()

        if data_type == "Volume":
            display_df["value"] = display_df["value"].apply(format_volume)
        else:
            display_df["value"] = display_df["value"].round(2)

        st.subheader(" Data  ")
        st.dataframe(display_df[["real_date", "value"]])

                # CHART
        # -----------------------------
        # CHART (FIXED SEASONAL VERSION 🔥)
        # -----------------------------
        import plotly.graph_objects as go

        st.subheader("Chart")

        # ✅ KEY: create week column
        df["week"] = df["real_date"].dt.isocalendar().week

        fig = go.Figure()

        years = sorted(df["series"].dropna().unique())
        latest_year = max(years)

        colors = {
            2022: "#4C78A8",
            2023: "#72B7B2",
            2024: "#F2CF5B",
            2025: "#B279A2",
            2026: "#FF9DA6"
        }

        for year in years:
            df_year = df[df["series"] == year].sort_values("week")

            fig.add_trace(go.Scatter(
                x=df_year["week"],   # 🔥 THIS FIXES EVERYTHING
                y=df_year["value"],
                mode="lines+markers",
                name=str(int(year)),
                line=dict(
                    width=4 if year == latest_year else 2,
                    color=colors.get(int(year), "#999999")
                ),
                marker=dict(size=6),
                opacity=1 if year == latest_year else 0.6  # fade older years
            ))

        fig.update_layout(
            template="simple_white",
            title=f"{commodity_name} {data_type} by History",
            xaxis_title="Weeks",
            yaxis_title="Volume (kg)" if data_type == "Volume" else "Price",
            hovermode="x unified",
            height=500,
            legend=dict(
                orientation="h",
                y=-0.2
            ),
            xaxis=dict(
                tickmode="linear",
                dtick=2
            )
        )

        st.plotly_chart(fig, use_container_width=True)

        # GPT
        st.subheader(" Market Insight")
        insight = analyze_with_gpt(df, period, data_type)
        st.write(insight)