# src/dashboard/app.py
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
from datetime import datetime, timedelta
import os

st.set_page_config(
    page_title="GridGuard Energy AI",
    page_icon="⚡",
    layout="wide"
)

st.title("⚡ GridGuard Energy AI")
st.subheader("Climate-Adaptive Energy Intelligence for Kenyan Mini-Grids")

# Load data
@st.cache_data
def load_data():
    # Load villages
    with open("data/villages.json", "r") as f:
        data = json.load(f)
        villages = data["villages"]
    
    # Load latest risk scores
    risk_files = [f for f in os.listdir('data/processed') if f.startswith('risk_scores_') and f.endswith('.parquet')]
    if risk_files:
        latest = sorted(risk_files)[-1]
        risk_df = pd.read_parquet(f'data/processed/{latest}')
        return villages, risk_df
    return villages, None

villages, risk_df = load_data()

if risk_df is None:
    st.error("No risk data found! Please run the risk engine first.")
    st.stop()

# Sidebar filters
st.sidebar.header("Filters")
village_names = risk_df['village_name'].unique()
selected_village = st.sidebar.selectbox("Select Village", village_names)

# Date range
min_date = risk_df['timestamp'].min()
max_date = risk_df['timestamp'].max()
date_range = st.sidebar.date_input(
    "Date Range",
    [min_date, max_date],
    min_value=min_date,
    max_value=max_date
)

# Filter data
filtered_df = risk_df[risk_df['village_name'] == selected_village]
filtered_df = filtered_df[
    (filtered_df['timestamp'] >= pd.to_datetime(date_range[0])) &
    (filtered_df['timestamp'] <= pd.to_datetime(date_range[1]))
]

# Layout
col1, col2, col3, col4 = st.columns(4)

# Current metrics
current = filtered_df.iloc[-1] if not filtered_df.empty else None

if current is not None:
    with col1:
        st.metric("Current Risk", f"{current['risk_score']:.1f}%")
    with col2:
        st.metric("Battery Level", f"{current['battery_level']*100:.1f}%")
    with col3:
        st.metric("Consumption", f"{current['consumption_kw']:.1f} kW")
    with col4:
        recommendation_color = "🟢" if current['risk_score'] <= 50 else "🟡" if current['risk_score'] <= 70 else "🔴"
        st.metric("Recommendation", f"{recommendation_color} {current['recommendation']}")

# Main charts
st.subheader(f"📈 Risk Trends - {selected_village}")

# Risk score over time
fig1 = px.line(
    filtered_df,
    x='timestamp',
    y='risk_score',
    title='Risk Score Over Time',
    color_discrete_sequence=['#FF6B6B']
)
fig1.add_hline(y=50, line_dash="dash", line_color="orange", annotation_text="YELLOW (Prepare Diesel)")
fig1.add_hline(y=70, line_dash="dash", line_color="red", annotation_text="RED (Switch to Diesel!)")
st.plotly_chart(fig1, use_container_width=True)

# Multi-metric chart
col1, col2 = st.columns(2)

with col1:
    st.subheader("☀️ Solar Radiation")
    fig2 = px.line(
        filtered_df,
        x='timestamp',
        y='shortwave_radiation',
        title='Solar Radiation (W/m²)',
        color_discrete_sequence=['#FFD93D']
    )
    st.plotly_chart(fig2, use_container_width=True)

with col2:
    st.subheader("🔋 Battery & Consumption")
    fig3 = go.Figure()
    fig3.add_trace(go.Scatter(
        x=filtered_df['timestamp'],
        y=filtered_df['battery_level'] * 100,
        name='Battery Level (%)',
        line=dict(color='#6BCB77')
    ))
    fig3.add_trace(go.Scatter(
        x=filtered_df['timestamp'],
        y=filtered_df['consumption_kw'],
        name='Consumption (kW)',
        line=dict(color='#4D96FF')
    ))
    fig3.update_layout(title='Battery Level vs Consumption')
    st.plotly_chart(fig3, use_container_width=True)

# Risk heatmap for all villages
st.subheader("🌍 Risk Heatmap - All Villages")

# Get latest risk for each village
latest_risk = risk_df.groupby('village_name').last().reset_index()
fig4 = px.bar(
    latest_risk,
    x='village_name',
    y='risk_score',
    color='risk_score',
    color_continuous_scale=['green', 'yellow', 'red'],
    title='Current Risk by Village',
    labels={'risk_score': 'Risk Score (%)', 'village_name': ''}
)
st.plotly_chart(fig4, use_container_width=True)

# Recommendations table
st.subheader("📋 Recent Recommendations")
recent = filtered_df.tail(20)[['timestamp', 'risk_score', 'battery_level', 'consumption_kw', 'recommendation']]
recent['timestamp'] = recent['timestamp'].dt.strftime('%Y-%m-%d %H:%M')
st.dataframe(recent, use_container_width=True)

# Export
st.sidebar.subheader("Export Data")
if st.sidebar.button("Download Risk Data (CSV)"):
    csv = filtered_df.to_csv(index=False)
    st.sidebar.download_button(
        label="Download CSV",
        data=csv,
        file_name=f"gridguard_risk_{selected_village}_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv"
    )

st.sidebar.info(
    """
    **Legend:**
    - 🟢 GREEN: Stay on Solar
    - 🟡 YELLOW: Prepare Diesel
    - 🔴 RED: Switch to Diesel NOW!
    """
)

st.sidebar.caption("Built by mbuguakevvz | GridGuard Energy AI")