import streamlit as st
import requests

st.title("K-Beauty HS Code 판정기 💄")

# 가이드북에 있는 주요 카테고리 리스트 (예시)
categories = ["기초화장품(에센스,로션)", "메이크업용 제품", "두발용 제품(샴푸)", "목욕용 제품", "면도용 제품"]
choice = st.selectbox("화장품 종류를 선택하세요:", categories)

if st.button("HS 코드 및 근거 조회"):
    with st.spinner("가이드북 분석 중..."):
        # Django API 호출
        res = requests.post("http://127.0.0.1:8000/api/match/", json={"product_name": choice})
        
        if res.status_code == 200:
            data = res.json()
            st.success(f"'{choice}'에 대한 판정 결과입니다.")
            st.info(data['analysis']) # 결과값 출력
        else:
            st.error("데이터를 가져오지 못했습니다.")