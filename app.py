import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from bs4 import BeautifulSoup
import yfinance as yf

# ---------------------------------------------------------
# 1. 페이지 설정
# ---------------------------------------------------------
st.set_page_config(page_title="My Stock Map", layout="wide")
st.title("🚀 내 주식 현황판 (Final Clean Ver.)")

# 고정 원금
FIXED_PRINCIPAL = 163798147 

# 내 포트폴리오
my_portfolio = {
    '섹터': ['반도체/IT', '반도체/IT', '방산/기계', '금융지주', '방산/기계', '자동차/소비재', '자동차/소비재', '방산/기계', '금융지주', '전력/인프라', '금융지주', '자동차/소비재', '금융지주', '가전/IT', '전력/인프라', '조선/중공업', '금융지주', '미국 빅테크', '미국 지수ETF', '미국 지수ETF', '미국 전기차', '미국 금융', '미국 빅테크', '미국 반도체'],
    '종목명': ['삼성전자', 'SK하이닉스', 'LIG넥스원', '하나금융지주', '현대로템', '현대차', '오리온', '한화', 'LG', 'TIGER AI전력기기', 'WON 초대형IB', 'KT&G', 'KB금융', 'LG전자', '효성중공업', 'HD현대중공업', 'KODEX 주주환원', 'Alphabet C', 'Invesco QQQ', 'TQQQ', 'Tesla', 'Berkshire B', 'Zeta Global', 'Qualcomm'],
    '종목코드': ['005930', '000660', '079550', '086790', '064350', '005380', '271560', '000880', '003550', '0117V0', '0154F0', '033780', '105560', '066570', '298040', '329180', '0153K0', 'GOOG', 'QQQ', 'TQQQ', 'TSLA', 'BRK-B', 'ZETA', 'QCOM'],
    '수량': [151, 12, 39, 114, 20, 27, 32, 24, 90, 500, 1100, 80, 21, 25, 2, 17, 800, 17, 2, 3, 4, 2, 58, 4]
}

# ---------------------------------------------------------
# 2. 데이터 가져오기 (무조건 가져오는 로직)
# ---------------------------------------------------------
def get_real_data(code):
    try:
        # [한국 주식] 코드가 숫자로 시작하면 네이버 직접 접속
        if code[0].isdigit():
            url = f"https://finance.naver.com/item/main.naver?code={code}"
            headers = {'User-Agent': 'Mozilla/5.0'}
            res = requests.get(url, headers=headers, timeout=2)
            soup = BeautifulSoup(res.text, 'html.parser')
            
            # 현재가 찾기
            curr_tag = soup.select_one('.no_today .blind')
            if not curr_tag: return 0, 0
            curr = int(curr_tag.text.replace(',', ''))
            
            # 전일 종가 찾기 (등락률 계산용)
            prev_tag = soup.select_one('.no_exday .blind')
            if prev_tag:
                prev = int(prev_tag.text.replace(',', ''))
                rate = ((curr - prev) / prev) * 100
            else:
                rate = 0
            
            return curr, rate
            
        # [미국 주식] 야후 파이낸스
        else:
            t = yf.Ticker(code)
            h = t.history(period="2d")
            if len(h) < 2: return 0, 0 # 데이터 없으면 0
            
            curr = h['Close'].iloc[-1]
            prev = h['Close'].iloc[-2]
            rate = ((curr - prev) / prev) * 100
            
            return curr * 1460, rate # 환율 1460원 적용
    except:
        return 0, 0

# ---------------------------------------------------------
# 3. 데이터프레임 생성
# ---------------------------------------------------------
if st.button('⚡ 데이터 새로고침'):
    st.cache_data.clear()

@st.cache_data
def make_data():
    df = pd.DataFrame(my_portfolio)
    prices = []
    rates = []
    
    # 로딩 바
    bar = st.progress(0)
    for i, code in enumerate(df['종목코드']):
        p, r = get_real_data(code)
        prices.append(p)
        rates.append(r)
        bar.progress((i+1)/len(df))
    bar.empty()
    
    df['현재가'] = prices
    df['등락률'] = rates # 여기엔 무조건 숫자만 들어감 (글자X)
    df['평가금액'] = df['현재가'] * df['수량']
    return df

df = make_data()

# ---------------------------------------------------------
# 4. 지도 그리기 (RGB 버그 완벽 수정)
# ---------------------------------------------------------
# 색상은 숫자에 따라 자동으로 칠해집니다.
fig = px.treemap(
    df,
    path=['섹터', '종목명'],
    values='평가금액',
    color='등락률', 
    color_continuous_scale=['#FF3333', '#222222', '#00CC00'], # 빨강 -> 검정 -> 초록
    range_color=[-3, 3] # -3% ~ +3% 기준
)

# [중요] 글자 디자인 직접 지정 (여기가 핵심!)
# customdata[0] = 현재가
# customdata[1] = 등락률
fig.data[0].customdata = df[['현재가', '등락률']]
fig.data[0].texttemplate = (
    "<b><span style='font-size:30px; color:white'>%{label}</span></b><br><br>" +
    "<b><span style='font-size:24px; color:white'>%{customdata[1]:+.2f}%</span></b><br>" +
    "<span style='font-size:16px; color:#CCCCCC'>₩%{customdata[0]:,.0f}</span>"
)
fig.update_layout(margin=dict(t=0, l=0, r=0, b=0))

st.plotly_chart(fig, use_container_width=True, height=800)

# ---------------------------------------------------------
# 5. 하단 요약 (원금/현재/누적)
# ---------------------------------------------------------
st.markdown("---")

total_asset = df['평가금액'].sum()
profit = total_asset - FIXED_PRINCIPAL
profit_rate = (profit / FIXED_PRINCIPAL) * 100
color = "#00CC00" if profit > 0 else "#FF3333"

c1, c2, c3 = st.columns(3)
c1.metric("💰 투자 원금", f"{FIXED_PRINCIPAL:,.0f} 원")
c2.metric("📊 현재 총 자산", f"{total_asset:,.0f} 원", delta=f"{profit:+,.0f} 원", delta_color="off")
c3.markdown(f"""
    <div style="text-align:center; padding:10px; border:2px solid {color}; border-radius:10px; background-color:#1E1E1E;">
        <span style="color:#AAA; font-size:14px;">누적 상승률</span><br>
        <span style="color:{color}; font-size:28px; font-weight:bold;">{profit_rate:+.2f}%</span>
    </div>
""", unsafe_allow_html=True)

