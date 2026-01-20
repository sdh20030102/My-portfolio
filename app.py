import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from bs4 import BeautifulSoup
import yfinance as yf

# 1. 설정 및 고정 데이터
st.set_page_config(page_title="My Portfolio", layout="wide")
st.title("🚀 오늘의 국장 & 미국 마켓맵")

# 고정 원금 (총 수익률 계산용)
FIXED_PRINCIPAL = 163798147 

my_portfolio = {
    '섹터': ['반도체/IT', '반도체/IT', '방산/기계', '금융지주', '방산/기계', '자동차/소비재', '자동차/소비재', '방산/기계', '금융지주', '전력/인프라', '금융지주', '자동차/소비재', '금융지주', '가전/IT', '전력/인프라', '조선/중공업', '금융지주', '미국 빅테크', '미국 지수ETF', '미국 지수ETF', '미국 전기차', '미국 금융', '미국 빅테크', '미국 반도체'],
    '종목명': ['삼성전자', 'SK하이닉스', 'LIG넥스원', '하나금융지주', '현대로템', '현대차', '오리온', '한화', 'LG', 'TIGER AI전력기기', 'WON 초대형IB', 'KT&G', 'KB금융', 'LG전자', '효성중공업', 'HD현대중공업', 'KODEX 주주환원', 'Alphabet C', 'Invesco QQQ', 'TQQQ', 'Tesla', 'Berkshire B', 'Zeta Global', 'Qualcomm'],
    '종목코드': ['005930', '000660', '079550', '086790', '064350', '005380', '271560', '000880', '003550', '0117V0', '0154F0', '033780', '105560', '066570', '298040', '329180', '0153K0', 'GOOG', 'QQQ', 'TQQQ', 'TSLA', 'BRK-B', 'ZETA', 'QCOM'],
    '수량': [151, 12, 39, 114, 20, 27, 32, 24, 90, 500, 1100, 80, 21, 25, 2, 17, 800, 17, 2, 3, 4, 2, 58, 4],
    '매수단가': [117639, 736000, 523833, 98789, 196918, 388518, 115500, 125000, 88428, 14450, 10350, 147500, 132605, 106700, 2208000, 615235, 10430, 287.55, 624.58, 54.50, 466.97, 493.98, 23.52, 182.39]
}

# 2. 데이터 수집 함수 (한국/미국 통합)
def fetch_data(code):
    try:
        # 한국 주식 (숫자로 시작)
        if code[0].isdigit():
            url = f"https://finance.naver.com/item/main.naver?code={code}"
            headers = {'User-Agent': 'Mozilla/5.0'}
            res = requests.get(url, headers=headers)
            soup = BeautifulSoup(res.text, 'html.parser')
            
            # 현재가와 전일비 가져오기
            price = int(soup.select_one('.no_today .blind').text.replace(',', ''))
            prev_price_text = soup.select_one('.no_exday .blind').text.replace(',', '')
            # 상승/하락 기호 처리 (+/-)
            diff = int(prev_price_text)
            ico = soup.select_one('.no_exday .ico')
            if ico and '하락' in ico.text:
                diff = -diff
                
            rate = (diff / (price - diff)) * 100
            return price, rate
        
        # 미국 주식
        else:
            t = yf.Ticker(code)
            h = t.history(period="2d")
            price = h['Close'].iloc[-1] * 1460 # 환율 적용
            rate = ((h['Close'].iloc[-1] - h['Close'].iloc[-2]) / h['Close'].iloc[-2]) * 100
            return price, rate
    except:
        return 0, 0

# 3. 메인 로직
if st.button("⚡ 새로고침"):
    st.cache_data.clear()

@st.cache_data
def get_processed_df():
    df = pd.DataFrame(my_portfolio)
    p_list, r_list = [], []
    bar = st.progress(0)
    for i, code in enumerate(df['종목코드']):
        p, r = fetch_data(code)
        p_list.append(p)
        r_list.append(r)
        bar.progress((i+1)/len(df))
    bar.empty()
    
    df['현재가'] = p_list
    df['오늘등락률'] = r_list
    df['평가금액'] = df['현재가'] * df['수량']
    # 누적 수익률 계산
    df['매수단가_KRW'] = df.apply(lambda x: x['매수단가']*1460 if not str(x['종목코드'])[0].isdigit() else x['매수단가'], axis=1)
    df['누적수익률'] = ((df['현재가'] - df['매수단가_KRW']) / df['매수단가_KRW']) * 100
    return df

df = get_processed_df()

# 4. 마켓맵 그리기
fig = px.treemap(
    df, path=['섹터', '종목명'], values='평가금액', color='오늘등락률',
    color_continuous_scale=['#FF3333', '#222222', '#00CC00'], range_color=[-3, 3], height=800
)

# 글씨 무조건 흰색 설정
fig.data[0].texttemplate = (
    "<b><span style='font-size:22px; color:white'>%{label}</span></b><br>" +
    "<span style='font-size:18px; color:white'>%{color:+.2f}%</span><br>" +
    "<span style='font-size:14px; color:white'>₩%{value:,.0f}</span>"
)
fig.update_layout(margin=dict(t=10, l=10, r=10, b=10))
st.plotly_chart(fig, use_container_width=True)

# 5. 하단 데이터 (요청하신 대로 유지)
st.markdown("---")
total_val = df['평가금액'].sum()
total_profit_rate = ((total_val - FIXED_PRINCIPAL) / FIXED_PRINCIPAL) * 100
st.subheader(f"💰 총 수익률(원금대비): {total_profit_rate:+.2f}%")

with st.expander("📊 상세 데이터 보기"):
    st.dataframe(df[['종목명', '현재가', '평가금액', '누적수익률']].style.format({'현재가':'₩{:,.0f}', '평가금액':'₩{:,.0f}', '누적수익률':'{:+.2f}%'}))
