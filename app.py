import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from bs4 import BeautifulSoup
import yfinance as yf
import re

# ---------------------------------------------------------
# 1. 설정 (Configuration)
# ---------------------------------------------------------
st.set_page_config(page_title="My Portfolio", layout="wide")
st.title("🚀 My Portfolio Dashboard (Clean Ver.)")

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
# 2. 데이터 수집기 (Core Logic)
# ---------------------------------------------------------

# 🇰🇷 한국 주식: 네이버 금융 "직접 파싱" (가장 확실한 방법)
def fetch_kr_stock(code):
    try:
        # 영문/숫자 혼용 코드(0154F0 등)도 URL에 그대로 넣으면 네이버가 인식합니다.
        url = f"https://finance.naver.com/item/main.naver?code={code}"
        headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=2)
        
        if response.status_code != 200:
            return 0, 0
            
        soup = BeautifulSoup(response.text, 'html.parser')

        # 1. 현재가 찾기 (네이버 공통 클래스)
        price_tag = soup.select_one('.no_today .blind')
        if not price_tag:
            return 0, 0
        current_price = int(price_tag.text.replace(',', ''))

        # 2. 전일 종가 찾아서 등락률 계산
        prev_tag = soup.select_one('.no_exday .blind')
        if prev_tag:
            prev_price = int(prev_tag.text.replace(',', ''))
            if prev_price > 0:
                change_rate = ((current_price - prev_price) / prev_price) * 100
            else:
                change_rate = 0.0
        else:
            change_rate = 0.0

        return current_price, change_rate
    except Exception:
        # 에러 발생 시 0 반환 (멈춤 방지)
        return 0, 0

# 🇺🇸 미국 주식: 야후 파이낸스
def fetch_us_stock(code, exchange_rate=1460):
    try:
        # GOOG 등도 yfinance가 잘 처리합니다.
        ticker = yf.Ticker(code)
        
        # fast_info가 최신 데이터를 가장 잘 가져옴
        curr = ticker.fast_info.last_price
        prev = ticker.fast_info.previous_close
        
        # 데이터가 없는 경우(장 시작 전 등) 히스토리로 백업
        if curr is None:
            hist = ticker.history(period="2d")
            if not hist.empty:
                curr = hist['Close'].iloc[-1]
                prev = hist['Close'].iloc[-2] if len(hist) > 1 else curr
            else:
                return 0, 0
                
        # 환율 적용
        curr_krw = curr * exchange_rate
        
        # 등락률 계산
        rate = ((curr - prev) / prev) * 100 if prev > 0 else 0
        
        return curr_krw, rate
    except Exception:
        return 0, 0

@st.cache_data(ttl=60) # 60초마다 데이터 갱신
def get_all_data():
    df = pd.DataFrame(my_portfolio)
    prices = []
    rates = []
    
    # 진행 상황 표시
    progress = st.progress(0)
    total_items = len(df)
    
    for i, row in df.iterrows():
        code = str(row['종목코드']).strip()
        
        # 숫자로 시작하면 한국 주식 (0154F0도 0으로 시작하므로 포함됨)
        if code[0].isdigit():
            p, r = fetch_kr_stock(code)
        # 그 외(영문)는 미국 주식
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
    
    # 0으로 나누기 방지 및 누적수익률 계산
    df['누적수익률'] = df.apply(lambda x: ((x['평가금액'] - x['투자원금']) / x['투자원금'] * 100) if x['투자원금'] > 0 else 0, axis=1)

    return df

# ---------------------------------------------------------
# 3. 화면 그리기 (UI)
# ---------------------------------------------------------

if st.button("⚡ 새로고침 (Refresh)"):
    st.cache_data.clear()
    st.rerun()

# 데이터 로드
try:
    df = get_all_data()
except Exception as e:
    st.error(f"데이터를 불러오는 중 오류가 발생했습니다: {e}")
    st.stop()

# HTML 포맷팅 함수 (무조건 흰색 글씨 고정)
def fmt_white(val, is_percent=True):
    if is_percent:
        return f"<span style='color:white; font-weight:bold'>{val:+.2f}%</span>"
    return f"<span style='color:white'>({val:+,.0f})</span>"

# 데이터프레임에 HTML 컬럼 추가
df['HTML_등락률'] = df['등락률'].apply(lambda x: fmt_white(x, True))
df['1주당등락폭'] = df.apply(lambda x: x['등락폭']/x['수량'] if x['수량']>0 else 0, axis=1)
df['HTML_등락폭'] = df['1주당등락폭'].apply(lambda x: fmt_white(x, False))

# 1. 국장 마켓맵 (트리맵)
# 미국주식마켓앱 로직은 건들지 말라고 하셨지만, 하나의 맵에 통합된 형태라 그대로 유지하되 로직만 깔끔하게 했습니다.
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
    "<b><span style='font-size:24px; color:white'>%{label}</span></b><br><br>" +
    "<span style='font-size:18px'>%{customdata[0]}</span><br>" + # 하얀색 등락률
    "<span style='font-size:16px; color:white'>₩%{customdata[1]:,.0f}</span><br>" + 
    "<span style='font-size:14px'>%{customdata[2]}</span>" # 하얀색 등락폭
)
fig.update_layout(margin=dict(t=10, l=10, r=10, b=10), font=dict(family="Arial"))

st.plotly_chart(fig, use_container_width=True)

# 2. 총 수익률 (건들지 않음 - 고정 원금 기준)
st.markdown("---")
cur_asset = df['평가금액'].sum()
profit = cur_asset - FIXED_PRINCIPAL
profit_rate = (profit / FIXED_PRINCIPAL) * 100
color = "#00CC00" if profit >= 0 else "#FF3333"

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

# 3. 상세 데이터 (건들지 않음 - 요청하신 항목만)
with st.expander("📊 상세 데이터 보기 (클릭)"):
    display_cols = ['종목명', '현재가', '평가금액', '누적수익률']
    st.dataframe(
        df[display_cols].style.format({
            '현재가': '₩{:,.0f}',
            '평가금액': '₩{:,.0f}',
            '누적수익률': '{:+.2f}%'
        })
    )


