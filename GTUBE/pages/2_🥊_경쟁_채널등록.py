import streamlit as st
import pandas as pd
import os
import re
import urllib.parse
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv

# 🔐 API 키 로드
load_dotenv()
API_KEY = os.getenv("YOUTUBE_API_KEY")

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data")
EXCEL_FILE = os.path.join(DATA_PATH, "competitor_channels.xlsx")

st.header("🥊 경쟁 채널 등록/관리")

# 초기 파일 구성
if not os.path.exists(DATA_PATH):
    os.makedirs(DATA_PATH)

if not os.path.exists(EXCEL_FILE):
    pd.DataFrame(columns=["channel_name", "channel_url", "channel_id"]).to_excel(EXCEL_FILE, index=False, engine="openpyxl")
else:
    df_check = pd.read_excel(EXCEL_FILE)
    if not all(col in df_check.columns for col in ["channel_name", "channel_url", "channel_id"]):
        pd.DataFrame(columns=["channel_name", "channel_url", "channel_id"]).to_excel(EXCEL_FILE, index=False, engine="openpyxl")

# API
def get_youtube_service():
    try:
        return build("youtube", "v3", developerKey=API_KEY)
    except Exception as e:
        st.error("YouTube API 초기화 실패")
        return None

def get_channel_info(youtube, handle_or_url):
    try:
        decoded_url = urllib.parse.unquote(handle_or_url)
        if "@" not in decoded_url:
            return None, None, None
        match = re.search(r"@([\w\\-_%]+)", decoded_url)
        if not match:
            return None, None, None
        handle = match.group(1)
        res = youtube.search().list(part="snippet", q=f"@{handle}", type="channel", maxResults=1).execute()
        items = res.get("items", [])
        if not items:
            return None, None, None
        item = items[0]
        channel_id = item.get("id", {}).get("channelId")
        channel_name = item.get("snippet", {}).get("title")
        channel_url = f"https://www.youtube.com/@{handle}"
        return channel_name.strip(), channel_url.strip(), channel_id.strip()
    except:
        return None, None, None

youtube = get_youtube_service()

# 세션 상태 초기화
if "run_after_add_2" not in st.session_state:
    st.session_state.run_after_add_2 = False
if "run_after_delete_2" not in st.session_state:
    st.session_state.run_after_delete_2 = False
if "duplicates_2" not in st.session_state:
    st.session_state.duplicates_2 = []
if "failures_2" not in st.session_state:
    st.session_state.failures_2 = []

st.subheader("➕ 경쟁 채널 추가 (여러 개 입력 가능)")
example = """https://www.youtube.com/@competitor1
https://www.youtube.com/@competitor2"""
urls_input = st.text_area("채널 URL 목록 (한 줄에 하나씩)", height=150, placeholder=example)

if st.button("채널 등록하기"):
    new_data = []
    duplicates = []
    failures = []
    lines = [line.strip() for line in urls_input.split("\n") if line.strip()]
    df = pd.read_excel(EXCEL_FILE)
    for url in lines:
        name, url_fixed, cid = get_channel_info(youtube, url)
        if not name or not cid:
            failures.append(url)
        elif cid in df['channel_id'].values:
            duplicates.append(url)
        else:
            new_data.append([name, url_fixed, cid])
    if new_data:
        df_new = pd.DataFrame(new_data, columns=["channel_name", "channel_url", "channel_id"])
        df = pd.concat([df, df_new], ignore_index=True)
        df.to_excel(EXCEL_FILE, index=False, engine="openpyxl")
        st.session_state.run_after_add_2 = True
    st.session_state.duplicates_2 = duplicates
    st.session_state.failures_2 = failures
    st.rerun()

# 등록 결과 메시지
if st.session_state.run_after_add_2:
    st.success("✅ 채널이 성공적으로 추가되었습니다.")
    if st.session_state.duplicates_2:
        st.info(f"이미 등록된 채널 {len(st.session_state.duplicates_2)}개:")
        st.code("\n".join(st.session_state.duplicates_2))
    if st.session_state.failures_2:
        st.warning(f"등록되지 않은 채널 {len(st.session_state.failures_2)}개:")
        st.code("\n".join(st.session_state.failures_2))
    st.session_state.run_after_add_2 = False

# 등록된 목록 표시 및 삭제
st.subheader("📋 등록된 경쟁 채널 목록")
df = pd.read_excel(EXCEL_FILE)
if df.empty:
    st.info("아직 등록된 채널이 없습니다.")
else:
    for i, row in df.iterrows():
        col1, col2, col3, col4 = st.columns([4, 6, 6, 1])
        col1.markdown(f"**{row['channel_name']}**")
        col2.markdown(f"[채널 링크]({row['channel_url']})")
        col3.code(row['channel_id'], language="text")
        if col4.button("삭제", key=f"del_{i}"):
            df.drop(index=i, inplace=True)
            df.reset_index(drop=True, inplace=True)
            df.to_excel(EXCEL_FILE, index=False, engine="openpyxl")
            st.session_state.run_after_delete_2 = True
            st.rerun()

if st.session_state.run_after_delete_2:
    st.success("🗑️ 채널이 성공적으로 삭제되었습니다.")
    st.session_state.run_after_delete_2 = False
