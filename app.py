import streamlit as st
import requests
import pandas as pd
import altair as alt

# Konfigurasi halaman
st.set_page_config(page_title="Analisis TikTok", layout="wide")

# --- Ambil daftar username dari endpoint ---
@st.cache_data
def get_usernames():
    url = "https://karyawan.berlcosmetics.com/api/getsocialmedia"
    res = requests.get(url)
    res.raise_for_status()
    data = res.json()
    # Filter hanya TikTok & yang tidak terhapus
    usernames = [d["username"] for d in data if d["platform"] == "tiktok" and d["isdelete"] == 0]
    return usernames

usernames = get_usernames()

# Input select
author = st.selectbox("Pilih Username TikTok:", usernames, index=0 if usernames else None)

# --- Load data TikTok dari API ---
@st.cache_data
def load_data(author: str):
    url = f"http://31.97.107.27:5000/api/tiktok/konten?author={author}"
    res = requests.get(url)
    res.raise_for_status()
    data = res.json()["data"]
    df = pd.DataFrame(data)

    # Konversi waktu posting
    df["createTimeISO"] = pd.to_datetime(df["createTimeISO"])
    df["hour"] = df["createTimeISO"].dt.hour
    df["day"] = df["createTimeISO"].dt.day_name()

    # Engagement rate (% likes per views)
    df["engagement_rate"] = (df["likeCount"] / df["playCount"]).fillna(0) * 100

    return df

if author:
    try:
        df = load_data(author)

        st.title(f"📊 Analisis Data TikTok: {author}")

        with st.expander("📄 Lihat Data Sample"):
            st.dataframe(df.head(200))

        # ================== ANALISIS & CHARTS ==================
        # 1. Rata-rata Views per Hari
        st.subheader("📊 Rata-rata Views per Hari")
        bar_day = (
            alt.Chart(df)
            .mark_bar()
            .encode(
                x=alt.X("day:N", sort=["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]),
                y="mean(playCount):Q",
                tooltip=["day", "mean(playCount)"]
            )
            .properties(height=400)
        )
        st.altair_chart(bar_day, use_container_width=True)

        # 2. Scatter Plot Views vs Likes
        st.subheader("🔘 Scatter Plot: Views vs Likes")
        scatter = (
            alt.Chart(df)
            .mark_circle(size=100, opacity=0.6)
            .encode(
                x="playCount:Q",
                y="likeCount:Q",
                color="day:N",
                tooltip=["createTimeISO", "playCount", "likeCount", "commentCount", "shareCount", "engagement_rate"]
            )
            .properties(height=400)
            .interactive()
        )
        st.altair_chart(scatter, use_container_width=True)

        # 3. Heatmap: rata-rata views per hari & jam
        st.subheader("🌡️ Heatmap: Rata-rata Views per Hari & Jam")
        heatmap_df = (
            df.groupby(["day", "hour"])["playCount"]
            .mean()
            .reset_index()
        )
        day_order = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
        heatmap_df["day"] = pd.Categorical(heatmap_df["day"], categories=day_order, ordered=True)
            
        heatmap = (
            alt.Chart(heatmap_df)
            .mark_rect()
            .encode(
                x=alt.X("hour:O", title="Jam"),
                y=alt.Y("day:O", title="Hari"),
                color=alt.Color("playCount:Q", scale=alt.Scale(scheme="greenblue")),
                tooltip=["day", "hour", "playCount"]
            )
            .properties(height=400)
        )
        st.altair_chart(heatmap, use_container_width=True)

        # 4. Rata-rata views per jam
        st.subheader("⏰ Rata-rata Views berdasarkan Jam Posting")
        bar_hour = (
            alt.Chart(df)
            .mark_bar()
            .encode(
                x="hour:O",
                y="mean(playCount):Q",
                tooltip=["hour", "mean(playCount)"]
            )
            .properties(height=400)
        )
        st.altair_chart(bar_hour, use_container_width=True)

        # 5. Engagement Rate per Hari
        st.subheader("📌 Engagement Rate Rata-rata per Hari")
        eng_rate_day = (
            df.groupby("day")["engagement_rate"]
            .mean()
            .reset_index()
        )
        eng_rate_day["day"] = pd.Categorical(eng_rate_day["day"], categories=day_order, ordered=True)

        chart_eng_rate_day = (
            alt.Chart(eng_rate_day)
            .mark_bar()
            .encode(
                x=alt.X("day:N", sort=day_order, title="Hari"),
                y=alt.Y("engagement_rate:Q", title="Engagement Rate (%)"),
                color=alt.Color("engagement_rate:Q", scale=alt.Scale(scheme="redyellowgreen")),
                tooltip=["day", "engagement_rate"]
            )
            .properties(height=400)
        )
        st.altair_chart(chart_eng_rate_day, use_container_width=True)

        # 6. Engagement Rate per Jam
        st.subheader("⏰ Engagement Rate Rata-rata berdasarkan Jam Posting")
        eng_rate_hour = (
            df.groupby("hour")["engagement_rate"]
            .mean()
            .reset_index()
        )

        chart_eng_rate_hour = (
            alt.Chart(eng_rate_hour)
            .mark_bar()
            .encode(
                x=alt.X("hour:O", title="Jam"),
                y=alt.Y("engagement_rate:Q", title="Engagement Rate (%)"),
                color=alt.Color("engagement_rate:Q", scale=alt.Scale(scheme="redyellowgreen")),
                tooltip=["hour", "engagement_rate"]
            )
            .properties(height=400)
        )
        st.altair_chart(chart_eng_rate_hour, use_container_width=True)

        # ================== ANALISIS TEKS ==================
        st.subheader("📑 Analisis Data")

        # Korelasi views vs likes
        correlation = df["playCount"].corr(df["likeCount"])
        st.write(f"🔗 **Korelasi antara Views dan Likes:** {correlation:.2f}")

        # Engagement rate per hari (tabel)
        st.write("🔥 **Rata-rata Engagement Rate per Hari (%):**")
        st.dataframe(eng_rate_day.sort_values("engagement_rate", ascending=False))

        # Outlier detection sederhana
        high_views = df[df["playCount"] > df["playCount"].quantile(0.9)]
        if not high_views.empty:
            st.write("🚀 **Konten dengan Views tinggi (Top 10%):**")
            st.dataframe(high_views[["createTimeISO", "playCount", "likeCount", "engagement_rate", "webVideoUrl"]])

        low_eng = df[df["engagement_rate"] < df["engagement_rate"].quantile(0.1)]
        if not low_eng.empty:
            st.write("⚠️ **Konten dengan Engagement Rendah (Bottom 10%):**")
            st.dataframe(low_eng[["createTimeISO", "playCount", "likeCount", "engagement_rate", "webVideoUrl"]])

    except Exception as e:
        st.error(f"Gagal load data untuk author '{author}': {e}")
