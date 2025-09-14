import streamlit as st
import requests
import pandas as pd
import altair as alt

st.set_page_config(layout="wide", page_title="Chart Only")

# Ambil data
url = "http://31.97.107.27:5000/api/tiktok/konten?author=fitozlimofficial"
res = requests.get(url)
data = res.json()["data"]
df = pd.DataFrame(data)
df["createTimeISO"] = pd.to_datetime(df["createTimeISO"])
df = df.sort_values("createTimeISO")

# Chart tunggal (misalnya Views)
chart_views = (
    alt.Chart(df)
    .mark_line(point=True)
    .encode(
        x="createTimeISO:T",
        y="playCount:Q",
        tooltip=["createTimeISO", "playCount", "likeCount", "commentCount"]
    )
    .interactive()
)

st.altair_chart(chart_views, use_container_width=True)
