import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from bs4 import BeautifulSoup
import yfinance as yf
import time

# ---------------------------------------------------------
# 1. 설정 (Configuration)
# ---------------------------------------------------------
st.set_page_config(page_title="My Portfolio", layout="wide")
st.title("🚀 My Portfolio Dashboard")

# 고정 원금 (사용자 설정)
FIXED_PRINCIPAL = 163798147 

# 포트폴리오 데이터
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
        '0154F0', '033780', '105560', '066570', '298040',
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
    # 누적 수익률 계산을 위한 매수단가
    '매수단가': [
        117639, 736000, 523833, 98789, 196918,
        388518, 115500, 125000, 88428, 14450,
        10350, 147500, 132605, 106700, 2208000,
        615235, 10430,
        287.55, 624.58, 54.50, 466.97,
        493.98, 23.52, 182.39
    ]
}

# ---------------------------------------------------------
# 2. 데이터 수집기 (Data Fetcher) - 핵심 엔진
# ---------------------------------------------------------

# 🇰🇷 한국 주식: 네이버 금융 "직접 파싱" (가장 강력함)
def fetch_kr_stock(code):
    try:
        url = f"https://finance.naver.com/item/main.naver?code={code}"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=3)
        soup = BeautifulSoup(response.text, 'html.parser')

        # 네이버 금융 페이지 구조상 'no_today' 클래스 안에 현재가가 있음
        # 1. 현재가 가져오기
        price_tag = soup.select_one('.no_today .blind')
        if not price_tag:
            return 0, 0
        current_price = int(price_tag.text.replace(',', ''))

        # 2. 전일 종가 가져오기 (등락률 계산용)
        prev_tag = soup.select_one('.no_exday .blind')
        if prev_tag:
            prev_price = int(prev_tag.text.replace(',', ''))
            change_rate = ((current_price - prev_price) / prev_price) * 100
        else:
            change_rate = 0.0

        return current_price, change_rate
    except:
        return 0, 0

# 🇺🇸 미국 주식: 야후 파이낸스
def fetch_us_stock(code, exchange_rate=1460):
    try:
        ticker = yf.Ticker(code)
        # fast_info가 최신 데이터를 가장 잘 가져옴
        curr = ticker.fast_info.last_price
        prev = ticker.fast_info.previous_close
        
        if curr is None: # 데이터가 비어있으면 0 처리
            return 0, 0
            
        # 환율 적용
        curr_krw = curr * exchange_rate
        prev_krw = prev * exchange_rate
        
        # 등락률 계산
        rate = ((curr - prev) / prev) * 100 if prev > 0 else 0
        
        return curr_krw, rate
    except:
        return 0, 0

@st.cache_data(ttl=60) # 60초마다 갱신
def get_all_data():
    df = pd.DataFrame(my_portfolio)
    prices = []
    rates = []
    
    # 진행률 바
    progress = st.progress(0)
    total_items = len(df)
    
    for i, row in df.iterrows():
        code = str(row['종목코드']).strip()
        
        # 한국 주식 (숫자로 시작)
        if code[0].isdigit():
            p, r = fetch_kr_stock(code)
        # 미국 주식
        else:
            p, r = fetch_us_stock(code)
            
        prices.append(p)
        rates.append(r)
        progress.progress((i + 1) / total_items)
        
    progress.empty()
    
    df['현재가'] = prices
    df['등락률'] = rates
    df['평가금액'] = df['현재가'] * df['수량']
    
    # 등락폭(원) 계산
    df['등락폭'] = df['평가금액'] - (df['평가금액'] / (1 + df['등락률']/100))
    
    # 누적 수익률 계산
    # 미국주식 매수단가 환율 적용
    df['매수단가_KRW'] = df.apply(lambda x: x['매수단가'] * 1460 if not str(x['종목코드'])[0].isdigit() else x['매수단가'], axis=1)
    df['투자원금'] = df['매수단가_KRW'] * df['수량']
    
    # 0으로 나누기 방지
    df['누적수익률'] = df.apply(lambda x: ((x['평가금액'] - x['투자원금']) / x['투자원금'] * 100) if x['투자원금'] > 0 else 0, axis=1)

    return df

# ---------------------------------------------------------
# 3. 화면 그리기 (UI Rendering)
# ---------------------------------------------------------

if st.button("⚡ 새로고침 (Refresh)"):
    st.cache_data.clear()
    st.rerun()

# 데이터 로드
df = get_all_data()

# HTML 포맷팅 함수 (글자색 흰색 고정)
def fmt_white(val, is_percent=True):
    if is_percent:
        return f"<span style='color:white; font-weight:bold'>{val:+.2f}%</span>"
    return f"<span style='color:white'>({val:+,.0f})</span>"

# 데이터프레임에 HTML 컬럼 추가
df['HTML_등락률'] = df['등락률'].apply(lambda x: fmt_white(x, True))
df['1주당등락폭'] = df.apply(lambda x: x['등락폭']/x['수량'] if x['수량']>0 else 0, axis=1)
df['HTML_등락폭'] = df['1주당등락폭'].apply(lambda x: fmt_white(x, False))

# 1. 트리맵 (Treemap)
fig = px.treemap(
    df,
    path=['섹터', '종목명'],
    values='평가금액',
    color='등락률',
    color_continuous_scale=['#FF3333', '#222222', '#00CC00'], # 빨강-검정-초록
    range_color=[-3, 3],
    height=800
)

# 텍스트 커스터마이징 (무조건 흰색)
fig.data[0].customdata = df[['HTML_등락률', '현재가', 'HTML_등락폭']]
fig.data[0].texttemplate = (
    "<b><span style='font-size:20px; color:white'>%{label}</span></b><br><br>" +
    "<span style='font-size:16px'>%{customdata[0]}</span><br>" +
    "<span style='font-size:14px; color:white'>₩%{customdata[1]:,.0f}</span><br>" +
    "<span style='font-size:12px'>%{customdata[2]}</span>"
)
fig.update_layout(margin=dict(t=10, l=10, r=10, b=10), font=dict(family="Arial"))

st.plotly_chart(fig, use_container_width=True)

# 2. 하단 수익률 박스 (고정 원금 대비)
st.markdown("---")
cur_asset = df['평가금액'].sum()
profit = cur_asset - FIXED_PRINCIPAL
profit_rate = (profit / FIXED_PRINCIPAL) * 100
color = "#00CC00" if profit >= 0 else "#FF3333" # 전체 수익률 색상

col1, col2, col3 = st.columns(3)
col1.metric("설정 원금", f"{FIXED_PRINCIPAL:,.0f} 원")
col2.metric("현재 자산", f"{cur_asset:,.0f} 원")
col3.markdown(f"""
    <div style="border: 2px solid {color}; border-radius: 10px; padding: 15px; text-align: center; background-color: #1E1E1E;">
        <span style="color: #AAAAAA; font-size: 14px;">총 수익률 (원금 대비)</span><br>
        <span style="color: {color}; font-size: 30px; font-weight: bold;">{profit_rate:+.2f}%</span><br>
        <span style="color: {color}; font-size: 16px;">({profit:+,.0f} 원)</span>
    </div>
""", unsafe_allow_html=True)

# 3. 상세 표 (요청하신 컬럼만)
with st.expander("📊 상세 데이터 보기 (클릭)"):
    display_cols = ['종목명', '현재가', '평가금액', '누적수익률']
    st.dataframe(
        df[display_cols].style.format({
            '현재가': '₩{:,.0f}',
            '평가금액': '₩{:,.0f}',
            '누적수익률': '{:+.2f}%'
        })
    )
