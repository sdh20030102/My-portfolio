import streamlit as st
import FinanceDataReader as fdr
import yfinance as yf
import pandas as pd
import plotly.express as px
import requests
from bs4 import BeautifulSoup

st.set_page_config(page_title="내 주식 현황판", layout="wide")
st.title("🚀 내 포트폴리오 (Real-time Hybrid)")

# ---------------------------------------------------------
# ▼▼ 내 포트폴리오 설정 ▼▼
# ---------------------------------------------------------
my_portfolio = {
    '섹터': [
        '반도체/IT', '반도체/IT', '방산/기계', '금융지주', '방산/기계', 
        '자동차/소비재', '자동차/소비재', '방산/기계', '금융지주', '전력/인프라', 
        '금융지주', '자동차/소비재', '금융지주', '가전/IT', '전력/인프라', 
        '조선/중공업', '금융지주',
        '미국 빅테크', '미국 지수ETF', '미국 지수ETF', '미국 전기차', 
        '미국 금융', '미국 빅테크', '미국 반도체'
    ],
    '종목명': [
        '삼성전자', 'SK하이닉스', 'LIG넥스원', '하나금융지주', '현대로템', 
        '현대차', '오리온', '한화', 'LG', 'TIGER AI전력기기', 
        'WON 초대형IB', 'KT&G', 'KB금융', 'LG전자', '효성중공업', 
        'HD현대중공업', 'KODEX 주주환원',
        'Alphabet C', 'Invesco QQQ', 'TQQQ', 'Tesla', 
        'Berkshire B', 'Zeta Global', 'Qualcomm'
    ],
    '종목코드': [
        '005930', '000660', '079550', '086790', '064350', 
        '005380', '271560', '000880', '003550', '0117V0', 
        '453470', '033780', '105560', '066570', '298040', 
        '329180', '0153K0',
        'GOOG', 'QQQ', 'TQQQ', 'TSLA', 
        'BRK-B', 'ZETA', 'QCOM'
    ],
    '수량': [
        151, 12, 39, 114, 20, 
        27, 32, 24, 90, 500,
        1100, 80, 21, 25, 2,
        17, 800,
        17, 2, 3, 4, 
        2, 58, 4
    ],
    '매수단가': [
        117639, 736000, 523833, 98789, 196918, 
        388518, 115500, 125000, 88428, 14450, 
        10350, 147500, 132605, 106700, 2208000, 
        615235, 10430,
        287.55, 624.58, 54.50, 466.97, 
        493.98, 23.52, 182.39
    ]
}

# 🇰🇷 한국 주식 크롤링 함수 (네이버 금융 직접 접속)
def get_naver_price(code):
    try:
        url = f"https://finance.naver.com/item/main.naver?code={code}"
        headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'}
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 'no_today' 클래스가 현재가입니다.
        price_text = soup.select_one('.no_today .blind').text
        return int(price_text.replace(',', ''))
    except:
        return 0

@st.cache_data
def load_data():
    df = pd.DataFrame(my_portfolio)
    current_prices = []
    exchange_rate = 1450 

    # 진행 상황바 표시 (크롤링이라 약간 시간 걸림)
    progress_bar = st.progress(0)
    total_stocks = len(df)

    for i, code in enumerate(df['종목코드']):
        try:
            # 1. 한국 주식 (숫자로 시작) -> 네이버 직접 크롤링!
            if str(code)[0].isdigit():
                price = get_naver_price(code)
                # 크롤링 실패 시 백업으로 FDR 사용
                if price == 0:
                    stock_data = fdr.DataReader(code)
                    if not stock_data.empty:
                        price = stock_data['Close'].iloc[-1]
            
            # 2. 미국 주식 (영어로 시작) -> yfinance 프리장/애프터장
            else:
                ticker = yf.Ticker(code)
                data = ticker.history(period="1d", prepost=True)
                if not data.empty:
                    price = data['Close'].iloc[-1] * exchange_rate
                else:
                    price = 0

            current_prices.append(price)
            
        except Exception as e:
            current_prices.append(0)
        
        # 진행률 업데이트
        progress_bar.progress((i + 1) / total_stocks)
    
    progress_bar.empty() # 로딩 끝나면 바 숨기기
    
    df['현재가'] = current_prices
    
    # 계산 로직
    df['계산용_현재가'] = df.apply(lambda x: x['매수단가'] if x['현재가'] == 0 else x['현재가'], axis=1)
    df['평가금액'] = df['계산용_현재가'] * df['수량']
    
    df['매수단가_원화'] = df.apply(
        lambda x: x['매수단가'] * exchange_rate if (not str(x['종목코드'])[0].isdigit()) else x['매수단가'], 
        axis=1
    )
    
    df['수익률(%)'] = ((df['계산용_현재가'] - df['매수단가_원화']) / df['매수단가_원화']) * 100
    
    return df

if st.button('🔄 시세 새로고침 (네이버/야후 연동)'):
    st.cache_data.clear()

try:
    df_result = load_data()
    
    total_asset = df_result['평가금액'].sum()
    st.metric(label="💰 총 자산 현황", value=f"{total_asset:,.0f} 원")

    fig = px.treemap(
        df_result, 
        path=['섹터', '종목명'], 
        values='평가금액', 
        color='수익률(%)',
        color_continuous_scale=['#FF0000', '#F0F2F6', '#00FF00'],
        color_continuous_midpoint=0,
        range_color=[-3, 3],
        height=900
    )

    # 지도에 가격 표시
    fig.data[0].customdata = df_result[['수익률(%)', '현재가']]
    fig.data[0].texttemplate = "<b>%{label}</b><br>%{customdata[0]:.2f}%<br>₩%{customdata[1]:,.0f}"
    
    fig.update_layout(font=dict(size=16))
    st.plotly_chart(fig, use_container_width=True)
    
    with st.expander("📊 상세 표 보기"):
        st.dataframe(df_result)
        
except Exception as e:
    st.error(f"오류: {e}")
