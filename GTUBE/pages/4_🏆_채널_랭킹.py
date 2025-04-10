import streamlit as st
import pandas as pd
import os
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from datetime import datetime, timedelta
from dotenv import load_dotenv

st.set_page_config(layout="wide")
st.title("🏆 경쟁 채널 랭킹 분석")

# 🔐 .env에서 API 키 로드
load_dotenv()
API_KEY = st.secrets["YOUTUBE_API_KEY"]

# 파일 경로 상수
COMPETITOR_FILE = "data/competitor_channels.xlsx"
CACHE_FILE = "data/channel_ranking_cache.xlsx"

# 유튜브 API 클라이언트 생성
def get_youtube_service():
    try:
        return build("youtube", "v3", developerKey=API_KEY)
    except Exception as e:
        st.error("YouTube API 초기화 실패")
        return None

# 랭킹 계산
def run_ranking():
    youtube = get_youtube_service()
    if not youtube:
        return None

    if not os.path.exists(COMPETITOR_FILE):
        st.warning("경쟁 채널이 등록되어 있지 않습니다.")
        return None

    df = pd.read_excel(COMPETITOR_FILE)
    results = []

    for _, row in df.iterrows():
        channel_id = row["channel_id"]
        channel_name = row["channel_name"]
        try:
            res = youtube.channels().list(part="statistics", id=channel_id).execute()
            stats = res["items"][0]["statistics"]
            subs = int(stats.get("subscriberCount", 0))
            vids = int(stats.get("videoCount", 0))

            res = youtube.search().list(part="snippet", channelId=channel_id, order="date", maxResults=50).execute()
            views_sum, count = 0, 0
            for item in res["items"]:
                vid_id = item["id"].get("videoId")
                if not vid_id:
                    continue
                publish_date = item["snippet"]["publishedAt"]
                if "T" in publish_date:
                    publish_date = datetime.strptime(publish_date, "%Y-%m-%dT%H:%M:%SZ")
                else:
                    continue
                if publish_date < datetime.utcnow() - timedelta(days=30):
                    continue
                vstats = youtube.videos().list(part="statistics", id=vid_id).execute()
                v = vstats["items"][0]["statistics"]
                views_sum += int(v.get("viewCount", 0))
                count += 1

            avg_daily = int(views_sum / 30) if count else 0
            est_revenue = avg_daily * 30 * 0.2

            results.append({
                "채널명": channel_name,
                "구독자 수": subs,
                "동영상 수": vids,
                "일일평균조회수": avg_daily,
                "월 예상수익": est_revenue,
                "채널링크": f"https://www.youtube.com/channel/{channel_id}"
            })
        except:
            continue

    df_result = pd.DataFrame(results)
    df_result = df_result.sort_values(by="월 예상수익", ascending=False).reset_index(drop=True)
    return df_result


# 캐시 로드
if os.path.exists(CACHE_FILE):
    df_cached = pd.read_excel(CACHE_FILE)
    st.subheader("📊 최근 저장된 랭킹 데이터")
    st.dataframe(df_cached)
else:
    st.warning("아직 저장된 랭킹 데이터가 없습니다. 먼저 수동 갱신을 해주세요.")

# 수동 새로고침
if st.button("📄 수동으로 랭킹 새로고침"):
    with st.spinner("데이터 수집 중..."):
        df = run_ranking()
        if df is not None:
            df.to_excel(CACHE_FILE, index=False)
            st.success("랭킹 갱신 완료!")
            st.dataframe(df)
