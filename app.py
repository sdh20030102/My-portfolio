import streamlit as st
import FinanceDataReader as fdr
import yfinance as yf
import pandas as pd
import plotly.express as px
import requests
from bs4 import BeautifulSoup

# 페이지 설정
st.set_page_config(page_title="내 자산 현황", layout="wide")
st.title("🚀 Market Map & My Portfolio")

# ---------------------------------------------------------
# ▼▼ 1. 내 원금 설정 (알려주신 금액으로 고정!) ▼▼
# ---------------------------------------------------------
# 172,883,881 - 9,085,734 = 163,798,147원
FIXED_PRINCIPAL = 172883881 - 9085734 

# ---------------------------------------------------------
# ▼▼ 2. 포트폴리오 종목 설정 ▼▼
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
        '0154F0', # ✅ WON 초대형IB
        '033780', '105560', '066570', '298040',
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
    # 원금을 직접 지정했으므로 개별 매수단가는 계산에서 제외 (0 처리)
    '매수단가': [0] * 24
}

# 🇰🇷 한국 주식 (네이버 메타 태그 크롤링)
def get_naver_data(code):
    try:
        url = f"https://finance.naver.com/item/main.naver?code={code}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 메타 태그에서 등락률 바로 가져오기 (정확도 UP)
        meta_desc = soup.find("meta", property="og:description")
        if meta_desc:
            content = meta_desc["content"]
            parts = content.split(",") 
            if len(parts) >= 3:
                current_price = int(parts[0].replace('원', '').replace(',', '').strip())
                rate_str = parts[2].strip().replace('%', '')
                current_rate = float(rate_str)
                return current_price, current_rate
        
        # 실패시 백업
        price_area = soup.select_one('.no_today .blind')
        current_price = int(price_area.text.replace(',', '').strip())
        return current_price, 0
    except:
        return 0, 0

# 🇺🇸 미국 주식 (야후)
def get_yahoo_data(code, exchange_rate):
    try:
        ticker = yf.Ticker(code)
        data = ticker.history(period="5d")
        if len(data) >= 2:
            current_price = data['Close'].iloc[-1] * exchange_rate
            prev_close = data['Close'].iloc[-2] * exchange_rate
            rate = ((current_price - prev_close) / prev_close) * 100
            return current_price, rate
        elif len(data) == 1:
             current_price = data['Close'].iloc[-1] * exchange_rate
             return current_price, 0
        return 0, 0
    except:
        return 0, 0

def load_data():
    df = pd.DataFrame(my_portfolio)
    current_prices = []
    daily_rates = []
    exchange_rate = 1460 # 환율

    progress_bar = st.progress(0)
    total = len(df)

    for i, raw_code in enumerate(df['종목코드']):
        code = str(raw_code).upper().strip()
        
        # 한국 주식
        if code[0].isdigit():
            curr, rate = get_naver_data(code)
            if curr == 0: # 백업
                try:
                    data = fdr.DataReader(code)
                    curr = data['Close'].iloc[-1]
                    prev = data['Close'].iloc[-2] if len(data) > 1 else curr
                    rate = ((curr - prev) / prev) * 100
                except:
                    curr, rate = 0, 0
        
        # 미국 주식
        else:
            curr, rate = get_yahoo_data(code, exchange_rate)

        current_prices.append(curr)
        daily_rates.append(rate)
        progress_bar.progress((i + 1) / total)

    progress_bar.empty()

    df['현재가'] = current_prices
    df['오늘등락률(%)'] = daily_rates
    
    # 평가금액 (현재 내 주식 가치)
    df['평가금액'] = df['현재가'] * df['수량']
    
    # 오늘 하루 변동폭 (원)
    df['오늘등락폭'] = df['평가금액'] - (df['평가금액'] / (1 + df['오늘등락률(%)']/100))

    return df

if st.button('⚡ 새로고침'):
    st.cache_data.clear()
    st.rerun()

try:
    df_result = load_data()

    # 색상 함수
    def format_color(val, type='percent'):
        color = '#00CC00' if val > 0 else '#FF3333' if val < 0 else 'white'
        if type == 'percent':
            return f"<span style='color:{color}; font-weight:bold'>{val:+.2f}%</span>"
        else:
            return f"<span style='color:{color}'>({val:+,.0f})</span>"

    df_result['HTML_등락률'] = df_result['오늘등락률(%)'].apply(lambda x: format_color(x, 'percent'))
    df_result['1주당등락폭'] = df_result['오늘등락폭'] / df_result['수량']
    df_result['HTML_등락폭'] = df_result['1주당등락폭'].apply(lambda x: format_color(x, 'value'))

    # 1. 트리맵: [오늘 시장 분위기] 보여줌 (등락률 기준)
    fig = px.treemap(
        df_result,
        path=['섹터', '종목명'],
        values='평가금액', 
        color='오늘등락률(%)', 
        color_continuous_scale=['#FF3333', '#262626', '#00CC00'], 
        color_continuous_midpoint=0,
        range_color=[-3, 3],
        height=900
    )
    
    fig.data[0].customdata = df_result[['HTML_등락률', '현재가', 'HTML_등락폭']]
    fig.data[0].texttemplate = (
        "<b><span style='font-size:24px'>%{label}</span></b><br><br>" +
        "<span style='font-size:18px'>%{customdata[0]}</span><br>" + 
        "<span style='font-size:16px'>₩%{customdata[1]:,.0f}</span><br>" + 
        "<span style='font-size:14px'>%{customdata[2]}</span>"
    )
    fig.update_layout(font=dict(family="Arial", size=14), margin=dict(t=20, l=10, r=10, b=10))
    st.plotly_chart(fig, use_container_width=True)

    # ---------------------------------------------------------
    # ▼▼ 2. 하단: [고정 원금 대비 수익률] ▼▼
    # ---------------------------------------------------------
    st.markdown("---")
    
    # 계산 로직: 현재 총 자산 - 고정 원금 = 총 수익금
    current_total_asset = df_result['평가금액'].sum()
    total_profit = current_total_asset - FIXED_PRINCIPAL
    total_return_rate = (total_profit / FIXED_PRINCIPAL) * 100
    
    # 색상 결정
    total_color = "#00CC00" if total_profit >= 0 else "#FF3333"
    sign = "+" if total_profit >= 0 else ""

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("설정된 원금", f"{FIXED_PRINCIPAL:,.0f} 원")
    with c2:
        st.metric("현재 총 자산", f"{current_total_asset:,.0f} 원")
    with c3:
        # 여기가 고정 원금 대비 수익률입니다!
        st.markdown(f"""
            <div style="background-color: #1E1E1E; padding: 15px; border-radius: 10px; border: 2px solid {total_color}; text-align:center;">
                <p style="margin:0; font-size:16px; color:#AAAAAA;">총 수익률 (원금 대비)</p>
                <p style="margin:5px 0 0 0; font-size:32px; font-weight:bold; color:{total_color};">
                    {sign}{total_return_rate:.2f}%
                </p>
                <p style="margin:0; font-size:14px; color:{total_color};">
                    ({sign}{total_profit:,.0f}원)
                </p>
            </div>
        """, unsafe_allow_html=True)

    with st.expander("📊 상세 등락표 보기"):
        st.dataframe(df_result[['종목명', '현재가', '오늘등락률(%)', '평가금액']].style.format({
            '현재가': '₩{:,.0f}',
            '오늘등락률(%)': '{:+.2f}%',
            '평가금액': '₩{:,.0f}'
        }))

except Exception as e:
    st.error(f"오류: {e}")
