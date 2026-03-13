import streamlit as st
import requests
import pandas as pd
import plotly.express as px

# [1] 페이지 기본 설정
st.set_page_config(
    page_title="K-Beauty 시장 인텔리전스",
    page_icon="📊",
    layout="wide"
)

st.title("📊 K-Beauty 카테고리별 수출 분석 대시보드")
st.markdown("가이드북 기반 HS 코드 판정 및 미국·일본 시장의 최근 5개년 수출 추이를 분석합니다.")
st.markdown("---")

# [2] 카테고리 목록 정의 (백엔드 DB/가이드북과 매칭되는 핵심 키워드)
CATEGORY_LIST = [
    "기초화장품", 
    "마스크팩", 
    "메이크업", 
    "입술화장품", 
    "눈화장품", 
    "샴푸",
    "헤어케어",
    "매니큐어"
]

# [3] 사이드바 설정
with st.sidebar:
    st.header("🔍 분석 설정")
    # 기존 text_input을 selectbox로 교체
    selected_category = st.selectbox(
        "분석할 화장품 카테고리를 선택하세요",
        options=CATEGORY_LIST,
        index=0  # 기본값: 기초화장품
    )
    
    st.write("") # 간격 조절
    submit_btn = st.button("🚀 분석 및 데이터 수집 시작", use_container_width=True)
    
    st.divider()
    st.caption("💡 **Tip**: 동일 카테고리 재검색 시 DB에 저장된 데이터를 사용하여 매우 빠르게 로드됩니다.")

# [4] 메인 분석 로직
if submit_btn:
    with st.spinner(f'"{selected_category}"에 대한 AI 분석 및 실적 수집을 진행 중입니다...'):
        try:
            # 장고 API 호출 (POST 방식)
            # 백엔드 주소가 다르다면 포트 번호를 확인하세요.
            response = requests.post(
                "http://127.0.0.1:8000/api/match/", 
                json={"category": selected_category},
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # 상단 결과 카드 레이아웃
                st.success(f"✅ 분석 완료: {selected_category}")
                
                col_metric, col_info = st.columns([1, 3])
                with col_metric:
                    st.metric(label="판정 HS 코드", value=result['hs_code'])
                with col_info:
                    st.info(f"**분류 근거(AI/DB):** {result['reason']}")

                st.divider()

                # 데이터 가공 (Plotly 시각화용)
                market_data = result['stats']
                plot_list = []
                for country, years_data in market_data.items():
                    for d in years_data:
                        plot_list.append({
                            "연도": d['year'],
                            "수출액(USD)": d['amount'],
                            "수출중량(kg)": d['weight'],
                            "국가": "미국 (US)" if country == "US" else "일본 (JP)"
                        })
                
                df = pd.DataFrame(plot_list)

                if not df.empty:
                    # 그래프 및 테이블 출력
                    tab1, tab2 = st.tabs(["📈 수출 추이 그래프", "📋 상세 데이터 시트"])
                    
                    with tab1:
                        fig = px.line(
                            df, x="연도", y="수출액(USD)", color="국가", 
                            markers=True, text=None,
                            title=f"최근 5개년 {selected_category} 수출 실적 비교 (단위: $)",
                            labels={"수출액(USD)": "수출 금액 ($)"}
                        )
                        fig.update_layout(hovermode="x unified")
                        st.plotly_chart(fig, use_container_width=True)

                    with tab2:
                        st.subheader("연도별/국가별 상세 실적 (USD)")
                        pivot_df = df.pivot(index='연도', columns='국가', values='수출액(USD)')
                        st.dataframe(pivot_df, use_container_width=True)
                        
                        # 성장률 간이 계산 표시 (선택사항)
                        st.caption("※ 본 데이터는 관세청 무역통계 API(TRASS)로부터 실시간/DB 연동 수집된 수치입니다.")
                else:
                    st.warning("수집된 통계 데이터가 존재하지 않습니다.")
            
            else:
                st.error(f"서버 응답 오류 (상태 코드: {response.status_code})")
                st.json(response.json())

        except requests.exceptions.ConnectionError:
            st.error("❌ 장고(Django) 서버가 실행 중이 아닙니다. `python manage.py runserver`를 확인해 주세요.")
        except Exception as e:
            st.error(f"❌ 예상치 못한 오류 발생: {e}")

else:
    # 초기 진입 화면
    st.info("👈 왼쪽 사이드바에서 카테고리를 선택한 후 분석 버튼을 눌러주세요.")