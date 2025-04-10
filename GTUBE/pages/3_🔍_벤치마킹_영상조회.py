import streamlit as st
import pandas as pd
import os
import time
import re
import io
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from googleapiclient.discovery import build
from dotenv import load_dotenv

st.set_page_config(layout="wide")
st.title("🔍 벤치마킹 채널 쇼츠 영상 조회")

load_dotenv()
API_KEY = st.secrets["YOUTUBE_API_KEY"]
youtube_api = build("youtube", "v3", developerKey=API_KEY)

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data")
EXCEL_FILE = os.path.join(DATA_PATH, "benchmark_channels.xlsx")

def get_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

def get_shorts_video_ids(channel_handle):
    shorts_url = f"https://www.youtube.com/@{channel_handle}/shorts"
    driver = get_driver()
    driver.get(shorts_url)
    time.sleep(2)
    last_height = driver.execute_script("return document.documentElement.scrollHeight")
    for _ in range(2):
        driver.execute_script("window.scrollTo(0, document.documentElement.scrollHeight);")
        time.sleep(2)
        new_height = driver.execute_script("return document.documentElement.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height
    elements = driver.find_elements(By.XPATH, '//a[contains(@href, "/shorts/")]')
    video_ids = list({el.get_attribute("href").split("/shorts/")[-1] for el in elements if "/shorts/" in el.get_attribute("href")})
    driver.quit()
    return video_ids

def get_video_details(video_ids):
    results = []
    for i in range(0, len(video_ids), 50):
        batch = video_ids[i:i+50]
        res = youtube_api.videos().list(part="snippet,statistics", id=",".join(batch)).execute()
        for item in res.get("items", []):
            stats = item.get("statistics", {})
            snippet = item.get("snippet", {})
            results.append({
                "title": snippet.get("title"),
                "video_id": item["id"],
                "channel_title": snippet.get("channelTitle"),
                "published_at": snippet.get("publishedAt"),
                "view_count": int(stats.get("viewCount", 0)),
                "url": f"https://www.youtube.com/shorts/{item['id']}"
            })
    return results

st.sidebar.header("🔧 필터 설정")
max_results = st.sidebar.slider("각 채널당 최대 영상 수", 1, 20, 5)
min_views = st.sidebar.slider("최소 조회수 (만)", 1, 100, 5)

# ✅ 조회된 결과를 세션에 유지
if "df_result" not in st.session_state:
    st.session_state.df_result = None

if st.button("벤치마킹 채널 쇼츠 영상 수집하기"):
    df = pd.read_excel(EXCEL_FILE)
    all_results = []
    for _, row in df.iterrows():
        channel_url = row["channel_url"]
        handle_match = re.search(r"@[\w\\-]+", channel_url)
        if not handle_match:
            continue
        channel_handle = handle_match.group().replace("@", "")
        st.write(f"📺 채널: {channel_handle} - 쇼츠 영상 조회 중...")
        try:
            shorts_ids = get_shorts_video_ids(channel_handle)
            videos = get_video_details(shorts_ids)
            df_channel = pd.DataFrame(videos)
            if df_channel.empty:
                continue
            df_channel["published_at"] = pd.to_datetime(df_channel["published_at"], errors="coerce")
            df_channel["published_at"] = df_channel["published_at"].dt.tz_localize(None)
            df_channel = df_channel.sort_values(by="published_at", ascending=False).head(max_results)
            df_channel = df_channel[df_channel["view_count"] >= min_views * 10000]
            if not df_channel.empty:
                all_results.append(df_channel)
        except Exception as e:
            st.error(f"❌ {channel_handle} 처리 실패: {e}")

    if all_results:
        df_result = pd.concat(all_results, ignore_index=True)
        df_result["published_at"] = df_result["published_at"].dt.strftime("%Y-%m-%d %H:%M:%S")  # ✅ 엑셀용 포맷
        st.session_state.df_result = df_result
        st.success(f"✅ 총 {len(df_result)}개 쇼츠 영상 수집 완료!")

# ✅ 이전 결과가 남아 있다면 보여주기
if st.session_state.df_result is not None:
    st.dataframe(st.session_state.df_result, use_container_width=True)
    buffer = io.BytesIO()
    st.session_state.df_result.to_excel(buffer, index=False, engine="openpyxl")
    buffer.seek(0)
    st.download_button(
        "📥 결과 엑셀 다운로드",
        data=buffer,
        file_name="shorts_results.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
