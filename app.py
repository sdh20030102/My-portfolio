import streamlit as st
import FinanceDataReader as fdr
import pandas as pd
import plotly.express as px

# 1. 페이지 설정 (앱 타이틀 등)
st.set_page_config(page_title="내 주식 현황판", layout="wide")

st.title("🚀 내 포트폴리오 실시간 맵")

# 2. 내 포트폴리오 데이터 (수정 가능)
my_portfolio = {
    '종목명': ['삼성전자', 'SK하이닉스', 'NAVER', '카카오', '현대차'],
    '종목코드': ['005930', '000660', '035420', '035720', '005380'],
    '수량': [100, 50, 30, 200, 40],
    '매수단가': [70000, 120000, 200000, 50000, 180000] 
}

# 데이터 로딩 함수 (캐싱을 사용하여 속도 향상)
@st.cache_data
def load_data():
    df = pd.DataFrame(my_portfolio)
    current_prices = []
    
    for code in df['종목코드']:
        stock_data = fdr.DataReader(code)
        current_price = stock_data['Close'].iloc[-1]
        current_prices.append(current_price)
    
    df['현재가'] = current_prices
    df['평가금액'] = df['현재가'] * df['수량']
    df['수익률(%)'] = ((df['현재가'] - df['매수단가']) / df['매수단가']) * 100
    return df

# 새로고침 버튼
if st.button('🔄 시세 새로고침'):
    st.cache_data.clear()

# 데이터 불러오기
try:
    df_result = load_data()

    # 3. 트리맵 그리기
    fig = px.treemap(
        df_result, 
        path=['종목명'], 
        values='평가금액',
        color='수익률(%)',
        color_continuous_scale=['#FF4B4B', '#F0F2F6', '#00CC96'], # 빨강(손실) -> 회색 -> 초록(이익)
        color_continuous_midpoint=0
    )
    
    fig.data[0].textinfo = 'label+text+value'
    fig.data[0].texttemplate = "%{label}<br>%{customdata[0]:.2f}%"
    fig.data[0].customdata = df_result[['수익률(%)']]

    # 차트 출력
    st.plotly_chart(fig, use_container_width=True)

    # 표로도 보여주기
    st.dataframe(df_result[['종목명', '현재가', '수익률(%)', '평가금액']])

except Exception as e:
    st.error(f"데이터를 불러오는 중 오류가 발생했습니다: {e}")
