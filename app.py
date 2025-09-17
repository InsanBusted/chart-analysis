import streamlit as st
import requests
import pandas as pd
import altair as alt
import locale

st.set_page_config(page_title="Analisis TikTok", layout="wide")

# --- Atur locale ke Bahasa Indonesia ---
try:
    locale.setlocale(locale.LC_TIME, "id_ID.UTF-8")
except:
    locale.setlocale(locale.LC_TIME, "")

# --- Ambil daftar username dari endpoint ---
@st.cache_data
def get_usernames():
    url = "https://karyawan.berlcosmetics.com/api/getsocialmedia"
    res = requests.get(url)
    res.raise_for_status()
    data = res.json()
    usernames = [d["username"] for d in data if d["platform"] == "tiktok" and d["isdelete"] == 0]
    return usernames

usernames = get_usernames()

# --- Pilih cara input ---
mode = st.radio("Pilih sumber username:", ["Dari API", "Input Manual"])

if mode == "Dari API":
    author = st.multiselect(
        "Cari atau pilih Username TikTok:",
        usernames,
        default=usernames[0] if usernames else None,
        max_selections=1
    )
    author = author[0] if author else None
else:
    author = st.text_input("Masukkan Username TikTok manual:")

st.write("👉 Username yang dipakai:", author)

# --- Load data TikTok dari API ---
@st.cache_data
def load_data(author: str):
    url = f"https://api.ratcs.my.id:5000/api/tiktok/konten?author={author}"
    res = requests.get(url)
    res.raise_for_status()
    data = res.json()["data"]
    df = pd.DataFrame(data)

    # Konversi waktu posting → UTC aware
    df["createTimeISO"] = pd.to_datetime(df["createTimeISO"], utc=True)
    df["hour"] = df["createTimeISO"].dt.hour
    df["day"] = df["createTimeISO"].dt.strftime("%A")

    # Engagement rate (% likes per views)
    df["engagement_rate"] = (df["likeCount"] / df["playCount"]).fillna(0) * 100
    return df

if author:
    try:
        df = load_data(author)

        st.title(f"📊 Analisis Data TikTok: {author}")

        with st.expander("📄 Lihat Data Sample"):
            st.dataframe(df.head(200))

        # --- Filter rentang waktu ---
        st.sidebar.header("🔎 Filter Data")
        range_option = st.sidebar.selectbox(
            "Pilih Rentang Waktu",
            ["Semua Data", "1 Minggu", "2 Minggu", "1 Bulan", "3 Bulan"],
            index=0
        )

        today = df["createTimeISO"].max()

        def get_start_date(option, today):
            if option == "1 Minggu":
                return today - pd.Timedelta(weeks=1)
            elif option == "2 Minggu":
                return today - pd.Timedelta(weeks=2)
            elif option == "1 Bulan":
                return today - pd.DateOffset(months=1)
            elif option == "3 Bulan":
                return today - pd.DateOffset(months=3)
            return df["createTimeISO"].min()

        start_date = pd.to_datetime(get_start_date(range_option, today), utc=True)
        df_filtered = df[df["createTimeISO"] >= start_date]

        st.success(f"📅 Data difilter dari **{start_date.date()}** sampai **{today.date()}**")

        # ================== ANALISIS & CHARTS ==================
        day_order = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]

        # 1. Rata-rata Views per Hari
        if st.checkbox("Tampilkan 📊 Rata-rata Views per Hari", value=True):
            st.subheader("📊 Rata-rata Views per Hari")
            bar_day = (
                alt.Chart(df_filtered)
                .mark_bar()
                .encode(
                    x=alt.X("day:N", sort=day_order, title="Hari"),
                    y=alt.Y("mean(playCount):Q", title="Rata-rata Views"),
                    tooltip=["day", "mean(playCount)"]
                )
                .properties(height=400)
            )
            st.altair_chart(bar_day, use_container_width=True)

        # 2. Scatter Plot Views vs Likes
        if st.checkbox("Tampilkan 🔘 Scatter Plot: Views vs Likes", value=True):
            st.subheader("🔘 Scatter Plot: Views vs Likes")
            scatter = (
                alt.Chart(df_filtered)
                .mark_circle(size=70, opacity=0.6)
                .encode(
                    x=alt.X("playCount:Q", title="Jumlah Views"),
                    y=alt.Y("likeCount:Q", title="Jumlah Likes"),
                    color=alt.Color("day:N", title="Hari"),
                    tooltip=[
                        "createTimeISO",
                        "playCount",
                        "likeCount",
                        "commentCount",
                        "shareCount",
                        "engagement_rate"
                    ],
                    href="webVideoUrl:N"
                )
                .properties(height=400)
                .interactive()
            )
            st.altair_chart(scatter, use_container_width=True)

        # 3. Heatmap
        if st.checkbox("Tampilkan 🌡️ Heatmap: Views per Hari & Jam", value=True):
            st.subheader("🌡️ Heatmap: Rata-rata Views per Hari & Jam")
            heatmap_df = df_filtered.groupby(["day", "hour"])["playCount"].mean().reset_index()
            heatmap_df["day"] = pd.Categorical(heatmap_df["day"], categories=day_order, ordered=True)

            heatmap = (
                alt.Chart(heatmap_df)
                .mark_rect()
                .encode(
                    x=alt.X("hour:O", title="Jam"),
                    y=alt.Y("day:O", title="Hari"),
                    color=alt.Color("playCount:Q", scale=alt.Scale(scheme="greenblue"), title="Rata-rata Views"),
                    tooltip=["day", "hour", "playCount"]
                )
                .properties(height=400)
            )
            st.altair_chart(heatmap, use_container_width=True)

        # 4. Rata-rata Views per Jam
        if st.checkbox("Tampilkan ⏰ Rata-rata Views per Jam", value=True):
            st.subheader("⏰ Rata-rata Views berdasarkan Jam Posting")
            bar_hour = (
                alt.Chart(df_filtered)
                .mark_bar()
                .encode(
                    x=alt.X("hour:O", title="Jam"),
                    y=alt.Y("mean(playCount):Q", title="Rata-rata Views"),
                    tooltip=["hour", "mean(playCount)"]
                )
                .properties(height=400)
            )
            st.altair_chart(bar_hour, use_container_width=True)

        # 5. Engagement Rate per Hari
        if st.checkbox("Tampilkan 📌 Engagement Rate per Hari", value=True):
            st.subheader("📌 Engagement Rate Rata-rata per Hari")
            eng_rate_day = df_filtered.groupby("day")["engagement_rate"].mean().reset_index()
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
        if st.checkbox("Tampilkan ⏰ Engagement Rate per Jam", value=True):
            st.subheader("⏰ Engagement Rate Rata-rata berdasarkan Jam Posting")
            eng_rate_hour = df_filtered.groupby("hour")["engagement_rate"].mean().reset_index()

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

    except Exception as e:
        st.error(f"Gagal memuat data untuk username '{author}': {e}")
