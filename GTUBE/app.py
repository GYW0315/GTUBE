# app.py - GTUBE 대시보드 진입점
import streamlit as st
from datetime import datetime

st.set_page_config(
    page_title="GTUBE 벤치마킹 시스템",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("📊 GTUBE 벤치마킹/분석 시스템")
st.markdown("""
이 대시보드는 다음과 같은 기능을 제공합니다:

1. 📌 **벤치마킹 채널 등록/관리**
2. 🥊 **경쟁 채널 등록/관리**
3. 🔍 **벤치마킹 채널 영상 조회 및 필터링 분석**
4. 🏆 **채널 랭킹 및 예상 수익 계산** (자동 + 수동 업데이트 지원)

좌측 사이드바에서 원하는 기능 페이지를 선택해주세요.
""")

st.info(f"현재 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
